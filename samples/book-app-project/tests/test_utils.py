import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from utils import get_book_details
from exceptions import InvalidBookDataError


def make_inputs(*values):
    """Return an iterator that supplies values in order to repeated input() calls."""
    return iter(values)


@pytest.fixture
def patch_input(monkeypatch):
    """Factory fixture: call with (title, author, year_str) to mock all three prompts."""
    def _patch(title, author, year_str):
        monkeypatch.setattr("builtins.input", lambda _: next(make_inputs(title, author, year_str)))

    def _patch_seq(*values):
        it = iter(values)
        monkeypatch.setattr("builtins.input", lambda _: next(it))

    return _patch_seq


# ---------------------------------------------------------------------------
# get_book_details — happy path
# ---------------------------------------------------------------------------

class TestGetBookDetailsHappyPath:
    def test_returns_tuple_of_three(self, patch_input):
        patch_input("1984", "George Orwell", "1949")
        result = get_book_details()
        assert len(result) == 3

    def test_title_is_returned(self, patch_input):
        patch_input("1984", "George Orwell", "1949")
        title, _, _ = get_book_details()
        assert title == "1984"

    def test_author_is_returned(self, patch_input):
        patch_input("1984", "George Orwell", "1949")
        _, author, _ = get_book_details()
        assert author == "George Orwell"

    def test_year_returned_as_int(self, patch_input):
        patch_input("1984", "George Orwell", "1949")
        _, _, year = get_book_details()
        assert year == 1949
        assert isinstance(year, int)

    def test_year_zero_is_valid(self, patch_input):
        patch_input("Ancient Text", "Unknown", "0")
        _, _, year = get_book_details()
        assert year == 0

    def test_strips_whitespace_from_inputs(self, patch_input):
        patch_input("  Dune  ", "  Frank Herbert  ", "1965")
        title, author, year = get_book_details()
        assert title == "Dune"
        assert author == "Frank Herbert"
        assert year == 1965

    @pytest.mark.parametrize("title,author,year_str,expected_year", [
        ("1984", "George Orwell", "1949", 1949),
        ("Dune", "Frank Herbert", "1965", 1965),
        ("Brave New World", "Aldous Huxley", "1932", 1932),
        ("Moby Dick", "Herman Melville", "1851", 1851),
    ])
    def test_various_valid_inputs(self, patch_input, title, author, year_str, expected_year):
        patch_input(title, author, year_str)
        t, a, y = get_book_details()
        assert t == title
        assert a == author
        assert y == expected_year


# ---------------------------------------------------------------------------
# get_book_details — empty strings
# ---------------------------------------------------------------------------

class TestGetBookDetailsEmptyStrings:
    def test_empty_title_is_returned_without_error(self, patch_input):
        """get_book_details does not validate title/author — caller is responsible."""
        patch_input("", "George Orwell", "1949")
        title, _, _ = get_book_details()
        assert title == ""

    def test_empty_author_is_returned_without_error(self, patch_input):
        patch_input("1984", "", "1949")
        _, author, _ = get_book_details()
        assert author == ""

    def test_whitespace_only_title_stripped_to_empty(self, patch_input):
        patch_input("   ", "George Orwell", "1949")
        title, _, _ = get_book_details()
        assert title == ""

    def test_whitespace_only_author_stripped_to_empty(self, patch_input):
        patch_input("1984", "   ", "1949")
        _, author, _ = get_book_details()
        assert author == ""


# ---------------------------------------------------------------------------
# get_book_details — invalid year formats
# ---------------------------------------------------------------------------

class TestGetBookDetailsInvalidYear:
    @pytest.mark.parametrize("bad_year", [
        "abc",
        "19.49",
        "19 49",
        "year",
        "!@#",
        "",
        "None",
        "1e3",
        "--1949",
    ])
    def test_raises_invalid_book_data_error(self, patch_input, bad_year):
        patch_input("1984", "George Orwell", bad_year)
        with pytest.raises(InvalidBookDataError):
            get_book_details()

    def test_error_message_contains_bad_value(self, patch_input):
        patch_input("1984", "George Orwell", "notayear")
        with pytest.raises(InvalidBookDataError, match="notayear"):
            get_book_details()

    def test_negative_year_string_is_valid_int(self, patch_input):
        """'-1' parses as int(-1); domain validation (year < 0) is BookCollection's job."""
        patch_input("Old Book", "Author", "-1")
        _, _, year = get_book_details()
        assert year == -1

    def test_float_string_raises(self, patch_input):
        patch_input("1984", "George Orwell", "1949.5")
        with pytest.raises(InvalidBookDataError):
            get_book_details()


# ---------------------------------------------------------------------------
# get_book_details — very long titles
# ---------------------------------------------------------------------------

class TestGetBookDetailsLongTitle:
    def test_long_title_returned_intact(self, patch_input):
        long_title = "A" * 1000
        patch_input(long_title, "Author", "2000")
        title, _, _ = get_book_details()
        assert title == long_title
        assert len(title) == 1000

    def test_long_title_with_spaces_stripped(self, patch_input):
        long_title = "  " + "B" * 500 + "  "
        patch_input(long_title, "Author", "2000")
        title, _, _ = get_book_details()
        assert title == "B" * 500

    def test_long_title_with_unicode(self, patch_input):
        long_title = "図書" * 200  # 400 CJK characters
        patch_input(long_title, "著者", "2024")
        title, author, year = get_book_details()
        assert title == long_title
        assert len(title) == 400


# ---------------------------------------------------------------------------
# get_book_details — special characters in author name
# ---------------------------------------------------------------------------

class TestGetBookDetailsSpecialCharactersInAuthor:
    @pytest.mark.parametrize("author", [
        "García Márquez",          # accent
        "Ó'Brien",                 # apostrophe + accent
        "Jean-Paul Sartre",        # hyphen
        "Tōgō Heihachirō",         # macron
        "Haruki Murakami (村上春樹)", # parentheses + CJK
        "Author & Co.",            # ampersand
        "Dr. Seuss",               # period
        "名無し",                   # CJK only
        "Ñoño",                    # tilde
        "Müller",                  # umlaut
    ])
    def test_special_author_returned_intact(self, patch_input, author):
        patch_input("Some Book", author, "2000")
        _, returned_author, _ = get_book_details()
        assert returned_author == author

    def test_author_with_newline_stripped(self, patch_input):
        """Trailing whitespace/newline is stripped by .strip()."""
        patch_input("Book", "Author\n", "2000")
        _, author, _ = get_book_details()
        assert author == "Author"

    def test_author_with_emoji(self, patch_input):
        patch_input("Book", "Author 📚", "2000")
        _, author, _ = get_book_details()
        assert author == "Author 📚"
