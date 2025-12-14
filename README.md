# AI Nutrition Bot

A Telegram bot that helps you track your daily nutrition using AI.

## Features

- **Natural Language Logging:** Just type "I ate a banana and a yogurt" and the bot will log the calories and macros.
- **Database:** Stores your logs in a local SQLite database.

## Setup

1.  **Clone the repository**
2.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure Environment Variables:**
    - Rename `.env.example` to `.env` (or create it).
    - Add your `TELEGRAM_BOT_TOKEN` (from BotFather).
    - Add your `OPENAI_API_KEY`.

## Running the Bot

```bash
python src/main.py
```
