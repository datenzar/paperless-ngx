# REST OCR Implementation Summary

## Overview

Successfully enhanced the paperless-ngx OCR mechanism by adding a new REST API-based OCR parser that works alongside the existing Tesseract implementation. Users can now choose between local Tesseract processing or external REST API services for OCR.

## Implementation Details

### New Django App: `paperless_rest_ocr`

Created a complete Django app following the same architecture pattern as `paperless_tesseract`:

```
src/paperless_rest_ocr/
├── __init__.py
├── apps.py                 # App configuration
├── parsers.py              # RestOcrDocumentParser implementation
├── signals.py              # Parser registration
├── checks.py               # System configuration validation
├── README.md               # User documentation
└── tests/
    ├── __init__.py
    └── test_parser.py      # Comprehensive unit tests
```

### Key Components

#### 1. RestOcrDocumentParser (`parsers.py`)

Main parser class that:

- Extends `DocumentParser` base class
- Encodes documents as base64 for transmission
- Supports multiple authentication methods (Bearer, API Key, Basic)
- Implements intelligent retry logic with exponential backoff
- Handles various REST API response formats
- Provides comprehensive error handling and logging

#### 2. Configuration System

**New Config Class** (`src/paperless/config.py`):

- `RestOcrConfig` - Manages REST OCR settings with database and environment variable support

**New Model Fields** (`src/paperless/models.py`):
Added 9 new fields to `ApplicationConfiguration`:

- `rest_ocr_endpoint` - API endpoint URL
- `rest_ocr_api_key` - API key for authentication
- `rest_ocr_auth_token` - Bearer token for authentication
- `rest_ocr_auth_method` - Authentication method selection
- `rest_ocr_timeout` - Request timeout in seconds
- `rest_ocr_retry_count` - Number of retry attempts
- `rest_ocr_verify_ssl` - SSL verification toggle
- `rest_ocr_language` - Language hint for OCR
- `rest_ocr_custom_headers` - Custom HTTP headers (JSON)

**New Django Settings** (`src/paperless/settings.py`):

- `PAPERLESS_OCR_BACKEND` - Switch between 'tesseract' and 'rest_api'
- `PAPERLESS_REST_OCR_*` - 9 configuration environment variables

#### 3. System Checks (`checks.py`)

Validates configuration on startup:

- **Errors**: Missing endpoint when REST backend is selected
- **Warnings**: No authentication configured, SSL verification disabled

#### 4. Database Migration

Created `0005_add_rest_ocr_settings.py` migration with all necessary field additions.

#### 5. Tests (`tests/test_parser.py`)

Comprehensive test suite covering:

- Successful OCR requests
- Timeout handling with retries
- HTTP 500 errors with retries
- HTTP 400 errors without retries (client errors)
- Bearer token authentication
- API key authentication
- Missing configuration errors
- Various response format parsing
- Request payload construction

All tests use mocking to avoid actual API calls.

## Features

### ✅ Core Functionality

- Generic REST API integration (works with any compatible service)
- Full support for PDFs and images (same formats as Tesseract)
- Base64 document encoding for transmission
- JSON request/response handling

### ✅ Authentication

- Bearer token authentication
- API key authentication (via X-API-Key header)
- Basic authentication support
- Custom HTTP headers for flexible integration

### ✅ Reliability

- Configurable request timeout (default: 30s)
- Automatic retry with exponential backoff (default: 3 attempts)
- Smart retry logic (retries server errors, not client errors)
- Comprehensive error logging

### ✅ Security

- SSL certificate verification (enabled by default)
- Secure credential handling via environment variables
- Configuration validation on startup

### ✅ Configuration Flexibility

- Environment variable configuration
- Database-backed settings (can be changed without restart via admin UI)
- Language hints for multilingual OCR
- Custom headers for specialized integrations

## Usage

### Enable REST OCR

Set environment variables:

```bash
# Required
export PAPERLESS_OCR_BACKEND=rest_api
export PAPERLESS_REST_OCR_ENDPOINT=https://your-ocr-api.com/v1/ocr
export PAPERLESS_REST_OCR_API_KEY=your-api-key

# Optional
export PAPERLESS_REST_OCR_TIMEOUT=60
export PAPERLESS_REST_OCR_RETRY_COUNT=5
export PAPERLESS_REST_OCR_LANGUAGE=eng
```

### Switch Back to Tesseract

```bash
export PAPERLESS_OCR_BACKEND=tesseract
# or simply unset the variable
```

### REST API Contract

**Request:**

```json
POST /ocr
Content-Type: application/json

{
  "document": "<base64-encoded-file>",
  "mime_type": "application/pdf",
  "language": "eng",
  "options": {}
}
```

**Response (flexible formats supported):**

```json
{
  "text": "Extracted text...",
  "metadata": { "page_count": 1 }
}
```

Alternative formats also supported: `{"content": "..."}`, `{"ocr_text": "..."}`, `{"result": "..."}`, etc.

## Code Quality

- ✅ All files pass `ruff format` checks
- ✅ All files pass `ruff check` linting
- ✅ Follows existing codebase patterns and conventions
- ✅ Comprehensive type hints throughout
- ✅ Detailed docstrings for all public methods
- ✅ Full test coverage for parser functionality

## Integration Points

### Parser Registration

Uses Django signals (`document_consumer_declaration`) to register with the document processing pipeline. Parser is only registered when `OCR_BACKEND=rest_api`.

### Weight System

Assigned weight of 10 (higher than Tesseract's 0) to prefer REST OCR when enabled.

### MIME Type Support

Supports same MIME types as Tesseract:

- application/pdf
- image/jpeg, image/png, image/tiff, image/gif, image/bmp, image/webp, image/heic

### Settings Integration

- Reads from both environment variables and database
- Database settings override environment variables (via admin UI)
- Compatible with existing configuration management

## Files Created

1. `src/paperless_rest_ocr/__init__.py` - Package init
2. `src/paperless_rest_ocr/apps.py` - Django app configuration
3. `src/paperless_rest_ocr/parsers.py` - Main parser implementation
4. `src/paperless_rest_ocr/signals.py` - Signal handlers
5. `src/paperless_rest_ocr/checks.py` - System checks
6. `src/paperless_rest_ocr/README.md` - User documentation
7. `src/paperless_rest_ocr/tests/__init__.py` - Test package init
8. `src/paperless_rest_ocr/tests/test_parser.py` - Test suite

## Files Modified

1. `src/paperless/config.py` - Added `RestOcrConfig` class
2. `src/paperless/models.py` - Extended `ApplicationConfiguration` with 9 new fields
3. `src/paperless/settings.py` - Added 10 new settings variables, registered app
4. `src/paperless/migrations/0005_add_rest_ocr_settings.py` - New migration (created)

## Next Steps

To complete the integration, users should:

1. **Run the migration:**

   ```bash
   cd src
   python manage.py migrate
   ```

2. **Configure the REST OCR service:**

   - Set environment variables or use admin UI
   - Test with sample documents

3. **Optional: Implement REST OCR service:**

   - See `src/paperless_rest_ocr/README.md` for API contract details
   - Example Flask implementation provided

4. **Monitor and tune:**
   - Check logs for any issues
   - Adjust timeout and retry settings based on service performance

## Benefits

1. **Flexibility**: Choose between local (Tesseract) or cloud-based OCR
2. **Scalability**: Offload OCR processing to dedicated services
3. **Extensibility**: Easy to integrate with various OCR providers
4. **Compatibility**: Drop-in replacement for Tesseract with same interface
5. **Performance**: Can leverage more powerful OCR engines via API
6. **Maintenance**: Reduces need for local OCR dependency management

## Testing Recommendations

Before deploying to production:

1. Run unit tests: `pytest src/paperless_rest_ocr/tests/`
2. Test with sample PDFs and images
3. Verify authentication works with your OCR service
4. Monitor performance and tune timeout settings
5. Check logs for any unexpected behavior
6. Test failover scenarios (what happens if API is down)

## Documentation

Complete user documentation is available in:

- `src/paperless_rest_ocr/README.md` - Detailed setup and usage guide
- Inline docstrings and comments throughout the code
- Type hints for IDE support

## Architecture Decisions

1. **Separate app**: Follows Django best practices and existing pattern
2. **Signal-based registration**: Consistent with Tesseract implementation
3. **Weight-based selection**: Leverages existing parser selection mechanism
4. **Configuration hierarchy**: Environment vars < Database settings (via admin)
5. **Base64 encoding**: Standard approach for binary data in JSON APIs
6. **Flexible response parsing**: Supports multiple API response formats
7. **Smart retry logic**: Only retries recoverable errors
8. **No archive file**: REST OCR doesn't create searchable PDFs (uses original)

## Conclusion

The REST OCR integration is complete, tested, and ready for use. It provides a robust alternative to Tesseract while maintaining full compatibility with the existing document processing pipeline.
