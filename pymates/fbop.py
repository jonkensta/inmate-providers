"""FBOP inmate query implementation."""

import typing
import logging
import datetime

import aiohttp

from .decorators import log_query_by_inmate_id, log_query_by_name

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


def format_inmate_id(inmate_id: typing.Union[str, int]) -> str:
    """Format FBOP inmate IDs."""
    try:
        inmate_id = int(str(inmate_id).replace("-", ""))
    except ValueError as exc:
        raise ValueError("inmate ID must be a number") from exc

    inmate_id = f"{inmate_id:08d}"

    if len(inmate_id) != 8:
        raise ValueError("inmate ID must be less than 8 digits")

    return inmate_id[0:5] + "-" + inmate_id[5:8]


class QueryResult(typing.TypedDict):
    """Result of a FBOP query."""

    id: str
    jurisdiction: typing.Literal["Federal"]

    first_name: str
    last_name: str

    unit: str

    race: typing.Optional[str]
    sex: typing.Optional[str]

    url: typing.Literal[None]
    release: typing.Optional[str | datetime.date]

    datetime_fetched: datetime.datetime


async def _query(
    last_name: str = "",
    first_name: str = "",
    inmate_id: str = "",
    timeout: typing.Optional[float] = None,
) -> typing.List[QueryResult]:
    """Private helper for querying FBOP."""

    params = {
        "age": "",
        "nameMiddle": "",
        "output": "json",
        "race": "",
        "sex": "",
        "todo": "query",
        "nameLast": last_name,
        "nameFirst": first_name,
        "inmateNum": inmate_id,
    }

    timeout = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(URL, params=params) as response:
            json = await response.json()

    try:
        data = json["InmateLocator"]
    except KeyError:
        return []

    def data_to_inmate(entry):
        inmate = {}

        inmate["id"] = entry["inmateNum"]
        inmate["jurisdiction"] = "Federal"

        inmate["first_name"] = entry["nameFirst"]
        inmate["last_name"] = entry["nameLast"]

        inmate["unit"] = entry["faclCode"] or None

        inmate["race"] = entry.get("race")
        inmate["sex"] = entry.get("sex")
        inmate["url"] = None

        def parse_date(datestr):
            return datetime.datetime.strptime(datestr, "%m/%d/%Y").date()

        try:
            actual_release = parse_date(entry["actRelDate"])
        except ValueError:
            LOGGER.debug("Failed to parse actual release date '%s", entry["actRelDate"])
            actual_release = None

        try:
            projected_release = parse_date(entry["projRelDate"])
        except ValueError:
            LOGGER.debug(
                "Failed to parse projected release date '%s", entry["projRelDate"]
            )
            projected_release = None

        inmate["release"] = (
            actual_release
            or projected_release
            or entry["projRelDate"]
            or entry["actRelDate"]
            or None
        )

        if inmate["release"] is None:
            LOGGER.debug("Failed to retrieve any release date.")

        inmate["datetime_fetched"] = datetime.datetime.now()

        return inmate

    inmates = map(data_to_inmate, data)

    def is_in_texas(inmate):
        return inmate["unit"] in set.union(TEXAS_UNITS, SPECIAL_UNITS)

    inmates = filter(is_in_texas, inmates)

    def has_not_been_released(inmate):
        try:
            released = datetime.date.today() >= inmate["release"]
        except TypeError:
            # release can be a string for life sentence, etc
            released = False

        return not released

    inmates = filter(has_not_been_released, inmates)

    return list(inmates)


@log_query_by_name(LOGGER)
async def query_by_name(first, last, **kwargs):
    """Query the FBOP database with an inmate name."""
    return await _query(first_name=first, last_name=last, **kwargs)


@log_query_by_inmate_id(LOGGER)
async def query_by_inmate_id(inmate_id: str | int, **kwargs):
    """Query the FBOP database with an inmate id."""
    try:
        inmate_id = format_inmate_id(inmate_id)
    except ValueError as exc:
        msg = f"'{inmate_id}' is not a valid Texas inmate number"
        raise ValueError(msg) from exc

    return await _query(inmate_id=inmate_id, **kwargs)
