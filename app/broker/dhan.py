import logging
import time
from typing import Dict, List, Optional

from dhanhq import dhanhq, marketfeed

from .base import BaseBroker, OrderResponse


class DhanBroker(BaseBroker):
    """Dhan broker integration for live trading"""
    
    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self.access_token = access_token
        self.api: Optional[dhanhq] = None
        self.logger = logging.getLogger("DhanBroker")
        
        # Import security map from dhan_client
        self.security_map = self._load_security_map()

    def _load_security_map(self) -> Dict[str, str]:
        """Load security ID mapping"""
        # Full mapping including all watchlist stocks
        return {
            # Original stocks
            "RELIANCE": "1333",
            "TCS": "11536",
            "INFY": "1594",
            "HDFCBANK": "1330",
            "ICICIBANK": "4963",
            "HINDUNILVR": "1394",
            "SBIN": "3045",
            "BHARTIARTL": "582",
            "ITC": "1660",
            "KOTAKBANK": "1922",
            
            # Watchlist stocks
            "AXISBANK": "5900",
            "ONGC": "2475",
            "OBEROIRLTY": "20",
            "VOLTAS": "3718",
            "ASHOKALEY": "7",
            "LTFH": "4592",
            "BANKBARODA": "558",
            "MM": "2031",
            "DELHIVERY": "1171",
            "TORNTPOWER": "3426",
            "UJJIVANSFB": "11184",
            "WEBELSOLAR": "3753",
            "DWARKESH": "1265",
            "HINDTENMIDC": "1388",
            "THANGAMAYL": "3322",
            "AXISCADES": "532",
            "V2RETAIL": "11958",
            "CLEARCAP": "1010",
            "STERTOOLS": "11217",
            "KERNEX": "10238",
            "SWSOLAR": "3753",  # Alias for WEBELSOLAR
            "DAVANGERE": "1173",
            "HINDALCO": "535",
            "IRCTC": "13611",
            "SILVERTUC": "3062",
            "TMB": "3326",
            "ASHOKLEY": "7",  # Alias
            "LICHSGFIN": "1997",
            "LTF": "4592",  # Alias for LTFH
            "SHRINGARMS": "10641",
            "DBREALTY": "1151",
            "MOTILALOFS": "2288",
            "TRIL": "11716",
            "MIDWESTLTD": "2248",
            "ATL": "11661",
            "SMLISUZU": "10787",
            "EMBDL": "1010",  # Alias for CLEARCAP
            "RBLBANK": "2674",
            "KAPSTON": "10059",
            "NMDCSTEEL": "11872",
            "SHRIRAMFIN": "3153"
        }

    def connect(self) -> bool:
        """Connect to Dhan API"""
        try:
            self.api = dhanhq(self.client_id, self.access_token)
            self.logger.info("Dhan API connected successfully")
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
        tag: str = "algo-trading"
    ) -> OrderResponse:
        """Place order on Dhan"""
        if not self.api:
            return OrderResponse(order_id="", status="failed", message="Broker not connected")

        # Get security ID
        security_id = self.get_token(symbol)
        if not security_id:
            return OrderResponse(order_id="", status="failed", message=f"Security ID not found for {symbol}")

        # Prepare order parameters
        transaction_type = marketfeed.BUY if side.upper() == "BUY" else marketfeed.SELL
        order_type = marketfeed.MARKET if price == 0.0 else marketfeed.LIMIT
        
        try:
            self.logger.info(f"Placing {side} order: {symbol} ({security_id}), Qty: {qty}, Price: {price}")
            
            # Place order using dhanhq library
            response = self.api.place_order(
                security_id=security_id,
                exchange_segment=marketfeed.NSE,
                transaction_type=transaction_type,
                quantity=qty,
                order_type=order_type,
                product_type=marketfeed.INTRA,  # Intraday
                price=price if order_type == marketfeed.LIMIT else 0,
                tag=tag
            )
            
            # Parse response
            if isinstance(response, dict):
                if response.get('status') == 'success':
                    order_id = response.get('data', {}).get('orderId', '')
                    return OrderResponse(
                        order_id=str(order_id),
                        status="submitted",
                        message="Order placed successfully"
                    )
                else:
                    error_msg = response.get('remarks', {}).get('error_message', str(response))
                    return OrderResponse(order_id="", status="failed", message=error_msg)
            else:
                return OrderResponse(order_id="", status="failed", message=str(response))
                
        except Exception as e:
            self.logger.error(f"Order placement failed: {e}")
            return OrderResponse(order_id="", status="failed", message=str(e))

    def get_token(self, symbol: str) -> Optional[str]:
        """Get security ID for symbol"""
        return self.security_map.get(symbol.upper())
    
    def get_order_status(self, order_id: str) -> dict:
        """Get status of an order"""
        if not self.api:
            return {"status": "error", "message": "Not connected"}
        
        try:
            response = self.api.get_order_by_id(order_id)
            return response
        except Exception as e:
            self.logger.error(f"Failed to get order status: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_positions(self) -> List[dict]:
        """Get current positions"""
        if not self.api:
            return []
        
        try:
            response = self.api.get_positions()
            if isinstance(response, dict) and response.get('status') == 'success':
                return response.get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"Failed to get positions: {e}")
            return []

    def get_funds(self) -> float:
        """Get available funds from Dhan API"""
        if not self.api:
            return 0.0
        
        try:
            response = self.api.get_fund_limits()
            if isinstance(response, dict) and response.get('status') == 'success':
                data = response.get('data', {})
                return float(data.get('availabelBalance', 0.0))
            return 0.0
        except Exception as e:
            self.logger.error(f"Failed to get funds: {e}")
            return 0.0
    
    def get_orders(self) -> List[dict]:
        """Get all orders for the day"""
        if not self.api:
            return []
        
        try:
            response = self.api.get_order_list()
            if isinstance(response, dict) and response.get('status') == 'success':
                return response.get('data', [])
            return []
        except Exception as e:
            self.logger.error(f"Failed to get orders: {e}")
            return []
