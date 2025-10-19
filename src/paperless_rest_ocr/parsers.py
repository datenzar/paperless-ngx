import base64
import json
import re
import time
from pathlib import Path

import requests

from documents.parsers import DocumentParser
from documents.parsers import ParseError
from documents.parsers import make_thumbnail_from_pdf
from paperless.config import RestOcrConfig


class RestOcrDocumentParser(DocumentParser):
    """
    This parser uses a REST API service to perform OCR on documents.
    It supports various authentication methods and can handle PDFs and images.
    """

    logging_name = "paperless.parsing.rest_ocr"

    def get_settings(self) -> RestOcrConfig:
        """
        This parser uses the REST OCR configuration settings
        """
        return RestOcrConfig()

    def get_page_count(self, document_path, mime_type):
        """
        Get page count for PDF documents
        """
        page_count = None
        if mime_type == "application/pdf":
            try:
                import pikepdf

                with pikepdf.Pdf.open(document_path) as pdf:
                    page_count = len(pdf.pages)
            except Exception as e:
                self.log.warning(
                    f"Unable to determine PDF page count {document_path}: {e}",
                )
        return page_count

    def extract_metadata(self, document_path, mime_type):
        """
        Extract metadata from PDF documents
        """
        result = []
        if mime_type == "application/pdf":
            import pikepdf

            namespace_pattern = re.compile(r"\{(.*)\}(.*)")

            pdf = pikepdf.open(document_path)
            meta = pdf.open_metadata()
            for key, value in meta.items():
                if isinstance(value, list):
                    value = " ".join([str(e) for e in value])
                value = str(value)
                try:
                    m = namespace_pattern.match(key)
                    if m is None:
                        continue
                    namespace = m.group(1)
                    key_value = m.group(2)
                    try:
                        namespace.encode("utf-8")
                        key_value.encode("utf-8")
                    except UnicodeEncodeError as e:
                        self.log.debug(f"Skipping metadata key {key}: {e}")
                        continue
                    result.append(
                        {
                            "namespace": namespace,
                            "prefix": meta.REVERSE_NS[namespace],
                            "key": key_value,
                            "value": value,
                        },
                    )
                except Exception as e:
                    self.log.warning(
                        f"Error while reading metadata {key}: {value}. Error: {e}",
                    )
        return result

    def get_thumbnail(self, document_path, mime_type, file_name=None):
        """
        Generate thumbnail from the document
        """
        return make_thumbnail_from_pdf(
            self.archive_path or document_path,
            self.tempdir,
            self.logging_group,
        )

    def construct_request_payload(self, document_path: Path, mime_type: str) -> dict:
        """
        Construct the payload for the REST API request
        """
        # Read and encode the document
        with Path(document_path).open("rb") as f:
            document_bytes = f.read()
            document_b64 = base64.b64encode(document_bytes).decode("utf-8")

        payload = {
            "document": document_b64,
            "mime_type": mime_type,
            "language": self.settings.language,
            "options": {},
        }

        return payload

    def construct_request_headers(self) -> dict:
        """
        Construct HTTP headers for the REST API request including authentication
        """
        headers = {"Content-Type": "application/json"}

        # Add authentication based on method
        auth_method = self.settings.auth_method.lower()

        if auth_method == "bearer" and self.settings.auth_token:
            headers["Authorization"] = f"Bearer {self.settings.auth_token}"
        elif auth_method == "api_key" and self.settings.api_key:
            headers["X-API-Key"] = self.settings.api_key
        elif auth_method == "basic" and self.settings.api_key:
            # For basic auth, we'd need username:password
            # For now, we'll use the api_key as the username if available
            import base64 as b64

            credentials = f"{self.settings.api_key}:".encode()
            encoded = b64.b64encode(credentials).decode("utf-8")
            headers["Authorization"] = f"Basic {encoded}"

        # Add custom headers if configured
        if self.settings.custom_headers:
            headers.update(self.settings.custom_headers)

        return headers

    def extract_text_from_response(self, response_data: dict) -> str:
        """
        Extract text from the API response
        Supports multiple response formats
        """
        # Try different common response formats
        if "text" in response_data:
            return response_data["text"]
        elif "content" in response_data:
            return response_data["content"]
        elif "ocr_text" in response_data:
            return response_data["ocr_text"]
        elif "result" in response_data:
            result = response_data["result"]
            if isinstance(result, str):
                return result
            elif isinstance(result, dict) and "text" in result:
                return result["text"]

        raise ParseError(
            f"Could not extract text from REST OCR response. "
            f"Response keys: {list(response_data.keys())}",
        )

    def make_api_request(
        self,
        document_path: Path,
        mime_type: str,
        attempt: int = 1,
    ) -> dict:
        """
        Make the REST API request with retry logic
        """
        if not self.settings.api_endpoint:
            raise ParseError(
                "REST OCR endpoint is not configured. "
                "Set PAPERLESS_REST_OCR_ENDPOINT environment variable.",
            )

        payload = self.construct_request_payload(document_path, mime_type)
        headers = self.construct_request_headers()

        try:
            self.log.debug(
                f"Making REST OCR request to {self.settings.api_endpoint} "
                f"(attempt {attempt}/{self.settings.retry_count})",
            )

            response = requests.post(
                self.settings.api_endpoint,
                json=payload,
                headers=headers,
                timeout=self.settings.timeout,
                verify=self.settings.verify_ssl,
            )

            response.raise_for_status()

            # Try to parse JSON response
            try:
                return response.json()
            except json.JSONDecodeError:
                # If not JSON, treat the whole response as text
                return {"text": response.text}

        except requests.exceptions.Timeout as e:
            error_msg = (
                f"REST OCR request timed out after {self.settings.timeout} seconds"
            )
            self.log.warning(f"{error_msg}: {e}")

            if attempt < self.settings.retry_count:
                wait_time = attempt * 2  # Exponential backoff
                self.log.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                return self.make_api_request(document_path, mime_type, attempt + 1)
            else:
                raise ParseError(f"{error_msg}. All {attempt} attempts failed.") from e

        except requests.exceptions.HTTPError as e:
            error_msg = f"REST OCR API returned HTTP error: {e.response.status_code}"
            if e.response.text:
                error_msg += f" - {e.response.text[:200]}"

            self.log.warning(error_msg)

            if attempt < self.settings.retry_count and e.response.status_code >= 500:
                # Only retry on server errors
                wait_time = attempt * 2
                self.log.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                return self.make_api_request(document_path, mime_type, attempt + 1)
            else:
                raise ParseError(error_msg) from e

        except requests.exceptions.RequestException as e:
            error_msg = f"REST OCR request failed: {e}"
            self.log.warning(error_msg)

            if attempt < self.settings.retry_count:
                wait_time = attempt * 2
                self.log.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                return self.make_api_request(document_path, mime_type, attempt + 1)
            else:
                raise ParseError(
                    f"{error_msg}. All {attempt} attempts failed.",
                ) from e

    def parse(self, document_path: Path, mime_type, file_name=None):
        """
        Parse the document using the REST OCR API
        """
        self.log.info(f"Starting REST OCR parsing for {document_path}")

        try:
            # Make the API request
            response_data = self.make_api_request(document_path, mime_type)

            # Extract text from response
            text = self.extract_text_from_response(response_data)

            if not text or len(text.strip()) == 0:
                self.log.warning("REST OCR returned empty text")
                self.text = ""
            else:
                self.text = text.strip()
                self.log.info(
                    f"Successfully extracted {len(self.text)} characters via REST OCR",
                )

            # For PDFs, we might want to create an archive file
            # For now, we'll use the original document as the archive
            if mime_type == "application/pdf":
                self.archive_path = None  # No separate archive for REST OCR
            else:
                # For images, we might want to convert to PDF
                # For simplicity, we'll skip archive creation for now
                self.archive_path = None

        except ParseError:
            raise
        except Exception as e:
            raise ParseError(
                f"Unexpected error during REST OCR parsing: {e.__class__.__name__}: {e!s}",
            ) from e
