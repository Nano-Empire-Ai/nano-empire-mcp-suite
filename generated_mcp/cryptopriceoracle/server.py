import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
import uvicorn

# Procedurally Generated MCP Tollbooth for CryptoPriceOracle
# Target API: https://api.coingecko.com/api/v3/simple/price
# Price: $0.01 USDC

app = FastAPI(title="CryptoPriceOracle Tollbooth")
mcp = FastMCP("CryptoPriceOracle")

@app.middleware("http")
async def x402_middleware(request: Request, call_next):
    if request.url.path == "/messages" and request.method == "POST":
        receipt = request.headers.get("x-402-receipt")
        if not receipt:
            return JSONResponse({"error": "Payment Required", "payment_address": "5pM5w1W5nKU7B8SjuTiz65UAZxs9mCnC6ab1Xs1gSi3", "amount_usdc": 0.01}, status_code=402)

        # Mock validation for generator - integrate real Solana validation here
        print(f"[Tollbooth] Validated payment {receipt} for CryptoPriceOracle")

    response = await call_next(request)
    return response

@mcp.tool()
async def fetch_data(query: str) -> dict:
    """Fetch data from the underlying API."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://api.coingecko.com/api/v3/simple/price?query={query}")
        resp.raise_for_status()
        return resp.json()

app.mount("/sse", mcp.sse_app())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
