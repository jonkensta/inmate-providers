"""TDCJ inmate query implementation."""

import contextlib
import datetime
import logging
import ssl
import typing
import urllib.request
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from nameparser import HumanName

from .decorators import log_query_by_inmate_id, log_query_by_name

LOGGER = logging.getLogger("PROVIDERS.TDCJ")

BASE_URL = "https://inmate.tdcj.texas.gov"
SEARCH_PATH = "InmateSearch/search.action"
SEARCH_URL = urljoin(BASE_URL, SEARCH_PATH)


def format_inmate_id(inmate_id: typing.Union[int, str]) -> str:
    """Format a TDCJ inmate ID."""
    inmate_id = int(inmate_id)
    return f"{inmate_id:08d}"


class QueryResult(typing.TypedDict):
    """Result of a TDCJ query."""

    id: str
    jurisdiction: typing.Literal["Texas"]

    first_name: str
    last_name: str

    unit: str

    race: typing.Optional[str]
    sex: typing.Optional[str]

    url: str
    release: typing.Optional[str | datetime.date]

    datetime_fetched: datetime.datetime


@contextlib.contextmanager
def _post_search_form(data: dict, timeout: float | None = None):
    data = {
        "btnSearch": "Search",
        "gender": "ALL",
        "page": "index",
        "race": "ALL",
        "sid": "",
        "tdcj": "",
        "lastName": "",
        "firstName": "",
        **data,
    }

    encoded = urllib.parse.urlencode(data).encode("utf-8")

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    request = urllib.request.Request(SEARCH_URL, data=encoded, method="POST")

    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        yield response


def _query(  # pylint: disable=too-many-locals
    last_name: str = "",
    first_name: str = "",
    inmate_id: str = "",
    timeout: float | None = None,
) -> list[QueryResult]:
    """Private helper for querying TDCJ."""

    data = {
        "lastName": last_name,
        "firstName": first_name,
        "tdcj": inmate_id,
    }

    with _post_search_form(data, timeout=timeout) as response:
        charset = response.info().get_content_charset() or "utf-8"
        text = response.read().decode(charset)

    html = text
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"class": "tdcj_table"})

    if table is None or not isinstance(table, Tag):
        return []

    for linebreak in table.find_all("br"):
        linebreak.replace_with(" ")

    rows = iter(table.find_all("tr"))

    try:
        next(rows)  # First row contains nothing.
        header = next(rows)
    except StopIteration:
        return []

    # Second row contains the column names.
    keys = [ele.text.strip() for ele in header.find_all("th")]

    def row_to_entry(row):
        values = [ele.text.strip() for ele in row.find_all("td")]
        entry = dict(zip(keys, values))
        entry["href"] = row.find("a").get("href")
        return entry

    entries = map(row_to_entry, rows)

    def entry_to_inmate(entry: dict):
        """Convert TDCJ inmate entry to inmate dictionary."""

        name = HumanName(entry.get("Name", ""))

        def build_url(href):
            return urljoin(BASE_URL, href)

        url = build_url(str(entry["href"])) if "href" in entry else None

        def parse_release_date(release):
            return datetime.datetime.strptime(release, "%Y-%m-%d").date()

        release = entry["Projected Release Date"]

        try:
            release = parse_release_date(release)
        except ValueError:
            LOGGER.debug("Failed to parse release date '%s'", release)

        return QueryResult(
            id=entry["TDCJ Number"],
            jurisdiction="Texas",
            first_name=name.first,
            last_name=name.last,
            unit=entry["Unit of Assignment"],
            race=entry.get("Race", None),
            sex=entry.get("Gender", None),
            url=url,
            release=release,
            datetime_fetched=datetime.datetime.now(),
        )

    return list(map(entry_to_inmate, entries))


@log_query_by_name(LOGGER)
def query_by_name(first, last, **kwargs):
    """Query the TDCJ database with an inmate name."""
    return _query(first_name=first, last_name=last, **kwargs)


@log_query_by_inmate_id(LOGGER)
def query_by_inmate_id(inmate_id: str | int, **kwargs):
    """Query the TDCJ database with an inmate id."""
    try:
        inmate_id = format_inmate_id(inmate_id)
    except ValueError as exc:
        msg = f"'{inmate_id}' is not a valid Texas inmate number"
        raise ValueError(msg) from exc

    return _query(inmate_id=inmate_id, **kwargs)
