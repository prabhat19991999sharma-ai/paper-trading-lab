"""
Dhan API Client for Historical Data Fetching

Fetches historical OHLCV data from Dhan API with:
- Daily and intraday (1-min) data support
- Automatic pagination for large date ranges
- Local CSV caching to minimize API calls
- Rate limiting and error handling
"""

import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from dhanhq import dhanhq

logger = logging.getLogger("DhanClient")


class DhanHistoricalClient:
    """Client for fetching historical data from Dhan API"""
    
    def __init__(
        self, 
        client_id: str, 
        access_token: str,
        cache_dir: str = "data/backtest_cache",
        rate_limit_delay: float = 0.5
    ):
        """
        Initialize Dhan Historical Data Client
        
        Args:
            client_id: Dhan client ID
            access_token: Dhan access_token (JWT)
            cache_dir: Directory for caching historical data
            rate_limit_delay: Delay in seconds between API requests
        """
        self.client_id = client_id
        self.access_token = access_token
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit_delay = rate_limit_delay
        
        # Initialize Dhan API client
        self.dhan = dhanhq(client_id, access_token)
        
        # Security ID mapping (to be loaded from scrip master or static map)
        self.security_map: Dict[str, str] = {}
        self._load_security_map()
        
    def _load_security_map(self):
        """Load symbol to security ID mapping"""
        # Static mapping for common stocks
        # TODO: Download and parse Dhan scrip master CSV for complete mapping
        self.security_map = {
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
            
            # User's watchlist stocks
            "AXISBANK": "5900",
            "ONGC": "2475",
            "OBEROIRLTY": "20",
            "VOLTAS": "3718",
            "ASHOKALEY": "7",
            "LTFH": "4592",  # L&T Finance Holdings
            "BANKBARODA": "558",
            "MM": "2031",  # Mahindra & Mahindra
            "DELHIVERY": "1171",
            "TORNTPOWER": "3426",
            "UJJIVANSFB": "11184",  # Ujjivan Small Finance Bank
            "WEBELSOLAR": "3753",  # Websol Energy
            "DWARKESH": "1265",  # Dwarikesh Sugar
            "HINDTENMIDC": "1388",  # Hindustan Tinfoll Ind (hindten)
            "THANGAMAYL": "3322",  # Thangamayil Jewellery
            "AXISCADES": "532",
            "V2RETAIL": "11958",
            "CLEARCAP": "1010",  # Embassy Developments
            "STERTOOLS": "11217",  # Sterling Tools
            "KERNEX": "10238",  # Kernex Microsystems
        }
        logger.info(f"Loaded {len(self.security_map)} security mappings")
    
    def get_security_id(self, symbol: str) -> Optional[str]:
        """Get Dhan security ID for a symbol"""
        return self.security_map.get(symbol.upper())
    
    def _cache_path(self, symbol: str, interval: str, start_date: str, end_date: str) -> Path:
        """Get cache file path for historical data"""
        filename = f"{symbol}_{interval}_{start_date}_{end_date}.csv"
        return self.cache_dir / filename
    
    def _load_from_cache(self, cache_path: Path) -> Optional[pd.DataFrame]:
        """Load historical data from cache"""
        if cache_path.exists():
            try:
                df = pd.read_csv(cache_path)
                df['ts'] = pd.to_datetime(df['ts'])
                logger.info(f"Loaded {len(df)} bars from cache: {cache_path.name}")
                return df
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
        return None
    
    def _save_to_cache(self, df: pd.DataFrame, cache_path: Path):
        """Save historical data to cache"""
        try:
            df.to_csv(cache_path, index=False)
            logger.info(f"Cached {len(df)} bars to {cache_path.name}")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
    
    def fetch_historical_intraday(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1",
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Fetch intraday historical data (1-min, 5-min, etc.)
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Candle interval - "1", "5", "15", "25", "60" (minutes)
            use_cache: Use cached data if available
            
        Returns:
            DataFrame with columns: ts, symbol, open, high, low, close, volume
        """
        cache_path = self._cache_path(symbol, f"{interval}min", start_date, end_date)
        
        # Check cache first
        if use_cache:
            cached_df = self._load_from_cache(cache_path)
            if cached_df is not None:
                return cached_df
        
        # Get security ID
        security_id = self.get_security_id(symbol)
        if not security_id:
            logger.error(f"Security ID not found for {symbol}")
            return pd.DataFrame()
        
        # Dhan API limits: 90 days per request for intraday
        # Break into chunks if date range > 90 days
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        all_bars = []
        current_start = start_dt
        
        while current_start < end_dt:
            # Calculate chunk end (90 days or less)
            chunk_end = min(current_start + timedelta(days=89), end_dt)
            
            logger.info(f"Fetching {symbol} from {current_start.date()} to {chunk_end.date()}")
            
            try:
                time.sleep(self.rate_limit_delay)  # Rate limiting
                
                # Use dhanhq library's intraday_minute_data method
                # Parameters: security_id, exchange_segment, instrument_type
                data = self.dhan.intraday_minute_data(
                    security_id=security_id,
                    exchange_segment=self.dhan.NSE,
                    instrument_type=self.dhan.EQUITY
                )
                
                logger.debug(f"API response: {data}")
                
                # Parse response
                if 'data' in data and 'open' in data['data']:
                    df_data = data['data']
                    df = pd.DataFrame({
                        'ts': pd.to_datetime(df_data['timestamp']),
                        'open': df_data['open'],
                        'high': df_data['high'],
                        'low': df_data['low'],
                        'close': df_data['close'],
                        'volume': df_data['volume']
                    })
                    
                    # Filter by date range
                    df['ts'] = pd.to_datetime(df['ts'])
                    df = df[(df['ts'] >= current_start) & (df['ts'] <= chunk_end + timedelta(days=1))]
                    
                    if not df.empty:
                        df['symbol'] = symbol
                        all_bars.append(df)
                        logger.info(f"Fetched {len(df)} bars")
                elif isinstance(data, dict) and ('open' in data or 'o' in data):
                    # Alternative response format
                    df = pd.DataFrame({
                        'ts': pd.to_datetime(data.get('timestamp', data.get('t', [])), unit='s'),
                        'open': data.get('open', data.get('o', [])),
                        'high': data.get('high', data.get('h', [])),
                        'low': data.get('low', data.get('l', [])),
                        'close': data.get('close', data.get('c', [])),
                        'volume': data.get('volume', data.get('v', []))
                    })
                    
                    if not df.empty:
                        df = df[(df['ts'] >= current_start) & (df['ts'] <= chunk_end + timedelta(days=1))]
                        df['symbol'] = symbol
                        all_bars.append(df)
                        logger.info(f"Fetched {len(df)} bars")
                else:
                    logger.warning(f"Unexpected response format: {data}")
                    
            except Exception as e:
                logger.error(f"API request failed: {e}")
            
            # Move to next chunk
            current_start = chunk_end + timedelta(days=1)
        
        # Combine all chunks
        if all_bars:
            result_df = pd.concat(all_bars, ignore_index=True)
            result_df = result_df.sort_values('ts').reset_index(drop=True)
            result_df = result_df.drop_duplicates(subset=['ts'], keep='first')  # Remove duplicates
            result_df = result_df[['ts', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
            
            # Save to cache
            if use_cache:
                self._save_to_cache(result_df, cache_path)
            
            return result_df
        else:
            logger.warning(f"No data fetched for {symbol}")
            return pd.DataFrame()
    
    def fetch_historical_daily(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Fetch daily historical data
        
        Args:
            symbol: Stock symbol
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            use_cache: Use cached data if available
            
        Returns:
            DataFrame with columns: ts, symbol, open, high, low, close, volume
        """
        cache_path = self._cache_path(symbol, "daily", start_date, end_date)
        
        # Check cache
        if use_cache:
            cached_df = self._load_from_cache(cache_path)
            if cached_df is not None:
                return cached_df
        
        security_id = self.get_security_id(symbol)
        if not security_id:
            logger.error(f"Security ID not found for {symbol}")
            return pd.DataFrame()
        
        # Use dhanhq library for daily data
        try:
            time.sleep(self.rate_limit_delay)
            
            # Use historical_daily_data method
            data = self.dhan.historical_daily_data(
                security_id=security_id,
                exchange_segment=self.dhan.NSE,
                instrument_type=self.dhan.EQUITY
            )
            
            logger.debug(f"Daily API response: {data}")
            
            if 'data' in data and isinstance(data['data'], dict):
                df_data = data['data']
                df = pd.DataFrame({
                    'ts': pd.to_datetime(df_data.get('timestamp', [])),
                    'open': df_data.get('open', []),
                    'high': df_data.get('high', []),
                    'low': df_data.get('low', []),
                    'close': df_data.get('close', []),
                    'volume': df_data.get('volume', [])
                })
            elif isinstance(data, dict) and ('open' in data or 'o' in data):
                df = pd.DataFrame({
                    'ts': pd.to_datetime(data.get('timestamp', data.get('t', [])), unit='s'),
                    'open': data.get('open', data.get('o', [])),
                    'high': data.get('high', data.get('h', [])),
                    'low': data.get('low', data.get('l', [])),
                    'close': data.get('close', data.get('c', [])),
                    'volume': data.get('volume', data.get('v', []))
                })
            else:
                logger.warning(f"Unexpected response format: {data}")
                return pd.DataFrame()
            
            if not df.empty:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                df = df[(df['ts'] >= start_dt) & (df['ts'] <= end_dt + timedelta(days=1))]
                df['symbol'] = symbol
                df = df[['ts', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
                
                if use_cache:
                    self._save_to_cache(df, cache_path)
                
                logger.info(f"Fetched {len(df)} daily bars for {symbol}")
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return pd.DataFrame()
