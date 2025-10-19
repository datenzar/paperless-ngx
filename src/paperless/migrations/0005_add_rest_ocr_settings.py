# Generated manually for REST OCR integration

import django.core.validators
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("paperless", "0004_applicationconfiguration_barcode_asn_prefix_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="applicationconfiguration",
            name="rest_ocr_endpoint",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                verbose_name="REST OCR API endpoint URL",
            ),
        ),
        migrations.AddField(
            model_name="applicationconfiguration",
            name="rest_ocr_api_key",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                verbose_name="REST OCR API key",
            ),
        ),
        migrations.AddField(
            model_name="applicationconfiguration",
            name="rest_ocr_auth_token",
            field=models.CharField(
                blank=True,
                max_length=512,
                null=True,
                verbose_name="REST OCR authentication token",
            ),
        ),
        migrations.AddField(
            model_name="applicationconfiguration",
            name="rest_ocr_auth_method",
            field=models.CharField(
                blank=True,
                help_text="bearer, api_key, or basic",
                max_length=16,
                null=True,
                verbose_name="REST OCR authentication method",
            ),
        ),
        migrations.AddField(
            model_name="applicationconfiguration",
            name="rest_ocr_timeout",
            field=models.PositiveIntegerField(
                null=True,
                validators=[django.core.validators.MinValueValidator(1)],
                verbose_name="REST OCR request timeout in seconds",
            ),
        ),
        migrations.AddField(
            model_name="applicationconfiguration",
            name="rest_ocr_retry_count",
            field=models.PositiveIntegerField(
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="REST OCR retry count",
            ),
        ),
        migrations.AddField(
            model_name="applicationconfiguration",
            name="rest_ocr_verify_ssl",
            field=models.BooleanField(
                null=True,
                verbose_name="Verify SSL certificate for REST OCR endpoint",
            ),
        ),
        migrations.AddField(
            model_name="applicationconfiguration",
            name="rest_ocr_language",
            field=models.CharField(
                blank=True,
                max_length=32,
                null=True,
                verbose_name="Language hint for REST OCR",
            ),
        ),
        migrations.AddField(
            model_name="applicationconfiguration",
            name="rest_ocr_custom_headers",
            field=models.JSONField(
                null=True,
                verbose_name="Custom HTTP headers for REST OCR requests",
            ),
        ),
    ]
