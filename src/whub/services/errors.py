"""Domain errors raised by whub services."""


class ServiceError(Exception):
    """Base error for invalid service operations."""


class NotFoundError(ServiceError):
    """Raised when a requested domain object does not exist."""
