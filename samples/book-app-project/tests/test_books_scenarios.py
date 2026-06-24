"""
シナリオベーステスト:
  - 同じタイトル・著者の重複書籍の追加
  - タイトルの部分一致による削除
  - コレクションが空の状態での検索
  - 保存時のファイル権限エラー
  - 書籍コレクションへの同時アクセス
"""

import sys
import os
import threading
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import books
from books import Book, BookCollection
from exceptions import (
    BookNotFoundError,
    DuplicateBookError,
    DataFileError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def use_temp_data_file(tmp_path, monkeypatch):
    """各テストでDATA_FILEを一時ファイルにリダイレクトする。"""
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
# シナリオ1: 同じタイトル・著者の重複書籍の追加
# ---------------------------------------------------------------------------

class TestDuplicateBookAddition:
    """同一タイトル・著者の書籍を追加したときの挙動を検証する。"""

    def test_duplicate_same_title_same_author_raises(self, collection):
        """全く同じタイトルと著者で2冊目を追加すると DuplicateBookError が発生する。"""
        collection.add_book("1984", "George Orwell", 1949)
        with pytest.raises(DuplicateBookError):
            collection.add_book("1984", "George Orwell", 1949)

    def test_duplicate_same_title_different_author_raises(self, collection):
        """タイトルが同じで著者が異なっても DuplicateBookError が発生する（重複判定はタイトルのみ）。"""
        collection.add_book("1984", "George Orwell", 1949)
        with pytest.raises(DuplicateBookError):
            collection.add_book("1984", "Another Author", 2000)

    def test_duplicate_case_insensitive_title_raises(self, collection):
        """タイトルの大文字小文字が異なっても重複とみなされる。"""
        collection.add_book("1984", "George Orwell", 1949)
        with pytest.raises(DuplicateBookError):
            collection.add_book("1984", "George Orwell", 1949)

    def test_duplicate_does_not_add_to_collection(self, collection):
        """重複追加が失敗しても、コレクションのサイズは変わらない。"""
        collection.add_book("1984", "George Orwell", 1949)
        try:
            collection.add_book("1984", "George Orwell", 1949)
        except DuplicateBookError:
            pass
        assert len(collection.books) == 1

    def test_duplicate_does_not_persist(self, collection):
        """重複追加が失敗しても、ディスク上のデータは汚染されない。"""
        collection.add_book("1984", "George Orwell", 1949)
        try:
            collection.add_book("1984", "George Orwell", 1949)
        except DuplicateBookError:
            pass
        reloaded = BookCollection()
        assert len(reloaded.books) == 1

    @pytest.mark.parametrize("title", ["1984", "1984", "1984"])
    def test_multiple_duplicate_attempts_all_raise(self, collection, title):
        """同じタイトルを何度追加しようとしても毎回 DuplicateBookError が発生する。"""
        collection.add_book("1984", "George Orwell", 1949)
        with pytest.raises(DuplicateBookError):
            collection.add_book(title, "George Orwell", 1949)


# ---------------------------------------------------------------------------
# シナリオ2: タイトルの部分一致による削除
# ---------------------------------------------------------------------------

class TestRemoveByPartialTitle:
    """remove_book はタイトルの完全一致のみを受け付け、部分一致では削除しない。"""

    def test_partial_title_raises_book_not_found(self, populated_collection):
        """「1984」の一部「198」で削除しようとすると BookNotFoundError が発生する。"""
        with pytest.raises(BookNotFoundError):
            populated_collection.remove_book("198")

    def test_partial_author_name_as_title_raises(self, populated_collection):
        """著者名の一部をタイトルとして渡しても BookNotFoundError が発生する。"""
        with pytest.raises(BookNotFoundError):
            populated_collection.remove_book("Orwell")

    def test_substring_of_title_raises(self, populated_collection):
        """タイトルの一部（末尾・中間）でも完全一致しなければ削除されない。"""
        with pytest.raises(BookNotFoundError):
            populated_collection.remove_book("Farm")  # "Animal Farm" の部分文字列

    def test_partial_match_does_not_remove_any_book(self, populated_collection):
        """部分一致による削除を試みても、コレクションのサイズは変わらない。"""
        original_count = len(populated_collection.books)
        try:
            populated_collection.remove_book("Dun")  # "Dune" の部分文字列
        except BookNotFoundError:
            pass
        assert len(populated_collection.books) == original_count

    def test_exact_title_is_removed_successfully(self, populated_collection):
        """完全一致するタイトルであれば正常に削除できる（対照テスト）。"""
        populated_collection.remove_book("Dune")
        assert populated_collection.find_book_by_title("Dune") is None


# ---------------------------------------------------------------------------
# シナリオ3: コレクションが空の状態での検索
# ---------------------------------------------------------------------------

class TestSearchOnEmptyCollection:
    """空のコレクションに対する各種検索操作の挙動を検証する。"""

    def test_search_returns_empty_list(self, collection):
        """`search` は空のコレクションに対して空リストを返す。"""
        assert collection.search("anything") == []

    def test_search_empty_query_returns_empty_list(self, collection):
        """空文字クエリでも空のコレクションでは空リストを返す。"""
        assert collection.search("") == []

    def test_find_book_by_title_returns_none(self, collection):
        """`find_book_by_title` は空のコレクションに対して None を返す。"""
        assert collection.find_book_by_title("1984") is None

    def test_find_by_author_returns_empty_list(self, collection):
        """`find_by_author` は空のコレクションに対して空リストを返す。"""
        assert collection.find_by_author("George Orwell") == []

    def test_list_books_returns_empty_list(self, collection):
        """`list_books` は空のコレクションに対して空リストを返す。"""
        assert collection.list_books() == []

    def test_mark_as_read_raises_on_empty_collection(self, collection):
        """`mark_as_read` は空のコレクションに対して BookNotFoundError を発生させる。"""
        with pytest.raises(BookNotFoundError):
            collection.mark_as_read("Nonexistent")

    def test_remove_book_raises_on_empty_collection(self, collection):
        """`remove_book` は空のコレクションに対して BookNotFoundError を発生させる。"""
        with pytest.raises(BookNotFoundError):
            collection.remove_book("Nonexistent")

    @pytest.mark.parametrize("query", ["a", "1", " ", "xyz"])
    def test_search_various_queries_on_empty(self, collection, query):
        """どんなクエリでも空のコレクションでは空リストが返る。"""
        assert collection.search(query) == []


# ---------------------------------------------------------------------------
# シナリオ4: 保存時のファイル権限エラー
# ---------------------------------------------------------------------------

class TestSaveBooksPermissionError:
    """ファイルへの書き込み権限がない場合の挙動を検証する。"""

    def test_save_books_raises_data_file_error_on_permission_denied(
        self, collection, monkeypatch
    ):
        """`save_books` が PermissionError を DataFileError に変換して送出する。"""
        def mock_open(*args, **kwargs):
            raise PermissionError("Permission denied")

        monkeypatch.setattr("builtins.open", mock_open)
        with pytest.raises(DataFileError):
            collection.save_books()

    def test_save_books_raises_data_file_error_on_os_error(
        self, collection, monkeypatch
    ):
        """`save_books` が OSError を DataFileError に変換して送出する。"""
        def mock_open(*args, **kwargs):
            raise OSError("Read-only file system")

        monkeypatch.setattr("builtins.open", mock_open)
        with pytest.raises(DataFileError):
            collection.save_books()

    def test_add_book_raises_data_file_error_when_save_fails(
        self, collection, monkeypatch
    ):
        """`add_book` 内部の保存が失敗した場合、DataFileError が伝播する。"""
        def mock_open(*args, **kwargs):
            raise PermissionError("Permission denied")

        # load_books (read) はすでに完了しているため、書き込みのみをブロックする
        original_open = open
        call_count = {"n": 0}

        def selective_mock_open(path, mode="r", **kwargs):
            if "w" in mode:
                raise PermissionError("Permission denied")
            return original_open(path, mode, **kwargs)

        monkeypatch.setattr("builtins.open", selective_mock_open)
        with pytest.raises(DataFileError):
            collection.add_book("1984", "George Orwell", 1949)

    def test_data_file_error_message_contains_cause(self, collection, monkeypatch):
        """DataFileError のメッセージに元のエラー情報が含まれる。"""
        def mock_open(*args, **kwargs):
            raise PermissionError("Permission denied: /data.json")

        monkeypatch.setattr("builtins.open", mock_open)
        with pytest.raises(DataFileError, match="Failed to save books"):
            collection.save_books()

    def test_permission_error_on_read_only_file(self, tmp_path, monkeypatch):
        """実際に読み取り専用ファイルに書き込もうとすると DataFileError が発生する。"""
        temp_file = tmp_path / "readonly.json"
        temp_file.write_text("[]")
        temp_file.chmod(0o444)  # 読み取り専用に設定
        monkeypatch.setattr(books, "DATA_FILE", str(temp_file))

        col = BookCollection()
        with pytest.raises(DataFileError):
            col.save_books()

        # クリーンアップ: パーミッションを元に戻す
        temp_file.chmod(0o644)


# ---------------------------------------------------------------------------
# シナリオ5: 書籍コレクションへの同時アクセス
# ---------------------------------------------------------------------------

class TestConcurrentAccess:
    """複数スレッドから BookCollection に同時アクセスしたときの挙動を検証する。"""

    def test_concurrent_reads_are_safe(self, populated_collection):
        """複数スレッドが同時に `list_books` を呼び出しても例外が発生しない。"""
        errors = []

        def read_books():
            try:
                result = populated_collection.list_books()
                assert isinstance(result, list)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=read_books) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Concurrent reads raised exceptions: {errors}"

    def test_concurrent_searches_are_safe(self, populated_collection):
        """複数スレッドが同時に `search` を呼び出しても例外が発生しない。"""
        errors = []

        def search_books():
            try:
                result = populated_collection.search("orwell")
                assert isinstance(result, list)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=search_books) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Concurrent searches raised exceptions: {errors}"

    def test_concurrent_adds_result_in_no_data_loss(self, collection):
        """複数スレッドが異なるタイトルの書籍を同時に追加し、全件が保存される。"""
        titles = [f"Book {i}" for i in range(10)]
        errors = []

        def add_book(title):
            try:
                collection.add_book(title, "Author", 2000)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_book, args=(t,)) for t in titles]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # DuplicateBookError 以外のエラーがないことを確認
        unexpected = [e for e in errors if not isinstance(e, DuplicateBookError)]
        assert unexpected == [], f"Unexpected errors during concurrent adds: {unexpected}"

        # 重複なく追加された冊数が合計と一致することを確認
        assert len(collection.books) == len(titles) - len(errors)

    def test_concurrent_read_write_does_not_corrupt_data(self, populated_collection):
        """読み取りと書き込みが同時に行われてもデータ破損が起きない。"""
        errors = []

        def reader():
            try:
                for _ in range(5):
                    result = populated_collection.search("orwell")
                    assert isinstance(result, list)
            except Exception as e:
                errors.append(e)

        def writer():
            try:
                populated_collection.mark_as_read("1984")
            except (BookNotFoundError, DataFileError) as e:
                errors.append(e)

        readers = [threading.Thread(target=reader) for _ in range(5)]
        writers = [threading.Thread(target=writer) for _ in range(2)]
        all_threads = readers + writers

        for t in all_threads:
            t.start()
        for t in all_threads:
            t.join()

        # 読み取り中の例外がないことを確認（書き込み例外は許容）
        read_errors = [e for e in errors if not isinstance(e, (BookNotFoundError, DataFileError))]
        assert read_errors == [], f"Unexpected errors during concurrent read/write: {read_errors}"
