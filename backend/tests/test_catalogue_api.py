"""The `catalogue` endpoints: `GET /entities` and `GET /entities/{id}` (spec section 12.1)."""

from fastapi.testclient import TestClient

STARTER_IDS = [
    "bank-melli-iran",
    "evraz-ntmk",
    "evraz-plc",
    "kim-chol-sam",
    "roman-abramovich",
    "russian-agricultural-bank",
    "sberbank",
    "sberbank-europe",
]


def test_list_entities_summarises_every_entity_in_id_order(client: TestClient) -> None:
    response = client.get("/api/v1/entities")

    assert response.status_code == 200
    entities = response.json()
    assert [entity["id"] for entity in entities] == STARTER_IDS
    sberbank = next(entity for entity in entities if entity["id"] == "sberbank")
    assert sberbank == {
        "id": "sberbank",
        "entity_type": "bank",
        "display_name": "PUBLIC JOINT STOCK COMPANY SBERBANK OF RUSSIA",
        "lists": ["ofac_sdn", "uk"],
        "countries": ["RU", "CN", "IN"],
        "name_variants": ["exact", "alias", "native_script", "fuzzed"],
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
    }


def ids(response_json: list[dict[str, object]]) -> list[object]:
    return [entity["id"] for entity in response_json]


def test_an_individual_supports_party_and_remittance_placements_only(client: TestClient) -> None:
    abramovich = next(e for e in client.get("/api/v1/entities").json() if e["id"] == "roman-abramovich")

    assert abramovich["entity_type"] == "individual"
    assert abramovich["display_name"] == "Roman Arkadyevich ABRAMOVICH"
    assert abramovich["lists"] == ["uk"]
    assert abramovich["countries"] == ["RU", "IL", "PT"]
    assert abramovich["name_variants"] == ["exact", "alias", "native_script", "fuzzed"]
    assert abramovich["placements"] == ["debtor", "creditor", "ultimate_debtor", "ultimate_creditor", "remittance"]
    assert abramovich["has_bic"] is False


def test_a_corporate_without_a_non_latin_name_lacks_native_script(client: TestClient) -> None:
    ntmk = next(e for e in client.get("/api/v1/entities").json() if e["id"] == "evraz-ntmk")

    assert ntmk["name_variants"] == ["exact", "alias", "fuzzed"]
    assert ntmk["placements"] == ["debtor", "creditor", "ultimate_debtor", "ultimate_creditor", "remittance"]
    assert ntmk["has_bic"] is False


def test_a_bank_with_only_a_gleif_bic_has_a_bic(client: TestClient) -> None:
    bank = next(e for e in client.get("/api/v1/entities").json() if e["id"] == "russian-agricultural-bank")

    assert bank["has_bic"] is True


def test_list_entities_filters_by_entity_type(client: TestClient) -> None:
    response = client.get("/api/v1/entities", params={"entity_type": "individual"})

    assert ids(response.json()) == ["kim-chol-sam", "roman-abramovich"]


def test_list_entities_filters_by_list(client: TestClient) -> None:
    response = client.get("/api/v1/entities", params={"list": "ofac_sdn"})

    assert ids(response.json()) == ["bank-melli-iran", "evraz-ntmk", "kim-chol-sam", "sberbank", "sberbank-europe"]


def test_list_entities_filters_by_country(client: TestClient) -> None:
    response = client.get("/api/v1/entities", params={"country": "GB"})

    assert ids(response.json()) == ["bank-melli-iran", "evraz-plc"]


def test_list_entities_filters_combine(client: TestClient) -> None:
    response = client.get("/api/v1/entities", params={"entity_type": "bank", "list": "uk", "country": "RU"})

    assert ids(response.json()) == ["russian-agricultural-bank", "sberbank"]


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
    assert sberbank["control_relationships"] == [
        {
            "controller": "sberbank",
            "controlled": "sberbank-europe",
            "role": "parent_company",
            "status": "current",
            "as_of": "2026-09-14",
            "source": "OFAC SDN_ADVANCED.XML ProfileRelationship: "
            '18716 SBERBANK EUROPE AG "Owned or Controlled By" 17018, Former="false"',
        }
    ]


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

    assert [(r["controller"], r["controlled"]) for r in evraz["control_relationships"]] == [
        ("roman-abramovich", "evraz-plc"),
        ("evraz-plc", "evraz-ntmk"),
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
