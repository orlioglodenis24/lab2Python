import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.link import Link
from app.models.user import User

ROLE_LIMITS: dict[str, int] = {"user": 3, "premium": 5}


def is_link_active(link: Link) -> bool:
    """Return True if the link is currently active (not deleted, not expired, not over click limit)."""
    if link.deleted_at is not None:
        return False
    now = datetime.now(timezone.utc)
    if link.expires_at is not None and link.expires_at <= now:
        return False
    if link.max_clicks is not None and link.clicks >= link.max_clicks:
        return False
    return True


async def get_user_links(db: AsyncSession, user: User) -> list[Link]:
    """Return all links for a user (including expired/deleted) with computed is_active."""
    result = await db.execute(select(Link).where(Link.user_id == user.id))
    return list(result.scalars().all())


async def count_active_links(db: AsyncSession, user: User) -> int:
    """Count the number of active links for a user using DB-level filtering."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(func.count()).select_from(Link).where(
            Link.user_id == user.id,
            Link.deleted_at.is_(None),
            (Link.expires_at.is_(None)) | (Link.expires_at > now),
            (Link.max_clicks.is_(None)) | (Link.clicks < Link.max_clicks),
        )
    )
    return result.scalar_one()


async def get_active_link_by_url(db: AsyncSession, user: User, original_url: str) -> Link | None:
    """Return an existing active link for the same user+url, if any."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Link).where(
            Link.user_id == user.id,
            Link.original_url == original_url,
            Link.deleted_at.is_(None),
            (Link.expires_at.is_(None)) | (Link.expires_at > now),
            (Link.max_clicks.is_(None)) | (Link.clicks < Link.max_clicks),
        )
    )
    return result.scalar_one_or_none()


async def create_link(
    db: AsyncSession,
    user: User,
    original_url: str,
    expires_at: datetime | None = None,
    max_clicks: int | None = None,
) -> Link:
    link = Link(
        user_id=user.id,
        original_url=original_url,
        code=str(uuid.uuid4()),
        expires_at=expires_at,
        max_clicks=max_clicks,
        clicks=0,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


async def soft_delete_link(db: AsyncSession, link: Link) -> Link:
    link.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(link)
    return link


async def get_link_by_code(db: AsyncSession, code: str) -> Link | None:
    result = await db.execute(select(Link).where(Link.code == code))
    return result.scalar_one_or_none()


async def increment_clicks(db: AsyncSession, link: Link) -> None:
    await db.execute(
        update(Link).where(Link.id == link.id).values(clicks=Link.clicks + 1)
    )
    await db.commit()
