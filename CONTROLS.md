# x402 Music Store — Controls

Self-hosted x402 music store. AI agents (or any wallet) pay **USDC on Base mainnet** to download MP3 tracks.

- **Directory:** `/Users/nate/x402-music-service`
- **Port:** `8001`
- **Payout:** Uphold `0x2B0ce1770bE9af228342ab9dc9B8Bbb615391dC2` (set in `.env` as `EVM_ADDRESS`)
- **Facilitator:** CDP cloud (`https://api.cdp.coinbase.com/platform/v2/x402`), authenticated from the key file at `.keys/cdp_api_key.json`. **There is NO separate local facilitator process — do not start one.**
- **Python:** the project's `.venv` (`.venv/bin/python`, Python 3.13)

> NOTE: Your old notes mention a local uvicorn facilitator on :4022 and a Hermes venv python — both are obsolete. The store uses the CDP cloud facilitator and its own `.venv`.

## Check if it's running
```bash
curl -s -m 5 -o /dev/null -w "store :8001 -> HTTP %{http_code}\n" http://localhost:8001/
```
- `402` = running and serving payment challenges (expected — not an error)
- `000` = not running

Health / free routes:
```bash
curl -s -m 5 -o /dev/null -w "health  -> %{http_code}\n" http://localhost:8001/health
curl -s -m 5 -o /dev/null -w "catalog -> %{http_code}\n" http://localhost:8001/catalog
curl -s -m 5 -o /dev/null -w "track   -> %{http_code}\n" http://localhost:8001/track/suno-songs/seaside-ae0d960b.mp3
# 402 on /track/* = paywall working
```

## Start (foreground — leave terminal open)
```bash
cd /Users/nate/x402-music-service
/Users/nate/x402-music-service/.venv/bin/python server.py
```
Expected banner:
```
🎵 Starting Nate's Music Store on port 8001
💰 Receiving payments to: 0x2B0ce1770bE9af228342ab9dc9B8Bbb615391dC2
🔧 Using facilitator at: https://api.cdp.coinbase.com/platform/v2/x402 (CDP mainnet)
📊 Total tracks available: 330
INFO:     Uvicorn running on http://0.0.0.0:8001
```

## Start (background — survives terminal close)
```bash
cd /Users/nate/x402-music-service
nohup /Users/nate/x402-music-service/.venv/bin/python server.py > /tmp/music-store.log 2>&1 &
echo "PID: $!"
tail -f /tmp/music-store.log
```

## Expose publicly (ngrok — separate terminal)
```bash
ngrok http 8001
```
- Free tier URL rotates on every restart (e.g. `https://xxxx.ngrok-free.dev`).
- Test: `curl -s -m 5 -o /dev/null -w "%{http_code}\n" https://YOUR-URL.ngrok-free.dev/`
- Update the Live demo link on PR xpaysh/awesome-x402#867 when it changes, or deploy to a static host for a stable URL.

## Stop
```bash
lsof -ti :8001 | xargs kill        # by port (no sudo; it's your process)
pkill -f "server.py"               # by process name
```

## Restart (clean)
```bash
lsof -ti :8001 | xargs kill 2>/dev/null
sleep 1
cd /Users/nate/x402-music-service
nohup /Users/nate/x402-music-service/.venv/bin/python server.py > /tmp/music-store.log 2>&1 &
```

## Test a real purchase (testnet, free)
`buyer_test.py` is an example x402 client. The same server code runs on Base Sepolia with the `x402.org` testnet facilitator (no CDP key) — fund a test wallet from the Base Sepolia faucet, set `FACILITATOR_URL=https://x402.org/facilitator` and `NETWORK=eip155:84532`, and run:
```bash
EVM_PRIVATE_KEY=<test_wallet_key> \
/Users/nate/x402-music-service/.venv/bin/python buyer_test.py
```
Mainnet purchase needs a buyer wallet holding real Base USDC.

## Links
- Repo: https://github.com/Nateateeight/x402-music-store
- Awesome x402 PR: https://github.com/xpaysh/awesome-x402/pull/867
