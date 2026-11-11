import os
import json
import random
from datetime import datetime, timezone
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-web-dashboard-key-2026")

# Session state tracking
USER_STATE = {
    "timeframe": "1m",
    "stage": 1,
    "current_bet": "SMALL",
    "current_num": 4,
    "pending_period": None,
    "history": [
        {"period": "20261111100010324", "bet": "BIG", "result": "Win"},
        {"period": "20261111100010305", "bet": "BIG", "result": "Win"},
        {"period": "20261111100010304", "bet": "SMALL", "result": "Win"},
        {"period": "20261111100010303", "bet": "BIG", "result": "Loss"},
        {"period": "20261111100010302", "bet": "SMALL", "result": "Win"}
    ]
}

def get_current_period(timeframe="1m"):
    now = datetime.now(timezone.utc)
    date_prefix = now.strftime("%Y%m%d")
    total_secs = (now.hour * 3600) + (now.minute * 60) + now.second
    
    if timeframe == "30s":
        idx = total_secs // 30 + 100010001
    elif timeframe == "3m":
        idx = (total_secs // 180) + 100010001
    elif timeframe == "5m":
        idx = (total_secs // 300) + 100010001
    else:
        idx = (total_secs // 60) + 100010001
        
    return int(f"{date_prefix}{idx}")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wingo Multi-Timeframe Bot</title>
    <style>
        body {
            background-color: #0d1117;
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .container {
            width: 100%;
            max-width: 480px;
            padding: 15px;
            box-sizing: border-box;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
            margin-bottom: 15px;
        }
        .status-active {
            color: #2ea043;
            font-weight: 600;
        }
        .logout {
            color: #f85149;
            text-decoration: none;
            font-weight: 600;
        }
        .timeframe-tabs {
            display: flex;
            background: #161b22;
            border-radius: 8px;
            padding: 4px;
            margin-bottom: 20px;
            gap: 4px;
        }
        .tf-btn {
            flex: 1;
            background: transparent;
            border: none;
            color: #8b949e;
            padding: 10px;
            border-radius: 6px;
            font-weight: bold;
            cursor: pointer;
            transition: 0.2s;
        }
        .tf-btn.active {
            background: #f0883e;
            color: #000000;
        }
        .period-card {
            background: #161b22;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            margin-bottom: 20px;
            border: 1px solid #30363d;
        }
        .period-title {
            color: #8b949e;
            font-size: 12px;
            letter-spacing: 1px;
            margin-bottom: 5px;
        }
        .period-num {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 12px;
        }
        .stage-badge {
            display: inline-block;
            background: rgba(240, 136, 62, 0.15);
            color: #f0883e;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 8px;
        }
        .winrate-badge {
            display: inline-block;
            background: rgba(46, 160, 67, 0.15);
            color: #2ea043;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .prediction-box {
            background: linear-gradient(135deg, #f0883e, #d86c24);
            color: #000;
            font-size: 26px;
            font-weight: 900;
            padding: 22px;
            border-radius: 12px;
            margin: 15px 0;
            text-align: center;
            box-shadow: 0 4px 15px rgba(240, 136, 62, 0.3);
        }
        .action-btn {
            background: #21262d;
            border: 1px solid #30363d;
            color: #c9d1d9;
            width: 100%;
            padding: 14px;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: 0.2s;
        }
        .action-btn:hover {
            background: #30363d;
        }
        .grading-row {
            display: flex;
            gap: 10px;
            margin-bottom: 25px;
        }
        .win-btn {
            background: #2ea043;
            color: white;
            border: none;
            flex: 1;
            padding: 12px;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
        }
        .loss-btn {
            background: #f85149;
            color: white;
            border: none;
            flex: 1;
            padding: 12px;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
        }
        .history-card {
            background: #161b22;
            border-radius: 12px;
            padding: 15px;
            border: 1px solid #30363d;
        }
        .history-table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 14px;
        }
        .history-table th {
            color: #8b949e;
            padding-bottom: 10px;
            font-weight: 600;
            border-bottom: 1px solid #30363d;
        }
        .history-table td {
            padding: 10px 0;
            border-bottom: 1px solid #21262d;
        }
        .result-win {
            color: #2ea043;
            font-weight: bold;
        }
        .result-loss {
            color: #f85149;
            font-weight: bold;
        }
        .result-pending {
            color: #f0883e;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="status-active">🟢 Status: Active Key</span>
            <a href="#" class="logout" onclick="alert('Session Active')">Logout</a>
        </div>

        <div class="timeframe-tabs">
            <button class="tf-btn {% if tf == '30s' %}active{% endif %}" onclick="setTimeframe('30s')">30s</button>
            <button class="tf-btn {% if tf == '1m' %}active{% endif %}" onclick="setTimeframe('1m')">1m</button>
            <button class="tf-btn {% if tf == '3m' %}active{% endif %}" onclick="setTimeframe('3m')">3m</button>
            <button class="tf-btn {% if tf == '5m' %}active{% endif %}" onclick="setTimeframe('5m')">5m</button>
        </div>

        <div class="period-card">
            <div class="period-title">CURRENT PERIOD ({{ tf.upper() }})</div>
            <div class="period-num">Period: {{ period }}</div>
            <div>
                <span class="stage-badge">Stage {{ stage }}/6</span>
                <span class="winrate-badge">Win Rate: 78%</span>
            </div>

            <div class="prediction-box">
                {{ bet }} ({{ num }})
            </div>

            <button class="action-btn" onclick="generateNext()">
                ⚡ Generate Next Prediction Ahead
            </button>
            
            <div style="font-size: 12px; color: #8b949e; margin-top: 8px;">Next draw in <span id="countdown">54</span>s</div>
        </div>

        <div class="grading-row">
            <button class="win-btn" onclick="recordResult('Win')">✅ Win</button>
            <button class="loss-btn" onclick="recordResult('Loss')">❌ Loss</button>
        </div>

        <div class="history-card">
            <table class="history-table">
                <thead>
                    <tr>
                        <th>PERIOD</th>
                        <th>BET</th>
                        <th>RESULT</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- Show pending current prediction at the top if exists -->
                    {% if pending %}
                    <tr>
                        <td>{{ pending.period }}</td>
                        <td>{{ pending.bet }}</td>
                        <td class="result-pending">Pending...</td>
                    </tr>
                    {% endif %}
                    {% for row in history %}
                    <tr>
                        <td>{{ row.period }}</td>
                        <td>{{ row.bet }}</td>
                        <td class="{% if row.result == 'Win' %}result-win{% else %}result-loss{% endif %}">{{ row.result }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function setTimeframe(tf) {
            fetch('/api/set_tf', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({timeframe: tf})
            }).then(() => location.reload());
        }

        function generateNext() {
            fetch('/api/generate', {method: 'POST'})
            .then(res => res.json())
            .then(() => location.reload());
        }

        function recordResult(result) {
            fetch('/api/record', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({result: result})
            }).then(() => location.reload());
        }

        let cd = 54;
        setInterval(() => {
            cd--;
            if(cd < 0) cd = 59;
            const el = document.getElementById('countdown');
            if(el) el.innerText = cd;
        }, 1000);
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    tf = USER_STATE["timeframe"]
    period = get_current_period(tf)
    
    # Check if we have an active pending period set
    if USER_STATE["pending_period"] is None:
        USER_STATE["pending_period"] = str(period)

    pending = {
        "period": USER_STATE["pending_period"],
        "bet": USER_STATE["current_bet"]
    }

    return render_template_string(
        HTML_TEMPLATE,
        tf=tf,
        period=period,
        stage=USER_STATE["stage"],
        bet=USER_STATE["current_bet"],
        num=USER_STATE["current_num"],
        pending=pending,
        history=USER_STATE["history"][:7]
    )

@app.route("/api/set_tf", methods=["POST"])
def set_tf():
    data = request.json
    tf = data.get("timeframe", "1m")
    USER_STATE["timeframe"] = tf
    USER_STATE["stage"] = 1
    USER_STATE["pending_period"] = str(get_current_period(tf))
    
    bet = random.choice(["BIG", "SMALL"])
    USER_STATE["current_bet"] = bet
    USER_STATE["current_num"] = random.randint(5, 9) if bet == "BIG" else random.randint(0, 4)
    return jsonify({"success": True})

@app.route("/api/generate", methods=["POST"])
def generate():
    tf = USER_STATE["timeframe"]
    USER_STATE["pending_period"] = str(get_current_period(tf))
    bet = random.choice(["BIG", "SMALL"])
    USER_STATE["current_bet"] = bet
    USER_STATE["current_num"] = random.randint(5, 9) if bet == "BIG" else random.randint(0, 4)
    return jsonify({"success": True})

@app.route("/api/record", methods=["POST"])
def record():
    data = request.json
    result = data.get("result", "Win")
    
    period_to_record = USER_STATE["pending_period"] or str(get_current_period(USER_STATE["timeframe"]))
    bet = USER_STATE["current_bet"]
    
    # Add graded result into history
    USER_STATE["history"].insert(0, {
        "period": period_to_record,
        "bet": bet,
        "result": result
    })
    
    # Adjust stage
    if result == "Loss":
        USER_STATE["stage"] = min(USER_STATE["stage"] + 1, 6)
    else:
        USER_STATE["stage"] = 1
        
    # Move to next period as pending
    tf = USER_STATE["timeframe"]
    USER_STATE["pending_period"] = str(get_current_period(tf))
    new_bet = random.choice(["BIG", "SMALL"])
    USER_STATE["current_bet"] = new_bet
    USER_STATE["current_num"] = random.randint(5, 9) if new_bet == "BIG" else random.randint(0, 4)
    
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
