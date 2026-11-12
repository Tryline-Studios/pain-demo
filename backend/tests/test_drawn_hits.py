"""`POST /api/v1/sample-files` with `hit_count`: drawn Hits on party and agent Placements (spec 6, 7, 11)."""

from fastapi.testclient import TestClient
from lxml import etree
from sample_files import assert_valid_sample_file, resolve

from pain_demo.catalogue import load_catalogue

CATALOGUE = load_catalogue()
FIXED = {"created_at": "2026-11-12T09:30:00Z", "execution_date": "2026-11-13"}


def generate(client: TestClient, **settings: object) -> dict:
    response = client.post("/api/v1/sample-files", json={**FIXED, **settings})
    assert response.status_code == 200, response.text
    envelope = response.json()
    assert_valid_sample_file(xml_of(envelope), envelope["answer_key"]["message_version"])
    return envelope


def xml_of(envelope: dict) -> bytes:
    return envelope["sample_file"]["xml"].encode("utf-8")


def test_each_hit_names_a_listed_entity_at_its_xpath(client: TestClient) -> None:
    envelope = generate(client, seed="three-hits", transaction_count=10, hit_count=3)
    key = envelope["answer_key"]
    document = etree.fromstring(xml_of(envelope))

    assert key["file"]["hit_count"] == 3
    assert [hit["id"] for hit in key["hits"]] == ["h1", "h2", "h3"]
    for hit in key["hits"]:
        (element,) = resolve(document, hit["xpath"])
        assert element.text == hit["name"]["rendered"]
        entity = CATALOGUE.entities[hit["entity"]["id"]]
        assert hit["name"]["rendered"] in [name.value for name in entity.names]
        assert hit["entity"]["entity_type"] == entity.entity_type
        assert (hit["origin"], hit["paired_with"], hit["displaced"]) == ("drawn", None, None)
