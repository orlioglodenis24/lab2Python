from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.link import LinkCreate, LinkOut
from app.services.links import (
    ROLE_LIMITS,
    count_active_links,
    create_link,
    get_active_link_by_url,
    get_user_links,
    is_link_active,
    soft_delete_link,
)
from sqlalchemy import select
from app.models.link import Link

router = APIRouter(prefix="/links", tags=["links"])


def _link_to_out(link: Link) -> LinkOut:
    return LinkOut(
        id=link.id,
        user_id=link.user_id,
        original_url=link.original_url,
        code=link.code,
        expires_at=link.expires_at,
        clicks=link.clicks,
        max_clicks=link.max_clicks,
        deleted_at=link.deleted_at,
        created_at=link.created_at,
        is_active=is_link_active(link),
    )


@router.get("", response_model=list[LinkOut])
async def list_links(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LinkOut]:
    links = await get_user_links(db, current_user)
    return [_link_to_out(link) for link in links]


@router.post("", response_model=LinkOut, status_code=status.HTTP_201_CREATED)
async def create_short_link(
    link_in: LinkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LinkOut:
    original_url = str(link_in.original_url)

    # Return existing active link if same URL already exists for this user
    existing = await get_active_link_by_url(db, current_user, original_url)
    if existing is not None:
        return _link_to_out(existing)

    # Enforce role-based limit
    limit = ROLE_LIMITS.get(current_user.role, 3)
    active_count = await count_active_links(db, current_user)
    if active_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Active link limit reached ({limit}) for role '{current_user.role}'.",
        )

    link = await create_link(
        db,
        user=current_user,
        original_url=original_url,
        expires_at=link_in.expires_at,
        max_clicks=link_in.max_clicks,
    )
    return _link_to_out(link)


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    link_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Link).where(Link.id == link_id))
    link = result.scalar_one_or_none()

    if link is None or link.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found.")

    if link.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your link.")

    await soft_delete_link(db, link)
