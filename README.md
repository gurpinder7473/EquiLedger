# Expense Reconciliation Backend (FastAPI + PostgreSQL)

This repository contains a minimal FastAPI backend implementing a rule-based
expense reconciliation system (single-group/single-user initial version).

## Contents
- `main.py` - FastAPI app with endpoints for participants, categories, transactions and settlement.
- `models.py` - SQLModel ORM models for Participants, Categories, Transactions, Splits, Payments.
- `compute.py` - Core reconciliation logic: compute_shares, compute_group_balance, settle.
- `requirements.txt` - Python dependencies.

## Quickstart (SQLite local test)
1. Create a Python virtualenv and activate it.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app (uses SQLite dev.db by default):
   ```bash
   uvicorn main:app --reload
   ```
4. Use the example `curl` commands in the earlier conversation to add participants and transactions.

## Using PostgreSQL
Set `DATABASE_URL` environment variable before starting the server, e.g.:
```bash
export DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5432/expense_db"
uvicorn main:app --reload
```

For production, add Alembic migrations and configure your DB accordingly.
