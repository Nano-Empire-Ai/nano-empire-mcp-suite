# Nano Empire MCP Suite (`nano-empire-mcp-suite`)

Model Context Protocol (MCP) server suite and verification harness for deterministic RFP/SOW compliance extraction, MCP tool readiness auditing, and `x402` Base USDC gateway routing.

![MCP Standard: 2024-11-05](https://img.shields.io/badge/MCP-2024--11--05-10b981)
![Mode: Local Stdio + x402 Gateway](https://img.shields.io/badge/mode-stdio_%2B_x402_Base_USDC-3b82f6)
![Base Mainnet Settlement: Block 51961194](https://img.shields.io/badge/Base_Mainnet-1_self--test_settled-6366f1)
![Outside Paying Customers: 0](https://img.shields.io/badge/outside_paying_customers-0-f59e0b)
![License: MIT](https://img.shields.io/badge/license-MIT-64748b)

---

## 1. Install & Run Today

```bash
git clone https://github.com/Nano-Empire-Ai/nano-empire-mcp-suite.git
cd nano-empire-mcp-suite
pip install -e .
pytest -v
```

### Add to Claude Desktop / Cursor (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "nano-empire-suite": {
      "command": "python",
      "args": ["-m", "src.run_server"]
    }
  }
}
```

---

## 2. Machine-Readable Discovery Links

- **Canonical LLM Index (`llms.txt`):** [`https://www.nanoempireai.com/llms.txt`](https://www.nanoempireai.com/llms.txt)
- **Live MCP Discovery Manifest:** [`https://www.nanoempireai.com/.well-known/mcp.json`](https://www.nanoempireai.com/.well-known/mcp.json)
- **A2A Agent Card (`v1.5.0`):** [`https://www.nanoempireai.com/.well-known/agent-card.json`](https://www.nanoempireai.com/.well-known/agent-card.json)
- **Poppy / PAP Manifest (`PAP/1.0`):** [`https://www.nanoempireai.com/.well-known/poppy.json`](https://www.nanoempireai.com/.well-known/poppy.json)
- **Commercial Offers (`offers.json`):** [`https://www.nanoempireai.com/offers.json`](https://www.nanoempireai.com/offers.json)

---

## 3. Exposed MCP Capabilities & Pricing

| Capability | Description | Pricing / Rail | Status |
|------------|-------------|----------------|--------|
| **`rfp_parser` / `BidShield`** | Deterministic extraction of binding RFP/SOW requirements (`shall`, `must`, `required`) and missing annexes | Open-source local / **$99** Urgent Triage via Stripe | **LIVE** |
| **`auditor` (`SkillProof`)** | Static & runtime audit of MCP tool schemas for silent coercion, unbounded pagination, and secret leakage | **$99** (3-Tool Pilot) / **$500** Full Battery via Stripe | **LIVE** |
| **`x402_gateway`** | HTTP 402 payment challenge and verification middleware for Base USDC (`eip155:8453`) | **$0.05 – $0.10 USDC** per call on Base Mainnet | **LIVE** |

---

## 4. Settlement Proof & Honest Volume Ledger

- **On-Chain Settlement Proof (Base Mainnet Block `51961194`):**
  - [`0x0581b819b2e5b481cbbcfb8fe81e6fe57a0d0ef9c6f8fc04952164761586da64`](https://basescan.org/tx/0x0581b819b2e5b481cbbcfb8fe81e6fe57a0d0ef9c6f8fc04952164761586da64) (`0.05 USDC` settled to `0x90E23A7b6F6494A879d05DDC4278D0e55Dec1e01`).
- **Volume Disclosure:** `1` verified self-test settlement on Base Mainnet; `0` outside paying customers to date.

---

## 5. License & Contact

- **License:** MIT
- **Contact:** Robert Lambert (`rob@nanoempireai.com`) · [`https://www.nanoempireai.com`](https://www.nanoempireai.com)
