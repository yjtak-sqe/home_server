import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db
from immich import ImmichClient

GEOJSON_PATH = Path(__file__).parent / "geojson" / "korea_sigun.geojson"
immich_client: ImmichClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    global immich_client
    db.init_db()
    immich_client = ImmichClient(
        os.environ["IMMICH_URL"],
        os.environ["IMMICH_API_KEY"],
    )
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/api/geojson")
def get_geojson():
    if not GEOJSON_PATH.exists():
        raise HTTPException(status_code=500, detail="GeoJSON not found")
    return Response(GEOJSON_PATH.read_text(), media_type="application/json")


@app.get("/api/regions")
def get_regions():
    return db.get_all_colors()


class ColorPayload(BaseModel):
    color: str


@app.put("/api/regions/{region_id}")
def set_region(region_id: str, payload: ColorPayload):
    db.set_color(region_id, payload.color)
    return {"ok": True}


@app.delete("/api/regions/{region_id}")
def delete_region(region_id: str):
    db.delete_color(region_id)
    return {"ok": True}


@app.get("/api/photos/{region_id}")
async def get_photos(region_id: str):
    return await immich_client.search_by_region(region_id)


@app.get("/api/thumbnails/{asset_id}")
async def get_thumbnail(asset_id: str):
    try:
        data = await immich_client.get_thumbnail(asset_id)
        return Response(data, media_type="image/jpeg")
    except Exception:
        raise HTTPException(status_code=502, detail="Immich thumbnail fetch failed")


app.mount("/", StaticFiles(directory=str(Path(__file__).parent / "static"), html=True))
