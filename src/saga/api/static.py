from fastapi import APIRouter
from starlette.responses import FileResponse

router = APIRouter()


@router.get("/static/{file_path:path}")
async def get_static(file_path: str) -> FileResponse:
    return FileResponse(f"src/saga/static/{file_path}")
