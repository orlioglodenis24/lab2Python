from datetime import datetime

from pydantic import BaseModel, HttpUrl


class LinkCreate(BaseModel):
    original_url: HttpUrl
    expires_at: datetime | None = None
    max_clicks: int | None = None


class LinkOut(BaseModel):
    id: int
    user_id: int
    original_url: str
    code: str
    expires_at: datetime | None
    clicks: int
    max_clicks: int | None
    deleted_at: datetime | None
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}
