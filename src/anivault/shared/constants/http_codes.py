"""HTTP Status Code Constants.

This module contains HTTP status code constants for clear and
type-safe handling of API responses and network operations.
"""


class HTTPStatusCodes:
    """HTTP status code constants."""

    # 2xx Success
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204

    # 3xx Redirection
    MOVED_PERMANENTLY = 301
    FOUND = 302
    NOT_MODIFIED = 304

    # 4xx Client Errors
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    PAYMENT_REQUIRED = 402
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    NOT_ACCEPTABLE = 406
    REQUEST_TIMEOUT = 408
    CONFLICT = 409
    GONE = 410
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429

    # 5xx Server Errors
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504

    # Status code ranges
    @staticmethod
    def is_success(code: int) -> bool:
        """Check if status code indicates success (2xx)."""
        return 200 <= code < 300

    @staticmethod
    def is_client_error(code: int) -> bool:
        """Check if status code indicates client error (4xx)."""
        return 400 <= code < 500

    @staticmethod
    def is_server_error(code: int) -> bool:
        """Check if status code indicates server error (5xx)."""
        return 500 <= code < 600

    @staticmethod
    def is_error(code: int) -> bool:
        """Check if status code indicates any error (4xx or 5xx)."""
        return code >= 400


class HTTPHeaders:
    """Common HTTP header names."""

    CONTENT_TYPE = "Content-Type"
    ACCEPT = "Accept"
    AUTHORIZATION = "Authorization"
    USER_AGENT = "User-Agent"
    RETRY_AFTER = "Retry-After"
    CACHE_CONTROL = "Cache-Control"
    ETAG = "ETag"
    IF_NONE_MATCH = "If-None-Match"


class ContentTypes:
    """Common content type values."""

    JSON = "application/json"
    XML = "application/xml"
    HTML = "text/html"
    PLAIN_TEXT = "text/plain"
    FORM_URLENCODED = "application/x-www-form-urlencoded"
    MULTIPART_FORM = "multipart/form-data"
