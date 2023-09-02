"""IBP inmate search utility."""

import asyncio
import logging
import functools
import typing

from . import fbop
from . import tdcj

LOGGER = logging.getLogger("PROVIDERS")

PROVIDERS = {
    "Texas": tdcj,
    "Federal": fbop,
}

LOGGERS = {
    "Texas": tdcj.LOGGER,
    "Federal": fbop.LOGGER,
}

Jurisdiction = typing.Literal["Texas", "Federal"]


def preprocess_kwargs(wrapped):
    """Preprocess the keyword args for a query function."""

    @functools.wraps(wrapped)
    async def wrapper(*args, jurisdictions=None, timeout=None):
        if jurisdictions is None:
            jurisdictions = PROVIDERS.keys()

        jurisdictions = list(set(jurisdictions))
        for jurisdiction in jurisdictions:
            if jurisdiction not in PROVIDERS:
                raise ValueError(f"Invalid jurisdiction '{jurisdiction}' given.")

        kwargs = {
            "jurisdictions": jurisdictions,
        }

        if timeout is not None:
            kwargs["timeout"] = timeout

        return await wrapped(*args, **kwargs)

    return wrapper


def postprocess_results(wrapped):
    """Postprocess the results of a query function."""

    @functools.wraps(wrapped)
    async def wrapper(*args, **kwargs):
        jurisdictions, aws = wrapped(*args, **kwargs)
        results = await asyncio.gather(*aws, return_exceptions=True)

        def is_exception(result) -> bool:
            return isinstance(result, Exception)

        errors = list(filter(is_exception, results))

        for jurisdiction, result in zip(jurisdictions, results):
            if is_exception(result):
                class_name = result.__class__.__name__
                error = f"Query returned '{class_name}: {result}'."
                LOGGERS[jurisdiction].error(error)

        def is_not_exception(result) -> bool:
            return not is_exception(result)

        inmates = [
            item for sublist in filter(is_not_exception, results) for item in sublist
        ]

        return inmates, errors

    return wrapper


@preprocess_kwargs
@postprocess_results
def query_by_inmate_id(
    inmate_id: str | int,
    jurisdictions: typing.Optional[typing.Iterable[Jurisdiction]] = None,
    timeout: typing.Optional[float] = 10.0,
):
    """Query jurisdictions with an inmate ID.

    :param inmate_id: Numeric identifier of the inmate.
    :type inmate_id: int or str

    :param jurisdictions: List of jurisdictions to search.
        If `None`, then all available jurisdictions are searched.

    :type jurisdictions: None or iterable of strings

    :param timeout: Time in seconds to wait for HTTP requests to complete.
    :type timeout: float

    :returns: tuple `(inmates, errors)` where

        - :py:data:`inmates` -- inmates matching search parameters.
        - :py:data:`errors` -- errors encountered while searching.

    """
    aws = [
        PROVIDERS[j].query_by_inmate_id(inmate_id=inmate_id, timeout=timeout)
        for j in jurisdictions
    ]
    return jurisdictions, aws


@preprocess_kwargs
@postprocess_results
def query_by_name(
    first: str,
    last: str,
    jurisdictions: typing.Optional[typing.Iterable[Jurisdiction]] = None,
    timeout: typing.Optional[float] = 10.0,
):
    """Query jurisdictions with an inmate name.

    :param first_name: Inmate first name to search.
    :type first_name: str

    :param last_name: Inmate last name to search.
    :type last_name: str

    :param jurisdictions: List of jurisdictions to search.
        If `None`, then all available jurisdictions are searched.

    :type jurisdictions: None or iterable of strings

    :param timeout: Time in seconds to wait for HTTP requests to complete.
    :type timeout: float

    :returns: tuple `(inmates, errors)` where

        - :py:data:`inmates` -- inmates matching search parameters.
        - :py:data:`errors` -- errors encountered while searching.

    """
    aws = [
        PROVIDERS[j].query_by_name(first=first, last=last, timeout=timeout)
        for j in jurisdictions
    ]
    return jurisdictions, aws
