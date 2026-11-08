from datetime import datetime, timedelta, timezone
import json
import os
import random
import threading
import time
import urllib.request
from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-win-go-key-2026")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "9237583887:AAEquYRmXGWJZwtmgrRTipR7_LicQE_5btU")
AUTHORIZED_USER_ID = "8842031370"
ADMIN_PASSWORD = "ADMIN-MASTER-2026"

VALID_KEYS = {
    "VIP-DEMO-1234": {"expires_at": None, "duration_label": "Permanent"},
    "PRO-WIN-9999": {"expires_at": None, "duration_label": "Permanent"}
}

stored_predictions = {30: {}, 60: {}, 180: {}, 300: {}}
prediction_cache = {}

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Win Go Dashboard</title>
    <style>
        body { background-color: #0b1329; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .login-card { background: #17223b; border-radius: 12px; padding: 24px; width: 100%; max-width: 360px; border: 1px solid #22304f; text-align: center; box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
        h2 { margin-bottom: 8px; color: #f59e0b; }
        p { color: #8f9bb3; font-size: 13px; margin-bottom: 20px; }
        input { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #334155; background: #0b1329; color: #fff; font-size: 14px; margin-bottom: 14px; box-sizing: border-box; text-align: center; }
        button { background: linear-gradient(135deg, #f59e0b, #d97706); color: #0b1329; font-weight: 700; width: 100%; padding: 12px; border: none; border-radius: 8px; cursor: pointer; font-size: 15px; }
        .error { color: #f87171; font-size: 12px; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>🔒 Restricted Access</h2>
        <p>Enter your assigned license key to access the dashboard.</p>
        <form method="POST">
            <input type="text" name="key" placeholder="Enter Access Key (e.g. WIN-VIP-...)" required autocomplete="off">
            <button type="submit">Access Dashboard</button>
        </form>
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
    </div>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Key Generator Admin Panel</title>
    <style>
        body { background-color: #0b1329; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 20px; display: flex; justify-content: center; }
        .container { width: 100%; max-width: 480px; }
        .card { background: #17223b; border-radius: 12px; padding: 20px; border: 1px solid #22304f; margin-bottom: 20px; }
        h2 { color: #f59e0b; margin-top: 0; text-align: center; }
        input, select, button { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #334155; background: #0b1329; color: #fff; font-size: 14px; margin-bottom: 12px; box-sizing: border-box; }
        button { background: #34d399; color: #0b1329; font-weight: 700; cursor: pointer; border: none; }
        .key-box { background: #0b1329; padding: 12px; border-radius: 6px; font-family: monospace; color: #34d399; text-align: center; margin-bottom: 10px; border: 1px dashed #34d399; font-size: 16px; font-weight: bold; }
        ul { padding-left: 0; list-style: none; font-size: 13px; color: #94a3b8; }
        li { background: #0b1329; padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; border: 1px solid #22304f; display: flex; justify-content: space-between; }
    </style>
</head>
<body>
<div class="container">
    <div class="card">
        <h2>⚡ Key Generator Admin</h2>
        {% if not logged_in %}
            <form method="POST">
                <input type="password" name="admin_pass" placeholder="Enter Admin Master Password" required>
                <button type="submit">Login to Admin</button>
            </form>
            {% if error %}<p style="color: #f87171; text-align: center;">{{ error }}</p>{% endif %}
        {% else %}
            <form method="POST">
                <input type="hidden" name="action" value="generate">
                <label style="font-size: 12px; color: #8f9bb3; display: block; margin-bottom: 4px;">Select Key Expiration Time:</label>
                <select name="duration">
                    <option value="1h">1 Hour Access</option>
                    <option value="24h" selected>24 Hours (1 Day)</option>
                    <option value="7d">7 Days Access</option>
                    <option value="never">Permanent (Never Expires)</option>
                </select>
                <button type="submit">🔑 Generate New Access Key</button>
            </form>

            {% if new_key %}
                <p style="margin-top: 15px; margin-bottom: 5px;">New Key Created ({{ duration_label }}):</p>
                <div class="key-box">{{ new_key }}</div>
            {% endif %}

            <h3 style="margin-top: 20px; font-size: 15px; color: #cbd5e1;">Active Keys Database:</h3>
            <ul>
                {% for k, data in keys.items() %}
                    <li>
                        <span><b>{{ k }}</b></span>
                        <span style="color: #34d399;">{{ data.duration_label }}</span>
                    </li>
                {% endfor %}
            </ul>
            <p style="text-align: center; margin-top: 20px;"><a href="/logout" style="color: #f87171; text-decoration: none; font-size: 13px;">Log out from admin</a></p>
        {% endif %}
    </div>
</div>
</body>
</html>
"""

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
        .top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 12px; }
        .logout-link { color: #f87171; text-decoration: none; font-weight: 600; }
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
        .table-header { display: grid; grid-template-columns: 1.8fr 1.2fr 1fr; background: #22304f; padding: 10px 12px; font-size: 11px; font-weight: 700; text-transform: uppercase; color: #8f9bb3; text-align: center; position: sticky; top: 0; z-index: 10; }
        .table-row { display: grid; grid-template-columns: 1.8fr 1.2fr 1fr; padding: 12px; align-items: center; border-bottom: 1px solid #22304f; font-size: 13px; text-align: center; }
        .col-period { font-family: monospace; font-size: 12px; color: #cbd5e1; text-align: left; }
        .col-bet { font-weight: 600; color: #a5b4fc; font-family: monospace; }
        .result-win { color: #34d399; font-weight: 700; }
        .result-loss { color: #f87171; font-weight: 700; }
        .result-pending { color: #94a3b8; font-weight: 600; }
    </style>
</head>
<body>
<div class="container">
    <div class="top-bar">
        <span style="color: #34d399;">● Status: Active Key</span>
        <a href="/logout" class="logout-link">Logout</a>
    </div>
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
            <div>Bet</div>
            <div>Result</div>
        </div>
        <div id="history-container">
            <div class="table-row"><div style="text-align: center;" colspan="3">Loading history...</div></div>
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
            if (res.status === 401) { window.location.href = '/login'; return; }
            const data = await res.json();
            document.getElementById('period-display').innerText = "Period: " + data.upcoming_period;
            document.getElementById('pred-display').innerText = data.prediction.size + " (" + data.prediction.number + ")";
            document.getElementById('rate-display').innerText = "Win Rate: " + data.win_rate + "%";
            let html = '';
            data.history.forEach(item => {
                let resClass = 'result-pending';
                if (item.result === 'Win') resClass = 'result-win';
                else if (item.result === 'Loss') resClass = 'result-loss';

                html += `
                    <div class="table-row">
                        <div class="col-period">${item.period}</div>
                        <div class="col-bet">${item.bet}</div>
                        <div class="${resClass}">${item.result}</div>
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

def is_key_valid(key):
    if key not in VALID_KEYS:
        return False
    key_info = VALID_KEYS[key]
    expires_at = key_info.get("expires_at")
    if expires_at and datetime.now(timezone.utc) > expires_at:
        return False
    return True

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        key = request.form.get("key", "").strip()
        if is_key_valid(key):
            session["user_key"] = key
            return redirect(url_
