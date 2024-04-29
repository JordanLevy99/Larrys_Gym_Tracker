from dataclasses import dataclass
from datetime import datetime


@dataclass
class Transaction:
    user_id: int
    symbol: str
    transaction_type: str
    quantity: int
    price: float
    transaction_date: datetime = None
    transaction_id: int = None
