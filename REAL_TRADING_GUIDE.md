# 💰 Real Money Trading Guide (Angel One)

> [!CAUTION]
> **RISK WARNING**: Enabling Real Trading will place **ACTUAL ORDERS** on your Angel One account.
> Use at your own risk. Start with minimal quantity.

## 1. Prerequisites
- **Angel One Account**: You need an active trading account.
- **SmartAPI Key**: Create one at [smartapi.angelbroking.com](https://smartapi.angelbroking.com/)
- **TOTP Enabled**: Ensure you have TOTP (Google Authenticator) enabled on your Angel account.

## 2. Configuration
You must provide your credentials via environment variables to enable Real Mode.

Create a `.env` file (or set variables in your terminal/cloud settings):

```bash
# Enable Real Trading (Default is "paper")
BROKER_NAME="angel-one"

# Angel One Credentials
ANGEL_API_KEY="your_api_key_here"
ANGEL_CLIENT_ID="your_client_id_here"  # e.g., P123456
ANGEL_PASSWORD="your_pin_or_password"
ANGEL_TOTP_KEY="your_totp_secret_key"  # From Google Auth setup
```

## 3. How to Run
### Local
```bash
# Export variables and run (or use .env file)
export BROKER_NAME="angel-one"
export ANGEL_API_KEY="..."
# ... export others ...

uvicorn app.main:app --reload
```

### Cloud (Render.com)
1. Go to your **Dashboard** > **Environment Variables**.
2. Add the variables listed above.
3. Redeploy.

## 4. Verification
- Open the dashboard.
- Look at the top right header.
- **Paper Mode**: Badge says "Paper" (Grey).
- **Real Mode**: Badge says "Active" (Green).
- Check the **Logs** tab (or terminal) for "Broker connected successfully".

## 5. Safety Features
- **Quantity Limits**: The app respects `max_position_pct` and `max_daily_loss` from `app/config.py`.
- **Token Mapping**: Currently maps ~10 major stocks (RELIANCE, INFY, etc.).
  - *Edit `app/broker/angel_one.py` to add more mapped tokens if needed.*
