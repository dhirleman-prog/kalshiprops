from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)

KALSHI_BASE = "https://trading-api.kalshi.com/trade-api/v2"

def kalshi_headers(api_key):
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/kalshi/markets", methods=["POST"])
def get_markets():
    data = request.json
    api_key = data.get("api_key", "")
    search = data.get("search", "").lower()

    if not api_key:
        return jsonify({"error": "No API key provided"}), 400

    try:
        all_markets = []
        cursor = None
        pages = 0

        while pages < 5:
            params = {"limit": 200, "status": "open"}
            if cursor:
                params["cursor"] = cursor

            resp = requests.get(
                f"{KALSHI_BASE}/markets",
                headers=kalshi_headers(api_key),
                params=params,
                timeout=10
            )

            if resp.status_code == 401:
                return jsonify({"error": "Invalid API key — check your Kalshi API key and try again"}), 401
            if not resp.ok:
                return jsonify({"error": f"Kalshi API error: {resp.status_code}"}), resp.status_code

            resp_data = resp.json()
            markets = resp_data.get("markets", [])
            all_markets.extend(markets)
            cursor = resp_data.get("cursor")
            pages += 1
            if not cursor or not markets:
                break

        keywords = ["point", "pts", "score", "lebron", "curry", "durant",
                    "tatum", "jokic", "embiid", "giannis", "luka", "kd",
                    "nba", "assists", "rebounds", "three"]

        if search:
            filtered = [m for m in all_markets if search in (m.get("title","") + m.get("subtitle","") + m.get("event_ticker","")).lower()]
        else:
            filtered = [m for m in all_markets if any(k in (m.get("title","") + m.get("subtitle","") + m.get("event_ticker","")).lower() for k in keywords)]

        grouped = {}
        for m in filtered:
            title = m.get("title", "")
            subtitle = m.get("subtitle", "")
            ticker = m.get("event_ticker", m.get("ticker", ""))

            import re
            threshold_match = re.search(r"(\d+)\+?\s*(?:pts?|points?)", title, re.IGNORECASE)
            if not threshold_match:
                continue

            threshold = int(threshold_match.group(1))
            group_key = re.sub(r"\d+\+?\s*(?:pts?|points?)", "", title, flags=re.IGNORECASE).strip()
            group_key = re.sub(r"\s+", " ", group_key).strip(" -–")

            if group_key not in grouped:
                grouped[group_key] = {
                    "name": group_key,
                    "event_ticker": ticker,
                    "props": []
                }

            yes_bid = m.get("yes_bid", 0)
            yes_ask = m.get("yes_ask", 0)
            last_price = m.get("last_price", 0)

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

        return jsonify({"players": result, "total_markets": len(all_markets), "matched": len(filtered)})

    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timed out — Kalshi may be slow, try again"}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Could not connect to Kalshi API"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/kalshi/events", methods=["POST"])
def get_events():
    data = request.json
    api_key = data.get("api_key", "")
    if not api_key:
        return jsonify({"error": "No API key"}), 400
    try:
        resp = requests.get(
            f"{KALSHI_BASE}/events",
            headers=kalshi_headers(api_key),
            params={"limit": 100, "status": "open"},
            timeout=10
        )
        if not resp.ok:
            return jsonify({"error": f"Kalshi error: {resp.status_code}"}), resp.status_code
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
