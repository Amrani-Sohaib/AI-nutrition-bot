# AI Nutrition Bot

A Telegram bot + mini web app to log meals (text/photo/barcode), view a dashboard, and set calorie goals.

## Features
- **Text logging:** Type "I ate chicken and rice" and it logs calories/macros via OpenAI.
- **Photo logging:** Analyze meal photos with OpenAI vision.
- **Barcode scan:** Decode barcodes and log products from Open Food Facts.
- **Goals:** Auto-calculate with a deterministic Mifflin-St Jeor formula or enter manually.
- **Dashboard:** Web App (GitHub Pages) shows calories, macros, and daily journal synced via Firebase.
- **Storage:** SQLite for local persistence; Firebase sync for the web dashboard.

## Setup
1. **Clone** the repo and create a venv
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```
2. **Install deps**
   ```bash
   pip install -r requirements.txt
   ```
3. **Env vars (.env)**
   - `TELEGRAM_BOT_TOKEN`
   - `OPENAI_API_KEY`
   - `FIREBASE_CREDENTIALS` (path to your serviceAccountKey.json) or keep the bundled `serviceAccountKey.json`

## Run the bot
```bash
python src/main.py
```
Then type `/start` in Telegram to get the keyboard.

## Web App deployment
The dashboard lives in `webapp/` and is served via GitHub Pages. See `DEPLOY_WEBAPP.md` for steps.

## Usage tips
- **Open Dashboard:** Use the Telegram button; it passes `userId` so the page loads your data.
- **Set Goals:** Tap **⚙️ Set Goals** → **🤖 Auto-Calculate** (Mifflin-St Jeor) or **✍️ Manual Setup** to enter kcal.
- **Logging:**
  - Text → **📝 Log Text**
  - Photo → **🥗 Log Meal (Photo)**
  - Barcode → **🔍 Scan Barcode** (then enter portion grams)

## Testing
See `TESTING_GUIDE.md` for manual checks (barcode strict mode, photo flow, portion control, delete flow).
