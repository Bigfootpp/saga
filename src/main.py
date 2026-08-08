import logging
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette import status
from starlette.responses import FileResponse

from debrid.get_debrid_service import get_debrid_service
from jackett.jackett_service import JackettService
from metdata.cinemeta import Cinemeta
from metdata.tmdb import TMDB
from models.manifest import ManifestResponse
from torrent.torrent_service import TorrentService
from torrent.torrent_smart_container import TorrentSmartContainer
from utils.filter_results import filter_items, sort_items
from utils.logger import setup_logger
from utils.parse_config import parse_config
from utils.stremio_parser import parse_to_stremio_streams
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
async def function(file_path: str):
    response = FileResponse(f"templates/{file_path}")
    return response


@app.get("/manifest.json")
@app.get("/{params}/manifest.json")
async def get_manifest():
    return ManifestResponse(
        id = ADDON_ID,
        icon = "https://i.imgur.com/tVjqEJP.png",
        name = "Jackett"
        + (" Community" if COMMUNITY_VERSION else "")
        + (" (Dev)" if isDev else ""),
        version = VERSION,
        description = "Elevate your Stremio experience with seamless access to Jackett torrent links, effortlessly "
        "fetching torrents for your selected movies within the Stremio interface.",
        resources = ["stream"],
        types = ["movie", "series"],
        catalogs=[],
    )


formatter = logging.Formatter(
    "[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s",
    "%m-%d %H:%M:%S",
)

logger.info("Started Jackett Addon")


@app.get("/{config}/stream/{stream_type}/{stream_id}")
async def get_results(config_b64: str, stream_type: str, stream_id: str, request: Request):
    jackett_service: JackettService | None = None
    start = time.time()
    stream_id = stream_id.replace(".json", "")

    config_obj = parse_config(config_b64)
    logger.info(f"{stream_type} request")

    if config_obj.metadata_provider == "tmdb" and config_obj.tmdb_api:
        metadata_provider = TMDB(config_obj)
        if not COMMUNITY_VERSION and config_obj.jackett:
            logger.info("Getting indexers' languages from Jackett for setting up TMDB")
            jackett_service = JackettService(config_obj)
            metadata_provider.indexers = jackett_service.get_indexers()
    else:
        metadata_provider = Cinemeta(config_obj)
    logger.info(f"Getting media from {config_obj.metadata_provider}")
    media = metadata_provider.get_metadata(stream_id, stream_type)
    if media is None:
        logger.error(f"Failed to get metadata for {stream_id} ({stream_type})")
        return {"streams": []}
    logger.info(f"Got media and properties: {media.titles}")

    debrid_service = get_debrid_service(config_obj)

    search_results = []

    if not COMMUNITY_VERSION and config_obj.jackett:
        logger.info("Searching for results on Jackett")
        jackett_service = jackett_service or JackettService(config_obj)
        jackett_search_results = jackett_service.search(media)
        logger.info(f"Got {len(jackett_search_results)} results from Jackett")

        logger.info("Filtering Jackett results")
        filtered_jackett_search_results = filter_items(
            jackett_search_results, media, config=config_obj
        )
        logger.info("Filtered Jackett results")

        search_results.extend(filtered_jackett_search_results)

    logger.debug(f"Converting result to TorrentItems (results: {len(search_results)})")
    torrent_service = TorrentService()
    torrent_results = torrent_service.convert_and_process(search_results, media)
    logger.debug(f"Converted result to TorrentItems (results: {len(torrent_results)})")

    torrent_smart_container = TorrentSmartContainer(torrent_results, media)

    if config_obj.debrid and config_obj.service in ["torbox", "premiumize"]:
        logger.debug("Checking availability")
        hashes = torrent_smart_container.get_hashes()
        ip = request.client.host if request.client else "127.0.0.1"
        result = debrid_service.get_availability_bulk(hashes, ip)
        torrent_smart_container.update_availability(result, type(debrid_service), media)
        logger.debug(f"Checked availability (results: {len(result.items())})")

    logger.debug("Getting best matching results")
    best_matching_results = torrent_smart_container.get_best_matching()
    best_matching_results = sort_items(best_matching_results, config_obj)
    logger.debug(f"Got best matching results (results: {len(best_matching_results)})")

    logger.info("Processing results")
    stream_list = parse_to_stremio_streams(best_matching_results, config_obj, media)
    logger.info(f"Processed results (results: {len(stream_list)})")

    logger.info(f"Total time: {time.time() - start}s")

    return {"streams": stream_list}


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
