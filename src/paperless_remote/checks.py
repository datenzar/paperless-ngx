from django.conf import settings
from django.core.checks import Error
from django.core.checks import register


@register()
def check_remote_parser_configured(app_configs, **kwargs):
    valid_engines = {"azureai", "ocrbridge-ocrmac"}
    if settings.REMOTE_OCR_ENGINE and settings.REMOTE_OCR_ENGINE not in valid_engines:
        return [
            Error(
                "Remote parser engine must be one of: azureai, ocrbridge-ocrmac.",
            ),
        ]

    if settings.REMOTE_OCR_ENGINE == "azureai" and not (
        settings.REMOTE_OCR_ENDPOINT and settings.REMOTE_OCR_API_KEY
    ):
        return [
            Error(
                "Azure AI remote parser requires endpoint and API key to be configured.",
            ),
        ]

    if settings.REMOTE_OCR_ENGINE == "ocrbridge-ocrmac" and not (
        settings.REMOTE_OCR_ENDPOINT and settings.REMOTE_OCR_API_KEY
    ):
        return [
            Error(
                "OCRBridge OCRMac remote parser requires endpoint and API key to be configured.",
            ),
        ]

    return []
