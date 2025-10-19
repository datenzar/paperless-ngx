from django.conf import settings


def get_parser(*args, **kwargs):
    from paperless_rest_ocr.parsers import RestOcrDocumentParser

    return RestOcrDocumentParser(*args, **kwargs)


def rest_ocr_consumer_declaration(sender, **kwargs):
    # Only register the REST OCR parser if the backend is set to 'rest_api'
    if getattr(settings, "OCR_BACKEND", "tesseract") != "rest_api":
        return None

    return {
        "parser": get_parser,
        "weight": 10,  # Higher weight than tesseract (0) to prefer REST OCR when enabled
        "mime_types": {
            "application/pdf": ".pdf",
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/tiff": ".tif",
            "image/gif": ".gif",
            "image/bmp": ".bmp",
            "image/webp": ".webp",
            "image/heic": ".heic",
        },
    }
