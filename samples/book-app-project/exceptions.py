class BookAppError(Exception):
    """Base exception for all BookApp domain errors."""


class BookNotFoundError(BookAppError):
    """Raised when a book cannot be found by title."""


class DuplicateBookError(BookAppError):
    """Raised when a book with the same title already exists."""


class InvalidBookDataError(BookAppError):
    """Raised when book field values fail validation (e.g., empty title, invalid year)."""


class DataFileError(BookAppError):
    """Raised on data file read/write failures."""
