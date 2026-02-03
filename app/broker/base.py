from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class OrderResponse:
    order_id: str
    status: str
    message: Optional[str] = None


class BaseBroker(ABC):
    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: str,
        qty: int,
        price: float = 0.0,
        stop_loss: float = 0.0,
        tag: str = "paper-trading-lab"
    ) -> OrderResponse:
        """
        Place an order.
        side: "BUY" or "SELL"
        price: 0.0 for MARKET order, > 0.0 for LIMIT order
        """
        pass

    @abstractmethod
    def get_token(self, symbol: str) -> Optional[str]:
        """Convert symbol (e.g., RELIANCE) to broker token (e.g., 2885)"""
        pass
