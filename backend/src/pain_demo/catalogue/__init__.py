"""The Entity Catalogue.

The catalogue itself (entities, Control Relationships, loading and startup validation) arrives with its own ticket.
Until then this package only carries the snapshot date that the Generator Version reports.
"""

from datetime import date
from typing import Final

SNAPSHOT_DATE: Final = date(2026, 9, 17)
"""The date the Entity Catalogue's Listings were last checked against the OFAC SDN and UK Sanctions List."""
