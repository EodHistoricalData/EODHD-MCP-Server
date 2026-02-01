# EODHD MCP Server

MCP (Model Context Protocol) server that exposes EODHD financial APIs to AI assistants (Claude Desktop, Claude Code, ChatGPT, etc.).

## Identity

Role: peer
Specialization: integration
Category: eodhd
Project ID: 17

## Governance

Model: Federation
- Автономен в решениях по MCP протоколу и API интеграции
- PM — общий протокол коммуникации
- Важные решения — эскалация человеку

## Network

PM API: https://pm-agent.eodhd.com/api
API_KEY: pma_7Kx9mR2vL4nQ8wF3jH6sY1bT5cA0dG
Repository: github.com/EodHistoricalData/EODHD-MCP-Server

## Tech Stack

- Language: Python 3.11+
- Framework: FastMCP
- HTTP: httpx
- Validation: Pydantic 2.0
- Tests: pytest, pytest-asyncio

## Project Structure

```
EODHD-MCP-Server/
├── app/                # MCP tools implementation
├── entrypoints/        # Entry points for different clients
├── examples/           # Usage examples
├── tests/              # Test suite
├── server.py           # Main server
├── cli.py              # CLI interface
├── manifest.json       # MCP manifest
└── docker-compose.yml  # Docker setup
```

## Supported Clients

- Claude Desktop
- Claude Code
- ChatGPT (MCP/Connectors)
- MCP Inspector
- Custom agents

## Available Tools

### Main Subscriptions
- End-of-day, intraday & tick data
- Live (delayed) quotes & US Live v2
- Fundamentals, earnings & financials
- News, sentiment & word weights
- Stock screener & discovery
- Corporate actions (dividends, splits, IPOs)
- Macro indicators, exchanges & listings

### Marketplace
- Options (contracts, EOD, underlying)
- illio (performance, risk)
- Praams (risk scoring, bonds)
- Investverte ESG

## Commands

```bash
# Install
pip install -e .

# Run server
python server.py

# Run with Docker
docker-compose up

# Run tests
pytest

# CLI
python cli.py --help
```

## Configuration

Set `EODHD_API_TOKEN` environment variable or in `.env`:
```
EODHD_API_TOKEN=your_api_token_here
```

## При старте сессии

1. POST /api/agent-status/17 → status: "online"
2. GET /api/messages/inbox?project_id=17
3. GET /api/projects/17/tasks?status=todo
4. Если PM недоступен — работай автономно

## При завершении сессии

1. POST /api/agent-status/17 → status: "offline"
2. Записать сессию в docs/sessions/ (создать если нет)
3. git commit && push

## Related Projects

- hitchhikers-guide — документация EODHD API
- FreshChatAgent — использует EODHD данные для поддержки

## Current Status

Version: 2.7.0
Status: Active development
