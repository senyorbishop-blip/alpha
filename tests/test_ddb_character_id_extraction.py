from server.integrations.service import extract_ddb_character_id


def test_extracts_plain_ddb_character_id():
    assert extract_ddb_character_id("87369199") == "87369199"


def test_extracts_ddb_character_id_from_character_urls():
    assert extract_ddb_character_id("https://www.dndbeyond.com/characters/87369199") == "87369199"
    assert extract_ddb_character_id("www.dndbeyond.com/profile/player/characters/87369199?foo=bar") == "87369199"


def test_extracts_ddb_character_id_from_sheet_pdf_url_with_digits_in_username():
    assert (
        extract_ddb_character_id("www.dndbeyond.com/sheet-pdfs/jborodin165_87369199.pdf")
        == "87369199"
    )


def test_extracts_ddb_character_id_from_query_parameter():
    assert extract_ddb_character_id("https://example.test/import?characterId=87369199") == "87369199"
