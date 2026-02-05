import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from app.config import CONFIG
from app.broker.dhan import DhanBroker

def main():
    print("--- DhanHQ Connection Test ---")
    
    # Check if credentials are set
    if not CONFIG.dhan_client_id or not CONFIG.dhan_access_token:
        print("[!] Credentials missing in app/config.py")
        print("    Please set 'dhan_client_id' and 'dhan_access_token'.")
        return

    print(f"Client ID: {CONFIG.dhan_client_id}")
    print("Access Token: " + "*" * 10 + CONFIG.dhan_access_token[-4:])
    
    broker = DhanBroker(CONFIG.dhan_client_id, CONFIG.dhan_access_token)
    
    print("\nConnecting...")
    if broker.connect():
        print("[+] Connection SUCCESSFUL!")
        try:
            # Try to fetch some data if possible, or just confirm object state
            print("    Broker object initialized and ready.")
        except Exception as e:
            print(f"[!] Error during post-connection check: {e}")
    else:
        print("[-] Connection FAILED.")

if __name__ == "__main__":
    main()
