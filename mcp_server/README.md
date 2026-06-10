# Rapora MCP Server (`rapora-mcp`)

`rapora-mcp` is a standalone [Model Context Protocol](https://modelcontextprotocol.io)
server that lets an AI agent (Claude Desktop, Cursor, etc.) drive a Rapora
instance through its REST API.

It is a **thin HTTP client** of the CRM API — it does *not* import Django, has no
database access of its own, and runs as its own [`uv`](https://docs.astral.sh/uv/)
package. Every request is authenticated with a **Personal Access Token (PAT)**
and the agent acts **as the user who owns that token**: it inherits exactly that
user's role and org. All Row-Level Security, permission checks, and field
validation are enforced by the backend — the MCP server never bypasses tenant
isolation and adds no privileges of its own.

> **Transports.** `rapora-mcp` runs in two modes, selected by `RAPORA_TRANSPORT`:
>
> - **`stdio`** (default) — the agent launches `rapora-mcp` as a local subprocess
>   and talks over stdin/stdout. The process acts as a single user, whose token
>   is `RAPORA_TOKEN`.
> - **`http`** — a hosted, multi-user server (e.g. mounted in the Django app at
>   `/mcp`). It holds **no** server-side token; instead **every request
>   authenticates with its own `Authorization: Bearer <pat>` header**, so each
>   caller acts strictly as their own CRM identity. See
>   [HTTP transport](#http-transport-hosted-multi-user) below.
>
> OAuth-based connect is planned for a later phase; today http mode uses a
> personal access token in the request header.

## Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/)
- A reachable Rapora backend (the community Rapora API)
- A Rapora Personal Access Token (`rapora_pat_…`)

## Install & run

```bash
cd mcp_server
uv sync
RAPORA_BASE_URL=http://localhost:8000 RAPORA_TOKEN=rapora_pat_… uv run rapora-mcp
```

`uv sync` creates `.venv/` from `pyproject.toml` + `uv.lock`. `uv run rapora-mcp`
launches the server over stdio (it will block waiting for an MCP client on
stdin — that is expected; normally your MCP client launches it for you).

### Configuration (environment variables)

| Variable         | Required            | Description                                                                                           |
| ---------------- | ------------------- | ---------------------------------------------------------------------------------------------------- |
| `RAPORA_BASE_URL`  | yes                 | Root URL of the CRM (the host, **not** an `/api/...` path), e.g. `http://localhost:8000`.             |
| `RAPORA_TRANSPORT` | no (default `stdio`)| `stdio` or `http`. See [HTTP transport](#http-transport-hosted-multi-user).                           |
| `RAPORA_TOKEN`     | stdio only          | A Personal Access Token, `rapora_pat_…`, sent as `Authorization: Bearer <token>`. **Required for stdio; must be unset for http** (where the token comes per-request from each caller's header). |
| `RAPORA_HOST`      | no (default `127.0.0.1`) | http only — bind address when serving standalone.                                                |
| `RAPORA_PORT`      | no (default `8900`) | http only — bind port when serving standalone.                                                       |
| `RAPORA_PATH`      | no (default `/mcp`) | http only — route the streamable endpoint is served at when serving standalone.                      |

In stdio mode, a missing `RAPORA_BASE_URL` or `RAPORA_TOKEN` exits immediately. In
http mode, a server-side `RAPORA_TOKEN` is rejected (it would make every caller
share one identity).

## HTTP transport (hosted, multi-user)

In http mode the server is long-lived and serves many users at once. There is
no server-side token: **each request must carry its own
`Authorization: Bearer <rapora_pat_…>` header**, and the server builds a fresh,
per-request client from that token — so every caller acts strictly as their own
CRM identity, with their own role and org. A request with no/invalid bearer
token is rejected before any API call is made.

There are two ways to run http mode:

**1. Mounted in the Django app (recommended).** The community backend mounts
this server at `/mcp` from `crm/asgi.py` when the optional `mcp` extra is
installed and the app is served under ASGI (uvicorn). Clients then connect to
`https://<your-api-host>/mcp` — see the hosted client config below.

```bash
# from Rapora/backend
uv sync --extra mcp                      # installs fastmcp + this package (editable)
RAPORA_BASE_URL=http://127.0.0.1:8000 \
  uv run uvicorn crm.asgi:application --host 0.0.0.0 --port 8000
# MCP is now at http://<host>:8000/mcp
```

Notes:

- The mount is **inactive under `runserver`/WSGI** — it only activates when you
  serve `crm.asgi:application` under an ASGI server (uvicorn).
- `RAPORA_BASE_URL` is the loopback the in-process tools call (defaults to
  `http://127.0.0.1:8000`). Leave `RAPORA_TOKEN` **unset** — http mode takes the
  token from each request. Set `RAPORA_MCP_ENABLED=false` to disable the mount.
- **Edge auth:** any `/mcp` request without a well-formed `Authorization: Bearer`
  header gets a `401` before reaching the MCP layer — even `initialize` and
  tool listing require a token (the token's validity is then checked by the
  backend on each API call).

**2. Standalone.** Run the server on its own port:

```bash
RAPORA_TRANSPORT=http RAPORA_BASE_URL=http://localhost:8000 \
  RAPORA_HOST=0.0.0.0 RAPORA_PORT=8900 uv run rapora-mcp
# streamable endpoint at http://localhost:8900/mcp
```

### Hosted client config (no install)

For clients that support remote MCP servers, point them at the URL and send the
token in a header — nothing to install:

```json
{
  "mcpServers": {
    "rapora": {
      "type": "http",
      "url": "https://api.rapora.io/mcp",
      "headers": { "Authorization": "Bearer rapora_pat_…" }
    }
  }
}
```

## Getting a Personal Access Token

A PAT identifies the user the agent acts as. Anyone holding the token has the
same CRM access as that user, scoped to their org — treat it like a password.

### Option A — CRM web UI (recommended)

In the CRM go to **Settings → API Tokens**, create a token, and copy the
`rapora_pat_…` value. **The raw token is shown only once at creation.** You can
revoke it from the same screen at any time. That page also shows ready-to-paste
config for each client below, pre-filled with your API host and token.

### Option B — Django shell (local / dev)

For a quick local token, mint one directly from the backend. This prints the raw
token once:

```bash
cd ../backend && uv run python manage.py shell -c "from common.models import Profile, PersonalAccessToken; p=Profile.objects.filter(role='ADMIN', is_active=True).first(); print(PersonalAccessToken.generate(p,'smoke')[0])"
```

The PAT table is created by the `common` app migrations — if you get a
`relation "personal_access_token" does not exist` error, run
`uv run python manage.py migrate common` first.

## Client configuration

Register `rapora-mcp` in your AI client and pass `RAPORA_BASE_URL` + `RAPORA_TOKEN` as
environment variables. **Claude Desktop, Cursor, and Gemini CLI share the
identical `mcpServers` JSON schema** — only the config file differs. **Codex CLI
uses TOML.** Replace `http://localhost:8000` with your API host (e.g.
`https://api.rapora.io`) and paste your `rapora_pat_…` token.

| Client         | Config file                                                            | Format |
| -------------- | ---------------------------------------------------------------------- | ------ |
| Claude Desktop | `claude_desktop_config.json` (Settings → Developer → Edit Config)      | JSON   |
| Cursor         | `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (per project)      | JSON   |
| Gemini CLI     | `~/.gemini/settings.json`                                              | JSON   |
| Codex CLI      | `~/.codex/config.toml`                                                  | TOML   |

### JSON clients (Claude Desktop / Cursor / Gemini CLI)

```json
{
  "mcpServers": {
    "rapora": {
      "command": "uvx",
      "args": ["rapora-mcp"],
      "env": {
        "RAPORA_BASE_URL": "http://localhost:8000",
        "RAPORA_TOKEN": "rapora_pat_…"
      }
    }
  }
}
```

### Codex CLI (TOML)

```toml
[mcp_servers.rapora]
command = "uvx"
args = ["rapora-mcp"]

[mcp_servers.rapora.env]
RAPORA_BASE_URL = "http://localhost:8000"
RAPORA_TOKEN = "rapora_pat_…"
```

Restart the client after editing its config; it launches `rapora-mcp` for you and
discovers the tools automatically.

### Until published — run from a local checkout

`rapora-mcp` is not yet on PyPI, so point the command at this directory instead of
using `uvx`. Use `--directory` with an absolute path so it works regardless of
the client's working directory. For the JSON clients:

```json
{
  "mcpServers": {
    "rapora": {
      "command": "uv",
      "args": ["run", "--directory", "/abs/path/to/mcp_server", "rapora-mcp"],
      "env": {
        "RAPORA_BASE_URL": "http://localhost:8000",
        "RAPORA_TOKEN": "rapora_pat_…"
      }
    }
  }
}
```

For Codex, set `command = "uv"` and
`args = ["run", "--directory", "/abs/path/to/mcp_server", "rapora-mcp"]`.
(Equivalently, from inside `mcp_server` you can just run `uv run rapora-mcp`.)

## Available tools

The server exposes **8 tools**. CRUD tools take an `entity` argument; supported
entities are: **leads, contacts, accounts, opportunities, tasks, cases,
invoices, solutions**.

| Tool           | Kind        | Description                                                                                                       |
| -------------- | ----------- | --------------------------------------------------------------------------------------------------------------- |
| `crm_search`   | read-only   | List/search records of an entity. Supports `query`, `filters`, `limit`, `offset`. `limit` is capped at **50**.   |
| `crm_get`      | read-only   | Fetch one record's full detail by `id`.                                                                          |
| `crm_create`   | write       | Create a record from a `data` object (validated server-side by the API).                                          |
| `crm_update`   | write       | Partially update a record (PATCH semantics) from a `data` object.                                                 |
| `crm_delete`   | destructive | Delete a record. **Requires `confirm=true`** — refuses to run otherwise.                                          |
| `crm_action`   | write       | Run a non-CRUD action on a record (see `list_actions`), e.g. `convert`, `add_comment`, `send`. Outward-facing actions (`send`) **require `confirm=true`**. |
| `crm_describe` | read-only   | Return an entity's fields, types, enums, and which are required — derived from the live OpenAPI schema.           |
| `list_actions` | read-only   | Return the allowed non-CRUD actions for each entity.                                                              |

### Entity → actions / API path

| Entity          | API path                  | Non-CRUD actions          |
| --------------- | ------------------------- | ------------------------- |
| `leads`         | `/api/leads/`             | `convert`, `add_comment`  |
| `contacts`      | `/api/contacts/`          | `add_comment`             |
| `accounts`      | `/api/accounts/`          | `add_comment`             |
| `opportunities` | `/api/opportunities/`     | `add_comment`             |
| `tasks`         | `/api/tasks/`             | —                         |
| `cases`         | `/api/cases/`             | `add_comment`             |
| `invoices`      | `/api/invoices/`          | `send`                    |
| `solutions`     | `/api/cases/solutions/`   | —                         |

> Note: solutions are served under the **cases** app at `/api/cases/solutions/`,
> not at a top-level `/api/solutions/`.
>
> `send` is outward-facing (emails a customer), so `crm_action` requires
> `confirm=true` for it — see the security model below.

## Security model

- **The agent acts as the token owner.** A PAT carries no extra privileges; the
  agent can do exactly what that user can do, in that user's org, and nothing
  more.
- **The backend is the only trust boundary.** All RLS (tenant isolation),
  RBAC/permission checks, and input validation happen server-side. The MCP
  server forwards requests and surfaces the API's responses and errors verbatim;
  it does not re-implement (or relax) any of those checks.
- **Read limits.** `crm_search` caps `limit` at 50 regardless of what the agent
  requests, to avoid pulling unbounded result sets.
- **Destructive & outward-facing ops are gated.** `crm_delete` refuses to run
  without `confirm=true`, and so do outward-facing actions like
  `crm_action(..., action="send")` (which emails a customer) — so a model can't
  delete a record or send an invoice by accident.
- **Tokens are revocable.** Revoke a PAT from the CRM (Settings → API Tokens) to
  immediately cut off an agent. Tokens may also carry an expiry.
- **Never commit a token.** Keep `RAPORA_TOKEN` out of source control, logs, and
  shared configs. Pass it via environment / your MCP client's `env` block.

## Manual smoke test

To exercise the real HTTP path without the full MCP stdio handshake, run the
plain async tool functions directly against a live backend:

1. Start (or confirm) a backend on `:8000` with the PAT migrations applied:

   ```bash
   cd ../backend
   uv run python manage.py migrate common      # ensures personal_access_token table exists
   uv run python manage.py runserver 8000
   ```

2. Mint a PAT (Option B above) and copy the printed `rapora_pat_…`.

3. Run a throwaway script against the live API:

   ```bash
   cd ../mcp_server
   RAPORA_BASE_URL=http://localhost:8000 RAPORA_TOKEN=rapora_pat_… uv run python - <<'PY'
   import asyncio, json, os
   from rapora_mcp.client import CrmClient
   from rapora_mcp import tools

   async def main():
       client = CrmClient(os.environ["RAPORA_BASE_URL"], os.environ["RAPORA_TOKEN"])
       print(await tools.crm_search(client, "leads", limit=5))
       print(json.dumps(await tools.crm_describe(client, "leads"), indent=2))

   asyncio.run(main())
   PY
   ```

   `crm_search` should return a paginated list payload, and `crm_describe`
   should return a non-empty field map for the `Lead` schema component.

## Development

```bash
uv sync
uv run pytest          # unit tests (client, tools, entities, server registration)
uv run black . && uv run isort .
```

Layout:

```
mcp_server/
├── src/rapora_mcp/
│   ├── server.py     # FastMCP server, ClientResolver, `rapora-mcp` entry + build_http_app
│   ├── tools.py      # the 8 tool implementations + OpenAPI describe heuristic
│   ├── client.py     # async httpx wrapper (CrmClient)
│   ├── entities.py   # entity → path / allowed-action registry
│   ├── auth.py       # per-request bearer-token extraction (http transport)
│   └── config.py     # env-var settings (transport, RAPORA_BASE_URL, RAPORA_TOKEN, …)
└── tests/
```
