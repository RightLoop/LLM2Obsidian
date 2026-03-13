"""Shared API dependencies."""

from fastapi import Request


def get_api_container(request: Request):
    """Return the app container from request state."""

    return request.app.state.container
