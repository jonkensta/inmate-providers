import json
import requests
from itertools import imap, ifilter

import logging
from datetime import date, datetime

logger = logging.getLogger('FBOP')

URL = "https://www.bop.gov/PublicInfo/execute/inmateloc"

TEXAS_UNITS = ['BAS', 'BML', 'BMM', 'BMP', 'BSC', 'BIG', 'BRY', 'CRW', 'EDN',
               'FTW', 'DAL', 'HOU', 'LAT', 'REE', 'RVS', 'SEA', 'TEX', 'TRV']

SPECIAL_UNITS = ['TEMP RELEASE', 'IN TRANSIT']


def query_by_name(first, last):
    """
    Query the FBOP database with an inmate name.
    """
    logger.debug("Querying with name %s, %s", last, first)
    matches = _query_helper(nameFirst=first, nameLast=last)
    if matches:
        logger.debug("%d result(s) returned", len(matches))
    else:
        logger.debug("No results were returned")
    return matches


def query_by_inmate_id(inmate_id):
    """
    Query the FBOP database with an inmate ID.
    """

    try:
        inmate_id = str(int(str(inmate_id).replace('-', '')))
    except ValueError:
        msg = "{} is not a valid Federal inmate number".format(inmate_id)
        raise ValueError(msg)

    inmate_id = format_inmate_id(inmate_id)
    logger.debug("Querying with ID %s", inmate_id)
    matches = _query_helper(inmateNum=inmate_id)

    if matches:
        assert len(matches) == 1
        logger.debug("A single result was returned")
        return matches[0]
    else:
        logger.debug("No results were returned")
        return None


def format_inmate_id(inmate_id):
    """
    Helper for formatting FBOP inmate IDs.
    """

    inmate_id = str(inmate_id).replace('-', '')
    inmate_id = list(inmate_id)
    num_zeros = 8 - len(inmate_id)
    inmate_id = num_zeros * ['0'] + inmate_id
    inmate_id.insert(len(inmate_id)-3, '-')
    return ''.join(inmate_id)


def _query_helper(**kwargs):
    """
    Private helper for querying FBOP.
    """

    params = {
        'age': '',
        'inmateNum': '',
        'nameFirst': '',
        'nameLast': '',
        'nameMiddle': '',
        'output': 'json',
        'race': '',
        'sex': '',
        'todo': 'query',
    }
    params.update(kwargs)

    try:
        response = requests.post(URL, params=params)
    except requests.exceptions.RequestException as exc:
        msg = "Error connecting to FBOP inmates database"
        raise requests.exceptions.ConnectionError(msg)

    data = json.loads(response.text)['InmateLocator']
    inmates = imap(_data_to_inmate, data)
    inmates = ifilter(_is_in_texas, inmates)
    inmates = ifilter(_has_not_been_released, inmates)
    inmates = list(inmates)

    for inmate in inmates:
        logger.debug(
            "%s, %s #%s: MATCHES",
            inmate['last_name'], inmate['first_name'], inmate['id']
        )

    return inmates


def _has_not_been_released(inmate):
    """
    Private helper for checking if an inmate has been released.
    """

    try:
        released = date.today() >= inmate['release']
    except TypeError:
        # release can be a string for life sentence, etc
        released = False

    return not released


def _is_in_texas(inmate):
    """
    Private helper for checking if an inmate is in Texas.
    """

    return (
        (inmate['unit'] in TEXAS_UNITS) or
        (inmate['unit'] in SPECIAL_UNITS)
    )


def _data_to_inmate(entry):
    inmate = dict()

    inmate['id'] = entry['inmateNum']
    inmate['jurisdiction'] = 'Federal'

    inmate['first_name'] = entry['nameFirst']
    inmate['last_name'] = entry['nameLast']

    inmate['unit'] = entry['faclCode'] or None

    inmate['race'] = entry.get('race')
    inmate['sex'] = entry.get('sex')
    inmate['url'] = None

    def parse_date(s):
        return datetime.strptime(s, "%m/%d/%Y").date()

    try:
        release = parse_date(entry['actRelDate'])
    except ValueError:
        try:
            release = parse_date(entry['projRelDate'])
        except ValueError:
            release = entry['projRelDate']
    finally:
        inmate['release'] = release

    inmate['datetime_fetched'] = datetime.now()

    return inmate
