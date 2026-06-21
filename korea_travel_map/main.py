import json
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
geojson_index: dict[str, dict] = {}  # region_name -> geometry


@asynccontextmanager
async def lifespan(app: FastAPI):
    global immich_client, geojson_index
    db.init_db()
    immich_client = ImmichClient(
        os.environ["IMMICH_URL"],
        os.environ["IMMICH_API_KEY"],
    )
    if GEOJSON_PATH.exists():
        data = json.loads(GEOJSON_PATH.read_text())
        geojson_index = {
            f["properties"]["name"]: f["geometry"]
            for f in data["features"]
        }
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


REGION_LIMITS: dict[str, int] = {
    "대구광역시": 1000,
}

@app.get("/api/photos/{region_id}")
async def get_photos(region_id: str):
    geometry = geojson_index.get(region_id)
    if not geometry:
        raise HTTPException(status_code=404, detail="Region not found")
    results = await immich_client.search_by_region(region_id, geometry)
    limit = REGION_LIMITS.get(region_id)
    if limit:
        results = results[:limit]
    return results


@app.get("/api/thumbnails/{asset_id}")
async def get_thumbnail(asset_id: str):
    try:
        data = await immich_client.get_thumbnail(asset_id)
        return Response(data, media_type="image/jpeg")
    except Exception:
        raise HTTPException(status_code=502, detail="Immich thumbnail fetch failed")


app.mount("/", StaticFiles(directory=str(Path(__file__).parent / "static"), html=True))
