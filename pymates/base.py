"""IBP inmate search utility.
"""

import logging
import functools

import requests

from . import fbop
from . import tdcj

LOGGER = logging.getLogger('PROVIDERS')

PROVIDERS = {
    'Texas':  ('TDCJ', tdcj),
    'Federal': ('FBOP', fbop),
}


def aggregate_results(query_func):
    """Aggregate the results of the query function together."""

    @functools.wraps(query_func)
    def inner(*args, **kwargs):
        inmates, errors = [], []

        for provider_inmates, provider_error in query_func(*args, **kwargs):
            inmates.extend(provider_inmates)
            errors.extend(provider_error)

        return inmates, errors

    return inner


@aggregate_results
def query_by_inmate_id(id_, jurisdictions=None, timeout=None):
    """Query jurisdictions with an inmate ID.

    :param id_: Numeric identifier of the inmate.
    :type id_: int or str

    :param jurisdictions: List of jurisdictions to search.
        If `None`, then all available jurisdictions are searched.

    :type jurisdictions: None or iterable

    :param timeout: Time in seconds to wait for HTTP requests to complete.
    :type timeout: float

    :returns: tuple `(inmates, errors)` where

        - :py:data:`inmates` -- inmates matching search parameters.
        - :py:data:`errors` -- errors encountered while searching.

    """

    if jurisdictions is None:
        jurisdictions = PROVIDERS.keys()

    for provider, module in (PROVIDERS[j] for j in jurisdictions):
        try:
            inmates = module.query_by_inmate_id(id_, timeout)
            errors = []

        except requests.exceptions.RequestException as exc:
            inmates = []
            class_name = exc.__class__.__name__
            error = f"{provider} query returned {class_name} request exception"
            errors = [error]
            LOGGER.error(error)

        yield inmates, errors


@aggregate_results
def query_by_name(first, last, jurisdictions=None, timeout=None):
    """Query jurisdictions with an inmate name.

    :param first_name: Inmate first name to search.
    :type first_name: str

    :param last_name: Inmate last name to search.
    :type last_name: str

    :param jurisdictions: List of jurisdictions to search.
        If `None`, then all available jurisdictions are searched.

    :type jurisdictions: None or iterable

    :param timeout: Time in seconds to wait for HTTP requests to complete.
    :type timeout: float

    :returns: tuple `(inmates, errors)` where

        - :py:data:`inmates` -- inmates matching search parameters.
        - :py:data:`errors` -- errors encountered while searching.

    """

    if jurisdictions is None:
        jurisdictions = PROVIDERS.keys()

    for provider, module in (PROVIDERS[j] for j in jurisdictions):
        try:
            inmates = module.query_by_name(first, last, timeout)
            errors = []

        except requests.exceptions.RequestException as exc:
            inmates = []
            class_ = exc.__class__.__name__
            error = f"{provider} query returned {class_} request exception"
            errors = [error]
            LOGGER.error(error)

        yield inmates, errors
