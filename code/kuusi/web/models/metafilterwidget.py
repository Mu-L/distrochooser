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

from json import dumps, loads
from web.models import Widget, Choosable, FacetteAssignment, Session, Page
from django.db import models
from typing import List, Dict
from django.core.cache import cache

class MetaFilterWidgetElement:
    def __init__(self):
        self.cell_type = None
        self.cell_name = None
        self.cell_func = None
    
    def __str__(self):
        return f"{self.cell_name} ({self.cell_type}) -> {self.cell_func}"
    
    def get_func_map(self):
        func_map = {
            "filter_number_gt": self.filter_number_gt,
            "filter_must_have_assignments": self.filter_must_have_assignments,
            "filter_must_match_language": self.filter_must_match_language
        }
        return func_map
    
    def verify(self):
        if self.cell_func not in self.get_func_map():
            raise Exception(f"Function {self.cell_func} not found")

    def apply_cell_func(self, obj: Choosable, value: any, collected_assignments: List[FacetteAssignment], session: Session) -> List[FacetteAssignment]:
        method = self.get_func_map()[self.cell_func]
        return method(obj, value, collected_assignments, session)
    

    def filter_must_match_language(self, obj: Choosable, value: any, collected_assignments, session: Session) -> FacetteAssignment:
        matches = "LANGUAGES" in obj.meta and session.language_code in obj.meta["LANGUAGES"].meta_value
        result = FacetteAssignment(
            catalogue_id = f"{self.cell_name}-" + ("suitable" if matches else "not-suitable"),
            description="suitable" if matches else "not-suitable",
            assignment_type=FacetteAssignment.AssignmentType.POSITIVE if matches else FacetteAssignment.AssignmentType.NEGATIVE
        )
        return result
    
    def filter_must_have_assignments(self, obj: Choosable, value: any, collected_assignments, session) -> FacetteAssignment:
        if value == "true" and len(collected_assignments) == 0: # all meta filter values are strings, basically
            result = FacetteAssignment(
                catalogue_id = f"{self.cell_name}-{obj.name}",
                description="not-suitable",
                assignment_type=FacetteAssignment.AssignmentType.BLOCKING
            )
            return result
        return None
    
    def filter_number_gt(self, obj: Choosable, value: any, collected_assignments, session) -> FacetteAssignment:
        if "AGE" not in obj.meta:
            return None
        matches = int(obj.meta["AGE"].years_since) < int(value)
        result = FacetteAssignment(
            catalogue_id = f"{self.cell_name}-" + ("suitable" if matches else "not-suitable"),
            description="suitable" if matches else "not-suitable",
            assignment_type=FacetteAssignment.AssignmentType.POSITIVE if matches else FacetteAssignment.AssignmentType.NEGATIVE
        )
        return result


class MetaFilterWidgetStructure:
    """
    Virtual class. do not persist.
    """
    def __init__(self, raw_input: List, pk):
        self.raw_input = raw_input
        self.structure = []
        self.original_pk = pk
    
    def parse(self):
        for _, row in enumerate(self.raw_input):
            row_list = []
            for _, cell in enumerate(row):
                cell_content = self.get_cell_content(cell)
                row_list.append(cell_content)
            self.structure.append(row_list)
        
    
    def stringify(self):
        return dumps(self.raw_input)
    
    def get_cell_from_structure(self, key: str) -> MetaFilterWidgetElement:
        cache_key = f"meta-widget-structure-{self.original_pk}-key-{key}-cell"
        cached = cache.get(cache_key)
        if cached:
            return cached
        for line in self.structure:
            for cell in line:
                if cell.cell_name == key:
                    cache.set(cache_key, cell)
                    return cell
        return None


    def get_cell_content(self, raw_input: str) -> MetaFilterWidgetElement:
        parts = raw_input.split(".")
        if parts.__len__() != 3:
            raise Exception(f"Cell content not parseable: {raw_input}")
        cell_type = parts[0]
        cell_name = parts[1]
        cell_func = parts[2]
        cell_obj = MetaFilterWidgetElement()
        cell_obj.cell_name = cell_name
        cell_obj.cell_func = cell_func
        cell_obj.cell_type = cell_type
        cell_obj.verify()
        return cell_obj

class MetaFilterWidget(Widget):
    # To keep this simple, this is for now one field instead of an additional nested structure
    structure = models.TextField(default=None, null=True, blank=True)

    @property
    def parsed_structure(self) -> MetaFilterWidgetStructure:
        cache_key = f"metafilterwidget-parsed-structure-{self.pk}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        obj = MetaFilterWidgetStructure(loads(self.structure), self.pk)
        obj.parse()
        cache.set(cache_key, obj)
        return obj
    
    def get_virtual_assignments(self, meta_filter_values, choosables: List[Choosable], collected_assignments: Dict[int, List[FacetteAssignment]], score_map: Dict[int, Dict], session: Session):
        structure = self.parsed_structure
        for stored_value in meta_filter_values:
            cell_obj =  structure.get_cell_from_structure(stored_value.key)
            stored_value_value = stored_value.value
            for choosable in choosables:
                result = cell_obj.apply_cell_func(choosable, stored_value_value, collected_assignments, session)
                if result is not None:
                    if choosable.pk not in collected_assignments:
                        collected_assignments[choosable.pk] = []
                    if choosable.pk not in score_map:
                        score_map[choosable.pk] = FacetteAssignment.AssignmentType.get_score_map_by_type()
                    collected_assignments[choosable.pk].append(result)
        return score_map, collected_assignments
class MetaFilterValue(models.Model):

    session = models.ForeignKey(
        to=Session,
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name="meta_filter_value_session",
    )
    key = models.CharField(null=False, blank=False, max_length=255)
    value = models.CharField(null=False, blank=False, max_length=255)
    page = models.ForeignKey(
        to=Page,
        on_delete=models.CASCADE,
        blank=True,
        default=None,
        null=True,
        related_name="meta_filter_value_page",
    )