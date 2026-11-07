from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services.links import get_link_by_code, increment_clicks, is_link_active

router = APIRouter(tags=["redirect"])


@router.get("/{code}")
async def redirect(code: str, db: AsyncSession = Depends(get_db)) -> Response:
    link = await get_link_by_code(db, code)

    if link is None or link.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found.")

    if not is_link_active(link):
        return Response(status_code=419, content="Link expired or click limit reached.")

    await increment_clicks(db, link)
    return RedirectResponse(url=link.original_url, status_code=status.HTTP_302_FOUND)
