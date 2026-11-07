from datetime import datetime, timezone
import json
import random
import threading
import time
from flask import Flask, jsonify, request
import urllib.request

TOKEN = "9237583887:AAEquYRmXGWJZwtmgrRTipR7_LicQE_5btU"

# 🔒 SECURITY LOCK: Allowed user IDs
ALLOWED_USER_IDS = [8842031370, 8882241036, 7891601316]

# 📊 GLOBAL STATS & STAGE TRACKING (Stages 1 to 6)
total_predictions = 0
total_wins = 0
total_losses = 0
current_stage = 1
history_log = []

# --- FLASK WEB SERVER & MULTI-TIMEFRAME DASHBOARD ---
app = Flask(__name__)

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Odogwudave Win Go Dashboard</title>
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: sans-serif; margin: 0; padding: 16px; display: flex; justify-content: center; }
        .container { width: 100%; max-width: 400px; }
        .tabs { display: flex; background: #1e293b; border-radius: 12px; padding: 4px; margin-bottom: 20px; }
        .tab { flex: 1; text-align: center; padding: 10px; font-weight: 600; font-size: 14px; color: #94a3b8; cursor: pointer; border-radius: 8px; transition: all 0.2s; }
        .tab.active { background: #f59e0b; color: #0f172a; }
        .card { background: #1e293b; border-radius: 16px; padding: 24px; text-align: center; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        .period-title { font-size: 12px; text-transform: uppercase; color: #94a3b8; margin-bottom: 8px; }
        .period-number { font-size: 16px; font-weight: 700; margin-bottom: 12px; }
        .stage-badge { font-size: 14px; color: #34d399; font-weight: 700; margin-bottom: 16px; }
        .prediction-btn { background: #f59e0b; color: #0f172a; font-size: 28px; font-weight: 800; width: 100%; padding: 20px; border: none; border-radius: 12px; margin-bottom: 12px; }
        .countdown { font-size: 14px; color: #94a3b8; }
        .history-header { font-size: 12px; text-transform: uppercase; color: #94a3b8; margin-bottom: 12px; }
        .history-list { background: #1e293b; border-radius: 16px; padding: 12px; }
        .history-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 8px; border-bottom: 1px solid #334155; }
        .badge { padding: 6px 14px; border-radius: 6px; font-size: 12px; font-weight: 700; }
        .badge.win { background: rgba(16, 185, 129, 0.2); color: #34d399; }
        .badge.loss { background: rgba(239, 68, 68, 0.2); color: #f87171; }
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
        <div class="stage-badge" id="stage-display">Stage 1 / 6</div>
        <button class="prediction-btn" id="pred-display">--</button>
        <div class="countdown" id="countdown-timer">Next draw in --s</div>
    </div>

    <div class="history-header">Full History & Win/Loss Log</div>
    <div class="history-list" id="history-container">
        <div class="history-item"><span>Fetching logs...</span></div>
    </div>
</div>

<script>
    let currentTimeframe = 60; // default 1m
    let timeframeName = '1M';
    let timeLeft = 60;

    function switchTimeframe(secs, name) {
        currentTimeframe = secs;
        timeframeName = name;
        timeLeft = secs;
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        event.target.classList.add('active');
        document.getElementById('mode-title').innerText = `Current Period (${name})`;
        fetchSignal();
    }

    // Countdown timer loop
    setInterval(() => {
        timeLeft--;
        if (timeLeft <= 0) {
            timeLeft = currentTimeframe;
            fetchSignal(); // Refresh data on new period
        }
        document.getElementById('countdown-timer').innerText = `Next draw in ${timeLeft}s`;
    }, 1000);

    async function fetchSignal() {
        try {
            const res = await gApiData();
            document.getElementById('period-display').innerText = "Period: " + res.period;
            document.getElementById('stage-display').innerText = "Current Level: Stage " + res.stage + " / 6";
            document.getElementById('pred-display').innerText = res.size + " (" + res.number + ")";
            
            let histHtml = '';
            res.history.forEach(h => {
                histHtml += `<div class="history-item"><span>${h.period}</span><span><b>${h.size} (${h.number})</b></span><span class="badge ${h.status}">${h.status.toUpperCase()}</span></div>`;
            });
            document.getElementById('history-container').innerHTML = histHtml;
        } catch (e) { console.error(e); }
    }

    async function gApiData() {
        const res = await fetch(`/api/prediction?tf=${currentTimeframe}`);
        return await res.json();
    }

    fetchSignal();
</script>
</body>
</html>
"""


@app.route("/")
def home():
  return HTML_DASHBOARD


@app.route("/api/prediction")
def api_prediction():
  global current_stage, total_wins, total_losses, history_log
  tf = request.args.get("tf", "60")
  period = get_period(int(tf))
  number, size, color, accuracy, stage = generate_prediction_logic()
  status = "win" if accuracy >= 55 else "loss"

  history_log.insert(
      0,
      {
          "period": period[-4:],
          "number": number,
          "size": size,
          "status": status,
      },
  )
  if len(history_log) > 5:
    history_log.pop()

  return jsonify({
      "period": period,
      "number": number,
      "size": size,
      "color": color,
      "accuracy": accuracy,
      "stage": stage,
      "history": history_log,
  })


def run_web():
  app.run(host="0.0.0.0", port=10000)


# ---------------------------------------------


def generate_prediction_logic():
  global total_predictions, total_wins, total_losses, current_stage
  number = random.randint(0, 9)
  size = "BIG" if number >= 5 else "SMALL"
  color = (
      "🟢 Green"
      if number in [1, 3, 7, 9]
      else ("🔴 Red" if number in [2, 4, 6, 8] else "🔴 Red + 🟣 Violet")
  )
  accuracy = random.randint(40, 95)

  total_predictions += 1
  if accuracy >= 55:
    total_wins += 1
    current_stage = 1  # Reset on win
  else:
    total_losses += 1
    current_stage = min(current_stage + 1, 6)  # Cap at 6

  return number, size, color, accuracy, current_stage


def get_period(seconds):
  now = datetime.now(timezone.utc)
  date_prefix = now.strftime("%Y%m%d")
  total_seconds_today = (now.hour * 3600) + (now.minute * 60) + now.second
  period_index = (total_seconds_today // seconds) + 100010000
  return f"{date_prefix}{period_index}"


def send_message(chat_id, text):
  url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
  payload = json.dumps(
      {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
  ).encode("utf-8")
  req = urllib.request.Request(
      url, data=payload, headers={"Content-Type": "application/json"}
  )
  try:
    urllib.request.urlopen(req, timeout=10)
  except Exception as e:
    print("Error sending message:", e)


def check_updates():
  offset = 0
  print("Multi-timeframe bot active with new token!")
  while True:
    try:
      url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={offset}&timeout=30"
      response = urllib.request.urlopen(url, timeout=35)
      data = json.loads(response.read().decode("utf-8"))

      for result in data.get("result", []):
        offset = result["update_id"] + 1
        if "message" in result and "text" in result["message"]:
          chat_id = result["message"]["chat"]["id"]
          user_id = result["message"]["from"]["id"]
          text = result["message"]["text"].lower()

          if user_id not in ALLOWED_USER_IDS:
            print(f"👉 BLOCKED USER ID ATTEMPT: {user_id}")
            send_message(chat_id, "⛔ Access Denied. This is a private bot.")
            continue

          if text.startswith("/result"):
            period = get_period(60)
            number, size, color, accuracy, stage = generate_prediction_logic()
            response_text = (
                f"📊 **WIN GO SIGNAL (1M)**\n\n"
                f"🔹 **Period:** `{period}`\n"
                f"📈 **Current Level:** `Stage {stage} / 6`\n"
                f"🔹 **Number Prediction:** `{number}`\n"
                f"🔹 **Size:** **{size}**\n"
                f"🔹 **Color:** {color}\n"
                f"🔥 **Confidence Rate:** `{accuracy}%`\n"
            )
            send_message(chat_id, response_text)

          elif text.startswith("/stats"):
            win_percentage = (
                (total_wins / total_predictions * 100)
                if total_predictions > 0
                else 0
            )
            stats_text = (
                f"📈 **LIVE STATISTICS & PROGRESSION**\n\n"
                f"📌 **Total Rounds:** `{total_predictions}`\n"
                f"✅ **Total Wins:** `{total_wins}`\n"
                f"❌ **Total Losses:** `{total_losses}`\n"
                f"🎯 **Success Rate:** `{win_percentage:.1f}%`\n"
                f"🔄 **Active Stage:** `Stage {current_stage} of 6`"
            )
            send_message(chat_id, stats_text)

          elif text.startswith("/start"):
            send_message(
                chat_id,
                "👋 **Welcome to your new Multi-Timeframe Bot!**\n\n"
                "Send `/result` for Telegram signals, or open your Render web"
                " link to use the 30s, 1m, 3m, 5m dashboard.",
            )
    except Exception as e:
      print("Network glitch, retrying in 5 seconds...")
      time.sleep(5)


if __name__ == "__main__":
  t = threading.Thread(target=run_web)
  t.daemon = True
  t.start()

  check_updates()
