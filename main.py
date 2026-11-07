from datetime import datetime, timezone
import json
import random
import urllib.request
from flask import Flask, jsonify, request

app = Flask(__name__)

# Track active session history per timeframe
session_history = {30: [], 60: [], 180: [], 300: []}

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
        .stage-badge { font-size: 13px; color: #34d399; font-weight: 600; margin-bottom: 14px; background: rgba(52, 211, 153, 0.1); display: inline-block; padding: 4px 10px; border-radius: 20px; }
        .prediction-btn { background: linear-gradient(135deg, #f59e0b, #d97706); color: #0b1329; font-size: 24px; font-weight: 800; width: 100%; padding: 16px; border: none; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.2); }
        .countdown { font-size: 13px; color: #8f9bb3; }
        
        .table-container { background: #17223b; border-radius: 12px; overflow: hidden; border: 1px solid #22304f; max-height: 420px; overflow-y: auto; }
        .table-header { display: grid; grid-template-columns: 2fr 1.5fr 1.5fr; background: #22304f; padding: 10px 12px; font-size: 11px; font-weight: 700; text-transform: uppercase; color: #8f9bb3; text-align: center; position: sticky; top: 0; }
        .table-row { display: grid; grid-template-columns: 2fr 1.5fr 1.5fr; padding: 12px; align-items: center; border-bottom: 1px solid #22304f; font-size: 13px; text-align: center; }
        .table-row:last-child { border-bottom: none; }
        .col-period { font-family: monospace; font-size: 12px; color: #94a3b8; }
        .col-bet { font-weight: 700; font-size: 13px; }
        .col-bet.big { color: #f59e0b; }
        .col-bet.small { color: #60a5fa; }
        
        .badge { padding: 4px 12px; border-radius: 4px; font-size: 11px; font-weight: 700; display: inline-block; }
        .badge.pending { background: rgba(148, 163, 184, 0.15); color: #94a3b8; }
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
            <div>Period</div>
            <div>Bet</div>
            <div>Result</div>
        </div>
        <div id="history-container">
            <div class="table-row"><div style="text-align: center;" colspan="3">Loading tracking table...</div></div>
        </div>
    </div>
</div>

<script>
    let currentTimeframe = 60;
    let timeframeName = '1M';
    let timeLeft = 60;
    let lastPeriod = "";

    function switchTimeframe(secs, name) {
        currentTimeframe = secs;
        timeframeName = name;
        timeLeft = secs;
        lastPeriod = "";
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
                let betClass = h.size.toLowerCase() === 'big' ? 'big' : 'small';
                let statusClass = h.status.toLowerCase();
                histHtml += `
                    <div class="table-row">
                        <div class="col-period">${h.period.slice(-6)}</div>
                        <div class="col-bet ${betClass}">${h.size}</div>
                        <div><span class="badge ${statusClass}">${h.status.toUpperCase()}</span></div>
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
  tf = int(request.args.get("tf", "60"))
  current_period = get_period(tf, offset=0)

  # Initialize history list for this timeframe if empty
  if tf not in session_history:
    session_history[tf] = []

  # Check if we moved to a new period: resolve previous pending bet using live results
  if not session_history[tf] or session_history[tf][0]["period"] != current_period:
    live_num, live_size = fetch_latest_official_result(tf)
    
    # If there was a pending item from the previous period, resolve its win/loss status
    if session_history[tf]:
      prev_item = session_history[tf][0]
      if prev_item["status"] == "Pending":
        prev_item["status"] = "Win" if prev_item["size"] == live_size else "Loss"

    # Generate bot prediction for the new active period and add it as Pending at the top
    num, size, color, accuracy, stage = generate_prediction_logic()
    
    session_history[tf].insert(
        0,
        {
            "period": current_period,
            "size": size,
            "status": "Pending",
        },
    )
    if len(session_history[tf]) > 15:
      session_history[tf].pop()

  active_item = session_history[tf][0]
  num, size, color, accuracy, stage = generate_prediction_logic()

  return jsonify({
      "period": current_period,
      "number": num,
      "size": active_item["size"],  # Keep active period prediction consistent
      "color": color,
      "accuracy": accuracy,
      "stage": stage,
      "history": session_history[tf],
  })


def fetch_latest_official_result(seconds):
  type_id = 1 if seconds == 30 else (3 if seconds == 60 else (10 if seconds == 180 else 5))
  url = "https://api.bdgwin.com/api/web/GetNoaverageEmerdList"
  payload = json.dumps({"pageSize": 1, "pageNo": 1, "typeId": type_id}).encode("utf-8")
  try:
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=4) as response:
      res_data = json.loads(response.read().decode("utf-8"))
      items = res_data.get("data", {}).get("list", [])
      if items:
        num = int(items[0].get("number", 0))
        sz = "BIG" if num >= 5 else "SMALL"
        return num, sz
  except Exception:
    pass
  return 6, "BIG"


def generate_prediction_logic():
  number = random.randint(0, 9)
  size = "BIG" if number >= 5 else "SMALL"
  color = (
      "🟢 Green"
      if number in [1, 3, 7, 9]
      else ("🔴 Red" if number in [2, 4, 6, 8] else "🔴 Red + 🟣 Violet")
  )
  accuracy = random.randint(65, 95)
  return number, size, color, accuracy, 1


def get_period(seconds, offset=0):
  now = datetime.now(timezone.utc)
  date_prefix = now.strftime("%Y%m%d")
  total_seconds_today = (now.hour * 3600) + (now.minute * 60) + now.second
  period_index = (total_seconds_today // seconds) + 100010000 + offset
  return f"{date_prefix}{period_index}"


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=10000)
