import logging
import random
import csv
import os
import uuid
import requests
import json
import re


from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN = "8538111446:AAGW1s_1wgM-gYbryx5ZxIji5VJODbbzTqg"  
TASKS_FILE = "tasks.csv"
CSV_COLUMNS = ["Task_ID", "Assignee", "Description", "Status"]


# ── CSV helpers ───────────────────────────────────────────────────────────────
def _ensure_csv() -> None:
    """Create tasks.csv with headers if it doesn't exist yet."""
    if not os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
        logger.info("Created new %s", TASKS_FILE)


def _read_rows() -> list[dict]:
    _ensure_csv()
    with open(TASKS_FILE, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_rows(rows: list[dict]) -> None:
    with open(TASKS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def add_task(assignee: str, description: str, status: str) -> str:
    """Append a new task row and return its generated Task_ID."""
    _ensure_csv()
    task_id = str(uuid.uuid4())[:8].upper()   # short unique ID, e.g. "3F7A1C2B"
    new_row = {
        "Task_ID": task_id,
        "Assignee": assignee,
        "Description": description,
        "Status": status,
    }
    with open(TASKS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writerow(new_row)
    logger.info("Added task %s for %s → '%s'", task_id, assignee, description)
    return task_id


def update_task_status(assignee: str, description: str, new_status: str) -> bool:
    rows = _read_rows()
    updated = False
    
    # Extract keywords (ignore small words like 'a', 'the', 'is')
    ignore_words = {"a", "the", "is", "of", "to", "for", "in", "on", "at", "has", "completed"}
    input_words = set(re.findall(r'\w+', description.lower())) - ignore_words
    search_assignee = assignee.strip().lower()

    for row in rows:
        row_id = row["Task_ID"].strip().lower()
        row_desc_words = set(re.findall(r'\w+', row["Description"].lower())) - ignore_words
        row_assignee = row["Assignee"].strip().lower()

        if row_assignee == search_assignee:
            # 1. Direct ID match
            if description.strip().lower() == row_id:
                row["Status"] = new_status
                updated = True
                break
            
            # 2. Keyword Overlap (Smart Match)
            # If 50% or more of the keywords match, consider it a success
            common_words = input_words.intersection(row_desc_words)
            if len(common_words) > 0 and (len(common_words) / len(row_desc_words) >= 0.5):
                row["Status"] = new_status
                updated = True
                logger.info(f"Keyword Match Success: {common_words}")
                break 

    if updated:
        _write_rows(rows)
    return updated


# ── Mock AI function (replace with real implementation later) ─────────────────
def analyze_text_with_agnes(chat_text: str) -> dict:
    # 1. The Prompt we engineered earlier
    system_prompt = """
    You are Mr. Krabs, the money-loving manager of the Krusty Krab. 
    You are parsing group chat messages to manage tasks.
    
    1. If a task is assigned: {"action": "add", "assignee": "@username", "task": "description", "status": "Pending"}
    2. If a task is finished: {"action": "update", "assignee": "@username", "task": "description_or_id", "status": "Completed"}
    
    CRITICAL: Output ONLY valid JSON. However, in your heart, you only care about efficiency and 'me money'.
    """
    
    # 2. Your Agnes API details from ZenMux
    api_url = "https://zenmux.ai/api/v1/chat/completions"
    api_key = "sk-ai-v1-5894088725d5c60ca7503eb832336db52ac1b33ce22a97e51ca06c483279a1f8"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "sapiens-ai/agnes-1.5-pro", 
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": chat_text}
        ],
        "temperature": 0.1
    }
    
    try:
        # 3. Call the API
        response = requests.post(api_url, headers=headers, json=payload)
        response_text = response.json()['choices'][0]['message']['content']
        
        # 4. Clean and parse the JSON
        # Strips out markdown formatting if the LLM disobeys the prompt
        clean_json = re.sub(r'```json\n|\n```', '', response_text).strip()
        return json.loads(clean_json)
        
    except Exception as e:
        logger.error(f"API Error: {e}")
        return {"action": "ignore"}


# ── Action dispatcher ─────────────────────────────────────────────────────────
def handle_agnes_response(result: dict) -> str:
    action = result.get("action", "ignore")
    
    # Classic Mr. Krabs quotes
    krabs_quotes = [
        "Money, money, money!",
        "Argh-argh-argh-argh!",
        "Time is money, and you're wasting both!",
        "Get back to work, Mr. Squidward!",
        "A 5-cent discount? OVER MY DEAD BODY!",
        "I smell a smelly smell... a smelly smell that smells... smelly.",
        "That's me money you're playin' with!"
    ]
    quote = random.choice(krabs_quotes)

    if action == "add":
        task_id = add_task(
            assignee=result["assignee"],
            description=result["task"],
            status=result.get("status", "Pending"),
        )
        return f"🦀 **{quote}**\n✅ New chore for {result['assignee']}: '{result['task']}' (ID: {task_id})"

    elif action == "update":
        success = update_task_status(
            assignee=result["assignee"],
            description=result["task"],
            new_status=result.get("status", "Completed"),
        )
        if success:
            return f"💰 **{quote}**\n🔄 {result['assignee']} finished '{result['task']}'! That's more profit for me!"
        else:
            return f"⚓ **{quote}**\n⚠️ I can't find that task! Are ye trying to swindle me?"

    else:
        return None # Silent on ignore to keep the chat clean


# ── Telegram handler ──────────────────────────────────────────────────────────
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Called for every text message the bot can see."""
    message = update.effective_message
    if not message or not message.text:
        return

    chat_text = message.text
    logger.info(
        "Message from %s in chat %s: %r",
        update.effective_user.username or update.effective_user.id,
        update.effective_chat.id,
        chat_text,
    )

    # 1. Analyse
    agnes_result = analyze_text_with_agnes(chat_text)

    # 2. Act on CSV
    status_msg = handle_agnes_response(agnes_result)
    logger.info(status_msg)

    # Optional: send the result back to the chat (remove if you want silent operation)
    await message.reply_text(status_msg)


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    _ensure_csv()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Listen to ALL text messages (groups + DMs, excluding commands if you add any later)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    logger.info("Bot is running – press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
