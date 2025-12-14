# 🚀 How to Deploy the Smart Scanner Web App

To make the **"📱 Smart Scanner"** button work on your phone, the `webapp/index.html` file must be hosted on the internet (Telegram requires a secure `https://` link).

The easiest and free way is to use **GitHub Pages**.

## Step 1: Push Code to GitHub
If you haven't already, push your project to a GitHub repository.

```bash
git add .
git commit -m "Add Web App"
git push origin main
```

## Step 2: Enable GitHub Pages
1. Go to your repository on **GitHub.com**.
2. Click on **Settings** (top right tab).
3. On the left sidebar, scroll down and click on **Pages**.
4. Under **Build and deployment** > **Source**, select **Deploy from a branch**.
5. Under **Branch**, select `main` and keep the folder as `/(root)`.
6. Click **Save**.

## Step 3: Get Your URL
1. Wait a minute or two. Refresh the page.
2. You will see a message: **"Your site is live at..."**
3. Copy that URL. It should look like:
   `https://your-username.github.io/AI-nutrition-bot/`

## Step 4: Update the Bot
1. Open `src/main.py`.
2. Find the `main_menu` section (around line 50).
3. Update the `url` in `WebAppInfo` to point to your file:
   
   ```python
   # Example
   WebAppInfo(url="https://your-username.github.io/AI-nutrition-bot/webapp/")
   ```
   *(Note: Don't forget to add `/webapp/` at the end if your index.html is in that folder!)*

4. Restart your bot.

## Step 5: Test it!
Open Telegram on your phone, click **"📱 Smart Scanner"**, and the camera should open instantly!
