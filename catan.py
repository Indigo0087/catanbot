import os
import logging
import sqlite3
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

DATABASE_FILE = os.getenv("DATABASE_FILE")

def init_db():
    """
    Initialize the SQLite database and create the 'winners' table if not exists.
    """
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS winners (
            username TEXT PRIMARY KEY,
            wins INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()

def increment_win_count(username: str):
    """
    Increment the win count for a specific username.
    If the user does not exist yet, insert them with 1 win.
    """
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # Check if user already exists
    cursor.execute("SELECT wins FROM winners WHERE username = ?", (username,))
    row = cursor.fetchone()

    if row is None:
        # Insert new record
        cursor.execute(
            "INSERT INTO winners (username, wins) VALUES (?, ?)",
            (username, 1),
        )
    else:
        # Update existing record
        new_count = row[0] + 1
        cursor.execute(
            "UPDATE winners SET wins = ? WHERE username = ?",
            (new_count, username),
        )

    conn.commit()
    conn.close()

def get_leaderboard():
    """
    Return a list of tuples (username, wins) for all winners, sorted by wins desc.
    """
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT username, wins FROM winners ORDER BY wins DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text("Hello! I will track who wins Catan in this chat.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the current Catan win stats."""
    leaderboard = get_leaderboard()
    if not leaderboard:
        await update.message.reply_text("No wins recorded yet!")
        return

    leaderboard_lines = [
        f"@{username}: {wins}" for username, wins in leaderboard
    ]
    leaderboard_text = "\n".join(leaderboard_lines)
    
    await update.message.reply_text(
        f"**Catan Wins Leaderboard**\n{leaderboard_text}",
        parse_mode="Markdown",
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle incoming messages:
      - Check if there is a photo attached.
      - Check if the message mentions a user (via @username mention).
      - If so, increment that user's 'win' count in the database.
    """
    message = update.effective_message
    
    print(message)

    # Only proceed if there is at least one photo in the message
    if not message.photo:
        return
    
    # Look for mentions in the message entities
    if message.caption_entities:
        for entity in message.caption_entities:
            print (entity, entity.type)
            if entity.type == "mention":
                # Extract the username from the message text
                mention_text = message.caption[entity.offset : entity.offset + entity.length]
                # mention_text should look like '@username'; remove '@'
                username = mention_text.lstrip("@")

                # Increment the user's count in the DB
                increment_win_count(username)
                logger.info("Incremented win for user: %s", username)

                # Optionally, reply to confirm
                await message.reply_text(f"Counted a Catan win for {mention_text}!")
                
                # If only one mention should increment per message, break here
                break

def main():
    """
    Start the bot, initialize the DB, and listen for updates.
    """
    # Initialize the database
    init_db()

    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

    # Replace 'YOUR_BOT_TOKEN' with the token you got from BotFather
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Catch all messages (that are not commands)
    application.add_handler(MessageHandler(filters.ALL, message_handler))
    
    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
