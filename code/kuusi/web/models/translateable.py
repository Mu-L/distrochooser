"""
distrochooser
Copyright (C) 2014-2025  Christoph Müller  <mail@chmr.eu>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import annotations
from typing import Any

from logging import getLogger
from os.path import join, exists
from json import loads, dumps
from os import listdir

from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from web.util import get_translation_haystack

logger = getLogger("root")

from kuusi.settings import (
    LOCALE_PATHS,
    AVAILABLE_LANGUAGES,
    DEFAULT_LANGUAGE_CODE
)

TRANSLATIONS = {}

def hot_load_translations(**kwargs):
    path = join(LOCALE_PATHS[0])
    files = listdir(path)
    for file in files:
        if ".json" in file:
            parts = file.split("-")
            language = parts[1].replace(".json", "").lower()
            if language not in TRANSLATIONS:
                TRANSLATIONS[language] = {}
            full_path = join(path, file)
            content = loads(open(full_path, "r").read())
            for key, value in content.items():
                TRANSLATIONS[language][key] = value


class TranslateableField(models.CharField):
    "A field which can be translated"

    def __init__(self, *args, **kwargs):
        kwargs["help_text"] = "A comment for translators to identify this value"
        super().__init__(*args, **kwargs)

    def get_msg_id(self, model_instance: Translateable):
        """
        Get a unique identifier to be used for translation purposes.
        """
        identifier = model_instance.catalogue_id
        return f"{identifier}-{self.name}"

    def pre_save(self, model_instance: Translateable, add: bool) -> Any:
        """
        Update records to make sure there is a record existing at all the time
        """
        if len(LOCALE_PATHS) == 0:
            raise Exception(f"No locale paths are set")
        model_type = type(model_instance).__name__
        msg_id = self.get_msg_id(model_instance)
        # Make sure that the TranslateAbleField has a record we can reference
        TranslateableFieldRecord.objects.filter(
            msg_id=msg_id,
            model_type=model_type
        ).delete()
        TranslateableFieldRecord.objects.create(
            msg_id=msg_id,
            model_type=model_type
        )
        self.update_json(msg_id)
        return super().pre_save(model_instance, add)

    def update_json(self, msg_id: str):
        for locale in AVAILABLE_LANGUAGES:
            lowercase_locale = locale[0].lower()
            path = join(LOCALE_PATHS[0], f"lang-{lowercase_locale}.json")
            entries = {}
            if exists(path):
                with open(path, "r") as file:
                    entries = loads(file.read())
            if msg_id not in entries:
                entries[msg_id] = None
            without_empty = {}
            for key, value in entries.items():
                if value is not None:
                    without_empty[key] = value
            with open(path, "w") as file:
                file.write(dumps(without_empty, indent=4))



class TranslateableFieldRecord(models.Model):
    msg_id = models.CharField(null=False, blank=False, max_length=250)
    model_type = models.TextField(null=True, blank=True, max_length=200)
    def __str__(self) -> str:
        return self.msg_id


class Translateable(models.Model):
    """
    This class is just used to trigger a signal, which clears up unused TranslateableFieldRecords

    If a TranslateField shall be used, the model must inherit this class.
    """
    # The catalogue_id needs to be set to allow uniquely identify the translated fields using this
    catalogue_id = models.CharField(null=True, blank=True, default=None, max_length=255) 

    is_invalidated = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"({self.catalogue_id})"
    def get_msgd_id_of_field(self, key: str) -> str:
        # get_field returns a Field[any, any], while we need something useable as
        # TranslateableField, so we ignore typing here
        field: TranslateableField = self._meta.get_field(key)  # type: ignore
        return field.get_msg_id(self)
    def __(self, key: str, language_code: str = DEFAULT_LANGUAGE_CODE) -> str:
        msg_id = self.get_msgd_id_of_field(key)
        haystack = get_translation_haystack(TRANSLATIONS, language_code)
        return f"{haystack[msg_id]}" if  msg_id in haystack and haystack[msg_id] is not None  else msg_id
     

    def remove_translation_records(self):
        """
        Removes the translation records form the database.
        """
        fields = self._meta.get_fields()

        field: models.Field | TranslateableField
        for field in fields:  # type:ignore
            if isinstance(field, TranslateableField):
                TranslateableFieldRecord.objects.filter(
                    msg_id=field.get_msg_id(self)
                ).delete()

@receiver(pre_delete, sender=Translateable)
def translateable_removing(sender, instance, using, **kwargs):
    origin: Translateable | models.QuerySet = kwargs["origin"]
    if isinstance(origin, models.QuerySet):
        entry: Translateable
        for entry in origin:
            entry.remove_translation_records()
    else:
        origin.remove_translation_records()