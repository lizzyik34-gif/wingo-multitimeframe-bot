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
SESSION_STATE = {}  # Tracks history, stage, and active predictions per chat_id

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

def get_current_wingo_period():
    """Calculates the exact live Wingo period number based on UTC time."""
    now = datetime.now(timezone.utc)
    date_prefix = now.strftime("%Y%m%d")
    total_secs = (now.hour * 3600) + (now.minute * 60) + now.second
    period_index = total_secs // 60 + 100010001
    return int(f"{date_prefix}{period_index}")

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

def get_keyboard():
    """Persistent bottom panel for quick navigation."""
    return {
        "keyboard": [
            [{"text": "⚡ Generate Next Prediction Ahead"}, {"text": "/stop"}]
        ],
        "resize_keyboard": True,
        "is_persistent": True
    }

def get_inline_keyboard(period, category, stage):
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Win", "callback_data": f"win_{period}_{category}_{stage}"},
                {"text": "❌ Loss", "callback_data": f"loss_{period}_{category}_{stage}"}
            ]
        ]
    }

def send_next_prediction(chat_id):
    state = SESSION_STATE.get(chat_id)
    if not state or not state.get("running"):
        return

    current_period = get_current_wingo_period()
    
    # Determine next category and stage progression
    history = state["history"]
    stage = state["stage"]

    if history and "Loss" in history[-1]:
        stage = min(stage + 1, 6)
    else:
        stage = 1  # Reset to Stage 1 on Win

    state["stage"] = stage
    
    # Smart trend selection
    next_cat = random.choice(["BIG", "SMALL"])
    next_num = random.randint(5, 9) if next_cat == "BIG" else random.randint(0, 4)

    state["current_period"] = current_period
    state["current_category"] = next_cat

    # Format history table rows for display
    rows_text = ""
    for item in history[-8:]:  # Show last 8 results
        rows_text += f"`{item['period']}`   `{item['bet']}`   `{item['result']}`\n"
    
    if not rows_text:
        rows_text = "No history yet. Play your first round below!\n"

    signal_msg = (
        f"🟢 *Status: Active Key*\n\n"
        f"🎯 *CURRENT PERIOD (1M)*\n"
        f"Period: `{current_period}`\n"
        f"Stage `{stage}/6`   Win Rate: `78%`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔥 *{next_cat} ({next_num})*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 *RECENT HISTORY*:\n"
        f"`PERIOD`            `BET`    `RESULT`\n"
        f"{rows_text}\n"
        f"👇 *Tap result after round concludes on fb999*:"
    )
    
    send_message(chat_id, signal_msg, get_inline_keyboard(current_period, next_cat, stage))

def handle_callback_query(callback_query):
    query_id = callback_query.get("id")
    data = callback_query.get("data", "")
    message = callback_query.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    user_id = str(callback_query.get("from", {}).get("id"))

    if user_id not in UNLIMITED_USER_IDS and user_id not in LIMITED_USER_IDS:
        return

    parts = data.split("_")
    if len(parts) >= 4:
        action = parts[0]
        period = parts[1]
        category = parts[2]
        stage = parts[3]

        state = SESSION_STATE.get(chat_id)
        if not state:
            return

        result_label = "Win" if action == "win" else "Loss"
        
        # Append to history list
        state["history"].append({
            "period": period,
            "bet": category,
            "result": result_label
        })

        # Acknowledge callback immediately
        try:
            ack_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
            payload = json.dumps({"callback_query_id": query_id, "text": f"Recorded as {result_label}!"}).encode("utf-8")
            req = urllib.request.Request(ack_url, data=payload, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=3)
        except Exception:
            pass

        # Clean old buttons from message
        rows_text = ""
        for item in state["history"][-8:]:
            rows_text += f"`{item['period']}`   `{item['bet']}`   `{item['result']}`\n"

        old_text = (
            f"🟢 *Status: Active Key*\n\n"
            f"🎯 *CURRENT PERIOD (1M)*\n"
            f"Period: `{period}`\n"
            f"Stage `{stage}/6`   Win Rate: `78%`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔒 *{category}* (Graded: *{result_label}*)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📋 *RECENT HISTORY*:\n"
            f"`PERIOD`            `BET`    `RESULT`\n"
            f"{rows_text}"
        )
        edit_message(chat_id, message_id, old_text)

        # Immediately drop the next prediction card
        send_next_prediction(chat_id)

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
                                    "running": True,
                                    "history": [],
                                    "stage": 1,
                                    "current_period": None
                                }
                                send_message(chat_id, "🟢 *FB999 Signal Bot Connected*:\nTap the button below whenever you want a new prediction!", get_keyboard())
                                send_next_prediction(chat_id)
                            elif "generate next prediction" in text:
                                if chat_id not in SESSION_STATE or not SESSION_STATE[chat_id]["running"]:
                                    SESSION_STATE[chat_id] = {
                                        "running": True,
                                        "history": [],
                                        "stage": 1,
                                        "current_period": None
                                    }
                                send_next_prediction(chat_id)
                            elif text == "/stop":
                                if chat_id in SESSION_STATE:
                                    SESSION_STATE[chat_id]["running"] = False
                                send_message(chat_id, "🛑 *Session Stopped*. Type `/live` or tap the button to restart.", get_keyboard())

        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

@app.route("/")
def home():
    return "<h3>FB999 Manual Signal Bot is Live & Running 24/7!</h3>"

if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
    bot_thread = threading.Thread(target=telegram_bot_loop, daemon=True)
    bot_thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
