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

from typing import List, Tuple

from web.models import Category, Page, Session
from django.core.cache import cache
from kuusi.settings import LONG_CACHE_TIMEOUT


def get_page_route(page: Page) -> List[Page]: 
    """
    Get a next page and all available pages from the given page as a start point
    """
    pages = []
    prev_page = page.previous_page
    while prev_page is not None:
        if prev_page:
            pages = [prev_page] + pages
            prev_page = prev_page.previous_page
        else:
            prev_page = None
    pages.append(page)
    next_page = page.next_page
    while next_page is not None:
        if next_page:
            pages.append(next_page)
            next_page = next_page.next_page
        else:
            next_page = None
    return pages

def get_categories_and_filtered_pages(page: Page, session: Session) -> Tuple[List[Page], List[Category]]: 
    # get the categories in an order fitting the pages


    # This structure might not change that often, use cached as often as possible, based on the user language and session version
    cache_suffix= f"categories-{session.language_code}-{session.version}"
    page_key = f"{cache_suffix}-pages"
    categories_key = f"{cache_suffix}-categories"
    cached_pages = cache.get(page_key)
    if cached_pages: 
        cached_categories =  cache.get(categories_key)
        return cached_pages, cached_categories

    pages = get_page_route(page)

    version_comp_pages = []
    chained_page: Page
    for chained_page in pages:
        if chained_page.is_visible(session):
            version_comp_pages.append(chained_page)

    categories = []
    for chained_page in version_comp_pages:
        # Child categories will be created later, when the steps are created.
        used_in_category = Category.objects.filter(
            target_page=chained_page, child_of__isnull=True
        )
        if used_in_category.count() > 0:
            categories.append(used_in_category.first())
    cache.set(page_key, version_comp_pages, LONG_CACHE_TIMEOUT)
    cache.set(categories_key, categories, LONG_CACHE_TIMEOUT)
    return version_comp_pages, categories