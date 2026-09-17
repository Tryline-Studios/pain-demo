"""The Entity Catalogue (spec section 3): the curated Sanctioned Entities shipped with the app.

One TOML file per Entity under `entities/`, the Control Relationships in `control_relationships.toml`, validated
by `load_catalogue` at startup.
"""

from pain_demo.catalogue.loader import Catalogue, CatalogueError, load_catalogue

__all__ = ["Catalogue", "CatalogueError", "load_catalogue"]
