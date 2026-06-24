import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import books
from books import Book, BookCollection
from exceptions import (
    BookNotFoundError,
    DuplicateBookError,
    InvalidBookDataError,
    DataFileError,
)


@pytest.fixture(autouse=True)
def use_temp_data_file(tmp_path, monkeypatch):
    """Redirect DATA_FILE to a temporary path for each test."""
    temp_file = tmp_path / "data.json"
    temp_file.write_text("[]")
    monkeypatch.setattr(books, "DATA_FILE", str(temp_file))


@pytest.fixture
def collection():
    return BookCollection()


@pytest.fixture
def populated_collection(collection):
    collection.add_book("1984", "George Orwell", 1949)
    collection.add_book("Animal Farm", "George Orwell", 1945)
    collection.add_book("Dune", "Frank Herbert", 1965)
    return collection


# ---------------------------------------------------------------------------
# Book dataclass
# ---------------------------------------------------------------------------

class TestBook:
    def test_defaults_read_to_false(self):
        book = Book(title="1984", author="George Orwell", year=1949)
        assert book.read is False

    def test_explicit_read_true(self):
        book = Book(title="1984", author="George Orwell", year=1949, read=True)
        assert book.read is True

    def test_fields_stored_correctly(self):
        book = Book(title="Dune", author="Frank Herbert", year=1965)
        assert book.title == "Dune"
        assert book.author == "Frank Herbert"
        assert book.year == 1965


# ---------------------------------------------------------------------------
# load_books
# ---------------------------------------------------------------------------

class TestLoadBooks:
    def test_loads_empty_collection_when_file_is_empty_list(self, collection):
        assert collection.books == []

    def test_loads_books_from_existing_file(self, tmp_path, monkeypatch):
        data = [{"title": "1984", "author": "George Orwell", "year": 1949, "read": False}]
        f = tmp_path / "data.json"
        f.write_text(json.dumps(data))
        monkeypatch.setattr(books, "DATA_FILE", str(f))

        col = BookCollection()
        assert len(col.books) == 1
        assert col.books[0].title == "1984"

    def test_starts_empty_when_file_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setattr(books, "DATA_FILE", str(tmp_path / "missing.json"))
        col = BookCollection()
        assert col.books == []

    def test_starts_empty_on_corrupted_json(self, tmp_path, monkeypatch):
        """__init__ catches DataFileError and starts empty; load_books raises it directly."""
        f = tmp_path / "data.json"
        f.write_text("not valid json {{{")
        monkeypatch.setattr(books, "DATA_FILE", str(f))

        col = BookCollection()
        assert col.books == []

    def test_load_books_raises_data_file_error_on_corrupt_json(self, tmp_path, monkeypatch):
        f = tmp_path / "data.json"
        f.write_text("not valid json {{{")
        monkeypatch.setattr(books, "DATA_FILE", str(f))

        col = BookCollection.__new__(BookCollection)
        col.books = []
        with pytest.raises(DataFileError):
            col.load_books()


# ---------------------------------------------------------------------------
# Context manager (__enter__ / __exit__)
# ---------------------------------------------------------------------------

class TestContextManager:
    def test_enter_returns_self(self, collection):
        with collection as ctx:
            assert ctx is collection

    def test_saves_on_clean_exit(self, collection):
        with collection:
            collection.books.append(Book("1984", "George Orwell", 1949))
        col2 = BookCollection()
        assert len(col2.books) == 1

    def test_does_not_save_on_exception(self, collection):
        try:
            with collection:
                collection.books.append(Book("1984", "George Orwell", 1949))
                raise RuntimeError("simulated error")
        except RuntimeError:
            pass
        col2 = BookCollection()
        assert col2.books == []

    def test_does_not_suppress_exception(self, collection):
        with pytest.raises(ValueError):
            with collection:
                raise ValueError("should propagate")


# ---------------------------------------------------------------------------
# save_books
# ---------------------------------------------------------------------------

class TestSaveBooks:
    def test_persists_books_to_disk(self, collection):
        collection.add_book("1984", "George Orwell", 1949)
        collection.save_books()

        col2 = BookCollection()
        assert len(col2.books) == 1
        assert col2.books[0].title == "1984"

    def test_persists_read_flag(self, collection):
        collection.add_book("1984", "George Orwell", 1949)
        collection.mark_as_read("1984")

        col2 = BookCollection()
        assert col2.books[0].read is True

    def test_saves_empty_collection(self, collection):
        collection.save_books()
        col2 = BookCollection()
        assert col2.books == []


# ---------------------------------------------------------------------------
# add_book
# ---------------------------------------------------------------------------

class TestAddBook:
    def test_returns_book_instance(self, collection):
        book = collection.add_book("1984", "George Orwell", 1949)
        assert isinstance(book, Book)

    def test_returned_book_has_correct_fields(self, collection):
        book = collection.add_book("1984", "George Orwell", 1949)
        assert book.title == "1984"
        assert book.author == "George Orwell"
        assert book.year == 1949
        assert book.read is False

    def test_increases_collection_size(self, collection):
        collection.add_book("1984", "George Orwell", 1949)
        collection.add_book("Dune", "Frank Herbert", 1965)
        assert len(collection.books) == 2

    def test_add_book_is_persisted(self, collection):
        collection.add_book("1984", "George Orwell", 1949)
        col2 = BookCollection()
        assert len(col2.books) == 1

    def test_raises_on_empty_title(self, collection):
        with pytest.raises(InvalidBookDataError):
            collection.add_book("", "George Orwell", 1949)

    def test_raises_on_whitespace_title(self, collection):
        with pytest.raises(InvalidBookDataError):
            collection.add_book("   ", "George Orwell", 1949)

    def test_raises_on_empty_author(self, collection):
        with pytest.raises(InvalidBookDataError):
            collection.add_book("1984", "", 1949)

    def test_raises_on_negative_year(self, collection):
        with pytest.raises(InvalidBookDataError):
            collection.add_book("1984", "George Orwell", -1)

    def test_raises_on_duplicate_title(self, collection):
        collection.add_book("1984", "George Orwell", 1949)
        with pytest.raises(DuplicateBookError):
            collection.add_book("1984", "Someone Else", 2000)

    def test_duplicate_check_is_case_insensitive(self, collection):
        collection.add_book("1984", "George Orwell", 1949)
        with pytest.raises(DuplicateBookError):
            collection.add_book("1984", "George Orwell", 1949)

    def test_year_zero_is_valid(self, collection):
        """Year 0 is on the boundary and must NOT raise."""
        book = collection.add_book("Ancient Text", "Unknown", 0)
        assert book.year == 0

    @pytest.mark.parametrize("title,author,year,exc", [
        ("", "George Orwell", 1949, InvalidBookDataError),
        ("   ", "George Orwell", 1949, InvalidBookDataError),
        ("1984", "", 1949, InvalidBookDataError),
        ("1984", "   ", 1949, InvalidBookDataError),
        ("1984", "George Orwell", -1, InvalidBookDataError),
    ])
    def test_invalid_inputs_raise(self, collection, title, author, year, exc):
        with pytest.raises(exc):
            collection.add_book(title, author, year)


# ---------------------------------------------------------------------------
# list_books
# ---------------------------------------------------------------------------

class TestListBooks:
    def test_returns_empty_list_initially(self, collection):
        assert collection.list_books() == []

    def test_returns_all_books(self, populated_collection):
        result = populated_collection.list_books()
        assert len(result) == 3

    def test_returns_same_objects(self, collection):
        collection.add_book("1984", "George Orwell", 1949)
        assert collection.list_books() is collection.books


# ---------------------------------------------------------------------------
# find_book_by_title
# ---------------------------------------------------------------------------

class TestFindBookByTitle:
    def test_finds_exact_match(self, populated_collection):
        book = populated_collection.find_book_by_title("1984")
        assert book is not None
        assert book.title == "1984"

    def test_case_insensitive(self, populated_collection):
        assert populated_collection.find_book_by_title("dune") is not None
        assert populated_collection.find_book_by_title("DUNE") is not None
        assert populated_collection.find_book_by_title("DuNe") is not None

    def test_returns_none_when_not_found(self, populated_collection):
        assert populated_collection.find_book_by_title("Unknown Title") is None

    def test_does_not_match_partial_title(self, populated_collection):
        assert populated_collection.find_book_by_title("19") is None

    def test_returns_none_on_empty_collection(self, collection):
        assert collection.find_book_by_title("1984") is None

    @pytest.mark.parametrize("title", ["1984", "dune", "ANIMAL FARM"])
    def test_case_insensitive_parametrized(self, populated_collection, title):
        assert populated_collection.find_book_by_title(title) is not None


# ---------------------------------------------------------------------------
# mark_as_read
# ---------------------------------------------------------------------------

class TestMarkAsRead:
    def test_sets_read_flag(self, populated_collection):
        populated_collection.mark_as_read("1984")
        assert populated_collection.find_book_by_title("1984").read is True

    def test_returns_none(self, populated_collection):
        result = populated_collection.mark_as_read("1984")
        assert result is None

    def test_case_insensitive(self, populated_collection):
        populated_collection.mark_as_read("DUNE")
        assert populated_collection.find_book_by_title("Dune").read is True

    def test_raises_when_not_found(self, collection):
        with pytest.raises(BookNotFoundError):
            collection.mark_as_read("Nonexistent Book")

    def test_mark_as_read_is_persisted(self, populated_collection):
        populated_collection.mark_as_read("1984")
        col2 = BookCollection()
        assert col2.find_book_by_title("1984").read is True

    def test_idempotent_when_already_read(self, populated_collection):
        populated_collection.mark_as_read("1984")
        populated_collection.mark_as_read("1984")
        assert populated_collection.find_book_by_title("1984").read is True


# ---------------------------------------------------------------------------
# remove_book
# ---------------------------------------------------------------------------

class TestRemoveBook:
    def test_returns_none_when_found(self, populated_collection):
        result = populated_collection.remove_book("1984")
        assert result is None

    def test_book_no_longer_in_collection(self, populated_collection):
        populated_collection.remove_book("1984")
        assert populated_collection.find_book_by_title("1984") is None

    def test_only_removes_target_book(self, populated_collection):
        populated_collection.remove_book("1984")
        assert len(populated_collection.books) == 2
        assert populated_collection.find_book_by_title("Dune") is not None

    def test_case_insensitive(self, populated_collection):
        populated_collection.remove_book("dune")
        assert populated_collection.find_book_by_title("Dune") is None

    def test_raises_when_not_found(self, collection):
        with pytest.raises(BookNotFoundError):
            collection.remove_book("Nonexistent Book")

    def test_removal_is_persisted(self, populated_collection):
        populated_collection.remove_book("1984")
        col2 = BookCollection()
        assert col2.find_book_by_title("1984") is None

    def test_raises_on_second_remove(self, populated_collection):
        populated_collection.remove_book("1984")
        with pytest.raises(BookNotFoundError):
            populated_collection.remove_book("1984")


# ---------------------------------------------------------------------------
# find_by_author
# ---------------------------------------------------------------------------

class TestFindByAuthor:
    def test_returns_all_books_by_author(self, populated_collection):
        results = populated_collection.find_by_author("George Orwell")
        assert len(results) == 2

    def test_case_insensitive(self, populated_collection):
        assert len(populated_collection.find_by_author("george orwell")) == 2
        assert len(populated_collection.find_by_author("GEORGE ORWELL")) == 2

    def test_returns_empty_list_when_not_found(self, populated_collection):
        assert populated_collection.find_by_author("Unknown Author") == []

    def test_does_not_match_partial_author(self, populated_collection):
        assert populated_collection.find_by_author("Orwell") == []

    def test_single_result(self, populated_collection):
        results = populated_collection.find_by_author("Frank Herbert")
        assert len(results) == 1
        assert results[0].title == "Dune"

    def test_returns_empty_list_on_empty_collection(self, collection):
        assert collection.find_by_author("George Orwell") == []

    def test_whitespace_author_returns_empty(self, populated_collection):
        assert populated_collection.find_by_author("  ") == []

    # --- エッジケース: ハイフンを含む著者名 ---

    def test_hyphenated_author_exact_match(self, collection):
        """ハイフンを含む著者名（例: "Jean-Paul Sartre"）を完全一致で検索できる。"""
        collection.add_book("Being and Nothingness", "Jean-Paul Sartre", 1943)
        results = collection.find_by_author("Jean-Paul Sartre")
        assert len(results) == 1
        assert results[0].title == "Being and Nothingness"

    def test_hyphenated_author_case_insensitive(self, collection):
        """ハイフンを含む著者名の大文字小文字を無視して検索できる。"""
        collection.add_book("Being and Nothingness", "Jean-Paul Sartre", 1943)
        assert len(collection.find_by_author("jean-paul sartre")) == 1
        assert len(collection.find_by_author("JEAN-PAUL SARTRE")) == 1

    def test_hyphenated_author_partial_does_not_match(self, collection):
        """ハイフンで分割した一部分（例: "Sartre"）は部分一致しない。"""
        collection.add_book("Being and Nothingness", "Jean-Paul Sartre", 1943)
        assert collection.find_by_author("Sartre") == []
        assert collection.find_by_author("Jean-Paul") == []

    def test_hyphen_vs_space_does_not_match(self, collection):
        """ハイフン区切りとスペース区切りは別の著者名として扱われる。"""
        collection.add_book("Being and Nothingness", "Jean-Paul Sartre", 1943)
        assert collection.find_by_author("Jean Paul Sartre") == []

    # --- エッジケース: 複数の名前を持つ著者 ---

    def test_multi_part_name_exact_match(self, collection):
        """複数パートからなる著者名（例: "Mary Wollstonecraft Shelley"）を完全一致で検索できる。"""
        collection.add_book("Frankenstein", "Mary Wollstonecraft Shelley", 1818)
        results = collection.find_by_author("Mary Wollstonecraft Shelley")
        assert len(results) == 1
        assert results[0].title == "Frankenstein"

    def test_multi_part_name_case_insensitive(self, collection):
        """複数パートからなる著者名の大文字小文字を無視して検索できる。"""
        collection.add_book("Frankenstein", "Mary Wollstonecraft Shelley", 1818)
        assert len(collection.find_by_author("mary wollstonecraft shelley")) == 1
        assert len(collection.find_by_author("MARY WOLLSTONECRAFT SHELLEY")) == 1

    def test_multi_part_name_partial_does_not_match(self, collection):
        """複数パートからなる著者名の一部分だけでは一致しない。"""
        collection.add_book("Frankenstein", "Mary Wollstonecraft Shelley", 1818)
        assert collection.find_by_author("Mary Shelley") == []
        assert collection.find_by_author("Wollstonecraft") == []

    def test_multiple_books_by_multipart_author(self, collection):
        """複数パートの著者名を持つ著者の全著作がまとめて取得できる。"""
        collection.add_book("Frankenstein", "Mary Wollstonecraft Shelley", 1818)
        collection.add_book("The Last Man", "Mary Wollstonecraft Shelley", 1826)
        results = collection.find_by_author("Mary Wollstonecraft Shelley")
        assert len(results) == 2

    # --- エッジケース: 空文字の著者名 ---

    def test_empty_string_query_returns_only_empty_author_books(self, collection):
        """空文字クエリは著者名が空文字の Book のみを返す（add_book では作れないケース）。"""
        # Book を直接生成して著者名を空にする
        collection.books.append(Book(title="Ghost Book", author="", year=2000))
        results = collection.find_by_author("")
        assert len(results) == 1
        assert results[0].title == "Ghost Book"

    def test_empty_string_query_does_not_match_normal_authors(self, collection):
        """空文字クエリは通常の著者名を持つ書籍にはマッチしない。"""
        collection.add_book("1984", "George Orwell", 1949)
        assert collection.find_by_author("") == []

    def test_empty_string_query_on_empty_collection(self, collection):
        """空文字クエリを空コレクションに対して使用すると空リストを返す。"""
        assert collection.find_by_author("") == []

    # --- エッジケース: アクセント付き文字を含む著者名 ---

    def test_accented_author_exact_match(self, collection):
        """アクセント付き文字を含む著者名（例: "Gabriel García Márquez"）を完全一致で検索できる。"""
        collection.add_book("One Hundred Years of Solitude", "Gabriel García Márquez", 1967)
        results = collection.find_by_author("Gabriel García Márquez")
        assert len(results) == 1
        assert results[0].title == "One Hundred Years of Solitude"

    def test_accented_author_case_insensitive(self, collection):
        """アクセント付き文字を含む著者名の大文字小文字を無視して検索できる。"""
        collection.add_book("One Hundred Years of Solitude", "Gabriel García Márquez", 1967)
        assert len(collection.find_by_author("gabriel garcía márquez")) == 1
        assert len(collection.find_by_author("GABRIEL GARCÍA MÁRQUEZ")) == 1

    def test_accented_author_unaccented_does_not_match(self, collection):
        """アクセントを除いた著者名（例: "Garcia Marquez"）はマッチしない。"""
        collection.add_book("One Hundred Years of Solitude", "Gabriel García Márquez", 1967)
        assert collection.find_by_author("Gabriel Garcia Marquez") == []

    def test_multiple_accented_authors(self, collection):
        """アクセント付き文字を含む複数の著者を正しく区別できる。"""
        collection.add_book("One Hundred Years of Solitude", "Gabriel García Márquez", 1967)
        collection.add_book("Ficciones", "Jorge Luis Borges", 1944)
        collection.add_book("Pedro Páramo", "Juan Rulfo", 1955)
        assert len(collection.find_by_author("Gabriel García Márquez")) == 1
        assert len(collection.find_by_author("Jorge Luis Borges")) == 1
        assert len(collection.find_by_author("Juan Rulfo")) == 1

    @pytest.mark.parametrize("author,expected_count", [
        ("Jean-Paul Sartre", 1),
        ("jean-paul sartre", 1),
        ("JEAN-PAUL SARTRE", 1),
        ("Jean-Paul", 0),         # 部分一致はマッチしない
        ("Jean Paul Sartre", 0),  # ハイフンなしはマッチしない
    ])
    def test_hyphenated_author_parametrized(self, collection, author, expected_count):
        """ハイフンを含む著者名の各クエリパターンの検索結果数を検証する。"""
        collection.add_book("Being and Nothingness", "Jean-Paul Sartre", 1943)
        assert len(collection.find_by_author(author)) == expected_count

    @pytest.mark.parametrize("author,expected_count", [
        ("Gabriel García Márquez", 1),
        ("gabriel garcía márquez", 1),
        ("GABRIEL GARCÍA MÁRQUEZ", 1),
        ("Gabriel Garcia Marquez", 0),   # アクセントなしはマッチしない
        ("García Márquez", 0),           # 部分一致はマッチしない
    ])
    def test_accented_author_parametrized(self, collection, author, expected_count):
        """アクセント付き文字を含む著者名の各クエリパターンの検索結果数を検証する。"""
        collection.add_book("One Hundred Years of Solitude", "Gabriel García Márquez", 1967)
        assert len(collection.find_by_author(author)) == expected_count


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

class TestSearch:
    def test_partial_title_match(self, collection):
        collection.add_book("The Great Gatsby", "F. Scott Fitzgerald", 1925)
        collection.add_book("Great Expectations", "Charles Dickens", 1861)
        collection.add_book("1984", "George Orwell", 1949)
        results = collection.search("great")
        assert len(results) == 2
        titles = [b.title for b in results]
        assert "The Great Gatsby" in titles
        assert "Great Expectations" in titles

    def test_partial_author_match(self, populated_collection):
        results = populated_collection.search("orwell")
        assert len(results) == 2

    def test_case_insensitive(self, collection):
        collection.add_book("Brave New World", "Aldous Huxley", 1932)
        assert len(collection.search("BRAVE")) == 1
        assert len(collection.search("huxley")) == 1

    def test_returns_empty_list_when_no_match(self, populated_collection):
        assert populated_collection.search("xyzzy_no_match") == []

    def test_matches_both_title_and_author_hit(self, collection):
        collection.add_book("George's Marvellous Medicine", "Roald Dahl", 1981)
        collection.add_book("1984", "George Orwell", 1949)
        results = collection.search("george")
        assert len(results) == 2

    def test_empty_query_matches_all(self, populated_collection):
        results = populated_collection.search("")
        assert len(results) == len(populated_collection.books)

    def test_search_on_empty_collection(self, collection):
        assert collection.search("anything") == []

    def test_empty_query_on_empty_collection(self, collection):
        assert collection.search("") == []

    def test_remove_last_book_leaves_empty_collection(self, collection):
        collection.add_book("Solo Book", "Author A", 2000)
        collection.remove_book("Solo Book")
        assert collection.list_books() == []

    def test_mark_as_read_on_empty_collection_raises(self, collection):
        with pytest.raises(BookNotFoundError):
            collection.mark_as_read("Nonexistent")
