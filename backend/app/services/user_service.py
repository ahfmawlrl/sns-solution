"""User business logic."""
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.user_client_assignment import RoleInClient, UserClientAssignment
from app.schemas.user import UserCreate, UserFilter
from app.services.auth_service import hash_password


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        role=data.role,
    )
    db.add(user)
    await db.flush()

    # Assign client associations if provided
    if data.client_ids:
        role_map = {
            UserRole.MANAGER: RoleInClient.MANAGER,
            UserRole.OPERATOR: RoleInClient.OPERATOR,
            UserRole.CLIENT: RoleInClient.VIEWER,
        }
        role_in_client = role_map.get(data.role, RoleInClient.VIEWER)
        for client_id in data.client_ids:
            assignment = UserClientAssignment(
                user_id=user.id,
                client_id=client_id,
                role_in_client=role_in_client,
            )
            db.add(assignment)

    return user


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def list_users(
    db: AsyncSession, filters: UserFilter
) -> tuple[list[User], int]:
    query = select(User)

    if filters.role is not None:
        query = query.where(User.role == filters.role)
    if filters.is_active is not None:
        query = query.where(User.is_active == filters.is_active)
    if filters.search:
        search = f"%{filters.search}%"
        query = query.where(or_(User.name.ilike(search), User.email.ilike(search)))

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    offset = (filters.page - 1) * filters.per_page
    query = query.order_by(User.created_at.desc()).offset(offset).limit(filters.per_page)
    result = await db.execute(query)
    users = list(result.scalars().all())

    return users, total


async def update_user(db: AsyncSession, user: User, **kwargs) -> User:
    for key, value in kwargs.items():
        if value is not None:
            setattr(user, key, value)
    return user


async def change_password(db: AsyncSession, user: User, new_password: str) -> User:
    user.password_hash = hash_password(new_password)
    return user
