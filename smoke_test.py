
import sys
import os

print("🔥 Starting Smoke Test...")

try:
    print("1. Testing Imports...")
    from app.config import CONFIG
    print(f"   Config loaded. Broker: {CONFIG.broker_name}")
    
    from app.broker.dhan import DhanBroker
    print("   DhanBroker imported.")
    
    from app.live_engine import LiveEngine
    print("   LiveEngine imported.")
    
    print("2. Testing DhanHQ Dependency...")
    import dhanhq
    print("   dhanhq imported successfully.")

    print("3. Testing App Initialization...")
    from app.main import app
    print("   FastAPI app object created.")
    
    print("✅ BACKEND SMOKE TEST PASSED")
    
except ImportError as e:
    print(f"❌ IMPORT ERROR: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ RUNTIME ERROR: {e}")
    sys.exit(1)
