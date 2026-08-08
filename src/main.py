import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette import status
from starlette.responses import FileResponse

from debrid.get_debrid_service import get_debrid_service
from models.manifest import ManifestResponse
from pipeline.stream_pipeline import StreamPipeline
from utils.logger import setup_logger
from utils.parse_config import parse_config
from utils.string_encoding import decodeb64

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
root_path = os.environ.get("ROOT_PATH") or ""
if root_path and not root_path.startswith("/"):
    root_path = f"/{root_path}"
app = FastAPI(root_path=root_path)

VERSION = "4.2.7"
isDev = os.getenv("NODE_ENV") == "development"
COMMUNITY_VERSION = os.getenv("IS_COMMUNITY_VERSION") == "true"
SPONSOR_MESSAGE = os.getenv("SPONSOR_MESSAGE")
ADDON_ID = os.getenv("ADDON_ID", "community.aymene69.jackett")


class LogFilterMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        request = Request(scope, receive)
        path = request.url.path
        sensible_path = re.sub(r"/ey.*?/", "/<SENSITIVE_DATA>/", path)
        logger.info(f"{request.method} - {sensible_path}")
        return await self.app(scope, receive, send)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not isDev:
    app.add_middleware(LogFilterMiddleware)

templates = Jinja2Templates(directory="templates")

logger = setup_logger(__name__)


def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if len(logger.handlers) > 0:
        return logger

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s",
        "%m-%d %H:%M:%S",
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


@app.get("/")
async def root():
    return RedirectResponse(url="/configure")


@app.get("/configure")
@app.get("/{config}/configure")
async def configure(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "isCommunityVersion": COMMUNITY_VERSION,
            "sponsorMessage": SPONSOR_MESSAGE,
            "version": VERSION,
        },
    )


@app.get("/static/{file_path:path}")
async def static_files(file_path: str):
    response = FileResponse(f"templates/{file_path}")
    return response


@app.get("/manifest.json")
@app.get("/{params}/manifest.json")
async def get_manifest():
    return ManifestResponse(
        id=ADDON_ID,
        icon="https://i.imgur.com/tVjqEJP.png",
        name="Jackett"
        + (" Community" if COMMUNITY_VERSION else "")
        + (" (Dev)" if isDev else ""),
        version=VERSION,
        description="Elevate your Stremio experience with seamless access to Jackett torrent links, effortlessly "
        "fetching torrents for your selected movies within the Stremio interface.",
        resources=["stream"],
        types=["movie", "series"],
        catalogs=[],
    )


logger.info("Started Jackett Addon")


@app.get("/{config}/stream/{stream_type}/{stream_id}")
async def get_results(config: str, stream_type: str, stream_id: str, request: Request):
    pipeline = StreamPipeline.from_request(request, config, COMMUNITY_VERSION)
    return pipeline.build_streams(stream_type, stream_id)


@app.get("/playback/{config}/{query}")
@app.head("/playback/{config}/{query}")
async def get_playback(config: str, query: str, request: Request):
    try:
        if not query:
            raise HTTPException(status_code=400, detail="Query required.")
        config_obj = parse_config(config)
        logger.info("Decoding query")
        query = decodeb64(query)
        logger.info(query)
        logger.info("Decoded query")
        ip = request.client.host if request.client else "127.0.0.1"
        debrid_service = get_debrid_service(config_obj)
        link = debrid_service.get_stream_link(query, ip)

        logger.info(f"Got link: {link}")
        return RedirectResponse(url=link, status_code=status.HTTP_301_MOVED_PERMANENTLY)

    except (ValueError, KeyError, RuntimeError) as e:
        logger.error(f"An error occurred: {e}")
        raise HTTPException(
            status_code=500, detail="An error occurred while processing the request."
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7000)
