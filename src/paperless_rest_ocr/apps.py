from django.apps import AppConfig

from paperless_rest_ocr.signals import rest_ocr_consumer_declaration


class PaperlessRestOcrConfig(AppConfig):
    name = "paperless_rest_ocr"

    def ready(self):
        from documents.signals import document_consumer_declaration

        document_consumer_declaration.connect(rest_ocr_consumer_declaration)

        AppConfig.ready(self)
