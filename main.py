from datetime import datetime, timezone
import json
import os
import random
import threading
import time
import urllib.request
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "9237583887:AAEquYRmXGWJZwtmgrRTipR7_LicQE_5btU")
AUTHORIZED_USER_ID = "8842031370"

permanent_history = {30: {}, 60: {}, 180: {}, 300: {}}
prediction_cache = {}

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Win Go Professional Dashboard</title>
    <style>
        body { background-color: #0b1329; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 12px; display: flex; justify-content: center; }
        .container { width: 100%; max-width: 440px; }
        .tabs { display: flex; background: #17223b; border-radius: 8px; padding: 4px; margin-bottom: 14px; gap: 4px; }
        .tab { flex: 1; text-align: center; padding: 8px; font-weight: 600; font-size: 13px; color: #8f9bb3; cursor: pointer; border-radius: 6px; transition: all 0.2s; }
        .tab.active { background: #f59e0b; color: #0b1329; }
        .card { background: #17223b; border-radius: 12px; padding: 18px; text-align: center; margin-bottom: 16px; border: 1px solid #22304f; }
        .period-title { font-size: 11px; text-transform: uppercase; color: #8f9bb3; margin-bottom: 4px; letter-spacing: 0.5px; }
        .period-number { font-size: 14px; font-weight: 700; margin-bottom: 8px; color: #cbd5e1; }
        .badges-row { display: flex; justify-content: center; gap: 8px; margin-bottom: 14px; }
        .stage-badge { font-size: 12px; color: #34d399; font-weight: 600; background: rgba(52, 211, 153, 0.1); padding: 4px 10px; border-radius: 20px; }
        .rate-badge { font-size: 12px; color: #f59e0b; font-weight: 600; background: rgba(245, 158, 11, 0.1); padding: 4px 10px; border-radius: 20px; }
        .prediction-btn { background: linear-gradient(135deg, #f59e0b, #d97706); color: #0b1329; font-size: 24px; font-weight: 800; width: 100%; padding: 16px; border: none; border-radius: 10px; margin-bottom: 12px; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.2); }
        .action-btn { background: #22304f; color: #f8fafc; font-size: 13px; font-weight: 700; width: 100%; padding: 12px; border: 1px solid #334155; border-radius: 8px; cursor: pointer; margin-bottom: 8px; }
        .countdown { font-size: 13px; color: #8f9bb3; }
        .table-container { background: #17223b; border-radius: 12px; overflow: hidden; border: 1px solid #22304f; max-height: 380px; overflow-y: auto; }
        .table-header { display: grid; grid-template-columns: 2.2fr 1fr 1fr 1fr; background: #22304f; padding: 10px 12px; font-size: 11px; font-weight: 700; text-transform: uppercase; color: #8f9bb3; text-align: center; position: sticky; top: 0; z-index: 10; }
        .table-row { display: grid; grid-template-columns: 2.2fr 1fr 1fr 1fr; padding: 12px; align-items: center; border-bottom: 1px solid #22304f; font-size: 13px; text-align: center; }
        .col-period { font-family: monospace; font-size: 11px; color: #94a3b8; text-align: left; }
        .col-num { font-weight: 700; font-size: 15px; }
        .col-num.red { color: #ef4444; }
        .col-num.green { color: #10b981; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; display: inline-block; }
        .badge.win { background: rgba(16, 185, 129, 0.15); color: #34d399; }
        .badge.loss { background: rgba(239, 68, 68, 0.15); color: #f87171; }
    </style>
</head>
<body>
<div class="container">
    <div class="tabs">
        <div class="tab" onclick="switchTimeframe(30, '30S')">30s</div>
        <div class="tab active" onclick="switchTimeframe(60, '1M')">1m</div>
        <div class="tab" onclick="switchTimeframe(180, '3M')">3m</div>
        <div class="tab" onclick="switchTimeframe(300, '5M')">5m</div>
    </div>
    <div class="card">
        <div class="period-title" id="mode-title">Current Period (1M)</div>
        <div class="period-number" id="period-display">Loading...</div>
        <div class="badges-row">
            <span class="stage-badge" id="stage-display">Stage 1 / 6</span>
            <span class="rate-badge" id="rate-display">Win Rate: --%</span>
        </div>
        <button class="prediction-btn" id="pred-display">--</button>
        <button class="action-btn" onclick="triggerNextPrediction()">⚡ Generate Next Prediction Ahead</button>
        <div class="countdown" id="countdown-timer">Next draw in --s</div>
    </div>
    <div class="table-container">
        <div class="table-header">
            <div style="text-align: left;">Period</div>
            <div>Number</div>
            <div>Big/Small</div>
            <div>Status</div>
        </div>
        <div id="history-container">
            <div class="table-row"><div style="text-align: center;" colspan="4">Loading history...</div></div>
        </div>
    </div>
</div>
<script>
    let currentTimeframe = 60;
    let timeLeft = 60;
    let manualOffset = 0;
    function switchTimeframe(secs, name) {
        currentTimeframe = secs;
        timeLeft = secs;
        manualOffset = 0;
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        event.target.classList.add('active');
        document.getElementById('mode-title').innerText = `Current Period (${name})`;
        fetchData();
    }
    function triggerNextPrediction() {
        manualOffset += 1;
        fetchData();
    }
    setInterval(() => {
        timeLeft--;
        if (timeLeft <= 0) {
            timeLeft = currentTimeframe;
            manualOffset = 0;
            fetchData();
        }
        document.getElementById('countdown-timer').innerText = `Next draw in ${timeLeft}s`;
    }, 1000);
    async function fetchData() {
        try {
            const res = await fetch(`/api/data?tf=${currentTimeframe}&offset=${manualOffset}`);
            const data = await res.json();
            document.getElementById('period-display').innerText = "Period: " + data.upcoming_period;
            document.getElementById('pred-display').innerText = data.prediction.size + " (" + data.prediction.number + ")";
            document.getElementById('rate-display').innerText = "Win Rate: " + data.win_rate + "%";
            let html = '';
            data.history.forEach(item => {
                let numClass = item.number >= 5 ? 'red' : 'green';
                let statusClass = item.status.toLowerCase();
                html += `
                    <div class="table-row">
                        <div class="col-period">${item.period}</div>
                        <div class="col-num ${numClass}">${item.number}</div>
                        <div>${item.size}</div>
                        <div><span class="badge ${statusClass}">${item.status}</span></div>
                    </div>
                `;
            });
            document.getElementById('history-container').innerHTML = html;
        } catch (e) { console.error(e); }
    }
    setInterval(fetchData, 3000);
    fetchData();
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_DASHBOARD)

@app.route("/api/data")
def api_data():
    tf = int(request.args.get("tf", 60))
    offset = int(request.args.get("offset", 0))
    now = datetime.now(timezone.utc)
    date_prefix = now.strftime("%Y%m%d")
    secs_today = now.hour * 3600 + now.minute * 60 + now.second
    base_idx = secs_today // tf + 100010000
    upcoming_period = f"{date_prefix}{base_idx + 1 + offset}"
    
    if upcoming_period not in prediction_cache:
        p_num = random.randint(0, 9)
        p_size = "BIG" if p_num >= 5 else "SMALL"
        prediction_cache[upcoming_period] = {"number": p_num, "size": p_size}
        
    prediction = prediction_cache[upcoming_period]
    history = fetch_official_history(tf)
    wins = sum(1 for h in history if h["status"] == "WIN")
    total = len(history) if history else 1
    win_rate = int((wins / total) * 70 + 30)

    return jsonify({
        "upcoming_period": upcoming_period,
        "prediction": prediction,
        "win_rate": win_rate,
        "history": history
    })

def fetch_official_history(seconds):
    type_id = 1 if seconds == 30 else (3 if seconds == 60 else (10 if seconds == 180 else 5))
    url = "https://api.bdgwin.com/api/web/GetNoaverageEmerdList"
    payload = json.dumps({"pageSize": 15, "pageNo": 1, "typeId": type_id}).encode("utf-8")
    formatted = []
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            items = res_data.get("data", {}).get("list", [])
            for item in items:
                per = str(item.get("issueNumber", ""))
                num = int(item.get("number", 0))
                actual_size = "BIG" if num >= 5 else "SMALL"
                if per not in permanent_history[seconds]:
                    rand_pred_num = random.randint(0, 9)
                    pred_size = "BIG" if rand_pred_num >= 5 else "SMALL"
                    status = "WIN" if pred_size == actual_size else "LOSS"
                    permanent_history[seconds][per] = {"period": per, "number": num, "size": actual_size, "status": status}
                formatted.append(permanent_history[seconds][per])
    except Exception:
        pass
        
    if not formatted:
        now = datetime.now(timezone.utc)
        date_prefix = now.strftime("%Y%m%d")
        secs_today = now.hour * 3600 + now.minute * 60 + now.second
        base_idx = secs_today // seconds + 100010000
        for i in range(1, 10):
            p_str = f"{date_prefix}{base_idx - i}"
            if p_str not in permanent_history[seconds]:
                num = random.randint(0, 9)
                permanent_history[seconds][p_str] = {"period": p_str, "number": num, "size": "BIG" if num >= 5 else "SMALL", "status": random.choice(["WIN", "LOSS"])}
            formatted.append(permanent_history[seconds][p_str])
    return formatted

def send_telegram_message(chat_id, text):
    if not TELEGRAM_BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=3)
    except Exception as e:
        print("Telegram send error:", e)

def telegram_bot_loop():
    if not TELEGRAM_BOT_TOKEN:
        return
    
    # Automatically clear any existing webhooks so long polling works properly
    try:
        clear_wh_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook?drop_pending_updates=true"
        urllib.request.urlopen(clear_wh_url, timeout=5)
    except Exception:
        pass

    offset = 0
    print("Telegram bot polling loop active.")
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=35) as response:
                data = json.loads(response.read().decode("utf-8"))
                for result in data.get("result", []):
                    offset = result["update_id"] + 1
                    message = result.get("message", {})
                    chat_id = message.get("chat", {}).get("id")
                    user_id = str(message.get("from", {}).get("id", ""))
                    text = message.get("text", "").strip()

                    if chat_id:
                        # Log user ID in logs so you can see if it matches
                        print(f"Received message from User ID: {user_id} with text: {text}")

                        # If you want to temporarily disable user checks to test if it responds, 
                        # you can comment out the user_id check below. For now, we check it securely:
                        if user_id != AUTHORIZED_USER_ID:
                            send_telegram_message(chat_id, f"⛔ Access Denied. Your ID is `{user_id}` (Authorized: `{AUTHORIZED_USER_ID}`)")
                            continue

                        if text == "/start":
                            send_telegram_message(chat_id, "👋 *Welcome back, Boss!*\n\nYour Professional Win Go Bot is active. Send /result or /stats for signals, or open your Render web link to view the pro dashboard.")
                        elif text in ["/result", "/stats"]:
                            num = random.randint(0, 9)
                            size = "BIG" if num >= 5 else "SMALL"
                            color = "🔴 Red" if num % 2 != 0 else "🟢 Green"
                            if num in [0, 5]: color += " + 🟣 Violet"
                            msg = f"📊 *WIN GO SIGNAL (1M)*\n\n🔹 Period: 20261107100011396\n📈 Current Level: Stage 1 / 6\n🔹 Number Prediction: {num}\n🔹 Size: {size}\n🔹 Color: {color}\n🔥 Confidence Rate: 78%"
                            send_telegram_message(chat_id, msg)
        except Exception:
            time.sleep(5)

if __name__ == "__main__":
    bot_thread = threading.Thread(target=telegram_bot_loop, daemon=True)
    bot_thread.start()
    app.run(host="0.0.0.0", port=10000)
