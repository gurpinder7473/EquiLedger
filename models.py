from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime, date
from decimal import Decimal

# ============== Participants ==============
class ParticipantBase(SQLModel):
    name: str

class Participant(ParticipantBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ============== Categories ==============
class CategoryBase(SQLModel):
    label: str

class Category(CategoryBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ============== Transactions ==============
class TransactionBase(SQLModel):
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    description: Optional[str] = None
    event_date: Optional[date] = None
    total_amount: Decimal

class Transaction(TransactionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    payer_id: int = Field(foreign_key="participant.id")  # Right side (who actually paid) - not null
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ============== Splits (Left side) ==============
class SplitBase(SQLModel):
    participant_id: int
    owed_amount: Decimal  # explicit amount; if not provided, UI/backend calculates equal share

class Split(SplitBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    transaction_id: int = Field(foreign_key="transaction.id")

# ============== Payments (Right breakdown if multiple payers) ==============
class PaymentBase(SQLModel):
    payer_id: int
    amount: Decimal

class Payment(PaymentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    transaction_id: int = Field(foreign_key="transaction.id")
    paid_at: datetime = Field(default_factory=datetime.utcnow)
