from __future__ import annotations
from typing import TYPE_CHECKING

from exceptions import InvalidBookDataError

if TYPE_CHECKING:
    from books import Book


def print_menu() -> None:
    print("\n📚 Book Collection App")
    print("1. Add a book")
    print("2. List books")
    print("3. Mark book as read")
    print("4. Remove a book")
    print("5. Exit")


def get_user_choice() -> str:
    return input("Choose an option (1-5): ").strip()


def get_book_details() -> tuple[str, str, int]:
    title = input("Enter book title: ").strip()
    author = input("Enter author: ").strip()

    year_input = input("Enter publication year: ").strip()
    try:
        year = int(year_input)
    except ValueError:
        raise InvalidBookDataError(f"Invalid year: {year_input!r}")

    return title, author, year


# --- Book display helpers ---

def print_books(books: list[Book]) -> None:
    """Display books in a user-friendly format."""
    if not books:
        print("No books found.")
        return

    print("\nYour Book Collection:\n")
    for index, book in enumerate(books, start=1):
        status = "✓" if book.read else " "
        print(f"{index}. [{status}] {book.title} by {book.author} ({book.year})")
    print()


# --- Input prompts ---

def prompt_add_book() -> tuple[str, str, str]:
    """Prompt the user for new book details and return raw strings."""
    title = input("Title: ").strip()
    author = input("Author: ").strip()
    year_str = input("Year: ").strip()
    return title, author, year_str


def prompt_remove_title() -> str:
    """Prompt the user for the title of a book to remove."""
    return input("Enter the title of the book to remove: ").strip()


def prompt_search_query() -> str:
    """Prompt the user for a search query."""
    return input("Search by title or author: ").strip()


def prompt_find_author() -> str:
    """Prompt the user for an author name to look up."""
    return input("Author name: ").strip()
