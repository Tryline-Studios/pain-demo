"""The pain001 boundary (spec 10.2): the only module that imports pain001.

For now it exposes the compiled XSD per Message Version; ticket #28 grows it into the renderer.
"""

import functools
import importlib.resources

import pain001
from lxml import etree


@functools.cache
def schema(message_version: str) -> etree.XMLSchema:
    """pain001's bundled XSD for a Message Version (pain.001.001.03 to .13), compiled once and reused."""
    xsd = importlib.resources.files(pain001) / "templates" / message_version / f"{message_version}.xsd"
    return etree.XMLSchema(etree.fromstring(xsd.read_bytes()))
