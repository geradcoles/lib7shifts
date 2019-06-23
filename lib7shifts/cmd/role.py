#!/usr/bin/env python3
"""usage:
  7shifts2sqlite role list [options]
  7shifts2sqlite role sync [options] [--] <sqlite_db>
  7shifts2sqlite role init_schema [options] [--] <sqlite_db>

  -h --help         show this screen
  -v --version      show version information
  --dry-run         does not commit data to database, but goes through inserts
  -d --debug        enable debug logging (low-level)

You must provide the 7shifts API key with an environment variable called
API_KEY_7SHIFTS.

"""
from docopt import docopt
import sys, os, os.path
import datetime
import sqlite3
import logging
import lib7shifts

DB_NAME = 'roles'
DB_TBL_SCHEMA = """CREATE TABLE IF NOT EXISTS {} (
    id PRIMARY KEY UNIQUE,
    name NOT NULL,
    department_id NOT NULL,
    location_id NOT NULL,
    created,
    modified
) WITHOUT ROWID
""".format(DB_NAME)
DB_INSERT_QUERY = """INSERT OR REPLACE INTO {}
    VALUES(?, ?, ?, ?, ?, ?)""".format(DB_NAME)
INSERT_FIELDS = ('id', 'name', 'department_id', 'location_id',
                 'created', 'modified')
_DB_HNDL = None
_CRSR = None

def db_handle(args):
    global _DB_HNDL
    if _DB_HNDL is None:
        _DB_HNDL = sqlite3.connect(args.get('<sqlite_db>'))
    return _DB_HNDL

def cursor(args):
    global _CRSR
    if _CRSR is None:
        _CRSR = db_handle(args).cursor()
    return _CRSR

def db_init_schema(args):
    tbl_schema = DB_TBL_SCHEMA
    print('initializing db schema', file=sys.stderr)
    print(tbl_schema, file=sys.stderr)
    cursor(args).execute(tbl_schema)

def filter_role_fields(roles, output_fields):
    """Given a list of role dicts from 7shifts, yield a tuple per role with the
    data we need to insert"""
    for role in roles:
        row = list()
        for field in output_fields:
            val = getattr(role, field)
            if isinstance(val, datetime.datetime):
                val = val.__str__()
            row.append(val)
        print(row, file=sys.stdout)
        yield row

def db_sync(roles, args):
    print("syncing database", file=sys.stderr)
    cursor(args).executemany(
        DB_INSERT_QUERY, filter_role_fields(roles, INSERT_FIELDS))
    if args.get('--dry-run', False):
        db_handle(args).rollback()
    else:
        db_handle(args).commit()

def get_api_key():
    try:
        return os.environ['API_KEY_7SHIFTS']
    except KeyError:
        raise AssertionError("API_KEY_7SHIFTS not found in environment")

def get_roles():
    client = lib7shifts.get_client(get_api_key())
    return lib7shifts.list_roles(client)

def main(**args):
    logging.basicConfig()
    if args['--debug']:
        logging.getLogger().setLevel(logging.DEBUG)
        print("arguments: {}".format(args), file=sys.stderr)
    else:
        logging.getLogger('lib7shifts').setLevel(logging.INFO)
    if args.get('list', False):
        for role in get_roles():
            print(role)
    elif args.get('sync', False):
        db_sync(get_roles(), args)
    elif args.get('init_schema', False):
        db_init_schema(args)
    else:
        print("no valid action in args", file=sys.stderr)
        print(args, file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    args = docopt(__doc__, version='7shifts2sqlite 0.1')
    sys.exit(main(**args))