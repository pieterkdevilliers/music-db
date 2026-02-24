from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import router
from app.services.musicbrainz import ALBUM_ART_DIR
import app.models  # noqa: F401 — ensures all models are registered with Base

ALBUM_ART_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Music DB API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3003"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.mount("/static", StaticFiles(directory=str(ALBUM_ART_DIR)), name="static")


@app.get("/")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
