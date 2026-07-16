# Nate's x402 Music Store

A self-hosted **x402** music store: AI agents (or anyone with a wallet) pay **USDC on Base mainnet** to download MP3 tracks. Built with [x402](https://github.com/coinbase/x402) + FastAPI, settled through the **Coinbase CDP facilitator**, payouts to a Uphold address.

> The HTTP 402 "Payment Required" status code, reborn for blockchain micropayments. Agents hit a track URL, get a signed payment challenge, pay $0.25 USDC, and receive the file — no accounts, no signup.

## How it works

- `server.py` serves 330 tracks from a local music directory.
- Protected routes (`/`, `/track/*`) return `402 Payment Required` with an x402 payment challenge (`/.well-known/x402.json` discovery manifest).
- A buyer wallet (any x402 client) signs a USDC EIP-3009 `transferWithAuthorization` to the payTo address; the CDP facilitator verifies + settles on-chain; the server serves the MP3.
- Payouts land at the merchant's Uphold address on Base mainnet.

## Requirements

- Python 3.13 + `uv`
- A Base-mainnet EVM address for payouts (`EVM_ADDRESS`)
- CDP API key (JSON) for the mainnet facilitator — `CDP_API_KEY_PATH`
- A music directory (`MUSIC_DIR`, default `/Users/nate/Music_Library`)
- A public URL (ngrok / tunnel / static host) so agents can reach it

## Run

```bash
uv venv && uv pip install -r requirements.txt   # or: pip install -e .
source .venv/bin/activate
cp .env.example .env   # fill EVM_ADDRESS + CDP_API_KEY_PATH
python server.py       # listens on :8001
```

Expose it: `ngrok http 8001` (or any tunnel / static host).

## Test a purchase (free, testnet)

The same server code runs on Base Sepolia with the `x402.org` testnet facilitator — no CDP key needed. Set `FACILITATOR_URL=https://x402.org/facilitator` and `NETWORK=eip155:84532`, fund a test wallet from the Base Sepolia faucet, and use `buyer_test.py` to complete a full buy→settle→serve cycle with zero real money. The end-to-end flow is verified on testnet; mainnet is a one-line network flip once a wallet holds real USDC.

## Files

- `server.py` — FastAPI app + x402 payment middleware
- `buyer_test.py` — example x402 client that purchases a track
- `.env.example` — required env vars

## Notes

- This is a real, working x402 store. Mainnet purchases require a buyer wallet funded with Base USDC.
- The merchant payout address is a self-custody Uphold deposit address on Base.
- Discovery: agents can list the catalog via `/catalog` (free) and the payment manifest at `/.well-known/x402.json`.
