"""Reusable HTTP exception helpers.

Thin wrappers around ``fastapi.HTTPException`` that improve readability at
call sites without changing any status code or detail message currently
used by the application.
"""
from fastapi import HTTPException


def not_found(detail: str = "Not Found") -> HTTPException:
    return HTTPException(status_code=404, detail=detail)


def forbidden(detail: str = "Forbidden") -> HTTPException:
    return HTTPException(status_code=403, detail=detail)


def unauthorized(detail: str = "Unauthorized") -> HTTPException:
    return HTTPException(status_code=401, detail=detail)


def bad_request(detail: str = "Bad Request") -> HTTPException:
    return HTTPException(status_code=400, detail=detail)
