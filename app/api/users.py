from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlmodel.ext.asyncio.session import AsyncSession

from app.storage.postgres import get_session
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    expires_in: float = 90 * 60  # длительность одной пары


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, session: AsyncSession = Depends(get_session)):
    user_service = UserService(session)
    token = await user_service.authenticate_user(
        email=data.email, password=data.password, expires_in=data.expires_in
    )
    return TokenResponse(access_token=token)
