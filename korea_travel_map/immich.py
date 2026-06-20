import httpx


def _keyword(region_name: str) -> str:
    for suffix in ("특별자치시", "광역시", "특별시", "특별자치도", "시", "군", "구"):
        if region_name.endswith(suffix):
            return region_name[: -len(suffix)]
    return region_name


class ImmichClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {"x-api-key": api_key}

    async def search_by_region(self, region_name: str) -> list[dict]:
        keyword = _keyword(region_name)
        results: dict[str, dict] = {}

        async with httpx.AsyncClient(headers=self.headers, timeout=10) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/api/search/metadata",
                    json={"city": keyword, "size": 100, "page": 1},
                )
                if resp.status_code == 200:
                    for asset in resp.json().get("assets", {}).get("items", []):
                        results[asset["id"]] = {
                            "id": asset["id"],
                            "date": asset.get("localDateTime", ""),
                        }
            except Exception:
                pass

            try:
                resp = await client.get(f"{self.base_url}/api/albums")
                if resp.status_code == 200:
                    matching = [a for a in resp.json() if keyword in a.get("albumName", "")]
                    for album in matching:
                        detail = await client.get(f"{self.base_url}/api/albums/{album['id']}")
                        if detail.status_code == 200:
                            for asset in detail.json().get("assets", []):
                                results[asset["id"]] = {
                                    "id": asset["id"],
                                    "date": asset.get("localDateTime", ""),
                                }
            except Exception:
                pass

        return sorted(results.values(), key=lambda x: x["date"], reverse=True)[:100]

    async def get_thumbnail(self, asset_id: str) -> bytes:
        async with httpx.AsyncClient(headers=self.headers, timeout=10) as client:
            resp = await client.get(f"{self.base_url}/api/assets/{asset_id}/thumbnail")
            resp.raise_for_status()
            return resp.content
