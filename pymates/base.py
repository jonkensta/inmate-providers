"""IBP inmate search utility."""

import asyncio
import logging
import functools

import urllib.error

from . import fbop
from . import tdcj

LOGGER = logging.getLogger("PROVIDERS")

PROVIDERS = {
    "Texas": ("TDCJ", tdcj),
    "Federal": ("FBOP", fbop),
}


def aggregate_results(query_func):
    """Aggregate the results of the query function together."""

    @functools.wraps(query_func)
    def inner(*args, **kwargs):

        inmates, errors = [], []
        providers, results = query_func(*args, **kwargs)
        for (provider, _), result in zip(providers, results):

            if isinstance(result, Exception):
                class_ = result.__class__.__name__
                error = f"{provider} query returned {class_} request exception."
                LOGGER.error(error)
                errors.append(error)
            else:
                inmates.extend(result)

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

    providers = [PROVIDERS[j] for j in jurisdictions]

    async def async_helper():
        loop = asyncio.get_event_loop()

        def generate_futures():
            for _, module in providers:
                yield loop.run_in_executor(
                    None, module.query_by_inmate_id, id_, timeout
                )

        futures = list(generate_futures())
        results = await asyncio.gather(*futures, return_exceptions=True)

        return results

    results = asyncio.run(async_helper())
    return providers, results


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

    providers = [PROVIDERS[j] for j in jurisdictions]

    async def async_helper():
        loop = asyncio.get_event_loop()

        def generate_futures():
            for _, module in providers:
                yield loop.run_in_executor(
                    None, module.query_by_name, first, last, timeout
                )

        futures = list(generate_futures())
        results = await asyncio.gather(*futures, return_exceptions=True)

        return results

    results = asyncio.run(async_helper())
    return providers, results
