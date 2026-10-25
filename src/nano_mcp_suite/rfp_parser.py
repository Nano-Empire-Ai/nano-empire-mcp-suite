"""MCP Tool: Deterministic RFP & Solicitation Compliance Shredder.

Exposes the live :8000 compliance extraction engine to Claude, Cursor, and foreign MCP swarms.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("nano-empire-rfp")
RFP_ENGINE_URL = os.environ.get("RFP_ENGINE_URL", "http://127.0.0.1:8000")


@mcp.tool()
def parse_enterprise_rfp(file_path: str, focus_area: str = "compliance") -> str:
    """
    Ingests an enterprise or government RFP/RFI document (.pdf) and deterministically
    extracts all compliance obligations, mandatory clauses (SHALL/MUST), categories,
    and verbatim page citations.
    """
    path = Path(file_path)
    if not path.exists():
        return json.dumps({
            "error": "FILE_NOT_FOUND",
            "file_path": file_path,
            "detail": f"File does not exist on disk: {file_path}",
        }, indent=2)

    try:
        file_bytes = path.read_bytes()
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(
                f"{RFP_ENGINE_URL}/api/analyze-rfp",
                files={"file": (path.name, file_bytes, "application/pdf")},
            )
            if resp.status_code == 200:
                data = resp.json()
                atoms = data.get("atoms", [])
                mandatory = [a for a in atoms if a.get("is_mandatory")]
                return json.dumps({
                    "status": "teardown_complete",
                    "document": path.name,
                    "page_count": data.get("page_count", 0),
                    "total_requirements": data.get("requirement_count", 0),
                    "mandatory_requirements": data.get("mandatory_count", 0),
                    "categories": data.get("categories", {}),
                    "first_cited_obligations": [
                        {
                            "id": a.get("atom_id"),
                            "page": a.get("source_page"),
                            "category": a.get("category"),
                            "clause": a.get("raw_text")[:140],
                        }
                        for a in mandatory[:5]
                    ],
                }, indent=2)
            else:
                return json.dumps({
                    "error": "ENGINE_ERROR",
                    "status_code": resp.status_code,
                    "detail": resp.text[:300],
                }, indent=2)
    except Exception as exc:
        return json.dumps({
            "error": "EXTRACTION_EXCEPTION",
            "detail": str(exc),
        }, indent=2)
