lib7shifts
==========

A user-created library/CLI for interacting with the 7shifts REST API in
Python3. This library is not officially supported or maintained by 7shifts, nor
is its use endorsed by 7shifts. As a user-made library, no warranties or
guarantees of future interoperability may be made, and features are included
solely at the discretion of our package maintainer. If you would like to help
us support and maintain this project, please reach out on Github.

Before using this library, it's a good idea to be familiar with 7shifts,
itself, and read the API documentation, here:

https://developers.7shifts.com/reference/introduction

Here's a quick example of the code usage::

    import lib7shifts
    # you can set your access token in ACCESS_TOKEN_7SHIFTS instead of below
    client = lib7shifts.get_client(access_token='YOUR_TOKEN')
    for shift in lib7shifts.list_shifts(client, user_id=1000):
        print(shift)

Object Model
------------
This package includes modules for each of the objects represented by the
7shifts API, including:

- Company
- Location
- Department
- Event (Scheduled)
- Role
- User
- Shift
- TimePunch
- TimePunchBreak
- Wage
- Receipt (sales records)
- Reports (daily_sales_labour, hours_wages modules)

The above are the object names in lib7shifts, and each object is designed to
mimic the API object representations, that is to say that they have the same
attributes and generally the same data types (except date fields, which are
converted to datetime objects). So if the API says that the ``User`` object has
an attribute called *id*, then our ``User`` class also has an attribute called
*id*, and the value is an integer. Similar for booleans, text fields, etc.

Each object is a thin wrapper around an underlying dictionary provided by
the API, but many have methods to make programming workflows simpler. For
example, objects that have a *user_id* attribute embedded within them also
have a ``get_user()`` method, which returns a ``lib7shifts.users.User``
representation of the user, which in turn has convenience methods for fetching
company data, and so on.

All of the objects above are defined in modules for each type, which is where
you want to look for documentation, but each one is imported directly into
the main package scope, so you need only to ``import lib7shifts`` to
access all of the objects programmatically.

Generally speaking, print calls on objects results in a simple dictionary
print of the underlying API data used to populate the object. Future code
improvements could bring better support for serialized object representations.

Functional Design Pattern
-------------------------
For speed and simplicity, functional
code is used for all supported CRUD operations (*Create, Read, Update and
Delete*, as well as *List*, a specialized version of *Read*). Each of the
objects listed above should have a ``create_[object]()`` function associated
with them, such as ``create_department()`` or ``create_event()``. Similarly,
read-type operations are done with ``get_`` or ``list_``
functions like ``get_user()`` and ``list_time_punches()``. You can probably
guess that delete operations start with the ``delete_`` prefix, and update
operations
start with the ``update_`` prefix. All of these functions take an
``APIClient7Shifts`` object as their first parameter, which is described in
more detail further below.

The new 7shifts V2 API supports the full gamut of CRUD operations for all
object types. Due to time constraints, this package
doesn't yet have every CRUD operation supported for every object type, but
it is trivial to add it now (see the ``lib7shifts.events`` and
``lib7shifts.receipts`` module for examples of a complete CRUD implementation).

All of the CRUD functions are imported directly into the main package scope,
so you simply need to ``import lib7shifts`` to get access to all of them.

Get An API Client
-----------------
Before you can do anything, you need to obtain/initialize a
``lib7shifts.APIClient7Shifts`` object, which you generally do using the
``lib7shifts.get_client`` function, as follows::

    import lib7shifts
    client = lib7shifts.get_client(access_token='YOUR_TOKEN')

While a bearer token may be supplied directly as we show above, you can also
supply that token by setting the *ACCESS_TOKEN_7SHIFTS* environment variable.
Full OAUTH authentication workflows are not yet supported, but may be added
with relative simplicity if needed.

*APIClient7Shifts* contains the code that performs all of the
low-level API interaction, including defining the underlying methods used
in all CRUD operations, defining parameter/field encodings, etc. This class
was originally just a child of the *apiclient* library's ``APIClient``
class, but it outgrew that and now features very little in common with that
codebase, but an important feature is the ability to rate limit requests by
passing a ``apiclient.RateLimiter`` object to the client using the
``rate_limit_lock`` named parameter.

Events
------
Here's an example of a workflows to perform all CRUD operations for events::

    # CREATE
    event_id = lib7shifts.create_event(
        client, company_id=1234, title='Some Event',
        description='A thing is happening',
        start_date='2019-06-03', start_time='12:00:00',
        end_date='2029-06-03', end_time='15:00:00', is_multi_day=False,
        color='FBAF40', location_ids=[12345]) # location has to be a list

    # READ
    event = lib7shifts.get_event(client, company_id, event_id)
    print(event)

    # UPDATE
    event = lib7shifts.get_event(client, company_id, event_id)
    lib7shifts.update_event(
        client, company_id, event.id, start_date='2019-06-06', title='Testing',
        start_time=event.start_time, end_date=event.end_date,
        end_time=event.end_time, is_multi_day=event.is_multi_day)

    # DELETE
    lib7shifts.delete_event(client, company_id, event.id)

    # LIST
    events = lib7shifts.list_events(
        client, company_id, location_id=1234,
        start_date='2019-06-03', end_date='2019-06-04')

Locations
---------
Here are some examples::

    # List all 7shifts locations
    for location in lib7shifts.list_locations(client, company_id):
        print(location)

    # Get a particular location
    location = lib7shifts.get_location(client, company_id, 1234)
    print(location.address)


Departments
-----------
Here's an example of looping over a list of departments to print their name and
ID number::

    for department in lib7shifts.list_departments(client, company_id):
        print("{:8d}: {}".format(department.id, department.name))

Shifts
------
Shifts have two different read-based methods - ``get_shift`` and
``list_shifts``.
The *get* method is designed to find a shift based on a specified ID,
whereas the *list* method finds all the shifts matching specified criteria. For
example, here's how we find all the shifts for the user with ID 1000::

    for shift in lib7shifts.list_shifts(client, company_id, user_id=1000):
        print(shift)

Note that we are printing a ``lib7shifts.shifts.Shift`` object in the for
loop.

Time Punches
------------
This is a quick example of looping over time punches for a specific period::

    for punch in lib7shifts.list_punches(
            client, company_id, **{'clocked_in[gte]':'2019-06-10'}):
        print("{:8d} From:{} To:{} User ID: {}".format(
            punch.id, punch.clocked_in, punch.clocked_out, punch.user_id))

This example uses 7shifts' *clocked_in[gte]* parameter to find all the punches
where the user clocked in on 2019-06-10 at 12am or later (in the timezone
of the company as configured in 7shifts, itself). Because Python functions
don't directly support brackets in the parameter names, you need to either
set them up as keys in a dictionary and pass in as ``**kwargs``, or you need
to use the syntax shown here to expand a dictionary into function parameters
inline.

Command-Line Interface
----------------------

This package includes a command-line tool for dumping data from 7shifts,
either to the screen or into an SQLite database, for further manipulation or
archival purposes. In the case of this package's author, the SQLite database
is queried against with complex joins to create weekly reports for managers
to report on the effectiveness of their supervisors, such as ensuring that
staff are punching in/out near shift boundaries, not generating overtime, etc.

The CLI command is named ``7shifts`` and supports list-type operations for
all of the object types listed earlier. See ``7shifts --help`` for a list of
supported objects and switches. And use ``7shifts [object] --help`` for a
list of options specific to the object type being queried.

You will need to set up an environment variable called
*ACCESS_TOKEN_7SHIFTS*, and populate it with your 7shifts API key, ensuring
that the environment variable is present in the scope where you run these
commands (generally, run ``export ACCESS_TOKEN_7SHIFTS=YOUR_TOKEN`` in the
shell environment where you run this command).

Here's an example of dumping all the shifts for a specific department::

    7shifts shift list 1234 --start=2019-07-01 --dept-id=93813 # 1234 = company

In addition to the normal objects supported by the documented API, the 7shifts
CLI also supports dumping daily sales and labour reports::

    7shifts daily_sales_labor 12345 2019-06-01 2019-06-30 # 12345 = location id

Hint: To get a list of your location ID's, use ``7shifts location list``.
