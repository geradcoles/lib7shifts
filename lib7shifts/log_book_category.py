"""
This module covers Log Book Post related methods and objects for the 7shifts API.

See https://developers.7shifts.com/reference/listlogbookposts for details.
"""

from . import base
from . import dates
from . import locations
from . import exceptions

ENDPOINT = "/v2/company/{company_id}/log_book_categories"


def list_log_book_categories(client, company_id, **kwargs):
    """Retrieve a list of log book categories for the given company.

    Supported kwargs::

        - None

    """
    for item in client.list(ENDPOINT.format(company_id=company_id), fields=kwargs)[
        "data"
    ]:
        yield LogBookCategory(**item)


class LogBookCategory(base.APIObject):
    """
    Represents the log_book_category object as defined in the API. Attributes defined by
    the API include:

    - id
    - company_id
    - name
    - col
    - sort
    - field_type
    - notify
    - required
    - created
    - uuid

    """
