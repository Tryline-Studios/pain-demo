"""Property (spec 15.1): any valid request in any Message Version yields XSD-valid XML whose Answer Key matches,
every Hit's XPath resolving to the exact element that carries its rendered name."""

import hashlib
import json
from decimal import Decimal

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st
from lxml import etree
from sample_files import assert_valid_sample_file, resolve

from pain_demo.app import create_app
from pain_demo.generation.clean_banks import SUPPORTED_COUNTRIES
from pain_demo.validation import MESSAGE_VERSIONS

CLIENT = TestClient(create_app())

amounts = st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000000"), places=2)

requests = st.fixed_dictionaries(
    {
        "message_version": st.sampled_from(MESSAGE_VERSIONS),
        "transaction_count": st.integers(min_value=1, max_value=100),
        "countries": st.lists(st.sampled_from(SUPPORTED_COUNTRIES), min_size=1, max_size=6),
        "amounts": st.tuples(amounts, amounts).map(sorted),
    },
    optional={
        "seed": st.text(st.characters(exclude_categories=["Cs"]), min_size=1, max_size=64),
        "message_id": st.text(st.characters(codec="ascii", min_codepoint=33), min_size=1, max_size=35),
        "currencies": st.lists(st.sampled_from(["EUR", "GBP", "USD", "CHF", "JPY", "PLN"]), min_size=1, max_size=3),
    },
)


@settings(max_examples=25, deadline=None)
@given(requests, st.data())
def test_any_valid_request_yields_a_valid_file_its_answer_key_describes(request: dict, data: st.DataObject) -> None:
    amount_min, amount_max = request.pop("amounts")
    hit_count = data.draw(st.integers(min_value=0, max_value=request["transaction_count"] + 2), label="hit_count")
    body: dict = {**request, "amount_min": str(amount_min), "amount_max": str(amount_max), "hit_count": hit_count}

    response = CLIENT.post("/api/v1/sample-files", json=body)

    assert response.status_code == 200, response.text
    envelope = response.json()
    xml = envelope["sample_file"]["xml"].encode("utf-8")
    key = envelope["answer_key"]
    assert_valid_sample_file(xml, body["message_version"])
    assert key["file"]["sha256"] == hashlib.sha256(xml).hexdigest()
    assert key["file"]["transaction_count"] == body["transaction_count"]
    document = etree.fromstring(xml)
    end_to_end_ids = document.xpath("//*[local-name()='EndToEndId']/text()")
    assert [t["end_to_end_id"] for t in key["transactions"]] == end_to_end_ids
    assert [t["number"] for t in key["transactions"]] == list(range(1, body["transaction_count"] + 1))
    assert document.xpath("//*[local-name()='GrpHdr']/*[local-name()='MsgId']/text()") == [key["file"]["message_id"]]
    (comment,) = [n for n in document.itersiblings(preceding=True) if isinstance(n, etree._Comment)]
    assert json.loads(str(comment.text).split("seed=", 1)[1]) == key["seed"]
    if "seed" in body:
        assert key["seed"] == body["seed"]
    assert len(key["hits"]) == key["file"]["hit_count"] == hit_count
    bic_element = "BIC" if body["message_version"] == "pain.001.001.03" else "BICFI"
    for hit in key["hits"]:
        (element,) = resolve(document, hit["xpath"])
        if hit.get("element") in {"ustrd", "addtl_rmt_inf"}:  # a remittance sentence around the name
            assert hit["name"]["rendered"] in str(element.text)
            assert len(str(element.text)) <= 140
        else:
            assert element.text == hit["name"]["rendered"]
        if "rendering_mode" in hit:
            bics = [e.text for e in resolve(document, hit["xpath"].removesuffix("Nm") + bic_element)]
            assert bics == ([hit["bic"]["value"]] if hit["rendering_mode"] == "name_and_bic" else [])
