IBP pymates
===========

Welcome to the documentation for the IBP :py:mod:`pymates`,
the IBP inmate lookup utility.
:py:mod:`pymates` is a Python module that finds Texas inmates;
it does this by doing the following:

    1) Query the `TDCJ`_ and `FBOP`_ websites with given search parameters.
    2) Record errors and aggregate the results.
    3) Return results along with a list of any errors that occurred.

.. _TDCJ: https://offender.tdcj.texas.gov/OffenderSearch/start.action;jsessionid=95ce98aac78b3c74ae4325cbed6a
.. _FBOP: https://www.bop.gov/mobile/find_inmate/byname.jsp

This project makes use of the following third-party Python modules:

    * :py:class:`BeautifulSoup` for parsing HTML responses
    * :py:class:`nameparser.parser.HumanName` for parsing names
    * :py:mod:`requests` for issuing HTTP requests

To read more about the API and usage, keep reading below:

.. toctree::
   :maxdepth: 2
   :caption: Contents:

API
---

.. automodule:: pymates

.. autofunction:: query_by_inmate_id

.. autofunction:: query_by_name

Results Format
--------------

Assuming an inmate is found,
the results are formatted as a Python :py:class:`dict` with the following fields:

    * `id` -- numeric identifier
    * `jurisdiction` -- prison system
    * `first_name` -- first name
    * `last_name` -- last name
    * `unit` -- prison unit
    * `race` -- racial ethnicity
    * `sex` -- gender
    * `url` -- webpage if available
    * `release` -- release date if available
    * `datime_fetched` -- datetime that this entry was fetched


Example Usage
-------------

Here are a couple examples of using this module;
getting started, you should import this module as follows::

    >>> import pymates

Querying with a ID:
```````````````````

An example of querying with a numeric ID '88888888'::

    >>> inmates, errors = pymates.query_by_inmate_id('88888888')

Query with a name:
``````````````````

An example of querying with a name, say "John Smith"::

    >>> inmates, errors = pymates.query_by_name("John", "Smith")
