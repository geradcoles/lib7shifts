"""usage:
  7shifts log_book category_list <company_id> [options]
  7shifts log_book list <company_id> <start_date> <end_date> [options]
  7shifts log_book get <company_id> <log_book_id>

Filter parameters for list operations:

  --location-id=SS  integer location ID for log book entries
  --message=TT      text to search for within post entries
  --user-id=DD      specify the ID of a user to searchf or posts from

General parameters:

  -h --help         show this screen
  -v --version      show version information
  -d --debug        enable debug logging (low-level)

<start_date> and <end_date> must be in YYYY-MM-DD format.

You must provide a 7shifts access token with an environment variable called
ACCESS_TOKEN_7SHIFTS.

"""

import logging
import lib7shifts
from .common import get_7shifts_client, print_api_data, print_api_object


LOG = logging.getLogger("lib7shifts.7shifts.log_book")


def list_log_book_posts(args):
    "Return a list of log book posts from the API"
    client = get_7shifts_client()
    kwargs = {
        "posted_date_gte": args.get("<start_date>"),
        "posted_date_lte": args.get("<end_date>"),
    }
    if args.get("--location-id"):
        kwargs["location_id"] = args.get("--location-id")
    return lib7shifts.list_log_book_posts(client, args.get("<company_id>"), **kwargs)


def get_log_book_post(args):
    "Get a single log book post from the API"
    client = get_7shifts_client()
    return lib7shifts.get_log_book_post(
        client, args.get("<company_id>"), args.get("<log_book_id>")
    )


def list_categories(args):
    "Fetch a list of log book categories from the API"
    client = get_7shifts_client()
    return lib7shifts.list_log_book_categories(client, args.get("<company_id>"))


def main(**args):
    """Run the cli-specified action (list, sync, init)"""
    if args.get("list", False):
        count = print_api_data(list_log_book_posts(args))
        LOG.info("%d posts found", count)
    elif args.get("get"):
        print_api_object(get_log_book_post(args))
    elif args.get("category_list"):
        print_api_data(list_categories(args))
    else:
        raise RuntimeError("no valid action in args")
    return 0
