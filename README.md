# OXXO Reconciliation Service

Backend service that reconciles cash payment transactions (OXXO/Efecty) across multiple source systems, detects reconciliation issues, and exposes findings via a REST API.

## Problem

UrbanStyle processes ~2,000 cash payments/week through OXXO (Mexico) and Efecty (Colombia). 18% of transactions are misreconciled due to time lags, multiple data sources, human error, and network delays. This service ingests data from 3 systems, runs 5 detection rules, and surfaces issues for the finance team.

## Tech Stack

- **Python 3.12+** / **FastAPI** / **SQLAlchemy** / **SQLite**
- **Testing:** pytest + httpx (109 tests, 97% coverage)

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest -v

# Generate test data (310 transactions)
python scripts/generate_test_data.py

# Start server
uvicorn app.main:app --reload

# Seed database and run detection
python scripts/seed_database.py

# Or run full demo
bash scripts/demo.sh
```

## Architecture

```
app/
  main.py              # FastAPI app with lifespan events
  config.py            # Configurable settings (thresholds, tolerances)
  database.py          # SQLAlchemy engine/session
  models.py            # 4 SQLAlchemy models (3 source tables + issues)
  enums.py             # PaymentStatus, IssueType, Severity, PaymentMethod, Currency
  schemas.py           # Pydantic request/response schemas
  routers/             # API endpoints (ingestion, transactions, detection, issues, batch)
  services/            # Business orchestration (ingestion, detection, issues, batch)
  rules/               # Pure detection functions (no DB, no HTTP dependencies)
tests/                 # 109 tests (61 unit + 35 integration + 13 data integrity)
scripts/               # Data generation, seeding, demo
data/                  # Generated JSON test data (300+ transactions)
```

### Three-Layer Separation

| Layer | Responsibility | Dependencies |
|-------|---------------|-------------|
| **API (routers/)** | HTTP endpoints, request validation, serialization | FastAPI, Pydantic schemas |
| **Detection (rules/)** | Pure business logic functions | Only domain models and enums |
| **Data (services/, models/)** | DB queries, ingestion, orchestration | SQLAlchemy |

The detection rules are **pure functions** — they receive data and return issues. No database or HTTP imports. This makes them trivially unit-testable and ensures a change in detection logic never requires touching the API layer.

## Database Models

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `voucher_records` | Voucher generation events | transaction_id, amount, currency, payment_method, status, created_at, expires_at |
| `payment_confirmations` | Store payment events | transaction_id, amount, currency, payment_method, status, paid_at |
| `settlement_records` | Fund settlement events | transaction_id, amount, currency, status, settled_at |
| `reconciliation_issues` | Detected issues | transaction_id, issue_type, severity, description, amount_at_risk, payment_method, currency |

The `TransactionView` is a read-only projection (Pydantic model, not a table) that aggregates the 3 source records + issues for a single transaction_id at query time.

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check |
| POST | `/api/v1/ingest/vouchers` | Ingest voucher records |
| POST | `/api/v1/ingest/payments` | Ingest payment confirmations |
| POST | `/api/v1/ingest/settlements` | Ingest settlement records |
| GET | `/api/v1/transactions/{txn_id}` | Cross-source transaction view |
| POST | `/api/v1/detection/run` | Trigger detection engine |
| GET | `/api/v1/issues` | Query issues (filters + pagination) |
| GET | `/api/v1/issues/summary` | Summary statistics |
| POST | `/api/v1/batch/reconcile` | Batch reconciliation (stretch) |
| GET | `/api/v1/batch/{job_id}` | Poll batch job status (stretch) |

### Example API Calls

```bash
# Ingest vouchers
curl -X POST http://localhost:8000/api/v1/ingest/vouchers \
  -H "Content-Type: application/json" \
  -d @data/vouchers.json

# Run detection
curl -X POST http://localhost:8000/api/v1/detection/run

# Query all HIGH severity issues for OXXO
curl "http://localhost:8000/api/v1/issues?severity=HIGH&payment_method=OXXO"

# Get transaction detail across all sources
curl http://localhost:8000/api/v1/transactions/TXN-OXXO-001

# Summary statistics
curl http://localhost:8000/api/v1/issues/summary
```

### Issues Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `issue_type` | string | ORPHANED_PAYMENT, STUCK_PENDING, AMOUNT_MISMATCH, ZOMBIE_COMPLETION, POST_EXPIRATION_PAYMENT |
| `severity` | string | LOW, MEDIUM, HIGH |
| `payment_method` | string | OXXO, EFECTY |
| `currency` | string | MXN, COP |
| `date_from` | string | ISO datetime filter |
| `date_to` | string | ISO datetime filter |
| `limit` | int | Page size (1-200, default 50) |
| `offset` | int | Pagination offset |

## Detection Rules

### 1. Orphaned Payment (Severity: HIGH)

**What it detects:** A payment confirmation exists in the payment processor but no corresponding voucher was ever generated.

**Why it matters:** This could indicate fraud (fake vouchers), system errors where voucher creation failed but the store still accepted payment, or data sync issues between systems.

**Logic:** For each payment confirmation, check if its `transaction_id` exists in the set of voucher `transaction_id`s. If not, it's orphaned.

**Edge cases:** Substring matching is avoided — `TXN-001` does not match `TXN-0010`. Set membership ensures exact matching.

### 2. Stuck Pending (Severity: MEDIUM / HIGH)

**What it detects:** A voucher was created more than 72 hours ago, is still in PENDING status, and no payment confirmation has been received.

**Why it matters:** The customer may have paid but the store network failed to transmit the confirmation, or the customer forgot to pay. Either way, the order is stuck and the customer may be frustrated.

**Logic:** For each voucher with `status == PENDING` and no matching payment confirmation, calculate the age in hours. If age > 72h → MEDIUM severity. If age > 120h → HIGH severity.

**Thresholds are configurable** via `config.py`:
- `stuck_pending_threshold_hours = 72` (flag as MEDIUM)
- `stuck_pending_high_threshold_hours = 120` (escalate to HIGH)

**Edge cases:**
- Transactions with status EXPIRED, CANCELLED, or PAID are excluded
- Exactly 72 hours is NOT flagged (boundary: strictly greater than)
- Compares against current time, not a fixed value

### 3. Amount Mismatch (Severity: LOW / MEDIUM / HIGH)

**What it detects:** The amount on the voucher doesn't match the amount actually paid, beyond a 1% tolerance for currency conversion rounding.

**Why it matters:** This indicates the store clerk entered a different amount, the customer paid a partial amount, or there was a currency conversion error.

**Logic:**
1. **Currency check first:** If voucher and payment currencies differ → HIGH severity with "currency mismatch" description (amount comparison is skipped since it would be meaningless)
2. **Amount comparison:** `abs(voucher_amount - paid_amount) / voucher_amount > 0.01`
   - 1-5% → LOW
   - 5-10% → MEDIUM
   - \>10% → HIGH

**`amount_at_risk`** = absolute difference between voucher and payment amounts.

**Edge cases:**
- Exactly 1% (e.g., 100.00 vs 101.00) is NOT flagged — tolerance is inclusive
- Zero voucher amount is skipped
- Uses `Decimal` arithmetic throughout to avoid floating-point drift
- COP large amounts (hundreds of thousands) are handled correctly
- Auto-resolution suggested for LOW severity: "Auto-approve if under 1% tolerance threshold"

### 4. Zombie Completion (Severity: HIGH)

**What it detects:** A transaction was marked COMPLETED (funds settled) but it never went through the CONFIRMED state — no payment confirmation record exists.

**Why it matters:** This means money was settled to the merchant without verification that the customer actually paid. This could be a system bypass, data sync issue, or potential fraud.

**Logic:** For each settlement record with `status == COMPLETED`, check if its `transaction_id` exists in the set of payment confirmations with `status == CONFIRMED`. If not, it's a zombie.

**Edge cases:**
- A payment may exist with status PENDING (not yet confirmed) — this is still flagged as a zombie because confirmation hasn't happened
- Non-COMPLETED settlements are excluded

### 5. Post-Expiration Payment (Severity: HIGH)

**What it detects:** A payment was received after the voucher's expiration timestamp.

**Why it matters:** The customer paid at the store after the voucher expired. The merchant may need to process a refund since the order may have already been cancelled or the inventory released.

**Logic:** For each (voucher, payment) pair where `voucher.expires_at` is set, check if `payment.paid_at > voucher.expires_at`. If so, flag it.

**Edge cases:**
- Payment exactly at expiration time is NOT flagged (boundary: strictly after)
- OXXO vouchers typically expire in 48 hours, Efecty in 72 hours — the rule uses the actual `expires_at` from each voucher, not a fixed window
- Vouchers without an expiration timestamp are skipped

## Detection Idempotency

`POST /api/v1/detection/run` uses a **delete-and-reinsert** strategy: all existing issues are deleted before re-running detection. This guarantees:
- No duplicate issues on repeated calls
- Fresh results reflecting current ingested data
- Response includes `previous_issues_cleared` and `new_issues_found`

## Test Data

The generator (`scripts/generate_test_data.py`) creates 310 realistic transactions:

| Category | Count | Details |
|----------|-------|---------|
| Full lifecycle (clean) | 180 | PENDING → PAID → CONFIRMED → COMPLETED |
| Expired (clean) | 40 | Voucher expired, no payment |
| Cancelled (clean) | 30 | Order cancelled before payment |
| In-progress (clean) | 20 | Recently created, still within 72h window |
| Orphaned payments | 8 | Payment without voucher |
| Stuck pending | 10 | PENDING > 72h, no payment |
| Amount mismatch | 10 | Various percentages + currency mismatch |
| Zombie completions | 6 | COMPLETED without CONFIRMED |
| Post-expiration | 6 | Payment after voucher expiry |

**Realistic patterns:**
- ~62% OXXO (MXN, 50-5,000 range), ~38% Efecty (COP, 10,000-500,000)
- Timing: voucher → payment (1-24h) → settlement (1-3 days)
- Edge cases: near-boundary amounts (1.01%), near-boundary times (72h+1s), weekend delays, COP rounding

## Testing

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run only detection rule tests
pytest tests/test_detection_rules.py -v

# Run only API integration tests
pytest tests/test_ingestion.py tests/test_issues_api.py tests/test_transactions.py -v
```

**109 tests total:**
- 61 pure function unit tests for detection rules (no DB required)
- 35 integration tests for API endpoints (ingestion, transactions, detection, issues, batch)
- 13 data integrity tests for generated test data
- 97% code coverage

## Stretch Goals Implemented

### Batch Reconciliation
- `POST /api/v1/batch/reconcile` — Submit vouchers, payments, and settlements in a single request
- Returns a `job_id` that can be polled via `GET /api/v1/batch/{job_id}`
- Processing runs in a background thread
- Job states: queued → processing → completed | failed

### Auto-Resolution Suggestions
Each detected issue includes a `suggested_resolution` field with actionable guidance:
- **Orphaned Payment:** "Investigate if the voucher was generated in a different system..."
- **Stuck Pending:** "Send a payment reminder to the customer..."
- **Amount Mismatch (LOW):** "Auto-approve if under 1% tolerance threshold..."
- **Amount Mismatch (HIGH):** "Escalate to finance team for manual review..."
- **Zombie Completion:** "Verify if the payment was actually confirmed..."
- **Post-Expiration:** "Process a refund to the customer..."

## Design Decisions

1. **TransactionView as projection, not table:** The 3 source systems have fundamentally different schemas and lifecycles. Instead of a denormalized aggregate table, `TransactionView` is composed at query time from the 3 source tables, preserving `source_system` provenance.

2. **Pure function detection rules:** Rules receive data, return issues. No DB imports, no HTTP dependencies. This makes them independently testable and ensures separation between detection logic and infrastructure.

3. **Decimal for monetary amounts:** All amounts use `Decimal(14,2)` to avoid floating-point drift. The 1% tolerance calculation uses `Decimal` arithmetic throughout.

4. **Configurable thresholds:** Detection thresholds (72h, 120h, 1%, 5%, 10%) are defined in `config.py` as `Settings` fields, making them easy to tune via environment variables.

5. **Denormalized issue fields:** `payment_method` and `currency` are denormalized into `reconciliation_issues` at detection time, so filtering issues by payment method requires no joins.

6. **SQLite for zero infrastructure:** A reviewer can clone, install, and run without setting up any external database. The same codebase works with PostgreSQL by changing one config value.
