from fastapi import APIRouter
from starlette.responses import FileResponse

router = APIRouter()


@router.get("/static/{file_path:path}")
async def get_manifest(file_path: str) -> FileResponse:
    return FileResponse(f"scr/saga/static/{file_path}")
