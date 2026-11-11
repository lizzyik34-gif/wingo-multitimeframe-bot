import os
import random
from datetime import datetime, timezone
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-web-dashboard-key-2026")

# --- MASTER ADMIN & USER KEYS ---
# Master key gives access to the Admin Dashboard
MASTER_ADMIN_KEY = "OWNER-ADMIN-2026"

# Regular authorized user keys (Admin can add more here or we can manage them)
VALID_ACCESS_KEYS = [
    "FB999-VIP-OWNER-777",
    "FB999-USER-888224",
    "FB999-PRO-KEY-1028"
]

USER_STATE = {
    "timeframe": "1m",
    "stage": 1,
    "current_bet": "BIG",
    "current_num": 6,
    "pending_period": None,
    "history": [
        {"period": "20261111100010333", "bet": "SMALL", "result": "Win"},
        {"period": "20261111100010332", "bet": "SMALL", "result": "Loss"},
        {"period": "20261111100010331", "bet": "SMALL", "result": "Loss"},
        {"period": "20261111100010330", "bet": "BIG", "result": "Win"}
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

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FB999 Bot - Login</title>
    <style>
        body {
            background-color: #0d1117;
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .login-box {
            background: #161b22;
            border: 1px solid #30363d;
            padding: 30px;
            border-radius: 12px;
            width: 100%;
            max-width: 350px;
            text-align: center;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }
        h2 { margin-bottom: 20px; color: #f0883e; }
        input {
            width: 100%;
            padding: 12px;
            background: #0d1117;
            border: 1px solid #30363d;
            color: white;
            border-radius: 8px;
            box-sizing: border-box;
            margin-bottom: 15px;
            font-size: 14px;
            text-align: center;
        }
        button {
            width: 100%;
            padding: 12px;
            background: #f0883e;
            color: #000;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
            font-size: 15px;
        }
        button:hover { background: #d86c24; }
        .error { color: #f85149; font-size: 13px; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>🔒 FB999 Secure Access</h2>
        <form method="POST" action="/login">
            <input type="text" name="access_key" placeholder="Enter Your Access Key" required autocomplete="off">
            <button type="submit">Access</button>
        </form>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
    </div>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FB999 Admin Dashboard</title>
    <style>
        body {
            background-color: #0d1117;
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .container {
            width: 100%;
            max-width: 500px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
        }
        h2 { color: #f0883e; margin: 0; }
        .logout { color: #f85149; text-decoration: none; font-weight: bold; }
        .card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        input {
            width: 100%;
            padding: 12px;
            background: #0d1117;
            border: 1px solid #30363d;
            color: white;
            border-radius: 8px;
            box-sizing: border-box;
            margin-bottom: 12px;
        }
        button {
            width: 100%;
            padding: 12px;
            background: #2ea043;
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
        }
        button:hover { background: #238636; }
        ul { padding-left: 20px; color: #8b949e; }
        li { margin-bottom: 8px; font-family: monospace; font-size: 15px; color: #c9d1d9; }
        .action-link {
            display: block;
            text-align: center;
            margin-top: 15px;
            background: #21262d;
            color: #f0883e;
            padding: 12px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: bold;
            border: 1px solid #30363d;
        }
        .action-link:hover { background: #30363d; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>👑 Admin Control Panel</h2>
            <a href="/logout" class="logout">Logout</a>
        </div>

        <div class="card">
            <h3>Add New Access Key</h3>
            <form method="POST" action="/admin/add_key">
                <input type="text" name="new_key" placeholder="Enter new user key (e.g. USER-JACK-123)" required autocomplete="off">
                <button type="submit">Add Key</button>
            </form>
            {% if msg %}
            <p style="color: #2ea043; font-size: 13px; margin-top: 10px;">{{ msg }}</p>
            {% endif %}
        </div>

        <div class="card">
            <h3>Active Authorized Keys</h3>
            <ul>
                {% for k in keys %}
                <li>{{ k }}</li>
                {% endfor %}
            </ul>
        </div>

        <a href="/" class="action-link">👉 Go to Signal Dashboard</a>
    </div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
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
        .status-active { color: #2ea043; font-weight: 600; }
        .logout { color: #f85149; text-decoration: none; font-weight: 600; }
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
        .tf-btn.active { background: #f0883e; color: #000000; }
        .period-card {
            background: #161b22;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            margin-bottom: 20px;
            border: 1px solid #30363d;
        }
        .period-title { color: #8b949e; font-size: 12px; letter-spacing: 1px; margin-bottom: 5px; }
        .period-num { font-size: 18px; font-weight: bold; margin-bottom: 12px; }
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
        }
        .action-btn:hover { background: #30363d; }
        .grading-row { display: flex; gap: 10px; margin-bottom: 25px; }
        .win-btn { background: #2ea043; color: white; border: none; flex: 1; padding: 12px; border-radius: 8px; font-weight: bold; cursor: pointer; }
        .loss-btn { background: #f85149; color: white; border: none; flex: 1; padding: 12px; border-radius: 8px; font-weight: bold; cursor: pointer; }
        .history-card { background: #161b22; border-radius: 12px; padding: 15px; border: 1px solid #30363d; }
        .history-table { width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }
        .history-table th { color: #8b949e; padding-bottom: 10px; font-weight: 600; border-bottom: 1px solid #30363d; }
        .history-table td { padding: 10px 0; border-bottom: 1px solid #21262d; }
        .result-win { color: #2ea043; font-weight: bold; }
        .result-loss { color: #f85149; font-weight: bold; }
        .result-pending { color: #f0883e; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="status-active">🟢 Status: Active Key</span>
            <div>
                {% if is_admin %}
                <a href="/admin" style="color: #f0883e; margin-right: 12px; text-decoration: none; font-weight: bold;">Admin Panel</a>
                {% endif %}
                <a href="/logout" class="logout">Logout</a>
            </div>
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
                <span class="stage-badge">Stage {{
