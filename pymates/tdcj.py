"""TDCJ inmate query implementation."""

import contextlib
import datetime
import logging
import subprocess
import typing
import urllib.request
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from nameparser import HumanName  # type: ignore

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

    url: typing.Optional[str]
    release: typing.Optional[str | datetime.date]

    datetime_fetched: datetime.datetime


def _curl_search_url(
    last_name: str = "",
    first_name: str = "",
    inmate_id: str = "",
    timeout: float | None = None,
):
    cmd = [
        "curl",
        "--ipv4",
        "-d",
        "btnSearch=Search",
        "-d",
        "gender=ALL",
        "-d",
        "race=ALL",
        "-d",
        f"tdcj={inmate_id}",
        "-d",
        f"lastName={last_name}",
        "-d",
        f"firstName={first_name}",
        "-d",
        "page=index",
        "-d",
        "sid=",
        SEARCH_URL,
    ]

    # Execute the command
    result = subprocess.run(
        cmd,
        capture_output=True,  # Capture stdout and stderr
        text=True,
        check=True,
        timeout=timeout,
    )

    return result.stdout


def _query(  # pylint: disable=too-many-locals
    last_name: str = "",
    first_name: str = "",
    inmate_id: str = "",
    timeout: float | None = None,
) -> list[QueryResult]:
    """Private helper for querying TDCJ."""

    html = _curl_search_url(last_name, first_name, inmate_id, timeout)

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"class": "tdcj_table"})

    if table is None or not isinstance(table, Tag):
        LOGGER.debug("Failed to find TDCJ table.")
        return []

    for linebreak in table.find_all("br"):
        linebreak.replace_with(" ")

    header_tag = table.find("thead")
    if header_tag is None or not isinstance(header_tag, Tag):
        LOGGER.debug("Failed to find TDCJ table header.")
        return []

    body_tag = table.find("tbody")
    if body_tag is None or not isinstance(body_tag, Tag):
        LOGGER.debug("Failed to find TDCJ table body.")
        return []

    header = header_tag.find("tr")
    if header is None or not isinstance(header, Tag):
        LOGGER.debug("Failed to find TDCJ table header row.")
        return []

    keys = [th.get_text(" ", strip=True) for th in header.find_all("th")]
    rows: list[Tag] = body_tag.find_all("tr")

    def row_to_inmate(row: Tag):
        """Convert TDCJ table row to inmate dictionary."""

        cells = row.find_all(["th", "td"])
        values = [c.get_text(" ", strip=True) for c in cells]
        if not values:
            return None

        entry = dict(zip(keys, values))
        anchor = row.find("a")
        entry["href"] = anchor.get("href") if isinstance(anchor, Tag) else None

        name = HumanName(entry.get("Name", ""))
        first: str = name.first
        last: str = name.last

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
            first_name=first,
            last_name=last,
            unit=entry["Unit of Assignment"],
            race=entry.get("Race", None),
            sex=entry.get("Gender", None),
            url=url,
            release=release,
            datetime_fetched=datetime.datetime.now(),
        )

    return [inmate for row in rows if (inmate := row_to_inmate(row)) is not None]


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
