import os
import argparse
import textwrap

def generate_tollbooth_mcp(name: str, endpoint: str, price_usd: float, output_dir: str):
    """
    Procedurally generates a new FastMCP server wrapped in the x402 tollbooth middleware.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    server_code = textwrap.dedent(f'''\
        import os
        import httpx
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
        from mcp.server.fastmcp import FastMCP
        import uvicorn

        # Procedurally Generated MCP Tollbooth for {name}
        # Target API: {endpoint}
        # Price: ${price_usd} USDC

        app = FastAPI(title="{name} Tollbooth")
        mcp = FastMCP("{name}")

        @app.middleware("http")
        async def x402_middleware(request: Request, call_next):
            if request.url.path == "/messages" and request.method == "POST":
                receipt = request.headers.get("x-402-receipt")
                if not receipt:
                    return JSONResponse({{"error": "Payment Required", "payment_address": "5pM5w1W5nKU7B8SjuTiz65UAZxs9mCnC6ab1Xs1gSi3", "amount_usdc": {price_usd}}}, status_code=402)
                
                # Mock validation for generator - integrate real Solana validation here
                print(f"[Tollbooth] Validated payment {{receipt}} for {name}")
                
            response = await call_next(request)
            return response

        @mcp.tool()
        async def fetch_data(query: str) -> dict:
            """Fetch data from the underlying API."""
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{endpoint}?query={{query}}")
                resp.raise_for_status()
                return resp.json()

        app.mount("/sse", mcp.sse_app())

        if __name__ == "__main__":
            port = int(os.environ.get("PORT", 8080))
            uvicorn.run(app, host="0.0.0.0", port=port)
    ''')

    dockerfile_code = textwrap.dedent(f'''\
        FROM python:3.11-slim
        WORKDIR /app
        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt
        COPY . .
        CMD ["python", "server.py"]
    ''')

    reqs_code = textwrap.dedent('''\
        fastapi
        uvicorn
        mcp<2
        httpx
    ''')

    with open(os.path.join(output_dir, "server.py"), "w") as f:
        f.write(server_code)
    
    with open(os.path.join(output_dir, "Dockerfile"), "w") as f:
        f.write(dockerfile_code)
        
    with open(os.path.join(output_dir, "requirements.txt"), "w") as f:
        f.write(reqs_code)

    print(f"[+] Successfully generated x402 MCP server '{name}' at {output_dir}")
    print(f"[+] Ready for Cloud Run deployment.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a Tollbooth MCP Server")
    parser.add_argument("--name", required=True, help="Name of the MCP Server")
    parser.add_argument("--endpoint", required=True, help="Public API endpoint to wrap")
    parser.add_argument("--price", type=float, default=0.10, help="Price in USDC per call")
    parser.add_argument("--out", default="./generated_mcp", help="Output directory")
    
    args = parser.parse_args()
    generate_tollbooth_mcp(args.name, args.endpoint, args.price, args.out)
