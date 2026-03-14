"""Shared API dependencies."""

from fastapi import Header, HTTPException, Request, status


def get_api_container(request: Request):
    """Return the app container from request state."""

    return request.app.state.container


def require_ui_admin_token(
    request: Request,
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> None:
    """Protect UI management endpoints with a shared admin token."""

    configured_token = request.app.state.container.settings.ui_admin_token
    if not configured_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="UI admin token is not configured.",
        )
    if x_admin_token != configured_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin token.",
        )
