from fastapi import APIRouter

from app.api.routes import albums, auth, collections, flac_import, musicians, musicbrainz, persons, roon_import

router = APIRouter()

router.include_router(auth.router)
router.include_router(collections.router)
router.include_router(albums.router)
router.include_router(musicians.router)
router.include_router(musicbrainz.router)
router.include_router(persons.router)
router.include_router(roon_import.router)
router.include_router(flac_import.router)
