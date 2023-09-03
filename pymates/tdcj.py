"""TDCJ inmate query implementation."""

import datetime
import logging
import typing
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup, Tag
from nameparser import HumanName

from .decorators import log_query_by_name, log_query_by_inmate_id


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


async def _query(  # pylint: disable=too-many-locals
    last_name: str = "",
    first_name: str = "",
    inmate_id: str = "",
    timeout: typing.Optional[float] = None,
) -> list[QueryResult]:
    """Private helper for querying TDCJ."""

    data = {
        "btnSearch": "Search",
        "gender": "ALL",
        "page": "index",
        "race": "ALL",
        "sid": "",
        "tdcj": inmate_id,
        "lastName": last_name,
        "firstName": first_name,
    }

    client_timeout = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=client_timeout) as session:
        async with session.post(SEARCH_URL, data=data) as response:
            html = await response.text()

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

        url = build_url(entry["href"]) if "href" in entry else None

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
async def query_by_name(first, last, **kwargs):
    """Query the TDCJ database with an inmate name."""
    return await _query(first_name=first, last_name=last, **kwargs)


@log_query_by_inmate_id(LOGGER)
async def query_by_inmate_id(inmate_id: str | int, **kwargs):
    """Query the TDCJ database with an inmate id."""
    try:
        inmate_id = format_inmate_id(inmate_id)
    except ValueError as exc:
        msg = f"'{inmate_id}' is not a valid Texas inmate number"
        raise ValueError(msg) from exc

    return await _query(inmate_id=inmate_id, **kwargs)
