"""
Base module for 7shifts API support. This module imports all of the user-facing
classes and functions from the other modules in lib7shifts, so you only need to
import this module to use the full suite, eg::

    from lib7shifts import get_client, list_punches
    client = get_client(access_token='YOUR_TOKEN')
    punches = list_punches(client, **{'clocked_in[gte]': '2019-06-07'})
    for punch in punches:
        print(punch)

Note that this code currently only supports access tokens rather than OAUTH.

"""
import os
import logging
import datetime
import json
import certifi
import urllib3

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode
from .time_punches import (
    get_punch,
    list_punches,
    TimePunch,
    TimePunchBreak,
    TimePunchBreakList,
)
from .locations import get_location, list_locations, Location
from .shifts import get_shift, list_shifts, Shift
from .companies import get_company, list_companies, Company
from .users import get_user, list_users, User
from .wages import list_user_wages, Wage, WageList
from .assignments import list_user_assignments, Assignments
from .roles import get_role, list_roles, Role
from .departments import get_department, list_departments, Department
from .events import (
    create_event,
    get_event,
    update_event,
    delete_event,
    list_events,
    Event,
)
from .receipts import (
    get_receipt,
    create_receipt,
    update_receipt,
    list_receipts,
    Receipt,
)
from .hours_wages import get_hours_and_wages_report
from .daily_sales_labor import get_daily_sales_and_labor
from .whoami import get_whoami
from . import dates
from . import exceptions

#: Specify the name of the environment variable where this code expects to
#: find the 7shifts API key, if not provided by the user directly.
ACCESS_TOKEN_ENVVAR = "ACCESS_TOKEN_7SHIFTS"


def get_client(access_token=None, **kwargs):
    """Returns an :class:`APIClient7Shifts` object.
    If no access_token is provided, local environment variable
    defined in :attr:`ACCESS_TOKEN_ENVVAR` above will be used (if present)"""
    if access_token is None:
        access_token = get_access_token_from_env()
    return APIClient7Shifts(access_token=access_token, **kwargs)


def get_access_token_from_env():
    """Returns the ACCESS_TOKEN_ENVVAR environment variable, raises an
    AssertionError if it is missing"""
    try:
        return os.environ[ACCESS_TOKEN_ENVVAR]
    except KeyError:
        raise AssertionError(
            "No access token provided and {} not found in environment".format(
                ACCESS_TOKEN_ENVVAR
            )
        )


class APIClient7Shifts(object):
    """
    7shifts API v2 client.

    Natively uses urllib3 connection pooling and includes support for rate
    limiting with a RateLimiter from the `apiclient` module. This code was
    originally based on the `apiclient` library, but has diverged substantially
    enough to be something all its own. Still, thanks to Andrey Petrov for the
    original design and inspiration.
    """

    BASE_URL = "https://api.7shifts.com/v2"
    ENCODING = "utf8"
    KEEP_ALIVE = True
    USER_AGENT = "py-lib7shifts"
    API_VERSION = "2023-06-01"

    def __init__(self, **kwargs):
        """
        Supported kwargs:

        - access_token: the api key to use for requests (required)
        - rate_limit_lock - from apiclient.ratelimiter module
        """
        self.log = logging.getLogger(self.__class__.__name__)
        self.access_token = kwargs.pop("access_token")
        self.rate_limit_lock = kwargs.pop("rate_limit_lock", None)
        self.__connection_pool = None

    def get_endpoint(self, endpoint, **urlopen_kw):
        """Directly make a GET call against `endpoint` with the defined
        urlopen_kw args"""
        return self._request("GET", endpoint, **urlopen_kw)

    def read(self, endpoint, item_id, **urlopen_kw):
        """Perform Reads against 7shifts API for the specified endpoint/ID.
        Pass parameters using the `fields` kwarg."""
        return self.get_endpoint("{}/{}".format(endpoint, item_id), **urlopen_kw)

    def create(self, endpoint, **urlopen_kw):
        """Performs Create operations in the 7shifts API
        IMPORTANT: Pass POST data using the ``body`` kwarg, unencoded. The
        data will be JSON encoded before posting.
        """
        body = json.dumps(urlopen_kw.pop("body", dict()))
        return self._request("POST", endpoint, body=body, **urlopen_kw)

    def update(self, endpoint, item_id, method="PUT", **urlopen_kw):
        """Perform Update operations for the given endpoint/item_id
        IMPORTANT: Pass PUT data using the ``body`` kwarg, unencoded. The
        data will be JSON encoded before posting.
        """
        body = json.dumps(urlopen_kw.pop("body", dict()))
        return self._request(
            method.upper(), "{}/{:d}".format(endpoint, item_id), body=body, **urlopen_kw
        )

    def delete(self, endpoint, item_id, **urlopen_kw):
        "Delete the item at the given endpoint with the given ID"
        return self._request(
            "DELETE", "{}/{:d}".format(endpoint, item_id), **urlopen_kw
        )

    def list(self, endpoint, **urlopen_kw):
        """Implements the List method for 7shifts API objects.
        Pass a list of parameters using the `fields` kwarg.
        By default, datetime objects will be serialized in YYYY-MM-DD format,
        since that's the most common case in the API. If you need a specific
        format, such as full date time, pass in as a string-formatted date.
        """
        fields = {}
        for key, val in urlopen_kw.get("fields", {}).items():
            # print('item: {}'.format(key))
            if isinstance(val, bool):
                if val:
                    fields[key] = "true"
                else:
                    fields[key] = "false"
            elif isinstance(val, (datetime.date, datetime.datetime)):
                # This is the most common use case. Callers that need a diff
                # format must provide a formatted string.
                fields[key] = val.strftime("%Y-%m-%d")
            else:
                fields[key] = val
        urlopen_kw["fields"] = fields
        return self._request("GET", endpoint, **urlopen_kw)

    @property
    def _connection_pool(self):
        """
        Returns an initialized connection pool. If the pool becomes broken
        in some way, it can be destroyed with :meth:`_destroy_pool` and a
        subsequent call to this attribute will initialize a new pool.
        """
        if self.__connection_pool is None:
            self._create_pool()
        return self.__connection_pool

    def _request(self, method, path, **urlopen_kw):
        """
        Wrapper around the ConnectionPool request method to add rate limiting
        and response handling.

        HTTP GET parameters should be passed as 'fields', and will be properly
        encoded by urllib3 and correctly placed into the request uri. For
        POST and PUT operations, the ``body`` kwarg should be supplied and
        already in encoded form (that's generally done by one of the methods
        above.)

        Any headers passed as kwargs will be merged with underlying ones that
        are required to make the API function properly, with the headers
        passed here overriding built-ins (such as to override the user_agent
        for a particular request).
        """
        try:
            self.rate_limit_lock.acquire()
        except AttributeError:
            pass
        response = self._connection_pool.request(method.upper(), path, **urlopen_kw)
        return self._handle_response(response)

    def _destroy_pool(self):
        """
        Tear down the existing HTTP(S)ConnectionPool such that a subsequent
        call to :attr:`_connection_pool` generates a new pool to work with.
        Useful in cases where authentication timeouts occur.
        """
        self.__connection_pool = None

    def _create_pool(self):
        """Use the handy urllib3 connection_from_url helper to create a
        pool of the correct type for HTTP/HTTPS.
        This also seeds the pool with the base URL so that subsequent requests
        only use the URI portion rather than an absolute URL.

        Stores a reference to the pool for use with :attr:`_connection_pool`
        """
        headers = urllib3.util.make_headers(
            keep_alive=self.KEEP_ALIVE, user_agent=self.USER_AGENT
        )
        headers["Authorization"] = f"Bearer {self.access_token}"
        headers["x-api-version"] = self.API_VERSION
        headers["accept"] = "application/json"
        headers["content-type"] = "application/json"
        self.__connection_pool = urllib3.connectionpool.connection_from_url(
            self.BASE_URL,
            cert_reqs="CERT_REQUIRED",
            ca_certs=certifi.where(),
            headers=headers,
        )

    def _handle_response(self, response):
        """
        In the case of a normal response, deserializes the response from
        JSON back into dictionary form and returns it. In case of a response
        code of 300 or higher, raises an :class:`exceptions.APIError`
        exception.
        Note that if you are seeing weirdness in the API response data, look
        at the :attr:`ENCODING` attribute for this class.
        """
        if response.status > 299:
            raise exceptions.APIError(response.status, response=response)
        return json.loads(response.data.decode(self.ENCODING))
