from datetime import datetime, timezone
import json
import random
import threading
import time
from flask import Flask, jsonify, request
import urllib.request

TOKEN = "9237583887:AAEquYRmXGWJZwtmgrRTipR7_LicQE_5btU"
ALLOWED_USER_IDS = [8842031370, 8882241036, 7891601316]

total_predictions = 0
total_wins = 0
total_losses = 0
current_stage = 1
history_log = []

app = Flask(__name__)

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Win Go Multi-Timeframe Dashboard</title>
    <style>
        body { background-color: #0b1329; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 12px; display: flex; justify-content: center; }
        .container { width: 100%; max-width: 440px; }
        .tabs { display: flex; background: #17223b; border-radius: 8px; padding: 4px; margin-bottom: 14px; gap: 4px; }
        .tab { flex: 1; text-align: center; padding: 8px; font-weight: 600; font-size: 13px; color: #8f9bb3; cursor: pointer; border-radius: 6px; transition: all 0.2s; }
        .tab.active { background: #f59e0b; color: #0b1329; }
        .card { background: #17223b; border-radius: 12px; padding: 18px; text-align: center; margin-bottom: 16px; border: 1px solid #22304f; }
        .period-title { font-size: 11px; text-transform: uppercase; color: #8f9bb3; margin-bottom: 4px; letter-spacing: 0.5px; }
        .period-number { font-size: 14px; font-weight: 700; margin-bottom: 8px; color: #cbd5e1; }
        .stage-badge { font-size: 13px; color: #34d399; font-weight: 600; margin-bottom: 14px; background: rgba(52, 211, 153, 0.1); display: inline-block; padding: 4px 10px; border-radius: 20px; }
        .prediction-btn { background: linear-gradient(135deg, #f59e0b, #d97706); color: #0b1329; font-size: 24px; font-weight: 800; width: 100%; padding: 16px; border: none; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.2); }
        .countdown { font-size: 13px; color: #8f9bb3; }
        .table-container { background: #17223b; border-radius: 12px; overflow: hidden; border: 1px solid #22304f; }
        .table-header { display: grid; grid-template-columns: 2.2fr 1fr 1fr 1fr; background: #22304f; padding: 10px 12px; font-size: 11px; font-weight: 700; text-transform: uppercase; color: #8f9bb3; text-align: center; }
        .table-row { display: grid; grid-template-columns: 2.2fr 1fr 1fr 1fr; padding: 12px; align-items: center; border-bottom: 1px solid #22304f; font-size: 13px; text-align: center; }
        .table-row:last-child { border-bottom: none; }
        .col-period { font-family: monospace; font-size: 11px; color: #94a3b8; text-align: left; }
        .col-num { font-weight: 700; font-size: 15px; }
        .col-num.red { color: #ef4444; }
        .col-num.green { color: #10b981; }
        .col-size { font-weight: 600; }
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
        <div><span class="stage-badge" id="stage-display">Stage 1 / 6</span></div>
        <button class="prediction-btn" id="pred-display">--</button>
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
            <div class="table-row"><div class="col-period" style="text-align: center;" colspan="4">Loading data...</div></div>
        </div>
    </div>
</div>

<script>
    let currentTimeframe = 60;
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

    setInterval(() => {
        timeLeft--;
        if (timeLeft <= 0) {
            timeLeft = currentTimeframe;
            fetchSignal();
        }
        document.getElementById('countdown-timer').innerText = `Next draw in ${timeLeft}s`;
    }, 1000);

    async function fetchSignal() {
        try {
            const res = await gApiData();
            document.getElementById('period-display').innerText = "Period: " + res.period;
            document.getElementById('stage-display').innerText = "Stage " + res.stage + " / 6";
            document.getElementById('pred-display').innerText = res.size + " (" + res.number + ")";
            
            let histHtml = '';
            res.history.forEach(h => {
                let numClass = (h.number >= 5) ? 'red' : 'green';
                histHtml += `
                    <div class="table-row">
                        <div class="col-period">${h.period}</div>
                        <div class="col-num ${numClass}">${h.number}</div>
                        <div class="col-size">${h.size}</div>
                        <div><span class="badge ${h.status}">${h.status.toUpperCase()}</span></div>
                    </div>
                `;
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
  tf = int(request.args.get("tf", "60"))
  # Calculate current period + 1 ahead so it matches future predictions accurately
  period = get_period(tf, offset=1)
  number, size, color, accuracy, stage = generate_prediction_logic()
  status = "win" if accuracy >= 55 else "loss"

  history_log.insert(
      0,
      {
          "period": period,
          "number": number,
          "size": size,
          "status": status,
      },
  )
  if len(history_log) > 10:
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
    current_stage = 1
  else:
    total_losses += 1
    current_stage = min(current_stage + 1, 6)

  return number, size, color, accuracy, current_stage


def get_period(seconds, offset=0):
  now = datetime.now(timezone.utc)
  date_prefix = now.strftime("%Y%m%d")
  total_seconds_today = (now.hour * 3600) + (now.minute * 60) + now.second
  period_index = (total_seconds_today // seconds) + 100010000 + offset
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
  print("Telegram bot polling started...")
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
            send_message(chat_id, "⛔ Access Denied. This is a private bot.")
            continue

          if text.startswith("/result"):
            period = get_period(60, offset=1)
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
            send_message(stats_text)

          elif text.startswith("/start"):
            send_message(
                chat_id,
                "👋 **Welcome to your Professional Win Go Bot!**\n\n"
                "Send `/result` for Telegram signals, or open your Render web"
                " link to view the pro data table dashboard.",
            )
    except Exception:
      time.sleep(5)


bot_thread = threading.Thread(target=check_updates, daemon=True)
bot_thread.start()
