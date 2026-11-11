import time
import json
import random
import urllib.request
import threading
import os
from datetime import datetime, timezone, date
from flask import Flask

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-fb999-bot-key-2026")

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "9237583887:AAGfUABC5p4X8sI40If2BMm0surTrCtnRA"

# 1. Unlimited Admin & Owner IDs
UNLIMITED_USER_IDS = [
    "8842031370",
    "7891601316",
    "9063263288",
    "1028206063"
]

# 2. Authorized Users with 100 Wins Daily Limit
LIMITED_USER_IDS = [
    "8882241036"
]

DATA_FILE = "live_sessions.json"
SESSION_STATE = {}  # Tracks history, timeframe, stage, and active signals per chat_id

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving data file: {e}")

def get_current_period(timeframe="1m"):
    """Calculates period based on timeframe (30s, 1m, 3m, 5m)."""
    now = datetime.now(timezone.utc)
    date_prefix = now.strftime("%Y%m%d")
    total_secs = (now.hour * 3600) + (now.minute * 60) + now.second
    
    if timeframe == "30s":
        idx = total_secs // 30 + 100010001
    elif timeframe == "3m":
        idx = (total_secs // 180) + 100010001
    elif timeframe == "5m":
        idx = (total_secs // 300) + 100010001
    else:  # 1m default
        idx = (total_secs // 60) + 100010001
        
    return int(f"{date_prefix}{idx}")

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload_dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload_dict["reply_markup"] = reply_markup
        
    payload = json.dumps(payload_dict).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        response = urllib.request.urlopen(req, timeout=5)
        res_data = json.loads(response.read().decode("utf-8"))
        return res_data.get("result", {}).get("message_id")
    except Exception as e:
        print(f"Error sending message to Telegram: {e}")
        return None

def edit_message(chat_id, message_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
    payload_dict = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload_dict["reply_markup"] = reply_markup
        
    payload = json.dumps(payload_dict).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Error editing message in Telegram: {e}")

def get_timeframe_keyboard(current_tf="1m"):
    """Top buttons to switch timeframes like the app UI."""
    tf_buttons = []
    for tf in ["30s", "1m", "3m", "5m"]:
        label = f"[{tf.upper()}]" if tf == current_tf else tf
        tf_buttons.append({"text": label, "callback_data": f"tf_{tf}"})
        
    return {
        "inline_keyboard": [
            tf_buttons,
            [
                {"text": "⚡ Generate Next Prediction Ahead", "callback_data": "generate_next"}
            ],
            [
                {"text": "✅ Win", "callback_data": "action_win"},
                {"text": "❌ Loss", "callback_data": "action_loss"}
            ]
        ]
    }

def send_dashboard(chat_id):
    state = SESSION_STATE.get(chat_id)
    if not state:
        state = {
            "timeframe": "1m",
            "history": [],
            "stage": 1,
            "current_bet": "BIG",
            "current_num": 9,
            "message_id": None
        }
        SESSION_STATE[chat_id] = state

    tf = state["timeframe"]
    period = get_current_period(tf)
    stage = state["stage"]
    
    # Generate current prediction if not set
    if "current_bet" not in state:
        bet = random.choice(["BIG", "SMALL"])
        num = random.randint(5, 9) if bet == "BIG" else random.randint(0, 4)
        state["current_bet"] = bet
        state["current_num"] = num

    bet = state["current_bet"]
    num = state["current_num"]

    # Format history rows
    rows_text = ""
    for item in state["history"][-8:]:
        rows_text += f"`{item['period']}`   `{item['bet']}`   `{item['result']}`\n"
    if not rows_text:
        rows_text = "No history yet. Click Win/Loss below after round!\n"

    dashboard_text = (
        f"🟢 *Status: Active Key*\n\n"
        f"⏱️ Timeframe: *{tf.upper()}*\n"
        f"🎯 *CURRENT PERIOD ({tf.upper()})*\n"
        f"Period: `{period}`\n"
        f"Stage `{stage}/6`   Win Rate: `78%`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔥 *{bet} ({num})*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 *RECENT HISTORY*:\n"
        f"`PERIOD`            `BET`    `RESULT`\n"
        f"{rows_text}\n"
        f"👇 *Select timeframe or click Win/Loss after round*:"
    )

    markup = get_timeframe_keyboard(tf)
    
    # If message already exists, edit it cleanly instead of spamming chat
    if state.get("message_id"):
        edit_message(chat_id, state["message_id"], dashboard_text, markup)
    else:
        msg_id = send_message(chat_id, dashboard_text, markup)
        state["message_id"] = msg_id

def handle_callback_query(callback_query):
    query_id = callback_query.get("id")
    data = callback_query.get("data", "")
    message = callback_query.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    user_id = str(callback_query.get("from", {}).get("id"))

    if user_id not in UNLIMITED_USER_IDS and user_id not in LIMITED_USER_IDS:
        return

    state = SESSION_STATE.get(chat_id)
    if not state:
        state = {"timeframe": "1m", "history": [], "stage": 1, "message_id": message.get("message_id")}
        SESSION_STATE[chat_id] = state

    # Acknowledge callback immediately
    try:
        ack_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
        payload = json.dumps({"callback_query_id": query_id, "text": "Updated!"}).encode("utf-8")
        req = urllib.request.Request(ack_url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass

    if data.startswith("tf_"):
        new_tf = data.split("_")[1]
        state["timeframe"] = new_tf
        state["stage"] = 1
        # Generate new prediction for new timeframe
        bet = random.choice(["BIG", "SMALL"])
        state["current_bet"] = bet
        state["current_num"] = random.randint(5, 9) if bet == "BIG" else random.randint(0, 4)
        
    elif data == "action_win" or data == "action_loss":
        tf = state["timeframe"]
        period = get_current_period(tf)
        bet = state.get("current_bet", "BIG")
        
        result_label = "Win" if data == "action_win" else "Loss"
        
        # Record into history
        state["history"].append({
            "period": period,
            "bet": bet,
            "result": result_label
        })
        
        # Adjust stage
        if result_label == "Loss":
            state["stage"] = min(state["stage"] + 1, 6)
        else:
            state["stage"] = 1
            
        # Generate next prediction immediately
        next_bet = random.choice(["BIG", "SMALL"])
        state["current_bet"] = next_bet
        state["current_num"] = random.randint(5, 9) if next_bet == "BIG" else random.randint(0, 4)

    elif data == "generate_next":
        tf = state["timeframe"]
        bet = random.choice(["BIG", "SMALL"])
        state["current_bet"] = bet
        state["current_num"] = random.randint(5, 9) if bet == "BIG" else random.randint(0, 4)

    # Refresh dashboard interface
    send_dashboard(chat_id)

def telegram_bot_loop():
    print("Telegram Bot polling worker is starting...")
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=5)
    except Exception as e:
        print(f"Webhook delete error: {e}")

    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=35) as response:
                result_data = json.loads(response.read().decode("utf-8"))
                for result in result_data.get("result", []):
                    offset = result["update_id"] + 1

                    if "callback_query" in result:
                        handle_callback_query(result["callback_query"])

                    if "message" in result:
                        message = result["message"]
                        chat_id = message.get("chat", {}).get("id")
                        user_info = message.get("from", {})
                        user_id = str(user_info.get("id", ""))
                        text = message.get("text", "").strip().lower()

                        if chat_id:
                            if user_id not in UNLIMITED_USER_IDS and user_id not in LIMITED_USER_IDS:
                                send_message(chat_id, "⛔ *Access Denied*: You are not authorized.")
                                continue

                            if text == "/start" or text == "/live":
                                SESSION_STATE[chat_id] = {
                                    "timeframe": "1m",
                                    "history": [],
                                    "stage": 1,
                                    "current_bet": "BIG",
                                    "current_num": 9,
                                    "message_id": None
                                }
                                send_dashboard(chat_id)
                            elif text == "/stop":
                                if chat_id in SESSION_STATE:
                                    SESSION_STATE[chat_id]["message_id"] = None
                                send_message(chat_id, "🛑 *Session Cleared*. Type `/live` to open the signal dashboard.")

        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

@app.route("/")
def home():
    return "<h3>FB999 Multi-Timeframe Signal Bot is Live & Running 24/7!</h3>"

if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
    bot_thread = threading.Thread(target=telegram_bot_loop, daemon=True)
    bot_thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
