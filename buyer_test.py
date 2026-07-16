#!/usr/bin/env python3
"""Live x402 purchase test against the running music store.

Uses the source wallet (0x2bEa...) as the buyer. It has ETH for gas but
no USDC, so this proves the full handshake and isolates the funding gap.
"""
import asyncio, os, sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from eth_account import Account
from web3 import Web3

from x402.client import x402Client
from x402.mechanisms.evm import EthAccountSignerWithRPC
from x402.mechanisms.evm.exact import ExactEvmScheme
from x402.http.clients.httpx import wrapHttpxWithPayment

STORE = os.getenv("STORE_URL", "https://exalted-curing-bulginess.ngrok-free.dev")
TRACK = os.getenv("TRACK", "suno-songs/seaside-ae0d960b.mp3")
RPC = os.getenv("BASE_RPC", "https://mainnet.base.org")

def main():
    key = os.getenv("EVM_PRIVATE_KEY")
    if not key:
        print("EVM_PRIVATE_KEY not set"); sys.exit(1)
    acct = Account.from_key(key)
    print(f"Buyer wallet: {acct.address}")

    # signer with RPC so it can read USDC balance/allowance + estimate gas
    signer = EthAccountSignerWithRPC(acct, RPC)
    client = x402Client()
    client.register("eip155:8453", ExactEvmScheme(signer))

    url = f"{STORE}/track/{TRACK}"
    print(f"Attempting: {url}")

    async def run():
        http = wrapHttpxWithPayment(client, timeout=30)
        try:
            resp = await http.get(url)
            print(f"FINAL STATUS: {resp.status_code}")
            print(f"BODY (first 200): {resp.text[:200]!r}")
            if resp.status_code == 200:
                print("SUCCESS: payment settled, got the file.")
            else:
                print("Non-200 — payment did not complete.")
        except Exception as e:
            print(f"EXCEPTION: {type(e).__name__}: {e}")
        finally:
            await http.aclose()

    asyncio.run(run())

if __name__ == "__main__":
    main()
