# Rapora

A modern, open-source CRM platform built with Django REST Framework and SvelteKit.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![Django](https://img.shields.io/badge/django-5.x-green.svg)
![SvelteKit](https://img.shields.io/badge/sveltekit-2.x-orange.svg)
![Svelte](https://img.shields.io/badge/svelte-5-orange.svg)
![Coverage](./coverage-badge.svg)

## Overview

Rapora is a full-featured Customer Relationship Management system designed for startups and small businesses. It combines a powerful Django REST API backend with a modern SvelteKit frontend, featuring multi-tenant architecture with PostgreSQL Row-Level Security (RLS) for enterprise-grade data isolation.

**Self-host it**: see [Quick Start](#quick-start) below to run the full stack with Docker Compose.

## Features

### Core CRM Modules
- **Leads** - Track and manage sales leads through your pipeline
- **Accounts** - Manage company/organization records
- **Contacts** - Store and organize contact information
- **Opportunities** - Track deals and sales opportunities
- **Cases** - Customer support case management
- **Tasks** - Task management with calendar and Kanban board views
- **Invoices** - Create and manage invoices

### Platform Features
- **Multi-Tenant Architecture** - PostgreSQL RLS for secure data isolation between organizations
- **JWT Authentication** - Secure token-based authentication
- **Team Management** - Organize users into teams with role-based access
- **Activity Tracking** - Comprehensive audit logs and activity history
- **Comments & Attachments** - Collaborate with comments and file attachments on any record
- **Tags** - Flexible tagging system for organizing records
- **Email Integration** - AWS SES integration for transactional emails
- **Background Tasks** - Celery + Redis for async task processing
- **AI Agents (MCP)** - Built-in [Model Context Protocol](https://modelcontextprotocol.io) server (`mcp_server/`) lets Claude, Cursor, Codex, Gemini and any MCP client search, create and update records via a personal access token — acting as you, with your role and permissions. See [`mcp_server/README.md`](mcp_server/README.md).

## Tech Stack

### Backend
- **Django 5.x** with Django REST Framework
- **PostgreSQL** with Row-Level Security (RLS)
- **Redis** for caching and Celery broker
- **Celery** for background task processing
- **JWT** for authentication
- **AWS S3** for file storage
- **AWS SES** for email delivery

### Frontend
- **SvelteKit 2.x** with Svelte 5 (runes)
- **TailwindCSS 4** for styling
- **shadcn-svelte** UI components
- **Zod** for schema validation
- **Axios** for API communication
- **Lucide** icons

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+ with pnpm
- PostgreSQL 14+
- Redis

### Backend Setup

The backend uses [`uv`](https://docs.astral.sh/uv/) for Python dependency management — it reads `pyproject.toml`, installs from `uv.lock`, and creates the virtual environment for you. uv is much faster than pip and gives reproducible installs out of the box.

```bash
# Clone the repository
git clone https://github.com/indranandjha1993/rapora.git
cd rapora/backend

# Install uv (one time, system-wide)
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or on macOS via Homebrew: brew install uv

# Install Python (matches the version in .python-version) and all deps into .venv/
uv sync

# Set up environment variables (see env.md for details)
cp .env.example .env
# Edit .env with your database and other settings

# Run migrations
uv run python manage.py migrate

# Create a superuser
uv run python manage.py createsuperuser

# Start the development server
uv run python manage.py runserver
```

`uv run <cmd>` resolves binaries from `.venv/bin/` automatically — no need to `source .venv/bin/activate`. If you prefer the activate-then-run flow, that still works:

```bash
source .venv/bin/activate
python manage.py runserver   # equivalent to `uv run python manage.py runserver`
```

Common dev commands (from `backend/`):

```bash
uv run pytest                                # run tests
uv run python manage.py makemigrations       # create migrations
uv run celery -A crm worker --loglevel=INFO  # background worker
uv add <package>                             # add a dependency (updates pyproject.toml + uv.lock)
uv add --group dev <package>                 # add a dev-only dependency
uv lock --upgrade                            # refresh the lockfile
```

### Frontend Setup

```bash
# In a new terminal, from the project root
cd frontend

# Install dependencies
pnpm install

# Start the development server
pnpm run dev
```

### Start Celery Worker

```bash
# In a new terminal
cd backend
uv run celery -A crm worker --loglevel=INFO
```

### Access the Application
- **Frontend**: http://localhost:5173
- **API Documentation**: http://localhost:8000/swagger-ui/
- **Admin Panel**: http://localhost:8000/admin/

### Connect your AI agent (MCP)

Let Claude, Cursor, Codex, Gemini, or any MCP client work in your CRM:

1. In the app, go to **Settings → API Tokens** and create a personal access token (shown once).
2. Register the `rapora-mcp` server in your AI client, passing `RAPORA_BASE_URL` (your API host, e.g. `http://localhost:8000`) and `RAPORA_TOKEN` (the token). The token page shows ready-to-paste config for each client.
3. Restart the client and start asking.

The agent authenticates **as you** and inherits your role, org and RLS scope — it can't see or do anything you can't. Full setup, the tool list, and the security model are in [`mcp_server/README.md`](mcp_server/README.md).

## Docker Setup

The compose file runs the application services (Django API, Celery worker + beat,
SvelteKit frontend). **PostgreSQL and Redis are external** — bring your own and
set their connection details in `.env`.

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY, DBHOST/DBNAME/DBUSER/DBPASSWORD, and Redis URLs.

# 2. Create the database and a NON-superuser role (RLS must be enforced).
#    See RLS_SETUP.md for the exact SQL.

# 3. Start the stack (first run builds images; migrations run automatically,
#    and an admin user from ADMIN_EMAIL / ADMIN_PASSWORD is created)
docker compose up --build

# (Optional) Load sample data
docker compose exec backend python manage.py seed_data --email admin@example.com
```

Once running (ports configurable via `BACKEND_PORT` / `FRONTEND_PORT` in `.env`):
- **Frontend**: http://localhost:5173
- **API / Swagger**: http://localhost:8000/swagger-ui/

### Daily workflow

```bash
docker compose up           # start all services (code changes auto-reload)
docker compose down         # stop all services
```

### Running commands inside containers

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python -m pytest
docker compose exec backend python manage.py manage_rls --status
```

### Environment configuration

All configuration lives in a single `.env` file (gitignored). Copy the template
and edit it:

```bash
cp .env.example .env
```

`.env.example` documents every variable, including the external PostgreSQL and
Redis connection settings and the publishable host ports.

## Project Structure

```
rapora/
├── backend/                 # Django REST API
│   ├── accounts/           # Accounts module
│   ├── cases/              # Cases module
│   ├── common/             # Shared models, utilities, RLS
│   ├── contacts/           # Contacts module
│   ├── invoices/           # Invoices module
│   ├── leads/              # Leads module
│   ├── opportunity/        # Opportunities module
│   ├── tasks/              # Tasks module
│   └── crm/                # Django project settings
├── frontend/               # SvelteKit frontend
│   ├── src/
│   │   ├── lib/           # Components, stores, utilities
│   │   └── routes/        # SvelteKit routes
│   │       ├── (app)/     # Authenticated app routes
│   │       └── (no-layout)/ # Auth pages (login, etc.)
│   ├── static/            # Static assets
│   └── Dockerfile         # Frontend dev container
├── mcp_server/             # MCP server (rapora-mcp) for AI agents
│   └── src/rapora_mcp/      # FastMCP tools over the REST API (stdio transport)
├── docker/                 # Docker support files
│   ├── backend/
│   │   └── entrypoint.sh  # DB wait + migrate + runserver
│   └── postgres/
│       └── init-rls-user.sql # Helper SQL to create the non-superuser RLS role
├── Dockerfile              # Backend / Celery image
├── docker-compose.yml      # Application stack (external Postgres + Redis)
└── .env.example            # Environment template (copy to .env)
```

## Multi-Tenancy & Security

Rapora uses PostgreSQL Row-Level Security (RLS) to ensure complete data isolation between organizations. Every database query is automatically filtered by organization context, providing enterprise-grade security.

```bash
# Check RLS status
python manage.py manage_rls --status

# Verify RLS user configuration
python manage.py manage_rls --verify-user

# Test data isolation
python manage.py manage_rls --test
```

## Development

### Testing

```bash
cd backend

# Run all tests with coverage
pytest

# Run tests without coverage (faster)
pytest --no-cov -x

# Run a specific module's tests
pytest accounts/tests/
pytest leads/tests/test_leads_kanban.py

# Run tests matching a keyword
pytest -k "test_login"

# View coverage report in browser
open htmlcov/index.html
```

### Backend Commands

```bash
# Format code
black . && isort .

# Check dependencies
pipdeptree
pip-check -H
```

### Dev login (skip the Google OAuth flow)

For local development you can mint a JWT for any user without going through Google sign-in. The command refuses to run unless `DEBUG=True`, and there's no web endpoint — it's only reachable through `manage.py`:

```bash
cd backend

# Mint tokens for an existing user (no org bound — same as the OAuth flow)
uv run python manage.py devlogin indranandjha0@gmail.com

# Bind to a specific org so you skip the orgswitch step on first load
uv run python manage.py devlogin indranandjha0@gmail.com --org "Rapora"

# Create the user on the fly (random password) if they don't exist yet
uv run python manage.py devlogin newdev@example.com --create
```

The command prints the access/refresh tokens plus a ready-to-paste `localStorage.setItem(...)` snippet — drop it into the browser devtools console on `http://localhost:5173` and reload to be signed in.

### Frontend Commands

```bash
cd frontend

# Type checking
pnpm run check

# Linting
pnpm run lint

# Formatting
pnpm run format
```

## API Documentation

The API follows RESTful conventions:

```
GET/POST       /api/<module>/                 # List/Create
GET/PUT/DELETE /api/<module>/<pk>/            # Detail/Update/Delete
GET/POST       /api/<module>/comment/<pk>/    # Comments
GET/POST       /api/<module>/attachment/<pk>/ # Attachments
```

Interactive API documentation is available at `/swagger-ui/` when running the backend.

## Contributing

We welcome contributions! Please see our contributing guidelines for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Community

- **Issues**: [GitHub Issues](https://github.com/indranandjha1993/rapora/issues)
- **GitHub**: [@indranandjha1993](https://github.com/indranandjha1993)
- **Contact**: indranandjha0@gmail.com

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

