"""IBP inmate search utility."""

import functools
import logging
import typing

from . import fbop, tdcj

Jurisdiction = typing.Literal["Texas", "Federal"]

PROVIDERS: dict[Jurisdiction, typing.Any] = {
    "Texas": tdcj,
    "Federal": fbop,
}

LOGGERS: dict[Jurisdiction, logging.Logger] = {
    "Texas": tdcj.LOGGER,
    "Federal": fbop.LOGGER,
}

QueryResult = tdcj.QueryResult | fbop.QueryResult


def wrap_query(wrapped):
    """query function."""

    @functools.wraps(wrapped)
    def wrapper(
        *args,
        jurisdictions: typing.Optional[typing.Iterable[Jurisdiction]] = None,
        timeout: typing.Optional[float] = None,
    ):
        if jurisdictions is None:
            jurisdictions = PROVIDERS.keys()

        jurisdictions = list(set(jurisdictions))
        for jurisdiction in jurisdictions:
            if jurisdiction not in PROVIDERS:
                raise ValueError(f"Invalid jurisdiction '{jurisdiction}' given.")

        inmates = []
        errors = []

        for jurisdiction in jurisdictions:
            logger = LOGGERS[jurisdiction]
            try:
                inmates.extend(wrapped(*args, jurisdiction, timeout=timeout))
            except Exception as error:  # pylint: disable=broad-exception-caught
                error_name = error.__class__.__name__
                message = f"Query returned '{error_name}: {error}'."
                logger.error(message)
                errors.append(error)

        return inmates, errors

    return wrapper


@wrap_query
def query_by_inmate_id(
    inmate_id: str | int,
    jurisdiction: Jurisdiction,
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
    provider = PROVIDERS[jurisdiction]
    return provider.query_by_inmate_id(inmate_id=inmate_id, timeout=timeout)


@wrap_query
def query_by_name(
    first: str,
    last: str,
    jurisdiction: Jurisdiction,
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
    provider = PROVIDERS[jurisdiction]
    return provider.query_by_name(first=first, last=last, timeout=timeout)
