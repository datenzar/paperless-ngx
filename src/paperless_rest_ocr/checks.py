from django.conf import settings
from django.core.checks import Error
from django.core.checks import Warning
from django.core.checks import register


@register()
def rest_ocr_config_check(app_configs, **kwargs):
    """
    Check that REST OCR is properly configured if enabled
    """
    errors = []
    warnings = []

    # Only check if REST OCR backend is selected
    if not hasattr(settings, "OCR_BACKEND") or settings.OCR_BACKEND != "rest_api":
        return errors + warnings

    # Check if endpoint is configured
    if not settings.REST_OCR_ENDPOINT:
        errors.append(
            Error(
                "REST OCR backend is selected but REST_OCR_ENDPOINT is not configured",
                hint="Set PAPERLESS_REST_OCR_ENDPOINT environment variable",
                id="paperless_rest_ocr.E001",
            ),
        )

    # Warn if authentication is not configured
    if not settings.REST_OCR_API_KEY and not settings.REST_OCR_AUTH_TOKEN:
        warnings.append(
            Warning(
                "REST OCR backend is configured but no authentication is set",
                hint="Consider setting PAPERLESS_REST_OCR_API_KEY or PAPERLESS_REST_OCR_AUTH_TOKEN for secure API access",
                id="paperless_rest_ocr.W001",
            ),
        )

    # Warn if SSL verification is disabled
    if not settings.REST_OCR_VERIFY_SSL:
        warnings.append(
            Warning(
                "SSL verification is disabled for REST OCR endpoint",
                hint="This is insecure. Enable PAPERLESS_REST_OCR_VERIFY_SSL in production",
                id="paperless_rest_ocr.W002",
            ),
        )

    return errors + warnings
