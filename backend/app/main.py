import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.core.logging  # noqa: F401
from app.api.routes import analysis, locations, nisar, watches
from app.core.config import settings
from app.core.logging import log
from app.services.watch_service import check_all


async def _watch_loop():
    while True:
        await asyncio.sleep(settings.watch_interval_minutes * 60)
        try:
            await asyncio.to_thread(check_all)
        except Exception as e:  # never let the loop die
            log.warning("Watch loop error: %s", e)


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(_watch_loop()) if settings.watch_interval_minutes > 0 else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="Earth Pulse API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","),
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(locations.router)
app.include_router(nisar.router)
app.include_router(watches.router)
app.include_router(analysis.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": settings.earthpulse_mode, "watch_interval_minutes": settings.watch_interval_minutes,
            "analysis_modules": "hdf5 screening metrics"}
