import uuid
from typing import Any
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.models.user import UserRole
from app.services.auth import AuthService

security = HTTPBearer()


async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    token = credentials.credentials
    return AuthService.decode_token(token)


async def get_current_user_id(
    payload: dict[str, Any] = Depends(get_current_user_payload),
) -> uuid.UUID:
    return uuid.UUID(payload["sub"])


async def get_current_user_role(
    payload: dict[str, Any] = Depends(get_current_user_payload),
) -> UserRole:
    return UserRole(payload["role"])


class RequireRoles:
    """
    @router.get("/admin-only", dependencies=[Depends(RequireRoles([UserRole.admin]))])
    """

    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(
        self, credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> dict[str, Any]:
        token = credentials.credentials
        payload = AuthService.check_permission(token, self.allowed_roles)
        return payload
