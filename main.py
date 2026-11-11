import os
import random
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "render-secure-key-2026")

MASTER_ADMIN_KEY = "OWNER-ADMIN-2026"

# Structured keys: stores expiration timestamps (None = Permanent)
ACCESS_KEYS = {
    "OWNER-ADMIN-2026": {"duration": "Permanent", "expires": None},
    "FB999-VIP-OWNER-777": {"duration": "Permanent", "expires": None},
    "FB999-USER-888224": {"duration": "24 Hours", "expires": (datetime.now(timezone.utc) + timedelta(days=1)).timestamp()}
}

USER_STATE = {
    "timeframe": "1m",
    "stage": 1,
    "current_bet": "BIG",
    "current_num": 6,
    "pending_period": None,
    "history": [
        {"period": "20261111100010333", "bet": "SMALL", "result": "Win"},
        {"period": "20261111100010332", "bet": "SMALL", "result": "Loss"}
    ]
}

def get_current_period(timeframe="1m"):
    now = datetime.now(timezone.utc)
    date_prefix = now.strftime("%Y%m%d")
    total_secs = (now.hour * 3600) + (now.minute * 60) + now.second
    
    if timeframe == "30s":
        idx = (total_secs // 30) + 100020001
    elif timeframe == "3m":
        idx = (total_secs // 180) + 100030001
    elif timeframe == "5m":
        idx = (total_secs // 300) + 100050001
    else:  # 1m
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
        body { background-color: #0d1117; color: #fff; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-box { background: #161b22; border: 1px solid #30363d; padding: 30px; border-radius: 12px; width: 100%; max-width: 350px; text-align: center; }
        h2 { color: #f0883e; }
        input { width: 100%; padding: 12px; background: #0d1117; border: 1px solid #30363d; color: white; border-radius: 8px; box-sizing: border-box; margin-bottom: 15px; text-align: center; }
        button { width: 100%; padding: 12px; background: #f0883e; color: #000; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }
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
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
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
    <title>Admin Dashboard</title>
    <style>
        body { background-color: #0d1117; color: #fff; font-family: sans-serif; padding: 20px; display: flex; flex-direction: column; align-items: center; }
        .container { width: 100%; max-width: 500px; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
        input, select { width: 100%; padding: 12px; background: #0d1117; border: 1px solid #30363d; color: white; border-radius: 8px; box-sizing: border-box; margin-bottom: 12px; }
        button { width: 100%; padding: 12px; background: #2ea043; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }
        a { color: #f0883e; text-decoration: none; font-weight: bold; }
        ul { padding-left: 0; list-style: none; }
        li { background: #0d1117; padding: 10px; border: 1px solid #30363d; margin-bottom: 8px; border-radius: 6px; display: flex; justify-content: space-between; font-size: 13px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>👑 Admin Control Panel</h2>
        <div class="card">
            <h3>Generate / Add Timed Key</h3>
            <form method="POST" action="/admin/add_key">
                <input type="text" name="new_key" placeholder="Enter custom key string" required>
                <select name="duration">
                    <option value="24h">24 Hours Access</option>
                    <option value="7d">7 Days Access</option>
                    <option value="30d">1 Month Access</option>
                    <option value="permanent">Permanent Access</option>
                </select>
                <button type="submit">Create Key</button>
            </form>
            {% if msg %}<p style="color: #2ea043; font-size: 13px; margin-top: 10px;">{{ msg }}</p>{% endif %}
        </div>
        <div class="card">
            <h3>Active Keys & Durations</h3>
            <ul>
                {% for k, info in keys.items() %}
                <li>
                    <span><strong>{{ k }}</strong></span>
                    <span style="color: #8b949e;">({{ info.duration }})</span>
                </li>
                {% endfor %}
            </ul>
        </div>
        <a href="/">👉 Go to Signal Dashboard</a> | <a href="/logout" style="color:#f85149; float:right;">Logout</a>
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
    <title>Wingo Dashboard</title>
    <style>
        body { background-color: #0d1117; color: #fff; font-family: sans-serif; margin: 0; padding: 15px; display: flex; flex-direction: column; align-items: center; }
        .container { width: 100%; max-width: 480px; }
        .tf-row { display: flex; gap: 5px; margin-bottom: 15px; }
        .tf-btn { flex: 1; padding: 8px; background: #161b22; border: 1px solid #30363d; color: #8b949e; border-radius: 6px; font-weight: bold; cursor: pointer; text-align: center; text-decoration: none; font-size: 13px; }
        .tf-btn.active { background: #f0883e; color: #000; border-color: #f0883e; }
        .period-card { background: #161b22; border-radius: 12px; padding: 20px; text-align: center; border: 1px solid #30363d; margin-bottom: 20px; }
        .prediction-box { background: linear-gradient(135deg, #f0883e, #d86c24); color: #000; font-size: 26px; font-weight: 900; padding: 22px; border-radius: 12px; margin: 15px 0; }
        .btn-row { display: flex; gap: 10px; margin-bottom: 20px; }
        .win-btn { background: #2ea043; color: white; border: none; flex: 1; padding: 12px; border-radius: 8px; font-weight: bold; cursor: pointer; }
        .loss-btn { background: #f85149; color: white; border: none; flex: 1; padding: 12px; border-radius: 8px; font-weight: bold; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; background: #161b22; border-radius: 12px; overflow: hidden; }
        th, td { padding: 10px; border-bottom: 1px solid #30363d; text-align: left; }
        th { color: #8b949e; }
    </style>
</head>
<body>
    <div class="container">
        <div style="display:flex; justify-content:space-between; margin-bottom:15px;">
            <span style="color: #2ea043; font-weight:bold;">🟢 Active</span>
            <div>
                {% if is_admin %}<a href="/admin" style="color: #f0883e; margin-right: 15px;">Admin Panel</a>{% endif %}
                <a href="/logout" style="color: #f85149; text-decoration:none;">Logout</a>
            </div>
        </div>
        
        <div class="tf-row">
            <a href="/set_tf/30s" class="tf-btn {% if tf == '30s' %}active{% endif %}">30s</a>
            <a href="/set_tf/1m" class="tf-btn {% if tf == '1m' %}active{% endif %}">1m</a>
            <a href="/set_tf/3m" class="tf-btn {% if tf == '3m' %}active{% endif %}">3m</a>
            <a href="/set_tf/5m" class="tf-btn
