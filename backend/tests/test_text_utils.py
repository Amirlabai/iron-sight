import pytest

from src.utils.text_utils import standardize_name


class TestStandardizeName:
    def test_should_return_none_when_name_is_none(self):
        assert standardize_name(None) is None

    def test_should_return_none_when_name_is_empty(self):
        assert standardize_name("") is None

    def test_should_return_none_when_only_punctuation_and_spaces(self):
        assert standardize_name(" - , ( ) ") is None

    def test_should_remove_dashes_commas_parentheses_and_spaces(self):
        assert standardize_name("Tel-Aviv") == "TelAviv"

    def test_should_normalize_hebrew_city_name(self):
        assert standardize_name("תל אביב") == "תלאביב"

    def test_should_return_same_result_for_equivalent_spacing(self):
        a = standardize_name("Beer Sheva")
        b = standardize_name("Beer  Sheva")
        assert a == b == "BeerSheva"

    def test_should_use_lru_cache_for_repeated_calls(self):
        standardize_name.cache_clear()
        first = standardize_name("Haifa")
        second = standardize_name("Haifa")
        assert first is second

    def test_should_strip_after_structural_normalization(self):
        assert standardize_name("  Haifa  ") == "Haifa"
