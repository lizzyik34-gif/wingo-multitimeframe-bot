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

permanent_history = {30: {}, 60: {}, 180: {}, 300: {}}
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
        .prediction-btn { background: linear-gradient(
