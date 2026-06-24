import json
from dataclasses import dataclass, asdict
from typing import List, Optional

from exceptions import (
    BookNotFoundError,
    DuplicateBookError,
    InvalidBookDataError,
    DataFileError,
)

DATA_FILE = "data.json"


@dataclass
class Book:
    """Represents a single book entry in the collection.

    Attributes:
        title (str): The title of the book.
        author (str): The name of the book's author.
        year (int): The publication year of the book.
        read (bool): Whether the book has been marked as read. Defaults to False.

    Example:
        >>> book = Book(title="1984", author="George Orwell", year=1949)
        >>> book.read
        False
    """

    title: str
    author: str
    year: int
    read: bool = False


class BookCollection:
    def __init__(self):
        """Initialize a BookCollection and load existing books from disk.

        Calls :meth:`load_books` automatically on construction so that any
        previously saved data is available immediately.

        Example:
            >>> collection = BookCollection()
        """
        self.books: List[Book] = []
        try:
            self.load_books()
        except DataFileError:
            self.books = []

    def __enter__(self) -> "BookCollection":
        """Support use as a context manager.

        Returns:
            BookCollection: The collection instance itself.

        Example:
            >>> with BookCollection() as col:
            ...     col.add_book("1984", "George Orwell", 1949)
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Persist the collection on exit if no exception occurred.

        Args:
            exc_type: Exception type, or ``None`` if no exception.
            exc_val: Exception value, or ``None`` if no exception.
            exc_tb: Exception traceback, or ``None`` if no exception.

        Returns:
            bool: Always ``False`` — exceptions are never suppressed.
        """
        if exc_type is None:
            self.save_books()
        return False

    def load_books(self):
        """Load books from the JSON data file into memory.

        Reads ``data.json`` from the current working directory and populates
        ``self.books``. If the file does not exist, the collection starts
        empty. If the file is corrupted, a warning is printed and the
        collection also starts empty.

        Returns:
            None

        Raises:
            DataFileError: If the file is corrupted and cannot be parsed.

        Example:
            >>> collection = BookCollection()
            >>> collection.load_books()  # reloads from disk
        """
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                self.books = [Book(**b) for b in data]
        except FileNotFoundError:
            self.books = []
        except json.JSONDecodeError as e:
            raise DataFileError(f"data.json is corrupted: {e}") from e

    def save_books(self):
        """Persist the current in-memory book collection to the JSON data file.

        Serializes all :class:`Book` instances in ``self.books`` to
        ``data.json`` using pretty-printed JSON (2-space indent).

        Returns:
            None

        Raises:
            DataFileError: If the file cannot be written (e.g., permission denied).

        Example:
            >>> collection = BookCollection()
            >>> collection.save_books()  # writes current state to data.json
        """
        try:
            with open(DATA_FILE, "w") as f:
                json.dump([asdict(b) for b in self.books], f, indent=2)
        except OSError as e:
            raise DataFileError(f"Failed to save books: {e}") from e

    def add_book(self, title: str, author: str, year: int) -> Book:
        """Add a new book to the collection and save to disk.

        Creates a :class:`Book` with ``read=False``, appends it to the
        in-memory list, and immediately persists the collection.

        Args:
            title (str): The title of the book to add.
            author (str): The name of the book's author.
            year (int): The publication year of the book.

        Returns:
            Book: The newly created :class:`Book` instance.

        Raises:
            InvalidBookDataError: If title or author is empty, or year is negative.
            DuplicateBookError: If a book with the same title already exists.
            DataFileError: If saving to disk fails.

        Example:
            >>> collection = BookCollection()
            >>> book = collection.add_book("1984", "George Orwell", 1949)
            >>> book.title
            '1984'
        """
        if not title.strip():
            raise InvalidBookDataError("Title cannot be empty.")
        if not author.strip():
            raise InvalidBookDataError("Author cannot be empty.")
        if year < 0:
            raise InvalidBookDataError(f"Year must be a non-negative integer, got {year!r}.")
        if self.find_book_by_title(title):
            raise DuplicateBookError(f"A book titled {title!r} already exists.")
        book = Book(title=title, author=author, year=year)
        self.books.append(book)
        self.save_books()
        return book

    def list_books(self) -> List[Book]:
        """Return all books currently in the collection.

        Returns:
            List[Book]: A list of all :class:`Book` instances. Returns an
            empty list if the collection is empty.

        Example:
            >>> collection = BookCollection()
            >>> collection.add_book("Dune", "Frank Herbert", 1965)
            Book(title='Dune', author='Frank Herbert', year=1965, read=False)
            >>> books = collection.list_books()
            >>> len(books)
            1
        """
        return self.books

    def find_book_by_title(self, title: str) -> Optional[Book]:
        """Find a book by its exact title (case-insensitive).

        Args:
            title (str): The title to search for. Matching is case-insensitive
                and requires a full title match (not a substring match).

        Returns:
            Optional[Book]: The matching :class:`Book` instance, or ``None``
            if no book with that title exists.

        Example:
            >>> collection = BookCollection()
            >>> collection.add_book("Dune", "Frank Herbert", 1965)
            Book(title='Dune', author='Frank Herbert', year=1965, read=False)
            >>> collection.find_book_by_title("dune").author
            'Frank Herbert'
            >>> collection.find_book_by_title("Unknown") is None
            True
        """
        for book in self.books:
            if book.title.lower() == title.lower():
                return book
        return None

    def mark_as_read(self, title: str) -> bool:
        """Mark a book as read by its title.

        Looks up the book by title (case-insensitive) and sets its ``read``
        attribute to ``True``, then saves the collection to disk.

        Args:
            title (str): The title of the book to mark as read.

        Returns:
            None

        Raises:
            BookNotFoundError: If no book with the given title exists.
            DataFileError: If saving to disk fails.

        Example:
            >>> collection = BookCollection()
            >>> collection.add_book("1984", "George Orwell", 1949)
            Book(title='1984', author='George Orwell', year=1949, read=False)
            >>> collection.mark_as_read("1984")
            >>> collection.find_book_by_title("1984").read
            True
            >>> collection.mark_as_read("Unknown")
            Traceback (most recent call last):
                ...
            exceptions.BookNotFoundError: No book found with title 'Unknown'.
        """
        book = self.find_book_by_title(title)
        if not book:
            raise BookNotFoundError(f"No book found with title {title!r}.")
        book.read = True
        self.save_books()

    def remove_book(self, title: str) -> bool:
        """Remove a book from the collection by its title.

        Looks up the book by title (case-insensitive), removes it from the
        in-memory list, and saves the updated collection to disk.

        Args:
            title (str): The title of the book to remove.

        Returns:
            None

        Raises:
            BookNotFoundError: If no book with the given title exists.
            DataFileError: If saving to disk fails.

        Example:
            >>> collection = BookCollection()
            >>> collection.add_book("1984", "George Orwell", 1949)
            Book(title='1984', author='George Orwell', year=1949, read=False)
            >>> collection.remove_book("1984")
            >>> collection.remove_book("1984")
            Traceback (most recent call last):
                ...
            exceptions.BookNotFoundError: No book found with title '1984'.
        """
        book = self.find_book_by_title(title)
        if not book:
            raise BookNotFoundError(f"No book found with title {title!r}.")
        self.books.remove(book)
        self.save_books()

    def find_by_author(self, author: str) -> List[Book]:
        """Find all books by a given author (case-insensitive exact match).

        Args:
            author (str): The author name to search for. Matching is
                case-insensitive and requires a full name match.

        Returns:
            List[Book]: A list of :class:`Book` instances whose author matches.
            Returns an empty list if no matches are found.

        Example:
            >>> collection = BookCollection()
            >>> collection.add_book("1984", "George Orwell", 1949)
            Book(title='1984', author='George Orwell', year=1949, read=False)
            >>> collection.add_book("Animal Farm", "George Orwell", 1945)
            Book(title='Animal Farm', author='George Orwell', year=1945, read=False)
            >>> len(collection.find_by_author("george orwell"))
            2
        """
        return [b for b in self.books if b.author.lower() == author.lower()]

    def search(self, query: str) -> List[Book]:
        """Search books by title or author using a case-insensitive partial match.

        Args:
            query (str): The search string. Any book whose title or author
                contains this string (case-insensitive) will be included in
                the results.

        Returns:
            List[Book]: A list of matching :class:`Book` instances. Returns an
            empty list if no matches are found.

        Example:
            >>> collection = BookCollection()
            >>> collection.add_book("1984", "George Orwell", 1949)
            Book(title='1984', author='George Orwell', year=1949, read=False)
            >>> collection.add_book("Brave New World", "Aldous Huxley", 1932)
            Book(title='Brave New World', author='Aldous Huxley', year=1932, read=False)
            >>> len(collection.search("orwell"))
            1
            >>> len(collection.search("world"))
            1
        """
        q = query.lower()
        return [b for b in self.books if q in b.title.lower() or q in b.author.lower()]
