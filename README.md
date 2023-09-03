pymates
=======

This Python module permits programmatic lookup of state and Federal Texas inmates.
To do this, the module queries the TDCJ and FBOP sites and aggregates the results together.
Lookup can be performed by name or by identifier

Getting Started
---------------

You can install this module in a Python virtual environment as follows:
```bash
python -m venv venv
source venv/bin/activate
pip install git+https://github.com/jonkensta/inmate-providers@main#egg=pymates
```

Example Usage
-------------

Here are a couple examples of using this module;
getting started, you should import this module as follows::
```python
import pymates
```

### Querying with a ID:

An example of querying with a numeric ID '88888888':

```python
inmates, errors = await pymates.query_by_inmate_id("88888888")
```

### Query with a name:

An example of querying with a name, say "John Smith":
```python
inmates, errors = await pymates.query_by_name("John", "Smith")
```

### Query result

The above queries return a list `inmates`; each inmate has the following fields:
- `id` -- TDCJ or FBOP numeric identifier
- `jurisdiction` -- prison system
- `first_name` -- first name
- `last_name` -- last name
- `unit` -- prison unit
- `race` -- racial ethnicity
- `sex` -- gender
- `url` -- webpage if available
- `release` -- release date if available
- `datime_fetched` -- datetime that this entry was fetched

See Also
--------

- [Read the Docs `pymates` documentation](https://pymates.readthedocs.io/en/latest/)
- [Inside Books Project](https://insidebooksproject.org/)

