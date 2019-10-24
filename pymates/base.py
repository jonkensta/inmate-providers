"""
Base interface module.
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
    """Aggregate the results of the query function together"""

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
    """Query jurisdictions with an inmate ID"""

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
    """Query jurisdictions with an inmate name"""

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
