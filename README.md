# WhatsApp Micro ERP

A **WhatsApp-based debt and inventory tracker** for Kenyan SMEs.  
Shopkeepers record credit sales by sending natural-language WhatsApp messages; the system parses them, persists the data in PostgreSQL, and integrates with **M-Pesa (Daraja API)** for payment confirmations.

---

## Features

| Feature | Details |
|---|---|
| **WhatsApp Cloud API webhook** | Receives and processes messages sent by shopkeepers |
| **Natural-language parser** | Regex-based engine parses messages like *"Njoroge bought 2kg sugar for 400 on credit"* |
| **PostgreSQL / SQLAlchemy ORM** | `users`, `customers`, and `transactions` tables with Alembic migrations |
| **M-Pesa Daraja integration** | STK Push initiation + callback handler to auto-confirm payments |
| **FastAPI** | Async REST API with OpenAPI docs at `/docs` |
| **Docker / docker-compose** | One-command local deployment |

---

## Quick Start

### 1 – Clone & configure

\`\`\`bash
cp .env.example .env
# Edit .env and fill in your WhatsApp and Daraja credentials
\`\`\`

### 2 – Run with Docker Compose

\`\`\`bash
docker compose up --build
\`\`\`

The API will be available at <http://localhost:8000>.  
Interactive docs: <http://localhost:8000/docs>

### 3 – Run locally (without Docker)

\`\`\`bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Ensure DATABASE_URL points to a running Postgres instance
uvicorn app.main:app --reload
\`\`\`

---

## Directory Structure

\`\`\`
.
├── app/
│   ├── main.py                  # FastAPI app factory & startup
│   ├── config.py                # Pydantic-settings config (env vars)
│   ├── database.py              # SQLAlchemy engine + session + Base
│   ├── models/
│   │   ├── models.py            # ORM models: User, Customer, Transaction
│   │   └── schemas.py           # Pydantic request/response schemas
│   ├── routers/
│   │   ├── webhook.py           # POST /webhook  (WhatsApp Cloud API)
│   │   └── mpesa.py             # POST /mpesa/callback  (Daraja STK Push)
│   ├── services/
│   │   ├── daraja.py            # Daraja API helpers (token, STK Push, parse)
│   │   └── transaction_service.py  # Business logic / DB writes
│   └── utils/
│       └── message_parser.py    # Regex message parser
├── alembic/                     # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── tests/
│   ├── test_message_parser.py
│   ├── test_daraja.py
│   └── test_api.py
├── .env.example
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── requirements-dev.txt
\`\`\`

---

## Message Patterns Supported

| Pattern | Type |
|---|---|
| \`<Name> bought <qty><unit> <item> for <amount> on credit\` | Credit sale |
| \`<Name> bought <qty><unit> <item> for <amount>\` | Credit sale |
| \`<Name> paid <amount>\` | Payment |
| \`<Name> paid <amount> via mpesa <REF>\` | Payment with M-Pesa reference |
| \`Record <qty><unit> <item> for <amount> cash from <Name>\` | Cash sale |

---

## Running Tests

\`\`\`bash
pip install -r requirements-dev.txt
pytest -v
\`\`\`

---

## Database Migrations

\`\`\`bash
# Generate a new migration after model changes
alembic revision --autogenerate -m "describe change"

# Apply all pending migrations
alembic upgrade head
\`\`\`

---

## Environment Variables

See \`.env.example\` for all required variables with descriptions.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| \`GET\` | \`/health\` | Liveness probe |
| \`GET\` | \`/webhook/\` | Meta webhook verification |
| \`POST\` | \`/webhook/\` | Receive WhatsApp messages |
| \`POST\` | \`/mpesa/callback\` | Daraja STK Push callback |
| \`GET\` | \`/docs\` | Swagger UI |
