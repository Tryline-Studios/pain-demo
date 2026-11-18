"""The `catalogue` endpoints: `GET /entities` and `GET /entities/{id}` (spec section 12.1)."""

from pathlib import Path

from fastapi.testclient import TestClient
from test_catalogue import MINIMAL_BANK, write_catalogue

from pain_workbench.app import create_app


def ids(response_json: list[dict[str, object]]) -> list[object]:
    return [entity["id"] for entity in response_json]


def summary_of(client: TestClient, entity_id: str) -> dict[str, object]:
    return next(entity for entity in client.get("/api/v1/entities").json() if entity["id"] == entity_id)


def detail_of(client: TestClient, entity_id: str) -> dict:
    response = client.get(f"/api/v1/entities/{entity_id}")
    assert response.status_code == 200
    return response.json()


def listing_refs(detail: dict) -> list[tuple[str, str]]:
    return [(listing["list"], listing["entry_id"]) for listing in detail["listings"]]


# --- the shipped roster (spec section 3.2, ticket #26)


def test_the_roster_facets_match_the_spec(client: TestClient, roster: dict[str, list[str]]) -> None:
    summaries = client.get("/api/v1/entities").json()

    by_type = {
        entity_type: sorted(s["id"] for s in summaries if s["entity_type"] == entity_type) for entity_type in roster
    }
    assert by_type == {entity_type: sorted(ids) for entity_type, ids in roster.items()}
    assert {entity_type: len(ids) for entity_type, ids in by_type.items()} == {
        "bank": 20,
        "corporate": 16,
        "individual": 14,
    }

    coverage = {"both": 0, "ofac_only": 0, "uk_only": 0}
    for summary in summaries:
        lists = set(summary["lists"])
        coverage["both" if lists == {"ofac_sdn", "uk"} else "ofac_only" if lists == {"ofac_sdn"} else "uk_only"] += 1
    assert coverage == {"both": 32, "ofac_only": 9, "uk_only": 9}

    banks = [s for s in summaries if s["entity_type"] == "bank"]
    assert all(bank["has_bic"] for bank in banks)
    gleif_only = [
        bank["id"] for bank in banks if all(bic["listing"] is None for bic in detail_of(client, bank["id"])["bics"])
    ]
    assert gleif_only == ["alfa-bank-belarus", "bank-melli-iran", "russian-agricultural-bank"]


def test_the_must_includes_of_spec_3_2_hold(client: TestClient) -> None:
    sberbank = detail_of(client, "sberbank")
    assert listing_refs(sberbank) == [("ofac_sdn", "17018"), ("uk", "RUS0256")]
    sabrrumm = next(bic for bic in sberbank["bics"] if bic["value"] == "SABRRUMM")
    assert sabrrumm["listing"] == {"list": "ofac_sdn", "entry_id": "17018"}

    assert listing_refs(detail_of(client, "evraz-plc")) == [("uk", "RUS1027")]
    assert listing_refs(detail_of(client, "roman-abramovich")) == [("uk", "RUS0270")]


def test_every_individual_has_a_sourced_control_relationship_and_both_parent_links_exist(
    client: TestClient, roster: dict[str, list[str]]
) -> None:
    for individual_id in roster["individual"]:
        relationships = detail_of(client, individual_id)["control_relationships"]
        assert relationships, individual_id
        assert all(r["controller"] == individual_id and r["source"] for r in relationships), individual_id

    parents = {
        (r["controller"], r["controlled"])
        for entity_id in roster["bank"] + roster["corporate"]
        for r in detail_of(client, entity_id)["control_relationships"]
        if r["role"] == "parent_company"
    }
    assert parents == {("sberbank", "sberbank-europe"), ("evraz-plc", "evraz-ntmk")}


def test_leis_are_stored_only_where_the_gleif_record_clearly_matches(client: TestClient) -> None:
    assert detail_of(client, "bank-sepah")["lei"] is None
    assert detail_of(client, "evraz-ntmk")["lei"] is None
    lei = detail_of(client, "sberbank-europe")["lei"]
    assert lei["value"] == "529900IZ8TASAYR3A694"
    assert lei["gleif_legal_name"] == "MeSoFa Vermögensverwaltungs AG in Abwicklung"


def test_no_domestic_bank_code_is_stored_as_a_bic(client: TestClient) -> None:
    evrofinance = detail_of(client, "evrofinance-mosnarbank")

    assert [bic["value"] for bic in evrofinance["bics"]] == ["EVRFRUMM"]
    assert "BIC 044525204" in [number["value"] for number in evrofinance["registration_numbers"]]


# --- listing and filtering


def test_list_entities_summarises_every_entity_in_id_order(client: TestClient, roster_ids: list[str]) -> None:
    response = client.get("/api/v1/entities")

    assert response.status_code == 200
    assert ids(response.json()) == roster_ids
    assert summary_of(client, "sberbank") == {
        "id": "sberbank",
        "entity_type": "bank",
        "display_name": "PUBLIC JOINT STOCK COMPANY SBERBANK OF RUSSIA",
        "lists": ["ofac_sdn", "uk"],
        "countries": ["RU", "CN", "IN"],
        "name_variants": ["exact", "alias", "native_script", "transliteration", "fuzzed"],
        "placements": [
            "debtor",
            "debtor_agent",
            "creditor",
            "creditor_agent",
            "ultimate_debtor",
            "ultimate_creditor",
            "intermediary_agent_1",
            "intermediary_agent_2",
            "intermediary_agent_3",
            "remittance",
        ],
        "has_bic": True,
        "has_controller": True,
    }


def test_an_individual_supports_party_and_remittance_placements_only(client: TestClient) -> None:
    abramovich = summary_of(client, "roman-abramovich")

    assert abramovich["entity_type"] == "individual"
    assert abramovich["display_name"] == "Roman Arkadyevich ABRAMOVICH"
    assert abramovich["lists"] == ["uk"]
    assert abramovich["countries"] == ["RU", "IL", "PT"]
    assert abramovich["name_variants"] == ["exact", "alias", "native_script", "transliteration", "fuzzed"]
    assert abramovich["placements"] == ["debtor", "creditor", "ultimate_debtor", "ultimate_creditor", "remittance"]
    assert abramovich["has_bic"] is False


def test_a_corporate_without_a_non_latin_name_lacks_native_script(client: TestClient) -> None:
    ntmk = summary_of(client, "evraz-ntmk")

    assert ntmk["name_variants"] == ["exact", "alias", "fuzzed"]
    assert ntmk["placements"] == ["debtor", "creditor", "ultimate_debtor", "ultimate_creditor", "remittance"]
    assert ntmk["has_bic"] is False


def test_only_an_entity_with_a_cyrillic_name_supports_transliteration(client: TestClient) -> None:
    # Bank Melli Iran's one non-Latin name is Persian: no transliteration in v1 (spec 7.4).
    assert summary_of(client, "bank-melli-iran")["name_variants"] == ["exact", "alias", "native_script", "fuzzed"]
    assert summary_of(client, "evraz-plc")["name_variants"] == ["exact", "native_script", "transliteration", "fuzzed"]


def test_only_a_controlled_legal_entity_can_bring_its_controller(client: TestClient) -> None:
    # `with_controller` needs a Control Relationship naming the Entity as the controlled side (spec 6.8).
    assert summary_of(client, "evraz-ntmk")["has_controller"] is True  # its controller is Evraz PLC
    assert summary_of(client, "bank-mellat")["has_controller"] is False
    assert summary_of(client, "roman-abramovich")["has_controller"] is False  # a controller, never controlled


def test_a_bank_with_only_a_gleif_bic_has_a_bic(client: TestClient) -> None:
    bank = summary_of(client, "russian-agricultural-bank")

    assert bank["has_bic"] is True


def test_list_entities_filters_by_entity_type(client: TestClient, roster: dict[str, list[str]]) -> None:
    response = client.get("/api/v1/entities", params={"entity_type": "individual"})

    assert ids(response.json()) == sorted(roster["individual"])


def test_list_entities_filters_by_list(client: TestClient) -> None:
    response = client.get("/api/v1/entities", params={"list": "ofac_sdn"})

    listed = ids(response.json())
    assert len(listed) == 41
    assert "sberbank" in listed
    assert {"roman-abramovich", "evraz-plc", "russian-agricultural-bank"}.isdisjoint(listed)


def test_list_entities_filters_by_country(client: TestClient) -> None:
    response = client.get("/api/v1/entities", params={"country": "GB"})

    assert ids(response.json()) == ["bank-melli-iran", "evraz-plc"]


def test_list_entities_filters_combine(client: TestClient) -> None:
    response = client.get("/api/v1/entities", params={"entity_type": "bank", "list": "uk", "country": "RU"})

    assert ids(response.json()) == [
        "alfa-bank",
        "bank-rossiya",
        "evrofinance-mosnarbank",
        "gazprombank",
        "promsvyazbank",
        "russian-agricultural-bank",
        "sberbank",
        "veb-rf",
        "vtb-bank",
    ]


def test_an_unknown_filter_value_is_a_validation_problem(client: TestClient) -> None:
    response = client.get("/api/v1/entities", params={"entity_type": "trust"})

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["type"] == "validation_error"
    assert body["errors"][0]["field"] == "entity_type"


def test_get_entity_returns_every_name_listing_bic_lei_and_address_with_its_source(client: TestClient) -> None:
    response = client.get("/api/v1/entities/sberbank")

    assert response.status_code == 200
    sberbank = response.json()
    assert sberbank["id"] == "sberbank"
    assert sberbank["entity_type"] == "bank"
    assert sberbank["listings"] == [
        {
            "list": "ofac_sdn",
            "entry_id": "17018",
            "programmes": ["UKRAINE-EO13662", "RUSSIA-EO14024"],
            "designation_date": "2022-04-06",
            "verified": {"snapshot_date": "2026-09-14", "source_file": "SDN_ADVANCED.XML"},
        },
        {
            "list": "uk",
            "entry_id": "RUS0256",
            "programmes": ["The Russia (Sanctions) (EU Exit) Regulations 2019"],
            "designation_date": "2022-03-01",
            "verified": {"snapshot_date": "2026-09-11", "source_file": "UK-Sanctions-List.xml"},
        },
    ]
    assert sberbank["names"][0] == {
        "value": "PUBLIC JOINT STOCK COMPANY SBERBANK OF RUSSIA",
        "source_type": "primary",
        "script": "latin",
        "script_source": "stated",
        "language": None,
        "listing": {"list": "ofac_sdn", "entry_id": "17018"},
    }
    assert len(sberbank["names"]) == 18
    assert {name["value"] for name in sberbank["names"] if name["script"] == "cyrillic"} == {
        "ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО СБЕРБАНК РОССИИ",
        "ПАО Сбербанк",
    }
    assert [bic["value"] for bic in sberbank["bics"]] == ["SABRRUMM", "SABRINDDXXX"]
    assert sberbank["bics"][0]["listing"] == {"list": "ofac_sdn", "entry_id": "17018"}
    assert sberbank["bics"][1]["listing"] is None
    assert sberbank["bics"][1]["citation"].startswith("GLEIF BIC-to-LEI mapping")
    assert sberbank["lei"]["value"] == "549300WE6TAF5EEWQS81"
    assert len(sberbank["addresses"]) == 5
    assert sberbank["addresses"][0] == {
        "lines": ["19 ul. Vavilova"],
        "city": "Moscow",
        "region": None,
        "postal_code": "117312",
        "country": "RU",
        "listing": {"list": "ofac_sdn", "entry_id": "17018"},
    }
    assert [(r["controller"], r["controlled"], r["role"]) for r in sberbank["control_relationships"]] == [
        ("herman-gref", "sberbank", "director"),
        ("sberbank", "sberbank-europe", "parent_company"),
    ]
    assert sberbank["control_relationships"][1] == {
        "controller": "sberbank",
        "controlled": "sberbank-europe",
        "role": "parent_company",
        "status": "current",
        "as_of": "2026-09-14",
        "source": "OFAC SDN_ADVANCED.XML ProfileRelationship: "
        '18716 SBERBANK EUROPE AG "Owned or Controlled By" 17018, Former="false"',
    }


def test_get_entity_for_an_individual_exposes_only_what_the_catalogue_holds(client: TestClient) -> None:
    abramovich = client.get("/api/v1/entities/roman-abramovich").json()

    assert set(abramovich) == {
        "id",
        "entity_type",
        "listings",
        "names",
        "date_of_birth",
        "place_of_birth",
        "nationalities",
        "country_of_residence",
        "control_relationships",
    }
    assert abramovich["date_of_birth"] == "1966-10-24"
    assert abramovich["place_of_birth"] == "Saratov, Russia"
    assert abramovich["nationalities"] == ["RU", "IL", "PT"]
    assert abramovich["country_of_residence"] is None
    assert [(r["controller"], r["controlled"], r["role"]) for r in abramovich["control_relationships"]] == [
        ("roman-abramovich", "evraz-plc", "ultimate_beneficial_owner")
    ]


def test_get_entity_lists_relationships_from_both_sides(client: TestClient) -> None:
    evraz = client.get("/api/v1/entities/evraz-plc").json()

    assert [(r["controller"], r["controlled"], r["role"]) for r in evraz["control_relationships"]] == [
        ("roman-abramovich", "evraz-plc", "ultimate_beneficial_owner"),
        ("alexander-abramov", "evraz-plc", "director"),
        ("alexander-abramov", "evraz-plc", "ultimate_beneficial_owner"),
        ("evraz-plc", "evraz-ntmk", "parent_company"),
    ]
    assert evraz["lei"]["gleif_legal_name"] == "EVRAZ PLC"
    assert "bics" not in evraz


def test_get_entity_for_an_unknown_id_is_a_404_problem(client: TestClient) -> None:
    response = client.get("/api/v1/entities/no-such-entity", headers={"X-Request-Id": "req-404"})

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "No Entity with id 'no-such-entity'",
        "instance": "req-404",
    }


CYRILLIC_BANK = """
[[names]]
value = "Банк"
source_type = "aka"
script = "cyrillic"
script_source = "stated"
listing = { list = "ofac_sdn", entry_id = "1" }
"""


def test_an_entity_whose_every_transliteration_is_listed_does_not_support_it(tmp_path: Path) -> None:
    write_catalogue(tmp_path, {"test-bank": MINIMAL_BANK.replace("TEST BANK", "BANK") + CYRILLIC_BANK})
    with TestClient(create_app(catalogue_root=tmp_path)) as client:
        (summary,) = client.get("/api/v1/entities").json()

    assert summary["name_variants"] == ["exact", "native_script", "fuzzed"]


def test_an_entity_with_no_latin_name_does_not_support_fuzzed(tmp_path: Path) -> None:
    cyrillic_only = MINIMAL_BANK.replace('"TEST BANK"', '"Тест Банк"').replace('"latin"', '"cyrillic"')
    write_catalogue(tmp_path, {"test-bank": cyrillic_only})
    with TestClient(create_app(catalogue_root=tmp_path)) as client:
        (summary,) = client.get("/api/v1/entities").json()

    assert "native_script" in summary["name_variants"]
    assert "fuzzed" not in summary["name_variants"]
