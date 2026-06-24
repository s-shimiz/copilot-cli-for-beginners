import sys
from books import Book, BookCollection
from exceptions import BookAppError, BookNotFoundError
from utils import (
    print_books,
    prompt_add_book,
    prompt_remove_title,
    prompt_search_query,
    prompt_find_author,
)


collection = BookCollection()


def handle_list() -> None:
    books = collection.list_books()
    print_books(books)


def handle_add() -> None:
    print("\nAdd a New Book\n")
    title, author, year_str = prompt_add_book()
    try:
        year = int(year_str) if year_str else 0
        collection.add_book(title, author, year)
        print("\nBook added successfully.\n")
    except (ValueError, BookAppError) as e:
        print(f"\nError: {e}\n")


def handle_remove() -> None:
    print("\nRemove a Book\n")
    title = prompt_remove_title()
    try:
        collection.remove_book(title)
        print("\nBook removed successfully.\n")
    except BookNotFoundError as e:
        print(f"\nError: {e}\n")


def handle_search() -> None:
    print("\nSearch Books\n")
    query = prompt_search_query()
    books = collection.search(query)
    print_books(books)


def handle_find() -> None:
    print("\nFind Books by Author\n")
    author = prompt_find_author()
    books = collection.find_by_author(author)
    print_books(books)


def show_help() -> None:
    print("\nBook Collection Helper\n\nCommands:")
    for name, (_, description) in COMMANDS.items():
        print(f"  {name:<8} - {description}")
    print()


COMMANDS: dict[str, tuple[callable, str]] = {
    "list":   (handle_list,   "Show all books"),
    "add":    (handle_add,    "Add a new book"),
    "remove": (handle_remove, "Remove a book by title"),
    "find":   (handle_find,   "Find books by author"),
    "search": (handle_search, "Search books by title or author"),
    "help":   (show_help,     "Show this help message"),
}


def main() -> None:
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()
    entry = COMMANDS.get(command)

    if entry:
        handler, _ = entry
        handler()
    else:
        print(f'Unknown command: "{command}".\n')
        show_help()


if __name__ == "__main__":
    main()
