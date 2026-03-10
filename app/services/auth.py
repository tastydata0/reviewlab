import datetime as dt
from typing import Any, Dict, Optional
import jwt
import bcrypt
from app.settings import SETTINGS
from app.models.user import UserRole
from fastapi import HTTPException, status


class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            password_bytes = plain_password.encode("utf-8")
            hashed_bytes = hashed_password.encode("utf-8")
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception:
            return False

    @staticmethod
    def get_password_hash(password: str) -> str:
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        hashed_bytes = bcrypt.hashpw(password_bytes, salt)
        return hashed_bytes.decode("utf-8")

    @staticmethod
    def create_access_token(
        user_id: str, role: UserRole, expires_delta: Optional[dt.timedelta] = None
    ) -> str:
        to_encode = {"sub": str(user_id), "role": role.value}
        if expires_delta:
            expire = dt.datetime.now(dt.timezone.utc) + expires_delta
        else:
            expire = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
                minutes=SETTINGS.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            SETTINGS.SECRET_KEY.get_secret_value(),
            algorithm=SETTINGS.ALGORITHM,
        )
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                SETTINGS.SECRET_KEY.get_secret_value(),
                algorithms=[SETTINGS.ALGORITHM],
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def check_permission(token: str, allowed_roles: list[UserRole]) -> Dict[str, Any]:
        payload = AuthService.decode_token(token)
        role_str = payload.get("role")
        if not role_str or UserRole(role_str) not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to perform this action",
            )
        return payload
