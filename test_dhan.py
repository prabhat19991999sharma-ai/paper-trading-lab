from dhanhq import dhanhq
from app.config import CONFIG
from datetime import datetime, timedelta

# Initialize client
dhan = dhanhq(CONFIG.dhan_client_id, CONFIG.dhan_access_token)

print("Testing Dhan API...")
print(f"Client ID: {CONFIG.dhan_client_id}")

# Date range
to_date = datetime.now().strftime("%Y-%m-%d")
from_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

# Test intraday data for RELIANCE (security_id: 1333)
print(f"\n📊 Fetching intraday data for RELIANCE (1333)...")
print(f"Date range: {from_date} to {to_date}")
try:
    data = dhan.intraday_minute_data(
        security_id="1333",
        exchange_segment=dhan.NSE,
        instrument_type="EQUITY",
        from_date=from_date,
        to_date=to_date
    )
    print(f"✓ Response received")
    print(f"Type: {type(data)}")
    if isinstance(data, dict):
        print(f"Keys: {list(data.keys())}")
        for key, value in list(data.items()):
            if isinstance(value, (list, tuple)):
                print(f"  {key}: {type(value).__name__} with {len(value)} items")
                if value and len(value) > 0:
                    print(f"    First item: {value[0]}")
            else:
                print(f"  {key}: {value}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print(f"\n📈 Fetching historical daily data for RELIANCE (1333)...")
try:
    data = dhan.historical_daily_data(
        security_id="1333",
        exchange_segment=dhan.NSE,
        instrument_type="EQUITY",
        from_date=from_date,
        to_date=to_date
    )
    print(f"✓ Response received  ")
    print(f"Type: {type(data)}")
    if isinstance(data, dict):
        print(f"Keys: {list(data.keys())}")
        for key, value in list(data.items()):
            if isinstance(value, (list, tuple)):
                print(f"  {key}: {type(value).__name__} with {len(value)} items")
            else:
                print(f"  {key}: {value}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
