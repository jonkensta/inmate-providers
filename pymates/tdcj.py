"""TDCJ inmate query implementation."""

import logging

import urllib.error
import urllib.parse
import urllib.request

from datetime import datetime

from bs4 import BeautifulSoup
from nameparser import HumanName

LOGGER = logging.getLogger("PROVIDERS.TDCJ")

BASE_URL = "https://offender.tdcj.texas.gov"
SEARCH_PATH = "OffenderSearch/search.action"


def query_by_name(first, last, timeout=None):
    """Query the TDCJ database with an inmate name."""
    LOGGER.debug("Querying with name %s, %s", last, first)
    matches = _query_helper(firstName=first, lastName=last, timeout=timeout)

    if not matches:
        LOGGER.debug("No results were returned")
        return []

    LOGGER.debug("%d result(s) returned", len(matches))
    return matches


def query_by_inmate_id(inmate_id, timeout=None):
    """Query the TDCJ database with an inmate id."""
    try:
        inmate_id = "{:08d}".format(int(inmate_id))
    except ValueError as exc:
        msg = "{} is not a valid Texas inmate number".format(inmate_id)
        raise ValueError(msg) from exc

    LOGGER.debug("Querying with ID %s", inmate_id)
    matches = _query_helper(tdcj=inmate_id, timeout=timeout)

    if not matches:
        LOGGER.debug("No results returned")
        return []

    if len(matches) > 1:
        LOGGER.error("Multiple results were returned for an ID query")
        return matches

    LOGGER.debug("A single result was returned")
    return matches


def format_inmate_id(inmate_id):
    """Helper for formatting TDCJ inmate IDs."""
    return "{:08d}".format(int(inmate_id))


def _query_helper(timeout=None, **kwargs):
    """Private helper for querying TDCJ."""
    params = {
        "btnSearch": "Search",
        "gender": "ALL",
        "page": "index",
        "race": "ALL",
        "tdcj": "",
        "sid": "",
        "lastName": "",
        "firstName": "",
    }
    params.update(kwargs)
    params = urllib.parse.urlencode(params).encode("ascii")

    url = urllib.parse.urljoin(BASE_URL, SEARCH_PATH)

    try:
        response = urllib.request.urlopen(url, params, timeout)
    except urllib.error.URLError as exc:
        exc_class_name = exc.__class__.__name__
        LOGGER.error("Query returned %s request exception", exc_class_name)
        raise

    soup = BeautifulSoup(response.read(), "html.parser")
    table = soup.find("table", {"class": "tdcj_table"})

    if table is None:
        return []

    for linebreak in table.find_all("br"):
        linebreak.replace_with(" ")

    rows = iter(table.findAll("tr"))

    # First row contains nothing.
    next(rows)

    # Second row contains the keys.
    keys = [ele.text.strip() for ele in next(rows).find_all("th")]

    def row_to_entry(row):
        values = [ele.text.strip() for ele in row.find_all("td")]
        entry = dict(zip(keys, values))
        entry["href"] = row.find("a").get("href")
        return entry

    entries = map(row_to_entry, rows)
    inmates = map(_entry_to_inmate, entries)
    inmates = list(inmates)

    return inmates


def _entry_to_inmate(entry):
    """Convert TDCJ inmate entry to inmate dictionary."""
    inmate = dict()

    inmate["id"] = entry["TDCJ Number"]
    inmate["jurisdiction"] = "Texas"

    name = HumanName(entry.get("Name", ""))
    inmate["first_name"] = name.first
    inmate["last_name"] = name.last

    inmate["unit"] = entry["Unit of Assignment"]

    inmate["race"] = entry.get("Race", None)
    inmate["sex"] = entry.get("Gender", None)

    if "href" in entry:
        inmate["url"] = urllib.parse.urljoin(BASE_URL, entry["href"])

    else:
        inmate["url"] = None

    release_string = entry["Projected Release Date"]
    try:
        release = datetime.strptime(release_string, "%Y-%m-%d").date()
    except ValueError:
        release = release_string
        LOGGER.debug("Failed to convert release date to date: %s", release)
    finally:
        inmate["release"] = release

    inmate["datetime_fetched"] = datetime.now()

    LOGGER.debug(
        "%s, %s #%s: MATCHES", inmate["last_name"], inmate["first_name"], inmate["id"]
    )

    return inmate
