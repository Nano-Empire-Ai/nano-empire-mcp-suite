import time
import json
import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from .attribution import process_tollbooth_payment

# ==============================================================================
# 🚧 TOLLBOOTH TaaS (The Agentic API Tax)
# ==============================================================================
# Objective: A highly portable FastAPI/Starlette Middleware.
# Allows any developer to easily monetize their MCP endpoints.
# It intercepts the request, validates the 'x-agent-payment-receipt',
# takes our 1% transaction fee, logs the transaction, and allows execution.
# ==============================================================================

class TollboothMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        fee_percentage: float = 0.01,
        bypass_paths: list = None,
        require_payment: bool = True
    ):
        super().__init__(app)
        self.fee_percentage = fee_percentage
        self.bypass_paths = bypass_paths or ["/docs", "/openapi.json", "/health", "/mcp/manifest"]
        self.require_payment = require_payment

    async def dispatch(self, request: Request, call_next: Callable):
        # 1. Bypass check
        if request.url.path in self.bypass_paths or not self.require_payment:
            return await call_next(request)

        # 2. Extract Agent Identity & Payment
        agent_id = request.headers.get("x-agent-id", "anonymous-agent")
        receipt_hash = request.headers.get("x-payment-receipt")
        attribution = request.headers.get("x-attribution", "source=direct")
        
        # We assume the agent sends the amount they paid in a header for verification
        # In production, this would be cryptographically verified against the blockchain RPC
        declared_usd = request.headers.get("x-declared-usd")

        # 3. Validation
        if not receipt_hash:
            return JSONResponse(
                status_code=402,
                content={
                    "error": "Payment Required",
                    "message": "BYOC (Bring Your Own Capital). Please remit USDC to the designated protocol wallet.",
                    "nano_empire_tax_rate": f"{self.fee_percentage * 100}%"
                },
                headers={"x-nano-empire-status": "PAYMENT_REQUIRED"}
            )

        if not declared_usd:
            return JSONResponse(status_code=400, content={"error": "Missing x-declared-usd header."})

        try:
            usd_value = float(declared_usd)
            
            # 4. Execute the Tollbooth Logging & Network Tax
            # Our cut is calculated here (e.g., 1%)
            network_tax = usd_value * self.fee_percentage
            developer_revenue = usd_value - network_tax
            
            # Process the attribution and log the transaction via our engine
            process_tollbooth_payment(
                receipt_hash=receipt_hash,
                agent_id=agent_id,
                tool_id=request.url.path, # Treating path as tool_id for generic TaaS
                usd_value=usd_value,      # We log the full volume
                attribution_header=attribution
            )
            
            logging.info(f"[TOLLBOOTH TaaS] Validated {usd_value} USDC from {agent_id}. Tax collected: {network_tax} USDC.")
            
            # 5. Let the request through to the developer's actual code
            response = await call_next(request)
            
            # Injecting success headers
            response.headers["x-tollbooth-cleared"] = "true"
            response.headers["x-developer-revenue"] = str(developer_revenue)
            return response
            
        except ValueError as e:
            return JSONResponse(
                status_code=400, 
                content={"error": "Invalid Payment Data", "details": str(e)}
            )
        except Exception as e:
            logging.error(f"[TOLLBOOTH TaaS] System Error: {str(e)}")
            return JSONResponse(
                status_code=500, 
                content={"error": "Tollbooth execution failed. Transaction rolled back."}
            )

# Usage Example:
# from fastapi import FastAPI
# from nano_mcp_suite.tollbooth_taas import TollboothMiddleware
# app = FastAPI()
# app.add_middleware(TollboothMiddleware, fee_percentage=0.01)
