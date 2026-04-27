from flask import Flask, render_template, request, jsonify
import requests
import os
import base64
import datetime
import re
import unicodedata
from urllib.parse import urlencode
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

app = Flask(__name__)

KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"
KALSHI_KEY_ID = "9b4644d1-e5ca-4546-930f-c7593c082612"

KALSHI_PRIVATE_KEY_PEM = """-----BEGIN PRIVATE KEY-----
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
aO7NnY/dGGakunE63QxAYmorUTZg
-----END PRIVATE KEY-----"""

def load_private_key():
    key_pem = os.environ.get("KALSHI_PRIVATE_KEY", KALSHI_PRIVATE_KEY_PEM)
    return serialization.load_pem_private_key(
        key_pem.strip().encode(), password=None, backend=default_backend()
    )

def sign_pss(private_key, text: str) -> str:
    message = text.encode('utf-8')
    signature = private_key.sign(
        message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')

def kalshi_headers(method: str, path: str):
    key_id = os.environ.get("KALSHI_KEY_ID", KALSHI_KEY_ID)
    ts = str(int(datetime.datetime.now().timestamp() * 1000))
    path_no_query = path.split('?')[0]
    msg = ts + method.upper() + path_no_query
    sig = sign_pss(load_private_key(), msg)
    return {
        'KALSHI-ACCESS-KEY': key_id,
        'KALSHI-ACCESS-SIGNATURE': sig,
        'KALSHI-ACCESS-TIMESTAMP': ts,
        'Content-Type': 'application/json'
    }

def normalize(s):
    return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode().lower()

def fetch_all_markets():
    all_markets = []
    cursor = None
    pages = 0
    while pages < 5:
        path = "/trade-api/v2/markets"
        params = {"limit": 200, "status": "open"}
        if cursor:
            params["cursor"] = cursor
        full_url = f"{KALSHI_BASE}/markets?{urlencode(params)}"
        resp = requests.get(full_url, headers=kalshi_headers("GET", path), timeout=15)
        if not resp.ok:
            raise Exception(f"Kalshi error {resp.status_code}: {resp.text[:300]}")
        resp_data = resp.json()
        markets = resp_data.get("markets", [])
        all_markets.extend(markets)
        cursor = resp_data.get("cursor")
        pages += 1
        if not cursor or not markets:
            break
    return all_markets

@app.route("/")
def index():
    return render_template("index.html")

# Debug endpoint — shows raw market titles so we can see exact format
@app.route("/api/kalshi/debug", methods=["POST"])
def debug_markets():
    data = request.json
    search = data.get("search", "jamal").lower()
    try:
        all_markets = fetch_all_markets()
        matches = []
        for m in all_markets:
            title = m.get("title", "")
            subtitle = m.get("subtitle", "")
            ticker = m.get("ticker", "")
            event_ticker = m.get("event_ticker", "")
            if search in normalize(title + subtitle + ticker + event_ticker):
                matches.append({
                    "title": title,
                    "subtitle": subtitle,
                    "ticker": ticker,
                    "event_ticker": event_ticker,
                    "yes_bid": m.get("yes_bid"),
                    "yes_ask": m.get("yes_ask"),
                    "last_price": m.get("last_price"),
                })
        return jsonify({"count": len(matches), "markets": matches[:30]})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/kalshi/markets", methods=["POST"])
def get_markets():
    data = request.json
    search = data.get("search", "").lower().strip()

    try:
        all_markets = fetch_all_markets()

        # Search filter with normalization for accented chars
        if search:
            filtered = [m for m in all_markets if
                search in normalize(m.get("title","") + m.get("subtitle","") + m.get("event_ticker",""))
                or search in (m.get("title","") + m.get("subtitle","") + m.get("event_ticker","")).lower()
            ]
        else:
            # Default: show all markets that look like player props
            filtered = [m for m in all_markets if re.search(r':\s*\d+\+', m.get("title",""))]

        # Group by player — try multiple title formats
        grouped = {}
        NON_POINTS = ["assist", "rebound", "three", "3pt", "3-pt", "block",
                      "steal", "turnover", "fg", "ft", "minute", "double",
                      "triple", "quarter", "half", "spread", "moneyline"]

        for m in filtered:
            title = m.get("title", "").strip()
            subtitle = m.get("subtitle", "").strip()

            # Skip non-points props
            combined = (title + subtitle).lower()
            if any(w in combined for w in NON_POINTS):
                continue

            # Try to extract player name and threshold from title
            # Format 1: "Jamal Murray: 25+" 
            # Format 2: "yes Jamal Murray: 3+,yes Tobias..." (parlay/combo — skip)
            # Format 3: "Timberwolves at Nuggets: Points" with subtitle "Jamal Murray: 25+"

            player_name = None
            threshold = None

            # Check subtitle first (often cleaner)
            for text in [subtitle, title]:
                m2 = re.match(r'^([A-Z][a-zA-Zéèêëàâäîïôùûüç\'\-\. ]+):\s*(\d+)\+\s*$', text.strip())
                if m2:
                    candidate = m2.group(1).strip()
                    # Make sure it looks like a person name (2+ words, not too long)
                    words = candidate.split()
                    if 2 <= len(words) <= 4 and len(candidate) < 40:
                        player_name = candidate
                        threshold = int(m2.group(2))
                        break

            if not player_name or threshold is None:
                continue
            if threshold < 5 or threshold > 75:
                continue

            ticker = m.get("event_ticker", m.get("ticker", ""))
            if player_name not in grouped:
                grouped[player_name] = {"name": player_name, "event_ticker": ticker, "props": []}

            yes_bid = m.get("yes_bid", 0) or 0
            yes_ask = m.get("yes_ask", 0) or 0
            last_price = m.get("last_price", 0) or 0

            if isinstance(yes_bid, str): yes_bid = int(float(yes_bid) * 100)
            if isinstance(yes_ask, str): yes_ask = int(float(yes_ask) * 100)
            if isinstance(last_price, str): last_price = int(float(last_price) * 100)

            if yes_bid == 0 and yes_ask == 0 and last_price > 0:
                yes_bid = max(1, last_price - 3)
                yes_ask = min(99, last_price + 3)

            grouped[player_name]["props"].append({
                "threshold": threshold,
                "bid": yes_bid,
                "ask": yes_ask,
                "mid": (yes_bid + yes_ask) / 2 if yes_bid and yes_ask else last_price,
                "volume": m.get("volume", 0) or 0,
                "ticker": m.get("ticker", "")
            })

        result = []
        for group in grouped.values():
            # Deduplicate thresholds
            seen = {}
            for prop in group["props"]:
                t = prop["threshold"]
                if t not in seen or prop["volume"] > seen[t]["volume"]:
                    seen[t] = prop
            group["props"] = sorted(seen.values(), key=lambda x: x["threshold"])
            if len(group["props"]) >= 2:
                result.append(group)

        result.sort(key=lambda x: sum(p["volume"] for p in x["props"]), reverse=True)

        return jsonify({"players": result, "total_markets": len(all_markets), "matched": len(filtered)})

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
