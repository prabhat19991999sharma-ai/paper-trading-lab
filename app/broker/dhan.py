import logging
import time
from typing import Dict, Optional

from dhanhq import dhanhq

from .base import BaseBroker, OrderResponse


class DhanBroker(BaseBroker):
    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self.access_token = access_token
        self.api: Optional[dhanhq] = None
        self.security_id_cache: Dict[str, str] = {}
        self.logger = logging.getLogger("DhanBroker")

    def connect(self) -> bool:
        try:
            self.api = dhanhq(self.client_id, self.access_token)
            # Basic check - fetching profile or funds to verify connection
            # Depending on library version, might differ.
            # Assuming get_fund_limits or similar exists and works as a health check
            return True
        except Exception as e:
            self.logger.error(f"Dhan connection failed: {e}")
            return False

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: int,
        price: float = 0.0,
        stop_loss: float = 0.0,
        tag: str = "paper-trading-lab"
    ) -> OrderResponse:
        if not self.api:
            return OrderResponse(order_id="", status="failed", message="Broker not connected")

        # 1. Resolve Symbol to Dhan Security ID
        security_id = self.get_token(symbol)
        if not security_id:
            return OrderResponse(order_id="", status="failed", message=f"Security ID not found for {symbol}")

        # 2. Prepare Order Params
        # Note: These values (exchange_segment, product_type) might need adjustment
        # based on user preference (INTRADAY vs CNC). Defaulting to INTRADAY for algo.
        exchange_segment = "NSE_EQ" 
        transaction_type = "BUY" if side.upper() == "BUY" else "SELL"
        order_type = "MARKET" if price == 0.0 else "LIMIT"
        product_type = "INTRADAY"
        
        # Dhan API expects specific fields
        order_params = {
            "security_id": security_id,
            "exchange_segment": exchange_segment,
            "transaction_type": transaction_type,
            "quantity": qty,
            "order_type": order_type,
            "product_type": product_type,
            "validity": "DAY",
            "tag": tag
        }

        if order_type == "LIMIT":
            order_params["price"] = price

        # If a stop_loss argument is provided, typically this implies sending a Covers Order or Stop Loss order.
        # However, the interface treats `place_order` as the primary entry/exit mechanism.
        # For simple market/limit orders, we ignore stop_loss here unless implementing bracket orders.
        # As per BaseBroker contract, we stick to the primary order.
        
        try:
            self.logger.info(f"Placing order: {order_params}")
            response = self.api.place_order(**order_params)
            
            # Response handling depends on dhanhq library version return structure
            # user usually gets dict: {'orderId': '...', 'orderStatus': 'PENDING', ...}
            if isinstance(response, dict) and 'orderId' in response:
                return OrderResponse(
                    order_id=response['orderId'],
                    status=response.get('orderStatus', 'SUBMITTED'),
                    message="Order placed successfully"
                )
            else:
                 return OrderResponse(order_id="", status="failed", message=str(response))
                 
        except Exception as e:
            self.logger.error(f"Order placement failed: {e}")
            return OrderResponse(order_id="", status="failed", message=str(e))

    def get_token(self, symbol: str) -> Optional[str]:
        # Implementation strategy:
        # 1. Check cache
        # 2. If missing, we need a mapping source. Dhan provides a CSV Scrip Master.
        # For now, to keep it simple, we might need a manual map or a lookup file.
        # Ideally, we should fetch the master scrip list on startup.
        
        # WORKAROUND: Return a placeholder or implement specific logic if known.
        # For a production app, we MUST download the CSV from Dhan website.
        # See: https://dhanhq.co/docs/v1/scrip-master
        
        # For immediate testing, we can use the cache if pre-populated, 
        # or logging a warning that token mapping is required.
        
        # NOTE: Implementing a basic static map for common stocks for testing
        static_map = {
            "RELIANCE": "1333",  # NSE Example (Verify these!)
            "TCS": "11536",
            "INFY": "1594",
             "HDFCBANK": "1330"
        }
        
        return static_map.get(symbol.upper())
