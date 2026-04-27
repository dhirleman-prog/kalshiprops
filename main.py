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

KALSHI_BASE = "https://api.elections.kalshi.com"
KALSHI_KEY_ID = "9b4644d1-e5ca-4546-930f-c7593c082612"

# Load private key once at startup
_PRIVATE_KEY = None

def get_private_key():
    global _PRIVATE_KEY
    if _PRIVATE_KEY is not None:
        return _PRIVATE_KEY
    pem_path = os.path.join(os.path.dirname(__file__), "kalshi_private.pem")
    if os.path.exists(pem_path):
        with open(pem_path, "rb") as f:
            pem_data = f.read()
    else:
        pem_str = os.environ.get("KALSHI_PRIVATE_KEY", "")
        if not pem_str:
            raise Exception("No private key found — upload kalshi_private.pem or set KALSHI_PRIVATE_KEY env var")
        pem_data = pem_str.strip().encode()
    _PRIVATE_KEY = serialization.load_pem_private_key(pem_data, password=None, backend=default_backend())
    return _PRIVATE_KEY

def sign_pss(text: str) -> str:
    message = text.encode("utf-8")
    signature = get_private_key().sign(
        message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode("utf-8")

def kalshi_headers(method: str, path: str):
    key_id = os.environ.get("KALSHI_KEY_ID", KALSHI_KEY_ID)
    ts = str(int(datetime.datetime.now().timestamp() * 1000))
    path_no_query = path.split("?")[0]
    sig = sign_pss(ts + method.upper() + path_no_query)
    return {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-SIGNATURE": sig,
        "KALSHI-ACCESS-TIMESTAMP": ts,
        "Content-Type": "application/json"
    }

def kalshi_get(path, params=None):
    query = urlencode(params) if params else ""
    full_url = f"{KALSHI_BASE}{path}{'?' + query if query else ''}"
    resp = requests.get(full_url, headers=kalshi_headers("GET", path), timeout=20)
    if not resp.ok:
        raise Exception(f"Kalshi {resp.status_code}: {resp.text[:300]}")
    return resp.json()

def normalize(s):
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()

NON_POINTS = ["assist", "rebound", "three", "3pt", "3-pt", "block", "steal",
              "turnover", "fg ", "ft ", "minute", "double", "triple",
              "quarter", "half", "spread", "moneyline", "winner", "will "]

def parse_player_points(m):
    title = m.get("title", "").strip()
    subtitle = m.get("subtitle", "").strip()
    combined = (title + " " + subtitle).lower()
    if any(w in combined for w in NON_POINTS):
        return None, None
    for text in [subtitle, title]:
        if not text:
            continue
        match = re.match(r"^([A-ZÀ-Ö][a-zA-ZÀ-öÙ-ý'\-\. ]+):\s*(\d+)\+\s*$", text.strip())
        if match:
            candidate = match.group(1).strip()
            words = candidate.split()
            if 2 <= len(words) <= 4 and len(candidate) < 40:
                threshold = int(match.group(2))
                if 5 <= threshold <= 75:
                    return candidate, threshold
    return None, None

def build_result(markets, search=""):
    grouped = {}
    for m in markets:
        player_name, threshold = parse_player_points(m)
        if not player_name:
            continue
        if search and search not in normalize(player_name) and search not in player_name.lower():
            continue

        yes_bid = m.get("yes_bid") or 0
        yes_ask = m.get("yes_ask") or 0
        last_price = m.get("last_price") or 0

        if isinstance(yes_bid, str): yes_bid = int(float(yes_bid) * 100)
        if isinstance(yes_ask, str): yes_ask = int(float(yes_ask) * 100)
        if isinstance(last_price, str): last_price = int(float(last_price) * 100)

        if yes_bid == 0 and yes_ask == 0 and last_price > 0:
            yes_bid = max(1, last_price - 3)
            yes_ask = min(99, last_price + 3)

        ticker = m.get("event_ticker", m.get("ticker", ""))
        if player_name not in grouped:
            grouped[player_name] = {"name": player_name, "event_ticker": ticker, "props": []}

        grouped[player_name]["props"].append({
            "threshold": threshold,
            "bid": yes_bid,
            "ask": yes_ask,
            "mid": (yes_bid + yes_ask) / 2 if yes_bid and yes_ask else last_price,
            "volume": m.get("volume") or 0,
            "ticker": m.get("ticker", "")
        })

    result = []
    for group in grouped.values():
        seen = {}
        for prop in group["props"]:
            t = prop["threshold"]
            if t not in seen or prop["volume"] > seen[t]["volume"]:
                seen[t] = prop
        group["props"] = sorted(seen.values(), key=lambda x: x["threshold"])
        if len(group["props"]) >= 2:
            result.append(group)

    result.sort(key=lambda x: sum(p["volume"] for p in x["props"]), reverse=True)
    return result

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/kalshi/markets", methods=["POST"])
def get_markets():
    data = request.json or {}
    search = data.get("search", "").lower().strip()

    try:
        all_markets = []

        # Fetch NBA markets directly using series_ticker on markets endpoint
        for series in ["KXNBAGAME", "KXNBA", "KXNBAPLAYER"]:
            try:
                cursor = None
                for _ in range(5):
                    params = {"series_ticker": series, "status": "open", "limit": 200}
                    if cursor:
                        params["cursor"] = cursor
                    resp = kalshi_get("/trade-api/v2/markets", params)
                    markets = resp.get("markets", [])
                    all_markets.extend(markets)
                    cursor = resp.get("cursor")
                    if not cursor or not markets:
                        break
            except:
                continue

        # Fallback — broad pagination if series approach found nothing
        if not all_markets:
            cursor = None
            for _ in range(20):
                params = {"limit": 200, "status": "open"}
                if cursor:
                    params["cursor"] = cursor
                try:
                    resp = kalshi_get("/trade-api/v2/markets", params)
                    markets = resp.get("markets", [])
                    all_markets.extend(markets)
                    cursor = resp.get("cursor")
                    if not cursor or not markets:
                        break
                except:
                    break

        result = build_result(all_markets, search)

        return jsonify({
            "players": result,
            "total_markets": len(all_markets),
            "matched": len(result),
            "nba_events": len(nba_event_tickers)
        })

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/debug/events")
def debug_events():
    try:
        out = {}
        for series in ["KXNBAGAME", "KXNBA", "KXNBAPLAYER", "KXSPORTS", "KXNBA26"]:
            try:
                resp = kalshi_get("/trade-api/v2/markets", {"series_ticker": series, "status": "open", "limit": 5})
                markets = resp.get("markets", [])
                out[series] = {
                    "count": len(markets),
                    "sample_titles": [m.get("title") for m in markets[:3]],
                    "sample_tickers": [m.get("ticker") for m in markets[:3]]
                }
            except Exception as ex:
                out[series] = f"error: {str(ex)}"
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/debug/sample")
def debug_sample():
    try:
        resp = kalshi_get("/trade-api/v2/markets", {"limit": 30, "status": "open"})
        return jsonify([{
            "title": m.get("title"),
            "subtitle": m.get("subtitle"),
            "event_ticker": m.get("event_ticker"),
            "ticker": m.get("ticker")
        } for m in resp.get("markets", [])])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
