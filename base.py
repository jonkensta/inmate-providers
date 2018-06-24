import logging
import requests

from . import fbop
from . import tdcj

providers = {
    'Texas':   ('TDCJ', tdcj),
    'Federal': ('FBOP', fbop),
}


def query_by_inmate_id(id_, jurisdictions=None, timeout=None):
    if jurisdictions is None:
        jurisdictions = ['Texas', 'Federal']

    inmates, errors = [], []
    for provider, module in (providers[j] for j in jurisdictions):
        try:
            inmate = module.query_by_inmate_id(id_, timeout)
        except requests.exceptions.RequestException as exc:
            exc_class_name = exc.__class__.__name__

            msg = (
                "{} query returned {} request exception"
                .format(provider, exc_class_name)
            )
            errors.append(msg)

            logger = logging.getLogger(provider)
            logger.error("Query returned %s request exception", exc_class_name)
        else:
            if inmate:
                inmates.append(inmate)
    return inmates, errors


def query_by_name(first_name, last_name, timeout=None):
    inmates, errors = [], []
    jurisdictions = ['Texas', 'Federal']
    for provider, module in (providers[j] for j in jurisdictions):
        try:
            part = module.query_by_name(first_name, last_name, timeout)
        except requests.exceptions.RequestException as exc:
            exc_class_name = exc.__class__.__name__

            msg = (
                "{} query returned {} request exception"
                .format(provider, exc_class_name)
            )
            errors.append(msg)

            logger = logging.getLogger(provider)
            logger.error("Query returned %s request exception", exc_class_name)
        else:
            inmates.extend(part)
    return inmates, errors
