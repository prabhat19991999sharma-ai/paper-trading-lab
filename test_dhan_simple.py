#!/usr/bin/env python3
"""Test basic Dhan API connectivity"""

from dhanhq import dhanhq
from app.config import CONFIG

# Initialize client
dhan = dhanhq(CONFIG.dhan_client_id, CONFIG.dhan_access_token)

print("Testing Dhan API Basic Connectivity...")
print(f"Client ID: {CONFIG.dhan_client_id}")
print(f"Token (first 50 chars): {CONFIG.dhan_access_token[:50]}...")

# Try the simplest API call - get fund limits
print("\n🔍 Testing fund limits API (simplest call)...")
try:
    funds = dhan.get_fund_limits()
    print(f"✓ Success!")
    print(f"Response type: {type(funds)}")
    if isinstance(funds, dict):
        print(f"Keys: {list(funds.keys())}")
        for key, value in funds.items():
            print(f"  {key}: {value}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Try to get holdings
print("\n📊 Testing holdings API...")
try:
    holdings = dhan.get_holdings()
    print(f"✓ Success!")
    print(f"Response type: {type(holdings)}")
    if isinstance(holdings, list):
        print(f"Number of holdings: {len(holdings)}")
    elif isinstance(holdings, dict):
        print(f"Keys: {list(holdings.keys())}")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n💡 If all APIs fail with 'Invalid Token', the token might be:")
print("   1. Expired or not yet active")
print("   2. For a different environment (sandbox vs production)")
print("   3. Missing required permissions for data APIs")
print("   4. Requires IP whitelisting")
print("\n   Please verify on Dhan's dashboard that the token is valid")
print("   and has permissions for historical data APIs")
