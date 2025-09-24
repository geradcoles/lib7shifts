"""
This module covers Log Book Post related methods and objects for the 7shifts API.

See https://developers.7shifts.com/reference/listlogbookposts for details.
"""

from . import base
from . import dates
from . import exceptions

ENDPOINT = "/v2/company/{company_id}/log_book_posts"


def list_log_book_posts(client, company_id, **kwargs):
    """Retrieve a list of schedule events for the given timeframe.

    Supported kwargs::

        - location_id: the location bound to the schedule events
        - log_book_category_id
        - user_id
        - date: a YYYY-MM-DD formatted date (required)
        - posted_date_gte: YYYY-MM-DD
        - posted_date_lte: YYYY-MM-DD
        - message
        - order_field: date or id
        - order_dir: asc or des

    """
    for item in client.list(ENDPOINT.format(company_id=company_id), fields=kwargs)[
        "data"
    ]:
        yield LogBookPost(**item)


def get_log_book_post(client, company_id, post_id):
    """Implements the 'Read' method from the 7shifts API for events.
    Returns a :class:`Event` object."""
    response = client.read(ENDPOINT.format(company_id=company_id), post_id)
    try:
        return LogBookPost(**response["data"])
    except KeyError:
        raise exceptions.EntityNotFoundError("LogBookPost", post_id)


class LogBookPost(base.APIObject):
    """
    Represents the log_book_post object as defined in the API. Attributes defined by
    the API include::

    - id
    - uuid
    - location_id
    - user_id
    - date
    - message
    - log_book_category_id
    - log_book_comment_count
    - created
    - company_id
    - attachments

    """
