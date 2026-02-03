import logging
import time
from typing import Dict, Optional

import pyotp
from SmartApi import SmartConnect

from .base import BaseBroker, OrderResponse

logger = logging.getLogger(__name__)


class AngelOneBroker(BaseBroker):
    def __init__(self, api_key: str, client_id: str, password: str, totp_key: str):
        self.api_key = api_key
        self.client_id = client_id
        self.password = password
        self.totp_key = totp_key
        self.smart_api: Optional[SmartConnect] = None
        self.token_map: Dict[str, str] = {}
        self._load_token_map()

    def _load_token_map(self):
        # NOTE: In a production app, we would fetch the full instrument dump from Angel:
        # https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json
        # For now, we populate common ones. User should provide a mapping file for full reliability.
        self.token_map = {
            "RELIANCE": "2885",
            "TCS": "11536",
            "INFY": "1594",
            "HDFC": "1330",
            "SBIN": "3045",
            "HINDALCO": "1363",
            "TITAN": "3506",
            # Add more as needed
        }

    def connect(self) -> bool:
        try:
            self.smart_api = SmartConnect(api_key=self.api_key)
            totp = pyotp.TOTP(self.totp_key).now()
            data = self.smart_api.generateSession(self.client_id, self.password, totp)
            
            if data['status'] and data['message'] == 'SUCCESS':
                logger.info(f"Connected to Angel One as {self.client_id}")
                return True
            else:
                logger.error(f"Angel Login Failed: {data['message']}")
                return False
        except Exception as e:
            logger.error(f"Angel Connection Error: {e}")
            return False

    def get_token(self, symbol: str) -> Optional[str]:
        # Basic normalization
        sym = symbol.upper().replace("-EQ", "").replace(" EQ", "")
        return self.token_map.get(sym)

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: int,
        price: float = 0.0,
        stop_loss: float = 0.0,
        tag: str = "paper-trading-lab"
    ) -> OrderResponse:
        if not self.smart_api:
            return OrderResponse(order_id="", status="error", message="Not connected")

        token = self.get_token(symbol)
        if not token:
            return OrderResponse(order_id="", status="error", message=f"Token not found for {symbol}")

        try:
            # Angel One Order Params
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": f"{symbol}-EQ",
                "symboltoken": token,
                "transactiontype": side.upper(),
                "exchange": "NSE",
                "ordertype": "MARKET" if price <= 0 else "LIMIT",
                "producttype": "INTRADAY",
                "duration": "DAY",
                "price": str(price) if price > 0 else "0",
                "squareoff": "0",
                "stoploss": "0",
                "quantity": str(qty)
            }

            # If we have a stop loss AND it's a bracket order (ROBO), we'd use that.
            # But SmartAPI 'ROBO' orders are complex. For simplicity, we place a simple order first.
            # Stop loss would ideally be a separate order placed after execution.
            
            logger.info(f"Placing Angel Order: {order_params}")
            order_id = self.smart_api.placeOrder(order_params)
            
            # SmartAPI returns just order ID string on success, or raises exception
            return OrderResponse(order_id=str(order_id), status="success", message="Order placed")
            
        except Exception as e:
            logger.error(f"Order Placement Failed: {e}")
            return OrderResponse(order_id="", status="error", message=str(e))
