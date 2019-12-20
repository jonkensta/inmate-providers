"""IBP inmate search utility.

The :py:mod:`pymates` module provides two functions for searching for Texas inmates:

    * :py:func:`query_by_inmate_id`
    * :py:func:`query_by_name`

Because Texas inmates can be housed in both Federal and state-level institutions,
these functions must search for inmates through the TDCJ and FBOP websites.
The driving utility of this module is that it provides a common interface to
both systems: Search parameters are given, both jurisdictions are searched, and
matching Federal and state-level inmates are returned back. All of this is
done without requiring the user to be concerned with the details.

"""

from .base import query_by_inmate_id, query_by_name

__all__ = ["query_by_inmate_id", "query_by_name"]
