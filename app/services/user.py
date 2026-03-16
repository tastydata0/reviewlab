import uuid
import datetime as dt
from typing import Optional, List
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from fastapi import HTTPException, status
from pydantic import EmailStr

from app.models.user import User, UserRole
from app.models.group import StudyGroup
from app.services.auth import AuthService


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_user(
        self, email: EmailStr, password: str, full_name: str
    ) -> User:
        statement = select(User).where(User.email == email)
        result = await self.session.execute(statement)
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        hashed_password = AuthService.get_password_hash(password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=UserRole.student,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def authenticate_user(
        self, email: str, password: str, expires_in: float
    ) -> str:
        statement = select(User).where(User.email == email)
        result = await self.session.execute(statement)
        user = result.scalars().first()

        if not user or not AuthService.verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return AuthService.create_access_token(
            user_id=str(user.id), role=user.role, expires_delta=dt.timedelta(expires_in)
        )

    async def create_study_group(self, name: str) -> StudyGroup:
        statement = select(StudyGroup).where(StudyGroup.name == name)
        result = await self.session.execute(statement)
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Study group with this name already exists",
            )

        group = StudyGroup(name=name)
        self.session.add(group)
        await self.session.commit()
        await self.session.refresh(group)
        return group

    async def get_all_study_groups(self) -> List[StudyGroup]:
        statement = select(StudyGroup)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_study_group(self, group_id: uuid.UUID) -> StudyGroup:
        group = await self.session.get(StudyGroup, group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Group not found"
            )
        return group

    async def get_group_users(self, group_id: uuid.UUID) -> List[User]:
        statement = select(User).where(User.group_id == group_id)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_user_by_id(self, user_id: uuid.UUID) -> User:
        user = await self.session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user

    async def get_user_by_email(self, email: str) -> User:
        statement = select(User).where(User.email == email)
        result = await self.session.execute(statement)
        user = result.scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user

    async def add_user_to_group(self, user_id: uuid.UUID, group_id: uuid.UUID) -> User:
        user = await self.get_user_by_id(user_id)
        group = await self.get_study_group(group_id)

        user.group_id = group.id
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def remove_user_from_group(self, user_id: uuid.UUID) -> User:
        user = await self.get_user_by_id(user_id)
        user.group_id = None
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_user(
        self,
        user_id: uuid.UUID,
        full_name: Optional[str] = None,
        email: Optional[EmailStr] = None,
    ) -> User:
        user = await self.get_user_by_id(user_id)

        if email and email != user.email:
            statement = select(User).where(User.email == email)
            result = await self.session.execute(statement)
            if result.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered by another user",
                )
            user.email = email

        if full_name:
            user.full_name = full_name

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_group(self, group_id: uuid.UUID, name: str) -> StudyGroup:
        group = await self.get_study_group(group_id)

        if name != group.name:
            statement = select(StudyGroup).where(StudyGroup.name == name)
            result = await self.session.execute(statement)
            if result.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Group with this name already exists",
                )
            group.name = name

        self.session.add(group)
        await self.session.commit()
        await self.session.refresh(group)
        return group

    async def promote_to_teacher(self, user_id: uuid.UUID) -> User:
        user = await self.get_user_by_id(user_id)
        if user.role == UserRole.admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot promote an admin to a teacher",
            )

        user.role = UserRole.teacher
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
