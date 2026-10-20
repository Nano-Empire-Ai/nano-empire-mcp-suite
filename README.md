# Nano Empire MCP Suite

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Model Context Protocol](https://img.shields.io/badge/MCP-Standard%20Ready-green.svg)](https://modelcontextprotocol.io)
[![Ed25519 Signed](https://img.shields.io/badge/Attestation-Ed25519-purple.svg)](https://nanoempireai.com)

Enterprise-grade Model Context Protocol (MCP) toolchain for deterministic government/enterprise RFP compliance extraction, security audits, and agent-to-agent (A2A) clearinghouse routing.

---

## 🛠️ MCP Tools Exposed

1. **`rfp_teardown`**: Deterministically analyzes complex government RFPs, grants, and Statements of Work (PDF/DOCX). Extracts verbatim binding obligations (`shall`, `must`, `required`), flags negative carve-outs, categorizes obligations (Technical, Security, Financial, Administrative), and outputs a page-cited compliance matrix in <4 seconds.
2. **`codebase_auditor`**: Scans repositories, MCP wrappers, and local binaries for credential leakage, prompt-injection attack surfaces, and compliance readiness.
3. **`a2a_router`**: Decentralized task routing and settlement broker connecting AI agents via x402 Base USDC and cryptographic Ed25519 attestation receipts.

---

## 🚀 Quick Start (Cursor, Claude Desktop, Windsurf)

### Add to Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "nano-empire-suite": {
      "command": "python",
      "args": ["-m", "nano_mcp_suite.server"]
    }
  }
}
```

### Installation

```bash
git clone https://github.com/roblambert9/nano-empire-mcp-suite.git
cd nano-empire-mcp-suite
pip install -e .
```

### Running Standalone

```bash
python -m nano_mcp_suite.server
```

---

## 🏛️ Verification & Compliance

All extraction events and audit records are signed with the Nano Empire Sovereign Root Ed25519 keypair and can be verified against the public manifest:

- **Public Agent Manifest**: `https://www.nanoempireai.com/.well-known/agents.json`
- **Machine Discovery**: `https://www.nanoempireai.com/llms.txt`
- **Root Node DID**: `did:nano:nanoempire:cortex-8412`

---

## 📄 License

MIT © [Nano Empire AI](https://nanoempireai.com)
