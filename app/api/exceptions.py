"""Custom exception classes for the application."""

class APIError(Exception):
    """Custom exception for API-related errors."""
    def __init__(self, message, status_code=None, details=None, payload=None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details
        self.payload = payload

    def __str__(self):
        return f"APIError: {self.args[0]} (Status: {self.status_code})"
