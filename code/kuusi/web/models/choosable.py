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

from typing import Dict
from django.db import models
from web.models import Translateable, TranslateableField
from django.utils.translation import gettext_lazy as _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from kuusi.settings import LONG_CACHE_TIMEOUT
class Choosable(Translateable):
    """
    Element ot be choosed.

    Must be translated
    """

    name = models.CharField(null=False, blank=False, max_length=120) # the name will be used for results lists mostly
    description = TranslateableField(
        null=True, blank=True, default=None, max_length=120
    )
    clicked = models.IntegerField(default=0)
    bg_color = models.CharField(max_length=10, default=None, null=True)
    fg_color = models.CharField(max_length=10, default=None, null=True)

    def __str__(self) -> str:
        return f"{self.name}"

    @property
    def meta(self) -> Dict[str, any]:
        cache_key = f"choosable-{self.pk}-metas"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        meta_objects = ChoosableMeta.objects.filter(meta_choosable=self).order_by(
            "meta_name"
        )
        result = {}

        meta_object: ChoosableMeta
        for meta_object in meta_objects:
            result[meta_object.meta_name.upper()] = meta_object
        cache.set(cache_key, result, LONG_CACHE_TIMEOUT)
        return result


    def as_toml(self):
        result = ""
        result += f"[choosable.{self.catalogue_id}]\n"
        result += f"name = \"{self.name}\"\nbg_color = \"{self.bg_color}\"\nfg_color = \"{self.fg_color}\"\n"
        return result + "\n"

class ChoosableMeta(Translateable):
    meta_choosable = models.ForeignKey(
        to=Choosable,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="choosablemeta_choosable",
    )

    class MetaName(models.TextChoices):
        CREATED = "AGE", _("AGE")
        COUNTRY = "COUNTRY",  _("COUNTRY")
        LICENSES = "LICENSES",  _("LICENSES")
        WEBSITE = "WEBSITE",  _("WEBSITE")
        LANGUAGES = "LANGUAGES", _("LANGUAGES")
    
    @property 
    def meta_type(self) -> str:
        default_type = "hidden";
        map = {
            "AGE": "date",
            "COUNTRY": "flag",
            "LICENSES": "text",
            "WEBSITE": "link",
        }
        return map[self.meta_name] if self.meta_name in map  else default_type

    @property 
    def meta_description(self) -> str:
        # used as with as_toml
        map = {
            "AGE": "To provide the age of the distribution, an age can be given. The value shall be in ISO 8601 format, e. g. 2017-10-27",
            "COUNTRY": "If the choosable is e. g. developed by a company based in a certain country, the value represents an ISO-639-1 code, e. g. 'it' for italy.",
            "LANGUAGES": "The list of languages supported by the choosable, comma separated as ISO-639-1 code, e. g. en,de,jp",
            "LICENSES": "A list of licenses used by the project in a SPDX format, e. g. AGPL-3.0-or-later",
            "WEBSITE": "The link to the project. Shall start with http(s)"
        }
        return map[self.meta_name]

    @property 
    def is_hidden(self) -> bool:
        return self.meta_type == "hidden"

    meta_name = models.CharField(
        max_length=25,
        blank=False,
        null=False,
        choices=MetaName.choices,
        default=MetaName.CREATED,
    )
    meta_value = models.CharField(
        max_length=255, blank=False, null=False, default="A value"
    )

    @property
    def as_list(self):
        return self.meta_value.split(",")

    @property
    def years_since(self):
        now = datetime.now()
        date = datetime.fromisoformat(self.meta_value)
        delta = relativedelta(now, date)
        return delta.years
    
    def as_toml(self):
        result = ""
        if self.meta_choosable:
            result += f"# {self.meta_description}\n"
            result += f"[[meta]]\n"
            result += f"choosable=\"{self.meta_choosable.catalogue_id}\"\n"
            result += f"meta_name=\"{self.meta_name.lower()}\"\n"
            result += f"meta_value=\"{self.meta_value}\"\n"
        return result + "\n"