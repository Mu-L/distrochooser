# Generated by Django 5.1.7 on 2025-06-28 07:22

import web.models.translateable
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0146_page_icon"),
    ]

    operations = [
        migrations.AddField(
            model_name="page",
            name="title",
            field=web.models.translateable.TranslateableField(
                blank=True,
                help_text="A comment for translators to identify this value",
                max_length=80,
                null=True,
            ),
        ),
        migrations.DeleteModel(
            name="Category",
        ),
    ]
