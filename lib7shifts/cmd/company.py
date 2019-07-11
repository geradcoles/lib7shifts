#!/usr/bin/env python3
"""usage:
  7shifts company list [options]
  7shifts company sync [options] [--] <sqlite_db>
  7shifts company init_schema [options] [--] <sqlite_db>

  -h --help         show this screen
  -v --version      show version information
  --dry-run         does not commit data to database, but goes through inserts
  -d --debug        enable debug logging (low-level)

You must provide the 7shifts API key with an environment variable called
API_KEY_7SHIFTS.

"""
from docopt import docopt
import sys
import os
import os.path
import datetime
import sqlite3
import logging
import lib7shifts
from .util import filter_fields

DB_NAME = 'companies'
DB_TBL_SCHEMA = """CREATE TABLE IF NOT EXISTS {} (
    id PRIMARY KEY UNIQUE,
    name NOT NULL,
    created,
    modified
) WITHOUT ROWID
""".format(DB_NAME)
DB_INSERT_QUERY = """INSERT OR REPLACE INTO {}
    VALUES(?, ?, ?, ?)""".format(DB_NAME)
INSERT_FIELDS = ('id', 'name', 'created', 'modified')
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
    return cursor(args).execute(tbl_schema)


def db_sync(args):
    print("syncing database", file=sys.stderr)
    companies = get_companies()
    cursor(args).executemany(
        DB_INSERT_QUERY, filter_fields(
            companies, INSERT_FIELDS, print_rows=args.get('--debug', False)))
    if args.get('--dry-run', False):
        db_handle(args).rollback()
    else:
        db_handle(args).commit()


def get_api_key():
    try:
        return os.environ['API_KEY_7SHIFTS']
    except KeyError:
        raise AssertionError("API_KEY_7SHIFTS not found in environment")


def get_companies():
    client = lib7shifts.get_client(get_api_key())
    return lib7shifts.list_companies(client)


def main(**args):
    if args.get('list', False):
        for company in get_companies():
            print(company)
    elif args.get('sync', False):
        db_sync(args)
    elif args.get('init_schema', False):
        db_init_schema(args)
    else:
        print("no valid action in args", file=sys.stderr)
        print(args, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    args = docopt(__doc__, version='7shifts2sqlite 0.1')
    logging.basicConfig()
    if args['--debug']:
        logging.getLogger().setLevel(logging.DEBUG)
        print("arguments: {}".format(args), file=sys.stderr)
    else:
        logging.getLogger('lib7shifts').setLevel(logging.INFO)
    sys.exit(main(**args))
