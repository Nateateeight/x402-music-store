import os
import glob
from fastapi import FastAPI, Response, HTTPException, Path, Request
from fastapi.middleware.cors import CORSMiddleware
from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServer
from cdp.x402 import create_facilitator_config
from dotenv import load_dotenv

load_dotenv()

# Configuration
EVM_ADDRESS = os.getenv("EVM_ADDRESS")
# CDP mainnet facilitator (supports eip155:8453 exact). Key loaded from JSON file.
CDP_KEY_PATH = os.getenv("CDP_API_KEY_PATH", "/Users/nate/Downloads/cdp_api_key.json")
MUSIC_DIR = "/Users/nate/Music_Library"

if not EVM_ADDRESS:
    raise RuntimeError("EVM_ADDRESS must be set in .env")

# Pre-load list of available tracks (relative paths from MUSIC_DIR)
AVAILABLE_TRACKS = {}
for root, dirs, files in os.walk(MUSIC_DIR):
    for file in files:
        if file.lower().endswith('.mp3'):
            # Store the relative path from MUSIC_DIR as the key
            rel_path = os.path.relpath(os.path.join(root, file), MUSIC_DIR)
            # Use the relative path as the key for the URL
            AVAILABLE_TRACKS[rel_path] = os.path.join(root, file)

if not AVAILABLE_TRACKS:
    raise RuntimeError(f"No MP3 files found in {MUSIC_DIR}")

# Initialize x402 protection with CDP mainnet facilitator (authenticated)
import json
with open(CDP_KEY_PATH) as _f:
    _cdp = json.load(_f)
_cdp_cfg = create_facilitator_config(_cdp["id"], _cdp["privateKey"])
# x402's HTTPFacilitatorClient accepts a dict with url + create_headers
facilitator = HTTPFacilitatorClient({
    "url": _cdp_cfg["url"],
    "create_headers": _cdp_cfg["create_headers"],
})
server = x402ResourceServer(facilitator)
server.register("eip155:8453", ExactEvmServerScheme())  # Base mainnet

# Define routes - only those that require x402 protection
routes = {
    "GET /": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact",
                pay_to=EVM_ADDRESS,
                price="$0.01",  # small amount to require payment
                network="eip155:8453",
            )
        ],
        mime_type="application/json",
        description="Homepage",
    ),
    "GET /track/*": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact",
                pay_to=EVM_ADDRESS,
                price="$0.25",  # 25 cents per track
                network="eip155:8453",
            )
        ],
        mime_type="audio/mpeg",
        description="Full music track",
    ),
    "GET /preview/*": RouteConfig(
        accepts=[],  # No protection needed for preview
        mime_type="audio/mpeg",
        description="30-second preview",
    ),
}

app = FastAPI(title="Nate's Music Store")

# Add CORS middleware to allow browser requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)

@app.get("/")
def root():
    return {
        "message": "Welcome to Nate's Music Store",
        "total_tracks": len(AVAILABLE_TRACKS),
        "sample_tracks": list(AVAILABLE_TRACKS.keys())[:5],
        "endpoints": {
            "catalog": "/catalog - List all available tracks",
            "preview": "/preview/*filepath - Free 30-second sample",
            "track": "/track/*filepath - Full track ($0.25)",
            "health": "/health - Service status",
        },
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/catalog")
def catalog():
    """Return a list of all available tracks (relative paths)."""
    # Return sorted list for consistency
    return {"tracks": sorted(AVAILABLE_TRACKS.keys())}

@app.get("/track/{filepath:path}")
def get_track(filepath: str = Path(...)):
    # Security: only allow files within MUSIC_DIR
    # Join and then check that the resolved path is still within MUSIC_DIR
    requested_path = os.path.normpath(os.path.join(MUSIC_DIR, filepath))
    if not requested_path.startswith(os.path.abspath(MUSIC_DIR)):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if filepath not in AVAILABLE_TRACKS:
        raise HTTPException(status_code=404, detail="Track not found")
    full_path = AVAILABLE_TRACKS[filepath]
    try:
        with open(full_path, "rb") as f:
            content = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return Response(content=content, media_type="audio/mpeg")

@app.get("/preview/{filepath:path}")
def get_preview(filepath: str = Path(...)):
    # Security: only allow files within MUSIC_DIR
    requested_path = os.path.normpath(os.path.join(MUSIC_DIR, filepath))
    if not requested_path.startswith(os.path.abspath(MUSIC_DIR)):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if filepath not in AVAILABLE_TRACKS:
        raise HTTPException(status_code=404, detail="Track not found")
    full_path = AVAILABLE_TRACKS[filepath]
    preview_path = f"/tmp/preview_{filepath.replace('/', '_')}"
    # Generate 30-second preview if not already cached
    if not os.path.exists(preview_path):
        cmd = f'ffmpeg -y -i "{full_path}" -t 30 -ac 1 -ab 64k "{preview_path}" >/dev/null 2>&1'
        result = os.system(cmd)
        if result != 0:
            raise HTTPException(status_code=500, detail="Failed to generate preview")
    try:
        with open(preview_path, "rb") as f:
            content = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return Response(content=content, media_type="audio/mpeg")

# --- x402 discovery manifest (lets agents/crawlers find the store) ---
MANIFEST = {
    "version": 1,
    "kind": "x402-manifest",
    "conformsTo": ["x402"],
    "network": "eip155:8453",
    "payTo": EVM_ADDRESS,
    "schemes": ["exact"],
    "expires": "2027-07-16T00:00:00Z",
    "paths": {
        "/": {
            "kind": "x402-payment",
            "amount": "$0.01",
            "asset": "USDC",
            "network": "eip155:8453",
            "payTo": EVM_ADDRESS,
            "mimeType": "application/json",
            "description": "Store homepage + track catalog",
        },
        "/track/{filepath}": {
            "kind": "x402-payment",
            "amount": "$0.25",
            "asset": "USDC",
            "network": "eip155:8453",
            "payTo": EVM_ADDRESS,
            "mimeType": "audio/mpeg",
            "description": "Full music track download",
        },
        "/preview/{filepath}": {
            "kind": "free",
            "mimeType": "audio/mpeg",
            "description": "30-second preview (no payment)",
        },
    },
}


@app.get("/.well-known/x402.json")
def x402_manifest():
    return MANIFEST


# ---------------------------------------------------------------------------
# the402 webhook receiver
# the402 POSTs purchase/settlement events here, signed with your Svix secret
# (whsec_...). We verify the signature before trusting the payload.
# ---------------------------------------------------------------------------
import hashlib
import hmac
import base64
import json as _json

WEBHOOK_SECRET = os.getenv("THE402_WEBHOOK_SECRET", "")  # whsec_...


def _verify_svix_sig(payload: bytes, header_sig: str, timestamp: str) -> bool:
    """Verify a Svix-style webhook signature (HMAC-SHA256, base64)."""
    if not WEBHOOK_SECRET or not header_sig:
        return False
    key = base64.b64decode(WEBHOOK_SECRET.replace("whsec_", ""))
    msg = f"{timestamp}.".encode() + payload
    expected = hmac.new(key, msg, hashlib.sha256).digest()
    got = base64.b64decode(header_sig)
    return hmac.compare_digest(expected, got)


@app.post("/webhook")
async def the402_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("webhook-signature", "")
    ts = request.headers.get("webhook-timestamp", "")
    # Svix format: "v1,<base64sig>"
    sig_part = sig.split(",")[-1] if sig else ""
    # If the402 sends no signature (health/test ping), accept it (don't 401).
    # Only enforce verification when a signature header is actually present.
    if sig_part and not _verify_svix_sig(body, sig_part, ts):
        print(f"[webhook] bad signature; payload: {body[:200]}")
        from fastapi import status
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bad signature")
    event = _json.loads(body) if body else {}
    print(f"[webhook] event: {event.get('type')} -> {_json.dumps(event)[:300]}")
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    import traceback
    port = int(os.getenv("PORT", "8001"))
    print(f"🎵 Starting Nate's Music Store on port {port}")
    print(f"💰 Receiving payments to: {EVM_ADDRESS or 'NOT SET'}")
    print(f"🔧 Using facilitator at: {_cdp_cfg['url']} (CDP mainnet)")
    print(f"📁 Music library: {MUSIC_DIR}")
    print(f"📊 Total tracks available: {len(AVAILABLE_TRACKS)}")
    try:
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        print(f"💥 Server error: {e}")
        traceback.print_exc()