import os
import json
import random
from datetime import datetime, timezone
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-web-dashboard-key-2026")

# --- AUTHORIZED ACCESS KEYS ---
# You can add or change your master admin keys and user keys here anytime!
VALID_ACCESS_KEYS = [
    "FB999-VIP-OWNER-777",
    "FB999-USER-888224",
    "FB999-PRO-KEY-1028"
]

# Session state tracking
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
            <button type="submit">Access Dashboard</button>
        </form>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
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
            border-radius
