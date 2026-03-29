import uuid
from typing import Any, Dict, List
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.models.user import UserRole
from app.services.auth import AuthService

security = HTTPBearer()


async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    token = credentials.credentials
    return AuthService.decode_token(token)


async def get_current_user_id(
    payload: Dict[str, Any] = Depends(get_current_user_payload),
) -> uuid.UUID:
    return uuid.UUID(payload["sub"])


class RequireRoles:
    """
    @router.get("/admin-only", dependencies=[Depends(RequireRoles([UserRole.admin]))])
    """

    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(
        self, credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> Dict[str, Any]:
        token = credentials.credentials
        payload = AuthService.check_permission(token, self.allowed_roles)
        return payload
