import base64
from pathlib import Path
from unittest import mock

import requests
from django.test import TestCase
from django.test import override_settings

from documents.parsers import ParseError
from paperless_rest_ocr.parsers import RestOcrDocumentParser


class TestRestOcrParser(TestCase):
    """
    Tests for the REST OCR parser
    """

    def setUp(self):
        """
        Set up test fixtures
        """
        self.parser = RestOcrDocumentParser(logging_group=None)
        self.sample_text = "This is sample OCR text from REST API"

    @override_settings(
        REST_OCR_ENDPOINT="http://localhost:8080/ocr",
        REST_OCR_API_KEY="test-api-key",
        REST_OCR_AUTH_METHOD="api_key",
        REST_OCR_TIMEOUT=30,
        REST_OCR_RETRY_COUNT=3,
        REST_OCR_VERIFY_SSL=True,
        REST_OCR_LANGUAGE="eng",
    )
    def test_successful_ocr_request(self):
        """
        Test successful OCR processing via REST API
        """
        # Mock the API response
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "text": self.sample_text,
            "metadata": {"confidence": 0.95, "page_count": 1},
        }

        # Create a temporary test file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test document")
            test_file_path = Path(f.name)

        try:
            with mock.patch("requests.post", return_value=mock_response):
                self.parser.parse(test_file_path, "text/plain")

            # Verify the text was extracted
            self.assertEqual(self.parser.get_text(), self.sample_text)

        finally:
            # Clean up
            test_file_path.unlink()
            self.parser.cleanup()

    @override_settings(
        REST_OCR_ENDPOINT="http://localhost:8080/ocr",
        REST_OCR_API_KEY="test-api-key",
        REST_OCR_TIMEOUT=30,
        REST_OCR_RETRY_COUNT=1,
    )
    def test_api_timeout_with_retry(self):
        """
        Test that timeouts trigger retries
        """
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test document")
            test_file_path = Path(f.name)

        try:
            # Mock timeout exception
            with mock.patch(
                "requests.post",
                side_effect=requests.exceptions.Timeout("Request timed out"),
            ):
                with self.assertRaises(ParseError) as context:
                    self.parser.parse(test_file_path, "text/plain")

                self.assertIn("timed out", str(context.exception).lower())

        finally:
            test_file_path.unlink()
            self.parser.cleanup()

    @override_settings(
        REST_OCR_ENDPOINT="http://localhost:8080/ocr",
        REST_OCR_API_KEY="test-api-key",
        REST_OCR_RETRY_COUNT=2,
    )
    def test_http_500_error_with_retry(self):
        """
        Test that 500 errors trigger retries
        """
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test document")
            test_file_path = Path(f.name)

        try:
            # Mock 500 error
            mock_response = mock.Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=mock_response,
            )

            with mock.patch("requests.post", return_value=mock_response):
                with self.assertRaises(ParseError) as context:
                    self.parser.parse(test_file_path, "text/plain")

                self.assertIn("500", str(context.exception))

        finally:
            test_file_path.unlink()
            self.parser.cleanup()

    @override_settings(
        REST_OCR_ENDPOINT="http://localhost:8080/ocr",
        REST_OCR_API_KEY="test-api-key",
    )
    def test_http_400_error_no_retry(self):
        """
        Test that 400 errors do not trigger retries
        """
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test document")
            test_file_path = Path(f.name)

        try:
            # Mock 400 error
            mock_response = mock.Mock()
            mock_response.status_code = 400
            mock_response.text = "Bad Request"
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=mock_response,
            )

            with mock.patch("requests.post", return_value=mock_response) as mock_post:
                with self.assertRaises(ParseError):
                    self.parser.parse(test_file_path, "text/plain")

                # Should only be called once (no retries for client errors)
                self.assertEqual(mock_post.call_count, 1)

        finally:
            test_file_path.unlink()
            self.parser.cleanup()

    @override_settings(
        REST_OCR_ENDPOINT="http://localhost:8080/ocr",
        REST_OCR_AUTH_TOKEN="test-bearer-token",
        REST_OCR_AUTH_METHOD="bearer",
    )
    def test_bearer_authentication(self):
        """
        Test that bearer token authentication is correctly applied
        """
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test document")
            test_file_path = Path(f.name)

        try:
            mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"text": "Success"}

            with mock.patch("requests.post", return_value=mock_response) as mock_post:
                self.parser.parse(test_file_path, "text/plain")

                # Verify the Authorization header was set correctly
                call_kwargs = mock_post.call_args[1]
                headers = call_kwargs["headers"]
                self.assertEqual(headers["Authorization"], "Bearer test-bearer-token")

        finally:
            test_file_path.unlink()
            self.parser.cleanup()

    @override_settings(
        REST_OCR_ENDPOINT="http://localhost:8080/ocr",
        REST_OCR_API_KEY="test-api-key",
        REST_OCR_AUTH_METHOD="api_key",
    )
    def test_api_key_authentication(self):
        """
        Test that API key authentication is correctly applied
        """
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test document")
            test_file_path = Path(f.name)

        try:
            mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"text": "Success"}

            with mock.patch("requests.post", return_value=mock_response) as mock_post:
                self.parser.parse(test_file_path, "text/plain")

                # Verify the X-API-Key header was set correctly
                call_kwargs = mock_post.call_args[1]
                headers = call_kwargs["headers"]
                self.assertEqual(headers["X-API-Key"], "test-api-key")

        finally:
            test_file_path.unlink()
            self.parser.cleanup()

    @override_settings(REST_OCR_ENDPOINT="")
    def test_missing_endpoint_configuration(self):
        """
        Test that missing endpoint raises an error
        """
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test document")
            test_file_path = Path(f.name)

        try:
            with self.assertRaises(ParseError) as context:
                self.parser.parse(test_file_path, "text/plain")

            self.assertIn("not configured", str(context.exception).lower())

        finally:
            test_file_path.unlink()
            self.parser.cleanup()

    @override_settings(
        REST_OCR_ENDPOINT="http://localhost:8080/ocr",
        REST_OCR_API_KEY="test-key",
    )
    def test_extract_text_from_various_response_formats(self):
        """
        Test that parser can handle different response formats
        """
        test_cases = [
            ({"text": "Sample text"}, "Sample text"),
            ({"content": "Sample text"}, "Sample text"),
            ({"ocr_text": "Sample text"}, "Sample text"),
            ({"result": "Sample text"}, "Sample text"),
            ({"result": {"text": "Sample text"}}, "Sample text"),
        ]

        for response_data, expected_text in test_cases:
            extracted = self.parser.extract_text_from_response(response_data)
            self.assertEqual(
                extracted,
                expected_text,
                f"Failed to extract text from {response_data}",
            )

    @override_settings(
        REST_OCR_ENDPOINT="http://localhost:8080/ocr",
        REST_OCR_API_KEY="test-key",
    )
    def test_construct_request_payload(self):
        """
        Test that request payload is correctly constructed
        """
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content")
            test_file_path = Path(f.name)

        try:
            payload = self.parser.construct_request_payload(
                test_file_path,
                "text/plain",
            )

            # Verify payload structure
            self.assertIn("document", payload)
            self.assertIn("mime_type", payload)
            self.assertIn("language", payload)
            self.assertEqual(payload["mime_type"], "text/plain")

            # Verify document is base64 encoded
            decoded = base64.b64decode(payload["document"])
            self.assertEqual(decoded, b"Test content")

        finally:
            test_file_path.unlink()
            self.parser.cleanup()
