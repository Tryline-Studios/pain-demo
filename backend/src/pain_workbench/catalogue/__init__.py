"""The Entity Catalogue (spec section 3): the curated Sanctioned Entities shipped with the app.

One TOML file per Entity under `entities/`, the Control Relationships in `control_relationships.toml`, validated
by `load_catalogue` at startup.
"""

from pain_workbench.catalogue.loader import DEFAULT_ROOT, Catalogue, CatalogueError, load_catalogue

__all__ = ["DEFAULT_ROOT", "Catalogue", "CatalogueError", "load_catalogue"]
