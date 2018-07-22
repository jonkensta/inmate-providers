import logging
from datetime import datetime

import requests
from nameparser import HumanName
from bs4 import BeautifulSoup


logger = logging.getLogger('TDCJ')

BASE_URL = "https://offender.tdcj.texas.gov"
SEARCH_PATH = "/OffenderSearch/search.action"


def query_by_name(first, last, timeout=None):
    """
    Query the TDCJ database with an inmate name.
    """
    logger.debug("Querying with name %s, %s", last, first)
    matches = _query_helper(firstName=first, lastName=last, timeout=timeout)
    if matches:
        logger.debug("%d result(s) returned", len(list(matches)))
    else:
        logger.debug("No results were returned")
    return list(matches)


def query_by_inmate_id(inmate_id, timeout=None):
    """
    Query the TDCJ database with an inmate id.
    """

    try:
        inmate_id = '{:08d}'.format(int(inmate_id))
    except ValueError:
        msg = "{} is not a valid Texas inmate number".format(inmate_id)
        raise ValueError(msg)

    logger.debug("Querying with ID %s", inmate_id)
    matches = _query_helper(tdcj=inmate_id, timeout=timeout)

    if matches:
        assert len(list(matches)) == 1
        logger.debug("A single result was returned")
        return list(matches)[0]

    else:
        logger.debug("No results returned")
        return None


def format_inmate_id(inmate_id):
    """
    Helper for formatting TDCJ inmate IDs.
    """
    return '{:08d}'.format(int(inmate_id))


def _query_helper(**kwargs):
    """
    Private helper for querying TDCJ.
    """

    timeout = kwargs.pop('timeout', None)

    params = {
        'btnSearch': 'Search',
        'gender':    'ALL',
        'page':      'index',
        'race':      'ALL',
        'tdcj':      '',
        'sid':       '',
        'lastName':  '',
        'firstName': ''
    }
    params.update(kwargs)

    with requests.Session() as session:
        url = BASE_URL + SEARCH_PATH
        response = session.post(url, params=params, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

    table = soup.find('table', {'class': 'tdcj_table'})

    if table is None:
        return []

    rows = table.findAll('tr')
    keys = [ele.text.strip() for ele in rows[0].findAll('th')]

    def row_to_entry(row):
        values = [ele.text.strip() for ele in row.findAll('td')]
        entry = dict(zip(keys, values))
        entry['href'] = row.find('a').get('href')
        return entry

    entries = map(row_to_entry, rows[1:])
    inmates = map(_entry_to_inmate, entries)

    return inmates


def _entry_to_inmate(entry):
    inmate = dict()

    inmate['id'] = entry['TDCJ Number']
    inmate['jurisdiction'] = 'Texas'

    name = HumanName(entry.get('Name', ''))
    inmate['first_name'] = name.first
    inmate['last_name'] = name.last

    inmate['unit'] = entry['Unit of Assignment']

    inmate['race'] = entry.get('Race', None)
    inmate['sex'] = entry.get('Gender', None)
    inmate['url'] = BASE_URL + entry['href'] if 'href' in entry else None

    release_string = entry['Projected Release Date']
    try:
        release = datetime.strptime(release_string, "%Y-%m-%d").date()
    except ValueError:
        release = release_string
        logger.debug("Failed to convert release date to date: %s", release)
    finally:
        inmate['release'] = release

    inmate['datetime_fetched'] = datetime.now()

    logger.debug(
        "%s, %s #%s: MATCHES",
        inmate['last_name'], inmate['first_name'], inmate['id']
    )

    return inmate
