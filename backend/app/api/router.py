from fastapi import APIRouter

from app.api.routes import auth, collections, albums, musicians

router = APIRouter()

router.include_router(auth.router)
router.include_router(collections.router)
router.include_router(albums.router)
router.include_router(musicians.router)
