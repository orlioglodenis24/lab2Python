from fastapi import FastAPI

from app.routers import auth, links, redirect

app = FastAPI(
    title="URL Shortener",
    description="A URL shortener API built with FastAPI, SQLAlchemy (async), and PostgreSQL.",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(links.router)
# Mount redirect router last (no prefix) so /{code} doesn't shadow other routes
app.include_router(redirect.router)
