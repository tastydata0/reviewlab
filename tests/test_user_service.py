import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status

# Import all models to ensure SQLAlchemy mappers are initialized correctly
from app.models.user import User, UserRole
from app.models.group import StudyGroup
from app.models.course import Course
from app.models.links import CourseUserLink
from app.models.task import Task
from app.models.task_group import TaskGroup
from app.services.user import UserService


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.get = AsyncMock()
    return session


@pytest.fixture
def user_service(mock_session):
    return UserService(mock_session)


def setup_mock_result(mock_session, return_value):
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = return_value
    mock_result.scalars.return_value.all.return_value = return_value if isinstance(return_value, list) else [return_value]
    mock_session.execute.return_value = mock_result
    return mock_result


@pytest.mark.asyncio
async def test_register_user_success(user_service, mock_session):
    # Setup
    email = "test@example.com"
    password = "SecurePassword123!"
    full_name = "Test User"
    
    setup_mock_result(mock_session, None)
    
    # Mock AuthService.get_password_hash
    with patch("app.services.user.AuthService.get_password_hash", return_value="hashed_pass"):
        user = await user_service.register_user(email, password, full_name)
        
        # Verify
        assert user.email == email
        assert user.full_name == full_name
        assert user.hashed_password == "hashed_pass"
        assert user.role == UserRole.student
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_register_user_already_exists(user_service, mock_session):
    # Setup
    email = "test@example.com"
    existing_user = User(email=email, hashed_password="...", full_name="...")
    setup_mock_result(mock_session, existing_user)
    
    # Verify exception
    with pytest.raises(HTTPException) as excinfo:
        await user_service.register_user(email, "SecurePassword123!", "Name")
    
    assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Email already registered" in excinfo.value.detail


@pytest.mark.asyncio
async def test_authenticate_user_success(user_service, mock_session):
    # Setup
    email = "test@example.com"
    password = "SecurePassword123!"
    user = User(id=uuid.uuid4(), email=email, hashed_password="hashed_password", full_name="Test", role=UserRole.student)
    
    setup_mock_result(mock_session, user)
    
    with patch("app.services.user.AuthService.verify_password", return_value=True), \
         patch("app.services.user.AuthService.create_access_token", return_value="fake_token"):
        
        token = await user_service.authenticate_user(email, password, 1.0)
        
        assert token == "fake_token"


@pytest.mark.asyncio
async def test_authenticate_user_invalid_credentials(user_service, mock_session):
    # Setup
    setup_mock_result(mock_session, None)
    
    with pytest.raises(HTTPException) as excinfo:
        await user_service.authenticate_user("wrong@email.com", "pass", 1.0)
    
    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_study_group_success(user_service, mock_session):
    # Setup
    name = "New Group"
    setup_mock_result(mock_session, None)
    
    group = await user_service.create_study_group(name)
    
    assert group.name == name
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_by_id_success(user_service, mock_session):
    # Setup
    user_id = uuid.uuid4()
    expected_user = User(id=user_id, email="test@test.com", hashed_password="...", full_name="...")
    mock_session.get.return_value = expected_user
    
    user = await user_service.get_user_by_id(user_id)
    
    assert user == expected_user
    mock_session.get.assert_called_with(User, user_id)


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(user_service, mock_session):
    mock_session.get.return_value = None
    
    with pytest.raises(HTTPException) as excinfo:
        await user_service.get_user_by_id(uuid.uuid4())
    
    assert excinfo.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_add_user_to_group_success(user_service, mock_session):
    # Setup
    user_id = uuid.uuid4()
    group_id = uuid.uuid4()
    user = User(id=user_id, email="test@test.com", hashed_password="...", full_name="...")
    group = StudyGroup(id=group_id, name="Test Group")
    
    mock_session.get.side_effect = [user, group]
    
    updated_user = await user_service.add_user_to_group(user_id, group_id)
    
    assert updated_user.group_id == group_id
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_promote_to_teacher_success(user_service, mock_session):
    # Setup
    user_id = uuid.uuid4()
    user = User(id=user_id, email="test@test.com", hashed_password="...", full_name="...", role=UserRole.student)
    mock_session.get.return_value = user
    
    updated_user = await user_service.promote_to_teacher(user_id)
    
    assert updated_user.role == UserRole.teacher
    mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_promote_admin_fails(user_service, mock_session):
    # Setup
    user_id = uuid.uuid4()
    user = User(id=user_id, email="test@test.com", hashed_password="...", full_name="...", role=UserRole.admin)
    mock_session.get.return_value = user
    
    with pytest.raises(HTTPException) as excinfo:
        await user_service.promote_to_teacher(user_id)
    
    assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
