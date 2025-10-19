# REST OCR Parser for Paperless-ngx

This module provides an alternative OCR mechanism for Paperless-ngx using a RESTful API service instead of the default Tesseract/OCRmyPDF approach.

## Features

- Generic REST API integration for OCR processing
- Support for multiple authentication methods (Bearer token, API key, Basic auth)
- Configurable timeout and retry logic
- Support for custom HTTP headers
- Handles PDFs and images (same formats as Tesseract parser)

## Configuration

### Environment Variables

To enable and configure the REST OCR parser, set the following environment variables:

#### Required Settings

```bash
# Enable REST OCR backend (default: tesseract)
PAPERLESS_OCR_BACKEND=rest_api

# REST API endpoint URL
PAPERLESS_REST_OCR_ENDPOINT=https://your-ocr-api.com/v1/ocr
```

#### Authentication Settings

Choose one of the following authentication methods:

```bash
# For Bearer token authentication (default method)
PAPERLESS_REST_OCR_AUTH_METHOD=bearer
PAPERLESS_REST_OCR_AUTH_TOKEN=your-bearer-token

# For API key authentication
PAPERLESS_REST_OCR_AUTH_METHOD=api_key
PAPERLESS_REST_OCR_API_KEY=your-api-key

# For Basic authentication
PAPERLESS_REST_OCR_AUTH_METHOD=basic
PAPERLESS_REST_OCR_API_KEY=username:password
```

#### Optional Settings

```bash
# Request timeout in seconds (default: 30)
PAPERLESS_REST_OCR_TIMEOUT=60

# Number of retry attempts (default: 3)
PAPERLESS_REST_OCR_RETRY_COUNT=5

# Verify SSL certificates (default: true)
PAPERLESS_REST_OCR_VERIFY_SSL=true

# Language hint for OCR (default: eng)
PAPERLESS_REST_OCR_LANGUAGE=eng

# Custom HTTP headers as JSON (optional)
PAPERLESS_REST_OCR_CUSTOM_HEADERS='{"X-Custom-Header": "value"}'
```

## REST API Contract

Your REST OCR service should implement the following contract:

### Request Format

**Endpoint:** `POST /ocr` (or your configured endpoint)

**Headers:**

- `Content-Type: application/json`
- Authentication headers (based on configured method)
- Any custom headers you've configured

**Request Body:**

```json
{
  "document": "<base64-encoded-file>",
  "mime_type": "application/pdf",
  "language": "eng",
  "options": {}
}
```

### Response Format

The API should return a JSON response with one of the following structures:

**Standard format:**

```json
{
  "text": "Extracted text content...",
  "metadata": {
    "page_count": 1,
    "confidence": 0.95
  }
}
```

**Alternative supported formats:**

```json
{ "content": "Extracted text..." }
```

```json
{ "ocr_text": "Extracted text..." }
```

```json
{ "result": "Extracted text..." }
```

```json
{ "result": { "text": "Extracted text..." } }
```

## Example REST API Implementation

Here's a minimal example of a compatible REST OCR service using Flask:

```python
from flask import Flask, request, jsonify
import base64
import pytesseract
from PIL import Image
import io

app = Flask(__name__)

@app.route('/ocr', methods=['POST'])
def ocr():
    data = request.json

    # Verify API key
    if request.headers.get('X-API-Key') != 'your-secret-key':
        return jsonify({"error": "Unauthorized"}), 401

    # Decode document
    document_bytes = base64.b64decode(data['document'])

    # Perform OCR (this is simplified)
    image = Image.open(io.BytesIO(document_bytes))
    text = pytesseract.image_to_string(
        image,
        lang=data.get('language', 'eng')
    )

    return jsonify({
        "text": text,
        "metadata": {
            "page_count": 1,
            "confidence": 0.95
        }
    })

if __name__ == '__main__':
    app.run(port=8080)
```

## Error Handling

The parser implements intelligent retry logic:

- **Timeouts:** Retries with exponential backoff
- **5xx errors:** Retries (server errors might be temporary)
- **4xx errors:** No retry (client errors are permanent)

All errors are logged with appropriate detail levels.

## Testing

Run the test suite:

```bash
cd src
pytest paperless_rest_ocr/tests/
```

## Switching Between OCR Backends

To switch back to Tesseract:

```bash
PAPERLESS_OCR_BACKEND=tesseract  # or simply remove the variable
```

To use REST OCR:

```bash
PAPERLESS_OCR_BACKEND=rest_api
```

## Security Considerations

1. **Always use HTTPS** for your REST OCR endpoint in production
2. **Enable SSL verification** (keep `PAPERLESS_REST_OCR_VERIFY_SSL=true`)
3. **Secure your API keys** - use environment variables or secrets management
4. **Consider data privacy** - documents are transmitted to the external service
5. **Use authentication** - never expose OCR endpoints without authentication

## Troubleshooting

### Parser not being used

Check that:

- `PAPERLESS_OCR_BACKEND=rest_api` is set
- The app is registered in `INSTALLED_APPS`
- Django has been restarted after configuration changes

### Authentication errors

Verify:

- Correct auth method is set
- API keys/tokens are valid
- Custom headers are properly formatted JSON

### Timeouts

Try:

- Increasing `PAPERLESS_REST_OCR_TIMEOUT`
- Increasing `PAPERLESS_REST_OCR_RETRY_COUNT`
- Checking network connectivity to the OCR service

### Empty text results

Ensure:

- Your API returns one of the supported response formats
- The `text` field contains actual content
- Check API logs for processing errors

## Performance Considerations

REST OCR performance depends on:

- Network latency to the OCR service
- Processing time of the external OCR service
- Document size and complexity

For best performance:

- Host the OCR service close to Paperless-ngx
- Tune timeout values based on your document sizes
- Monitor OCR service capacity

## Migration from Tesseract

1. Set up and test your REST OCR service
2. Configure environment variables
3. Set `PAPERLESS_OCR_BACKEND=rest_api`
4. Restart Paperless-ngx
5. Test with a sample document
6. Monitor logs for any issues

Existing documents are not affected - only new documents will use REST OCR.
