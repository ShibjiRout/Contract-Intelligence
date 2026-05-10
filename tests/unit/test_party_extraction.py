from contracts_platform.pipeline.party_extraction.extractor import extract_parties
from contracts_platform.pipeline.party_extraction.normalizer import (
    generate_party_id,
    normalize_party_name,
)


def test_normalize_party_name_collapses_case_and_whitespace():
    assert normalize_party_name("  Acme   Supplies Ltd.\n") == "acme supplies ltd"


def test_generate_party_id_is_stable():
    normalized = "acme supplies ltd"
    assert generate_party_id(normalized) == generate_party_id(normalized)
    assert generate_party_id(normalized).startswith("party_")


def test_extract_parties_from_between_clause():
    text = "This Agreement is made between Acme Supplies Ltd and Beta Retail PLC."

    parties = extract_parties(text)

    assert parties == [
        {
            "party_id": generate_party_id("acme supplies ltd"),
            "name": "Acme Supplies Ltd",
            "normalized_name": "acme supplies ltd",
            "role": "party_a",
        },
        {
            "party_id": generate_party_id("beta retail plc"),
            "name": "Beta Retail PLC",
            "normalized_name": "beta retail plc",
            "role": "party_b",
        },
    ]
