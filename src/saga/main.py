from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from saga.api.configure import router as configure_router
from saga.api.manifest import router as manifest_router
from saga.api.static import router as static_router
from saga.api.stream import router as stream_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(manifest_router)
app.include_router(static_router)
app.include_router(configure_router)
app.include_router(stream_router)
