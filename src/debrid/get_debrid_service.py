from fastapi.exceptions import HTTPException

from debrid.alldebrid import AllDebrid
from debrid.premiumize import Premiumize
from debrid.realdebrid import RealDebrid
from debrid.torbox import TorBox
from models.config import Config


def get_debrid_service(config: Config):
    service_name = config.service
    match service_name:
        case "realdebrid":
            debrid_service = RealDebrid(config)
        case "alldebrid":
            debrid_service = AllDebrid(config)
        case "premiumize":
            debrid_service = Premiumize(config)
        case "torbox":
            debrid_service = TorBox(config)
        case _:
            raise HTTPException(
                status_code=500, detail="Invalid service configuration."
            )

    return debrid_service
