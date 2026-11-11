import os
import random
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "render-secure-key-2026")

MASTER_ADMIN_KEY = "OWNER-ADMIN-2026"

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
            <h3>Generate Timed Key</h3>
            <form method="POST" action="/admin/add_key">
                <input type="text" name="new_key" placeholder="Enter key string" required>
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
            <h3>Active Keys</h3>
            <ul>
                {% for k, info in keys.items() %}
                <li><span><strong>{{ k }}</strong></span><span style="color: #8b949e;">({{ info.duration }})</span></li>
                {% endfor %}
            </ul>
        </div>
        <a href="/">👉 Go to Dashboard</a> | <a href="/logout" style="color:#f85149; float:right;">Logout</a>
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
            <a href="/set_tf/5m" class="tf-btn {% if tf == '5m' %}active{% endif %}">5m</a>
        </div>
        <div class="period-card">
            <div style="color: #8b949e; font-size: 12px;">CURRENT PERIOD ({{ tf.upper() }})</div>
            <div style="font-size: 18px; font-weight: bold; margin: 10px 0;">Period: {{ period }}</div>
            <div class="prediction-box">{{ bet }} ({{ num }})</div>
        </div>
        <div class="btn-row">
            <button class="win-btn" onclick="record('Win')">✅ Win</button>
            <button class="loss-btn" onclick="record('Loss')">❌ Loss</button>
        </div>
        <table>
            <thead><tr><th>Period</th><th>Bet</th><th>Result</th></tr></thead>
            <tbody>
                {% if pending %}<tr><td>{{ pending.period }}</td><td>{{ pending.bet }}</td><td style="color:#f0883e;">Pending...</td></tr>{% endif %}
                {% for row in history %}<tr><td>{{ row.period }}</td><td>{{ row.bet }}</td><td style="color: {% if row.result == 'Win' %}#2ea043{% else %}#f85149{% endif %};">{{ row.result }}</td></tr>{% endfor %}
            </tbody>
        </table>
    </div>
    <script>
        function record(res) {
            fetch('/api/record', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({result: res})})
            .then(() => location.reload());
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    tf = USER_STATE["timeframe"]
    period = get_current_period(tf)
    if USER_STATE["pending_period"] is None:
        USER_STATE["pending_period"] = str(period)
    pending = {"period": USER_STATE["pending_period"], "bet": USER_STATE["current_bet"]}
    return render_template_string(DASHBOARD_TEMPLATE, period=period, bet=USER_STATE["current_bet"], num=USER_STATE["current_num"], pending=pending, history=USER_STATE["history"], is_admin=session.get("is_admin", False), tf=tf)

@app.route("/set_tf/<tf>")
def set_timeframe(tf):
    if tf in ["30s", "1m", "3m", "5m"]:
        USER_STATE["timeframe"] = tf
        USER_STATE["pending_period"] = str(get_current_period(tf))
    return redirect(url_for("index"))

@app.route("/admin", methods=["GET"])
def admin_panel():
    if not session.get("is_admin"):
        return redirect(url_for("index"))
    return render_template_string(ADMIN_TEMPLATE, keys=ACCESS_KEYS, msg="")

@app.route("/admin/add_key", methods=["POST"])
def add_key():
    if not session.get("is_admin"):
        return redirect(url_for("index"))
    new_key = request.form.get("new_key", "").strip()
    duration_choice = request.form.get("duration", "24h")
    if new_key:
        now = datetime.now(timezone.utc)
        if duration_choice == "24h":
            expires = (now + timedelta(days=1)).timestamp()
            label = "24 Hours"
        elif duration_choice == "7d":
            expires = (now + timedelta(days=7)).timestamp()
            label = "7 Days"
        elif duration_choice == "30d":
            expires = (now + timedelta(days=30)).timestamp()
            label = "1 Month"
        else:
            expires = None
            label = "Permanent"
        ACCESS_KEYS[new_key] = {"duration": label, "expires": expires}
        msg = f"Created key '{new_key}' ({label})!"
    else:
        msg = "Key cannot be empty!"
    return render_template_string(ADMIN_TEMPLATE, keys=ACCESS_KEYS, msg=msg)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        key = request.form.get("access_key", "").strip()
        if key == MASTER_ADMIN_KEY:
            session["authenticated"] = True
            session["is_admin"] = True
            return redirect(url_for("admin_panel"))
        elif key in ACCESS_KEYS:
            key_data = ACCESS_KEYS[key]
            if key_data["expires"] is not None and datetime.now(timezone.utc).timestamp() > key_data["expires"]:
                error = "This Access Key has expired!"
            else:
                session["authenticated"] = True
                session["is_admin"] = False
                return redirect(url_for("index"))
        else:
            error = "Invalid Access Key!"
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/api/record", methods=["POST"])
def record():
    if not session.get("authenticated"): return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    result = data.get("result", "Win")
    period_to_record = USER_STATE["pending_period"] or str(get_current_period(USER_STATE["timeframe"]))
    USER_STATE["history"].insert(0, {"period": period_to_record, "bet": USER_STATE["current_bet"], "result": result})
    USER_STATE["pending_period"] = str(get_current_period(USER_STATE["timeframe"]))
    bet = random.choice(["BIG", "SMALL"])
    USER_STATE["current_bet"] = bet
    USER_STATE["current_num"] = random.randint(5, 9) if bet == "BIG" else random.randint(0, 4)
    return jsonify({"success": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
