"""
core/exceptions.py — Shared domain exceptions.
"""
from rest_framework.exceptions import APIException
from rest_framework import status


class NotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "not_found"

    def __init__(self, detail: str = "Not found.") -> None:
        super().__init__(detail=detail)


class PermissionDenied(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "permission_denied"

    def __init__(self, detail: str = "You do not have permission to perform this action.") -> None:
        super().__init__(detail=detail)


class ValidationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "validation_error"

    def __init__(self, detail: str) -> None:
        super().__init__(detail=detail)


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"

    def __init__(self, detail: str) -> None:
        super().__init__(detail=detail)
