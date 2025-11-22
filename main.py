from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import Session, select, SQLModel, create_engine
from typing import List
from decimal import Decimal
import os

from models import Participant, Category, Transaction, Split, Payment
from compute import compute_group_balance, settle

# DB URL: set via env var, example:
# export DATABASE_URL="postgresql://user:pass@localhost:5432/expense_db"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
engine = create_engine(DATABASE_URL, echo=False)

app = FastAPI(title="Expense Reconciliation API")

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

def get_session():
    with Session(engine) as session:
        yield session

# ========== Participant endpoints ==========
@app.post("/participants", response_model=Participant)
def create_participant(p: Participant, session: Session = Depends(get_session)):
    session.add(p)
    session.commit()
    session.refresh(p)
    return p

@app.get("/participants", response_model=List[Participant])
def list_participants(session: Session = Depends(get_session)):
    return session.exec(select(Participant)).all()

# ========== Category endpoints ==========
@app.post("/categories", response_model=Category)
def create_category(c: Category, session: Session = Depends(get_session)):
    session.add(c)
    session.commit()
    session.refresh(c)
    return c

@app.get("/categories", response_model=List[Category])
def list_categories(session: Session = Depends(get_session)):
    return session.exec(select(Category)).all()

# ========== Transaction endpoints ==========
from pydantic import BaseModel

class SplitIn(BaseModel):
    participant_id: int
    owed_amount: Decimal = None

class PaymentIn(BaseModel):
    payer_id: int
    amount: Decimal

class TransactionIn(BaseModel):
    category_id: int = None
    description: str = None
    event_date: str = None  # ISO date optional
    total_amount: Decimal
    payer_id: int = None
    left: List[SplitIn] = []
    payments: List[PaymentIn] = []

@app.post("/transactions")
def create_transaction(payload: TransactionIn, session: Session = Depends(get_session)):
    # create main transaction record
    if payload.payer_id is None and len(payload.payments) == 0:
        raise HTTPException(status_code=400, detail="Either payer_id or payments must be provided (Right side required).")
    tx = Transaction(
        category_id = payload.category_id,
        description = payload.description,
        event_date = payload.event_date,
        total_amount = payload.total_amount,
        payer_id = payload.payer_id or (payload.payments[0].payer_id if payload.payments else None)
    )
    session.add(tx)
    session.commit()
    session.refresh(tx)
    # create splits
    for s in payload.left:
        sp = Split(transaction_id=tx.id, participant_id=s.participant_id, owed_amount=s.owed_amount)
        session.add(sp)
    # create payments
    for p in payload.payments:
        pay = Payment(transaction_id=tx.id, payer_id=p.payer_id, amount=p.amount)
        session.add(pay)
    session.commit()
    return {"id": tx.id}

@app.get("/transactions")
def list_transactions(session: Session = Depends(get_session)):
    txs = session.exec(select(Transaction)).all()
    results = []
    for t in txs:
        # fetch splits and payments
        splits = session.exec(select(Split).where(Split.transaction_id == t.id)).all()
        payments = session.exec(select(Payment).where(Payment.transaction_id == t.id)).all()
        results.append({
            "id": t.id,
            "category_id": t.category_id,
            "description": t.description,
            "event_date": t.event_date.isoformat() if t.event_date else None,
            "total_amount": t.total_amount,
            "payer_id": t.payer_id,
            "left_rows": [{"participant_id": s.participant_id, "owed_amount": s.owed_amount} for s in splits],
            "payments": [{"payer_id": p.payer_id, "amount": p.amount} for p in payments]
        })
    return results

# ========== Settlement endpoint ==========
@app.get("/settlement")
def settlement(session: Session = Depends(get_session)):
    # For single-user/group scenario: assume all participants are part of single "group".
    participants = session.exec(select(Participant)).all()
    member_ids = [p.id for p in participants]
    txs = list_transactions(session)
    net = compute_group_balance(txs, member_ids)
    settlements = settle(net)
    # Friendly format
    result = {
        "net": {str(k): str(v) for k, v in net.items()},
        "settlements": [{"from": s[0], "to": s[1], "amount": str(s[2])} for s in settlements]
    }
    return result
