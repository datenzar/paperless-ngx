from pathlib import Path
from typing import cast

import httpx
from django.conf import settings

from documents.parsers import ParseError
from paperless.config import OcrConfig
from paperless_tesseract.parsers import RasterisedDocumentParser


class RemoteEngineConfig:
    def __init__(
        self,
        engine: str,
        api_key: str | None = None,
        endpoint: str | None = None,
    ):
        self.engine = engine
        self.api_key = api_key
        self.endpoint = endpoint

    def engine_is_valid(self):
        return (
            self.engine in ["azureai", "ocrbridge-ocrmac"]
            and bool(self.api_key)
            and bool(self.endpoint)
        )


class RemoteDocumentParser(RasterisedDocumentParser):
    """
    This parser uses remote OCR engines to parse documents.

    Supported engines:
    - azureai
    - ocrbridge-ocrmac
    """

    logging_name = "paperless.parsing.remote"

    def get_settings(self) -> OcrConfig:
        """
        Returns the configuration for the remote OCR engine, loaded from Django settings.
        """
        return cast(
            "OcrConfig",
            RemoteEngineConfig(
                engine=settings.REMOTE_OCR_ENGINE,
                api_key=settings.REMOTE_OCR_API_KEY,
                endpoint=settings.REMOTE_OCR_ENDPOINT,
            ),
        )

    def supported_mime_types(self):
        if self.settings.engine_is_valid():
            return {
                "application/pdf": ".pdf",
                "image/png": ".png",
                "image/jpeg": ".jpg",
                "image/tiff": ".tiff",
                "image/bmp": ".bmp",
                "image/gif": ".gif",
                "image/webp": ".webp",
            }
        else:
            return {}

    def azure_ai_vision_parse(
        self,
        file: Path,
    ) -> str | None:
        """
        Uses Azure AI Vision to parse the document and return the text content.
        It requests a searchable PDF output with embedded text.
        The PDF is saved to the archive_path attribute.
        Returns the text content extracted from the document.
        If the parsing fails, it returns None.
        """
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
        from azure.ai.documentintelligence.models import AnalyzeOutputOption
        from azure.ai.documentintelligence.models import DocumentContentFormat
        from azure.core.credentials import AzureKeyCredential

        client = DocumentIntelligenceClient(
            endpoint=self.settings.endpoint,
            credential=AzureKeyCredential(self.settings.api_key),
        )

        try:
            with file.open("rb") as f:
                analyze_request = AnalyzeDocumentRequest(bytes_source=f.read())
                poller = client.begin_analyze_document(
                    model_id="prebuilt-read",
                    body=analyze_request,
                    output_content_format=DocumentContentFormat.TEXT,
                    output=[AnalyzeOutputOption.PDF],  # request searchable PDF output
                    content_type="application/json",
                )

            poller.wait()
            result_id = poller.details["operation_id"]
            result = poller.result()

            # Download the PDF with embedded text
            self.archive_path = self.tempdir / "archive.pdf"
            with self.archive_path.open("wb") as f:
                for chunk in client.get_analyze_result_pdf(
                    model_id="prebuilt-read",
                    result_id=result_id,
                ):
                    f.write(chunk)
            return result.content
        except Exception as e:
            self.log.error(f"Azure AI Vision parsing failed: {e}")
        finally:
            client.close()

        return None

    def ocrbridge_ocrmac_parse(
        self,
        file: Path,
        mime_type: str,
    ) -> str:
        endpoint = self.settings.endpoint.rstrip("/") + "/v2/ocr/ocrmac/process"

        try:
            with (
                file.open("rb") as f,
                httpx.Client(
                    timeout=settings.CELERY_TASK_TIME_LIMIT,
                ) as client,
            ):
                response = client.post(
                    endpoint,
                    headers={"X-API-Key": self.settings.api_key},
                    files={"file": (file.name, f, mime_type)},
                    data={"output_format": "pdf"},
                )
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    detail = None
                    error_code = None
                    try:
                        payload = e.response.json()
                        if isinstance(payload, dict):
                            detail = payload.get("detail")
                            error_code = payload.get("error_code")
                    except ValueError:
                        pass

                    message = f"OCRBridge OCRMac parsing failed: HTTP {e.response.status_code}"
                    if detail:
                        message += f" - {detail}"
                    if error_code:
                        message += f" (error_code: {error_code})"

                    self.log.error(message)
                    raise ParseError(message) from e

            content_type = response.headers.get("content-type", "").lower()
            if "application/pdf" not in content_type:
                message = (
                    "OCRBridge OCRMac parsing failed: expected PDF response, got "
                    f"{content_type or 'unknown content type'}"
                )
                self.log.error(message)
                raise ParseError(message)

            self.archive_path = self.tempdir / "archive.pdf"
            self.archive_path.write_bytes(response.content)

            sidecar_file = self.tempdir / "sidecar.txt"
            text = self.extract_text(sidecar_file, self.archive_path)
            if text is None:
                message = "OCRBridge OCRMac parsing failed: unable to extract text from PDF response"
                self.log.error(message)
                raise ParseError(message)

            return text
        except Exception as e:
            if isinstance(e, ParseError):
                raise

            message = f"OCRBridge OCRMac parsing failed: {e}"
            self.log.error(message)
            raise ParseError(message) from e

    def parse(self, document_path: Path, mime_type, file_name=None):
        if not self.settings.engine_is_valid():
            self.log.warning(
                "No valid remote parser engine is configured, content will be empty.",
            )
            self.text = ""
        elif self.settings.engine == "azureai":
            self.text = self.azure_ai_vision_parse(document_path)
        elif self.settings.engine == "ocrbridge-ocrmac":
            self.text = self.ocrbridge_ocrmac_parse(document_path, mime_type)
