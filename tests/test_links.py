from links import (
    _build_query,
    _extract_search_terms,
    _first_valid_url,
    _url_matches_address,
    build_search_url,
)


# ---------------------------------------------------------------------------
# _extract_search_terms
# ---------------------------------------------------------------------------


class TestExtractSearchTerms:
    def test_apt_prefix_stripped(self):
        assert "APT" not in _extract_search_terms(
            "APT 66, BLOCK B, RIVERSIDE COURT DUBLIN 4"
        )

    def test_unit_number_kept(self):
        assert "66" in _extract_search_terms("APT 66, BLOCK B, RIVERSIDE COURT DUBLIN 4")

    def test_block_stripped(self):
        result = _extract_search_terms("APARTMENT 58 BLOCK B, RIVERSIDE COURT, DUBLIN 4")
        assert "BLOCK" not in result.upper()

    def test_county_stripped(self):
        # County is stripped when it is its own comma-separated part
        result = _extract_search_terms("APT 9, BLOCK F, RIVERSIDE COURT, DUBLIN 4")
        assert "DUBLIN" not in result.upper()

    def test_development_kept(self):
        result = _extract_search_terms("APT 116 - BLK A1, RIVERSIDE COURT, WESTSIDE")
        assert "RIVERSIDE COURT" in result.upper()

    def test_no_apt_prefix(self):
        result = _extract_search_terms("89C RIVERSIDE COURT, WESTSIDE, DUBLIN 4")
        assert "89C" in result.upper()
        assert "RIVERSIDE COURT" in result.upper()

    def test_dash_block_stripped(self):
        # "APT 116 - BLK A1" — the dash+block should be stripped cleanly
        result = _extract_search_terms("APT 116 - BLK A1, RIVERSIDE COURT, WESTSIDE")
        assert "-" not in result
        assert "BLK" not in result.upper()

    def test_blocka_no_space(self):
        result = _extract_search_terms("APT 24, BLOCKA, RIVERSIDE COURT DUBLIN 4")
        assert "24" in result
        assert "RIVERSIDE COURT" in result.upper()


# ---------------------------------------------------------------------------
# _build_query
# ---------------------------------------------------------------------------


class TestBuildQuery:
    def test_development_quoted(self):
        result = _build_query("APT 66, BLOCK B, RIVERSIDE COURT DUBLIN 4")
        assert '"RIVERSIDE COURT"' in result

    def test_unit_number_unquoted(self):
        result = _build_query("APT 66, BLOCK B, RIVERSIDE COURT DUBLIN 4")
        # unit number appears outside of quotes
        assert result.startswith("66 ")

    def test_block_included(self):
        result = _build_query("APT 66, BLOCK B, RIVERSIDE COURT DUBLIN 4")
        assert "block B" in result

    def test_dublin_not_in_quoted_phrase(self):
        result = _build_query("APT 74, BLOCK B, RIVERSIDE COURT DUBLIN 4")
        # The quoted part should not include Dublin
        quoted = result.split('"')[1] if '"' in result else ""
        assert "DUBLIN" not in quoted.upper()
        assert "4" not in quoted

    def test_dash_block_label(self):
        result = _build_query("APT 116 - BLK A1, RIVERSIDE COURT, WESTSIDE")
        assert "116" in result
        assert "block A1" in result
        assert '"RIVERSIDE COURT"' in result

    def test_blocka_no_space(self):
        result = _build_query("APT 24, BLOCKA, RIVERSIDE COURT DUBLIN 4")
        assert "24" in result
        assert "block A" in result
        assert '"RIVERSIDE COURT"' in result

    def test_no_apt_prefix_quotes_development(self):
        result = _build_query("89C RIVERSIDE COURT, WESTSIDE, DUBLIN 4")
        assert '"RIVERSIDE COURT"' in result
        assert "89C" in result

    def test_non_apt_no_block(self):
        result = _build_query("4 RIVERSIDE COURT, WESTSIDE, DUBLIN 4")
        assert '"RIVERSIDE COURT"' in result
        assert result.startswith("4 ")

    def test_28a_no_apt_prefix(self):
        result = _build_query("28A RIVERSIDE COURT, WESTSIDE, DUBLIN 4")
        assert '"RIVERSIDE COURT"' in result
        assert "28A" in result

    def test_different_blocks_produce_different_queries(self):
        q_b = _build_query("APT 66, BLOCK B, RIVERSIDE COURT DUBLIN 4")
        q_c = _build_query("APT 66, BLOCK C, RIVERSIDE COURT DUBLIN 4")
        assert q_b != q_c
        assert "block B" in q_b
        assert "block C" in q_c


# ---------------------------------------------------------------------------
# _url_matches_address
# ---------------------------------------------------------------------------


class TestUrlMatchesAddress:
    # Correct matches — should return True
    def test_correct_block_and_unit(self):
        assert _url_matches_address(
            "https://www.myhome.ie/residential/brochure/apartment-9-block-f-riverside-court/1000001",
            "APT 9, BLOCK F, RIVERSIDE COURT DUBLIN 4",
        )

    def test_correct_block_b(self):
        assert _url_matches_address(
            "https://www.myhome.ie/residential/brochure/58-block-b-riverside-court/1000002",
            "APARTMENT 58 BLOCK B, RIVERSIDE COURT, DUBLIN 4",
        )

    def test_correct_block_a1(self):
        assert _url_matches_address(
            "https://www.myhome.ie/residential/brochure/apartment-116-block-a-riverside-court/1000003",
            "APT 116 - BLK A1, RIVERSIDE COURT, WESTSIDE",
        )

    def test_house_number_correct(self):
        assert _url_matches_address(
            "https://www.myhome.ie/residential/brochure/17-elm-park/1000004",
            "17 ELM PARK, NORTHSIDE, DUBLIN 6",
        )

    def test_house_number_alphanumeric_correct(self):
        assert _url_matches_address(
            "https://www.myhome.ie/residential/brochure/28a-oak-avenue/1000005",
            "28A OAK AVENUE, DUBLIN 6",
        )

    def test_house_number_wrong(self):
        # URL has 80, address says 17 — should be rejected
        assert not _url_matches_address(
            "https://www.myhome.ie/residential/brochure/80-elm-park/1000006",
            "17 ELM PARK, NORTHSIDE, DUBLIN 6",
        )

    def test_alphanumeric_house_number_validates_digits_only(self):
        # "89C" → checks "89" in slug, not "89c" (letter suffix may appear differently in URL)
        assert _url_matches_address(
            "https://www.myhome.ie/residential/brochure/89-block-c-riverside-court/1000007",
            "89C RIVERSIDE COURT, WESTSIDE, DUBLIN 4",
        )

    # Wrong matches — should return False
    def test_wrong_block_letter(self):
        assert not _url_matches_address(
            "https://www.myhome.ie/residential/brochure/apt-74-block-a-riverside-court/1000008",
            "APT 74, BLOCK B, RIVERSIDE COURT DUBLIN 4",
        )

    def test_wrong_block_blocka_format(self):
        assert not _url_matches_address(
            "https://www.myhome.ie/residential/brochure/apartment-24-block-c-riverside-court/1000009",
            "APT 24, BLOCKA, RIVERSIDE COURT DUBLIN 4",
        )

    def test_wrong_development(self):
        # URL has riverside-village, address says riverside-court — block C is present but
        # fix 3 only checks block/unit, not development (that's fix 2's job)
        assert not _url_matches_address(
            "https://www.myhome.ie/residential/brochure/86-riverside-village/1000010",
            "APARTMENT 86, BLOCK C, RIVERSIDE COURT",
        )  # block C not in URL → False

    def test_unit_number_missing_from_url(self):
        assert not _url_matches_address(
            "https://www.myhome.ie/residential/brochure/riverside-court-block-a/1000011",
            "APT 8 BLOCK A, RIVERSIDE COURT, WESTSIDE DUBLIN 4",
        )

    def test_wrong_block_and_development(self):
        assert not _url_matches_address(
            "https://www.myhome.ie/residential/brochure/apartment-66-block-c-riverside-gate/1000012",
            "APT 66, BLOCK B, RIVERSIDE COURT DUBLIN 4",
        )


# ---------------------------------------------------------------------------
# _first_valid_url
# ---------------------------------------------------------------------------


class TestFirstValidUrl:
    def test_returns_first_brochure_url(self):
        candidates = [
            "https://www.myhome.ie/residential/brochure/apartment-9-block-f/1000013",
            "https://www.myhome.ie/residential/brochure/apartment-10-block-f/1000014",
        ]
        result = _first_valid_url(candidates, "APT 9, BLOCK F, RIVERSIDE COURT DUBLIN 4")
        assert result == candidates[0]

    def test_skips_priceregister_url(self):
        candidates = [
            "https://www.myhome.ie/priceregister/apt-9-block-f/1000015",
            "https://www.myhome.ie/residential/brochure/apartment-9-block-f/1000016",
        ]
        result = _first_valid_url(candidates, "APT 9, BLOCK F, RIVERSIDE COURT DUBLIN 4")
        assert "brochure" in result

    def test_skips_for_rent_url(self):
        candidates = [
            "https://www.daft.ie/for-rent/apartment-riverside/1000017",
            "https://www.daft.ie/for-sale/apartment-9-block-f/1000018",
        ]
        result = _first_valid_url(candidates, "APT 9, BLOCK F, RIVERSIDE COURT DUBLIN 4")
        assert "for-sale" in result

    def test_skips_wrong_block(self):
        candidates = [
            "https://www.myhome.ie/residential/brochure/apartment-9-block-a/1000019",
            "https://www.myhome.ie/residential/brochure/apartment-9-block-f/1000020",
        ]
        result = _first_valid_url(candidates, "APT 9, BLOCK F, RIVERSIDE COURT DUBLIN 4")
        assert result == candidates[1]

    def test_returns_none_when_no_match(self):
        candidates = [
            "https://www.myhome.ie/priceregister/apt-9/1000021",
            "https://www.daft.ie/for-rent/apartment/1000022",
        ]
        assert _first_valid_url(candidates, "APT 9, BLOCK F, RIVERSIDE COURT DUBLIN 4") is None

    def test_empty_candidates(self):
        assert _first_valid_url([], "APT 9, BLOCK F, RIVERSIDE COURT DUBLIN 4") is None


# ---------------------------------------------------------------------------
# build_search_url
# ---------------------------------------------------------------------------


class TestBuildSearchUrl:
    def test_returns_google_url(self):
        url = build_search_url("APT 9, BLOCK F, RIVERSIDE COURT DUBLIN 4")
        assert url.startswith("https://www.google.com/search?")

    def test_includes_myhome_site_operator(self):
        url = build_search_url("APT 9, BLOCK F, RIVERSIDE COURT DUBLIN 4")
        assert "myhome.ie" in url

    def test_includes_daft_site_operator(self):
        url = build_search_url("APT 9, BLOCK F, RIVERSIDE COURT DUBLIN 4")
        assert "daft.ie" in url
