import httpx


def _point_in_polygon(lon: float, lat: float, polygon: list) -> bool:
    """Ray casting algorithm for point-in-polygon."""
    inside = False
    coords = polygon[0]  # exterior ring
    n = len(coords)
    j = n - 1
    for i in range(n):
        xi, yi = coords[i][0], coords[i][1]
        xj, yj = coords[j][0], coords[j][1]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _contains(geometry: dict, lon: float, lat: float) -> bool:
    if geometry["type"] == "Polygon":
        return _point_in_polygon(lon, lat, geometry["coordinates"])
    elif geometry["type"] == "MultiPolygon":
        return any(_point_in_polygon(lon, lat, poly) for poly in geometry["coordinates"])
    return False


class ImmichClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {"x-api-key": api_key}
        self._markers_cache: list[dict] | None = None

    async def _get_markers(self, client: httpx.AsyncClient) -> list[dict]:
        if self._markers_cache is None:
            resp = await client.get(f"{self.base_url}/api/map/markers", timeout=30)
            resp.raise_for_status()
            self._markers_cache = resp.json()
        return self._markers_cache

    async def search_by_region(self, region_name: str, geometry: dict) -> list[dict]:
        async with httpx.AsyncClient(headers=self.headers, timeout=30) as client:
            markers = await self._get_markers(client)

        results = [
            {"id": m["id"], "date": ""}
            for m in markers
            if _contains(geometry, m["lon"], m["lat"])
        ]
        return results

    async def get_thumbnail(self, asset_id: str) -> bytes:
        async with httpx.AsyncClient(headers=self.headers, timeout=10) as client:
            resp = await client.get(f"{self.base_url}/api/assets/{asset_id}/thumbnail")
            resp.raise_for_status()
            return resp.content
