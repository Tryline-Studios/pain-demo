"""Bank identifiers shared by the Entity Catalogue and the Clean Bank List: the BIC and its parts."""

from schwifty import BIC as SchwiftyBIC
from schwifty.exceptions import SchwiftyException

BIC_PATTERN = r"^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$"
"""Upper case, 8 or 11 characters; documents the shape in OpenAPI, while `well_formed_bic` checks the country code."""

BIC8_LENGTH = 8


def well_formed_bic(value: str) -> str:
    """A Pydantic field validator body: schwifty checks structure and country code."""
    try:
        SchwiftyBIC(value)
    except SchwiftyException as error:
        msg = f"BIC is not well-formed: {error}"
        raise ValueError(msg) from error
    return value


def bic8(value: str) -> str:
    """The institution, country and location parts: what two BICs of the same institution share."""
    return value[:BIC8_LENGTH]


def bic_country(value: str) -> str:
    return value[4:6]
