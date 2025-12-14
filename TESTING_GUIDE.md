# Testing Guide for New Features

## 1. Strict Mode Verification
We have separated "Barcode Scanning" and "Food Photo Logging" to prevent the bot from guessing wrong.

### Test Barcode Mode:
1. Click **"🔍 Scan Barcode"** in the menu.
2. Send a photo of a product with a barcode.
   - **Expected:** Bot detects barcode and finds product.
3. Send a photo of a random object (no barcode).
   - **Expected:** Bot says "❌ No barcode detected" and asks you to try again or cancel. **It should NOT try to analyze the food.**

### Test Food Photo Mode:
1. Click **"🥗 Log Meal (Photo)"** in the menu.
2. Send a photo of a meal.
   - **Expected:** Bot analyzes the food with AI and logs it.
3. Send a photo of a barcode.
   - **Expected:** Bot analyzes it as an image (might say "I see a package..."). It will NOT scan the barcode strictly.

### Test "Lazy" Mode (No Button Clicked):
1. **Do not click any button.** Just send a photo.
2. Send a barcode photo.
   - **Expected:** Bot finds barcode and logs it.
3. Send a food photo (no barcode).
   - **Expected:** Bot tries to find barcode, fails, says **"⚠️ No barcode detected. Analyzing as food image..."**, and THEN analyzes the food.
   - This confirms the bot is not just "guessing" silently.

## 2. Portion Control
1. After a successful barcode scan, the bot will ask for the portion size.
2. Type `1` or `100` for 100g.
3. Type `200` for 200g.
4. **Expected:** The logged calories/macros should be adjusted based on your input.

## 8. Unified Logic & Delete Fix
1. **Test Barcode Logging:**
   - Scan a barcode -> Enter portion.
   - **Expected:** You now see the **Synthesis** (Totals + Chart) and the **[📜 Show Item Details]** button, just like text/photo logging.
   
2. **Test Delete All:**
   - Log 2 items.
   - Go to "Manage / Delete Items".
   - Delete the first one.
   - Delete the second one (the last one).
   - **Expected:** Instead of getting stuck, the bot should say "No logs found for today" or return to an empty journal view.
