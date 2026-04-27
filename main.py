from flask import Flask, render_template, request, jsonify
import requests
import os
import base64
import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

app = Flask(__name__)

KALSHI_BASE = "https://trading-api.kalshi.com/trade-api/v2"
KALSHI_KEY_ID = "9022d636-4a74-43c3-b198-060f9c329032"

KALSHI_PRIVATE_KEY_PEM = """-----BEGIN PRIVATE KEY-----
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
B1tPXAt9CCp2Wz3yF3060y2d1w47Vg==
-----END PRIVATE KEY-----"""

def load_private_key():
    key_pem = os.environ.get("KALSHI_PRIVATE_KEY", KALSHI_PRIVATE_KEY_PEM)
    return serialization.load_pem_private_key(
        key_pem.strip().encode(),
        password=None,
        backend=default_backend()
    )

def sign_pss(private_key, text: str) -> str:
    message = text.encode('utf-8')
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH
        ),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')

def kalshi_headers(method: str, path: str):
    key_id = os.environ.get("KALSHI_KEY_ID", KALSHI_KEY_ID)
    ts = str(int(datetime.datetime.now().timestamp() * 1000))
    path_no_query = path.split('?')[0]
    msg = ts + method.upper() + path_no_query
    private_key = load_private_key()
    sig = sign_pss(private_key, msg)
    return {
        'KALSHI-ACCESS-KEY': key_id,
        'KALSHI-ACCESS-SIGNATURE': sig,
        'KALSHI-ACCESS-TIMESTAMP': ts,
        'Content-Type': 'application/json'
    }

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/kalshi/markets", methods=["POST"])
def get_markets():
    data = request.json
    search = data.get("search", "").lower()

    try:
        import re
        from urllib.parse import urlencode

        all_markets = []
        cursor = None
        pages = 0

        while pages < 5:
            path = "/trade-api/v2/markets"
            params = {"limit": 200, "status": "open"}
            if cursor:
                params["cursor"] = cursor

            query = urlencode(params)
            full_url = f"{KALSHI_BASE}/markets?{query}"

            resp = requests.get(
                full_url,
                headers=kalshi_headers("GET", path),
                timeout=15
            )

            if resp.status_code == 401:
                return jsonify({"error": "Authentication failed — RSA signature rejected."}), 401
            if resp.status_code == 403:
                return jsonify({"error": "Access forbidden — check key permissions."}), 403
            if not resp.ok:
                return jsonify({"error": f"Kalshi API error {resp.status_code}: {resp.text[:300]}"}), resp.status_code

            resp_data = resp.json()
            markets = resp_data.get("markets", [])
            all_markets.extend(markets)
            cursor = resp_data.get("cursor")
            pages += 1
            if not cursor or not markets:
                break

        keywords = ["point", "pts", "score", "lebron", "curry", "durant",
                    "tatum", "jokic", "embiid", "giannis", "luka",
                    "nba", "assists", "rebounds", "three", "basket"]

        if search:
            filtered = [m for m in all_markets if search in (
                m.get("title","") + m.get("subtitle","") + m.get("event_ticker","")
            ).lower()]
        else:
            filtered = [m for m in all_markets if any(
                k in (m.get("title","") + m.get("subtitle","") + m.get("event_ticker","")).lower()
                for k in keywords
            )]

        grouped = {}
        for m in filtered:
            title = m.get("title", "")
            ticker = m.get("event_ticker", m.get("ticker", ""))

            threshold_match = re.search(r"(\d+)\+?\s*(?:pts?|points?|assists?|rebounds?)", title, re.IGNORECASE)
            if not threshold_match:
                continue

            threshold = int(threshold_match.group(1))
            group_key = re.sub(r"\d+\+?\s*(?:pts?|points?|assists?|rebounds?)", "", title, flags=re.IGNORECASE).strip()
            group_key = re.sub(r"\s+", " ", group_key).strip(" -–")

            if group_key not in grouped:
                grouped[group_key] = {"name": group_key, "event_ticker": ticker, "props": []}

            yes_bid = m.get("yes_bid", 0)
            yes_ask = m.get("yes_ask", 0)
            last_price = m.get("last_price", 0)

            # Handle fixed-point dollar format (March 2026+)
            if isinstance(yes_bid, str):
                yes_bid = int(float(yes_bid) * 100)
            if isinstance(yes_ask, str):
                yes_ask = int(float(yes_ask) * 100)
            if isinstance(last_price, str):
                last_price = int(float(last_price) * 100)

            if yes_bid == 0 and yes_ask == 0 and last_price > 0:
                yes_bid = max(1, last_price - 3)
                yes_ask = min(99, last_price + 3)

            grouped[group_key]["props"].append({
                "threshold": threshold,
                "bid": yes_bid,
                "ask": yes_ask,
                "mid": (yes_bid + yes_ask) / 2 if yes_bid and yes_ask else last_price,
                "volume": m.get("volume", 0),
                "ticker": m.get("ticker", "")
            })

        result = []
        for group in grouped.values():
            group["props"].sort(key=lambda x: x["threshold"])
            if len(group["props"]) >= 2:
                result.append(group)

        result.sort(key=lambda x: sum(p["volume"] for p in x["props"]), reverse=True)

        return jsonify({
            "players": result,
            "total_markets": len(all_markets),
            "matched": len(filtered)
        })

    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timed out — try again"}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Could not connect to Kalshi API"}), 503
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
