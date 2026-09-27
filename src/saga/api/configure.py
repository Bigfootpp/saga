from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from starlette.responses import FileResponse

router = APIRouter()


@router.get("/configure")
@router.get("/{config}/configure")
async def configure() -> FileResponse:
    return FileResponse("src/saga/static/index.html")


@router.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse("/configure")
