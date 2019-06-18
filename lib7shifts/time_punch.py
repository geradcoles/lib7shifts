"""
This library is used for all time-punch related code and objects.
"""
import datetime
#import cachetools
from . import base
from . import dates
from . import users
from . import shifts
from . import locations
from . import roles
from . import departments

ENDPOINT = '/time_punches'

#@cachetools.cached(cache=cachetools.LRUCache(maxsize=1000))
def get_punch(punch_id, client=None):
    """Implements the 'Read' operation from the 7shifts API. Supply a punch ID.
    Returns a :class:`TimePunch` object.
    """
    response = client.call("{}/{}".format(ENDPOINT, punch_id))
    try:
        punch_id = response['data']['time_punch']
        return TimePunch(**response['data'], client=client)
    except KeyError:
        raise exceptions.EntityNotFoundError('Time Punch', punch_id)

def list_punches(**kwargs):
    """Implements the 'List' method for Time Punches as outlined in the API,
    and returns a TimePunchList object representing all the punches. Provide a
    'client' parameter with an active :class:`lib7shifts.APIClient`
    object.

    Supports the same kwargs as the API arguments, such as:

    - clocked_in[gte] (datetime format optional)
    - clocked_in[lte] (datetime format optional)
    - clocked_out[gte] (datetime format optional)
    - clocked_out[lte] (datetime format optional)
    - location_id
    - department_id
    - limit
    - offset
    - order_field
    - order_dir

    See https://www.7shifts.com/partner-api#crud-toc-time-punches-list for
    details.
    """
    client = kwargs.pop('client')
    api_params = {}
    for name, val in kwargs.items():
        if isinstance(val, datetime.datetime):
            api_params[name] = dates.from_datetime(val)
        else:
            api_params[name] = val
    response = client.call("{}".format(ENDPOINT), params=api_params)
    return TimePunchList.from_api_data(response['data'], client=client)

class TimePunch(base.APIObject):
    """
    An object representing a time punch, including break data. Requires the
    `time_punch` parameter to be useful, but can also be seeded with:

    - time_punch_break
    - location
    - department
    - shift
    - user

    All of the above come in directly from an API 'Read' call, and thus are
    directly present whenever a :class:`TimePunch` is instantiated from a call
    to :func:`api_read`. However, :class:`TimePunch` has several fetch methods
    that will fall back to the API whenever details about the above are not
    present, and will return appropriate objects, which are cached internally,
    so subsequent calls to retrieve the same location will not keep hitting
    the 7shifts API.
    """
    def __init__(self, **kwargs):
        super(TimePunch, self).__init__(**kwargs)
        self._breaks = None
        self._user = None
        self._role = None
        self._location = None
        self._department = None
        self._shift = None

    def __getattr__(self, name):
        """
        Because this class is passed a nested dictionary, the parent's
        behaviour needs to be overloaded to look deeper in the dict to find its
        attributes.
        """
        return self._data['time_punch'][name]

    def get_shift(self):
        """Return a :class:`lib7shifts.shifts.Shift`
        object corresponding to the shift that the punch was associated with.
        An API fetch will be used if this object wasn't initially seeded with
        shift data from a :func:`read` operation.
        """
        if self._shift is None:
            self._shift = shifts.get_shift(self.shift_id, client=self.client)
        return self._shift

    def get_user(self):
        """Return a :class:`lib7shfits.users.User` class for the user.
        An API fetch will be used if this object wasn't initially seeded with
        user data from a :func:`read` operation."""
        if self._user is None:
            self._user = users.get_user(self.user_id, client=self.client)
        return self._user

    def get_role(self):
        """Return a :class:`lib7shifts.roles.Role` object for the role
        specified by the punch.
        An API fetch will be used to fulfill this call."""
        if self._role is None:
            self._role = roles.get_role(self.role_id, client=self.client)
        return self._role

    def get_location(self):
        """Returns a :class:`lib7shifts.locations.Location` object corresponding
        to the location of the punch.
        An API fetch will be used if this object wasn't initially seeded with
        location data from a :func:`read` operation."""
        if self._location is None:
            self._location = locations.get_location(
                self.location_id, client=self.client)
        return self._location

    def get_department(self):
        """Returns a :class:`lib7shifts.departments.Department` object
        corresponding to the punch.
        An API fetch will be used if this object wasn't initially seeded with
        department data from a :func:`read` operation."""
        if self._department is None:
            self._department = departments.get_department(
                self.department_id, client=self.client)
        return self._department

    @property
    def clocked_in(self):
        "Returns a :class:`datetime.datetime` object for the punch-in time"
        return dates.to_datetime(self._data['time_punch']['clocked_in'])

    @property
    def clocked_out(self):
        "Returns a :class:`datetime.datetime` object for the punch-out time"
        return dates.to_datetime(self._data['time_punch']['clocked_out'])

    @property
    def created(self):
        "Returns a :class:`datetime.datetime` object for punch creation time"
        return dates.to_datetime(self._get_punch_attr('created'))

    @property
    def modified(self):
        """Returns a :class:`datetime.datetime` object corresponding to the
        last time this punch was modified"""
        return dates.to_datetime(self._get_punch_attr('modified'))

    @property
    def breaks(self):
        """Returns a TimePunchBreakList object with all breaks
        for this punch"""
        if self._breaks is None:
            self._breaks = TimePunchBreakList.from_api_data(
                self._data['time_punch_break'])
        return self._breaks

    def __str__(self):
        fmt = "Time Punch\n  UserID: {}\n  LocationID: {}\n  DepartmentID: {}\n"
        fmt += "  Clocked In: {}\n  Clock Out: {}"
        return fmt.format(
            self.user_id, self.location_id, self.department_id,
            self._data['time_punch']['clocked_in'],
            self._data['time_punch']['clocked_out'])

class TimePunchList(list):
    """
    Object representing a list of TimePunch objects, including vivifying
    them from API response data.
    """

    @classmethod
    def from_api_data(cls, data, client=None):
        """Provide this method with the punch data returned directly from
        the API in raw format.
        """
        obj_list = []
        for item in data:
            obj_list.append(TimePunch(**item, client=client))
        return cls(obj_list)

class TimePunchBreak(base.APIObject):
    "Represent a Time Punch Break"
    def __init__(self, **kwargs):
        super(TimePunchBreak, self).__init__(**kwargs)
        self._user = None

    @property
    def in_time(self):
        """Returns a :class:`datetime.datetime` object corresponding to the
        time the break started"""
        return dates.to_datetime(self._data['in'])

    @property
    def out_time(self):
        """Returns a :class:`datetime.datetime` object corresponding to the
        time the break ended"""
        return dates.to_datetime(self._data['out'])

    def get_user(self):
        """Perform an API fetch and return a :class:`lib7shfits.users.User`
        class for the user"""
        if self._user is None:
            self._user = users.get_user(self.user_id, client=self.client)
        return self._user

    @property
    def created(self):
        raise NotImplementedError

    @property
    def modified(self):
        raise NotImplementedError

class TimePunchBreakList(list):
    """
    An interable list of TimePunchBreak objects.
    """

    @classmethod
    def from_api_data(cls, data, client=None):
        """Provide this method with the break data returned directly from
        the API in raw format.
        """
        obj_list = []
        for item in data:
            obj_list.append(TimePunchBreak(**item, client=client))
        return cls.__init__(obj_list)
