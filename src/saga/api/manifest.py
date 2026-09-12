from fastapi import APIRouter

from saga.models.manifest import ManifestResponse

router = APIRouter()


@router.get("/manifest.json")
@router.get("/{config}/manifest.json")
async def get_manifest() -> ManifestResponse:
    return ManifestResponse(
        id="community.bigfootpp.saga",
        icon="",  # "https://i.imgur.com/tVjqEJP.png",
        name="Saga",
        version="0.1.0",
        description="Elevate your Stremio experience with seamless access to Jackett torrent links, effortlessly "
        "fetching torrents for your selected movies within the Stremio interface.",
        resources=["stream"],
        types=["movie", "series"],
        catalogs=[],
    )
