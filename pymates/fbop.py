"""FBOP inmate query implementation."""

import json
import urllib
import logging
from datetime import date, datetime

LOGGER = logging.getLogger("PROVIDERS.FBOP")

URL = "https://www.bop.gov/PublicInfo/execute/inmateloc"

TEXAS_UNITS = {
    "BAS",
    "BML",
    "BMM",
    "BMP",
    "BSC",
    "BIG",
    "BRY",
    "CRW",
    "EDN",
    "FTW",
    "DAL",
    "HOU",
    "LAT",
    "REE",
    "RVS",
    "SEA",
    "TEX",
    "TRV",
}

SPECIAL_UNITS = {"TEMP RELEASE", "IN TRANSIT"}


def query_by_name(first, last, timeout=None):
    """Query the FBOP database with an inmate name."""
    LOGGER.debug("Querying with name %s, %s", last, first)
    matches = _query_helper(nameFirst=first, nameLast=last, timeout=timeout)

    if not matches:
        LOGGER.debug("No results were returned")
        return []

    LOGGER.debug("%d result(s) returned", len(matches))
    return matches


def query_by_inmate_id(inmate_id, timeout=None):
    """Query the FBOP database with an inmate ID."""
    try:
        inmate_id = format_inmate_id(inmate_id)
    except ValueError as exc:
        msg = f"'{inmate_id}' is not a valid Federal inmate number"
        raise ValueError(msg) from exc

    LOGGER.debug("Querying with ID %s", inmate_id)
    matches = _query_helper(inmateNum=inmate_id, timeout=timeout)

    if not matches:
        LOGGER.debug("No results were returned")
        return []

    if len(matches) > 1:
        LOGGER.error("Multiple results were returned for an ID query")
        return matches

    LOGGER.debug("A single result was returned")
    return matches


def format_inmate_id(inmate_id):
    """Format FBOP inmate IDs."""
    try:
        inmate_id = int(str(inmate_id).replace("-", ""))
    except ValueError:
        raise ValueError("inmate ID must be a number (dashes are okay)")

    inmate_id = "{:08d}".format(inmate_id)

    if len(inmate_id) != 8:
        raise ValueError("inmate ID must be less than 8 digits")

    return inmate_id[0:5] + "-" + inmate_id[5:8]


def _query_helper(timeout=None, **kwargs):
    """Private helper for querying FBOP."""
    params = {
        "age": "",
        "inmateNum": "",
        "nameFirst": "",
        "nameLast": "",
        "nameMiddle": "",
        "output": "json",
        "race": "",
        "sex": "",
        "todo": "query",
    }
    params.update(kwargs)
    params = urllib.parse.urlencode(params).encode("ascii")

    try:
        response = urllib.request.urlopen(URL, params, timeout)
    except urllib.error.URLError as exc:
        exc_class_name = exc.__class__.__name__
        LOGGER.error("Query returned %s request exception", exc_class_name)
        raise

    try:
        data = json.loads(response.read())["InmateLocator"]
    except KeyError:
        return []

    inmates = map(_data_to_inmate, data)
    inmates = filter(_is_in_texas, inmates)
    inmates = filter(_has_not_been_released, inmates)
    inmates = list(inmates)

    for inmate in inmates:
        last, first = inmate["last_name"], inmate["first_name"]
        id_ = inmate["id"]
        LOGGER.debug("%s, %s #%s: MATCHES", last, first, id_)

    return inmates


def _has_not_been_released(inmate):
    """Private helper for checking if an inmate has been released."""
    try:
        released = date.today() >= inmate["release"]
    except TypeError:
        # release can be a string for life sentence, etc
        released = False

    return not released


def _is_in_texas(inmate):
    """Private helper for checking if an inmate is in Texas."""
    return inmate["unit"] in set.union(TEXAS_UNITS, SPECIAL_UNITS)


def _data_to_inmate(entry):
    """Private helper for formatting the FBOP JSON output."""
    inmate = dict()

    inmate["id"] = entry["inmateNum"]
    inmate["jurisdiction"] = "Federal"

    inmate["first_name"] = entry["nameFirst"]
    inmate["last_name"] = entry["nameLast"]

    inmate["unit"] = entry["faclCode"] or None

    inmate["race"] = entry.get("race")
    inmate["sex"] = entry.get("sex")
    inmate["url"] = None

    def parse_date(datestr):
        """Parse an FBOP date."""
        return datetime.strptime(datestr, "%m/%d/%Y").date()

    try:
        release = parse_date(entry["actRelDate"])
    except ValueError:
        try:
            release = parse_date(entry["projRelDate"])
        except ValueError:
            release = entry["projRelDate"]

    inmate["release"] = release
    inmate["datetime_fetched"] = datetime.now()

    return inmate
