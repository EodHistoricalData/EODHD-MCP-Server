import httpx
from .config import EODHD_API_KEY

async def make_request(url: str) -> dict | None:
    if "api_token=" not in url:
        url += f"&api_token={EODHD_API_KEY}" if "?" in url else f"?api_token={EODHD_API_KEY}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
