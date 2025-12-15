import asyncio
import logging
import sys
import os
import uuid

import json

import base64

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.config import TELEGRAM_BOT_TOKEN
from src.database.db import init_db, get_db_connection, get_daily_summary, clear_daily_logs, get_daily_logs, delete_log, get_logs_by_group
from src.services.openai_service import process_user_message, analyze_food_image, calculate_daily_goals
from src.services.off_service import search_product, get_product_by_barcode
from src.services.barcode_service import decode_barcode
from src.utils.visualization import generate_text_progress_bar
from src.services.firebase_service import init_firebase, update_user_stats_in_firebase

# Define States
class BotStates(StatesGroup):
    waiting_for_barcode = State()
    waiting_for_food_photo = State()
    waiting_for_portion = State()

class ProfileStates(StatesGroup):
    waiting_for_age = State()
    waiting_for_gender = State()
    waiting_for_weight = State()
    waiting_for_height = State()
    waiting_for_activity = State()
    waiting_for_manual_cals = State()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Initialize Firebase
init_firebase()

# Main Menu Keyboard
# NOTE: Replace 'https://your-webapp-url.com' with your actual hosted URL
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🥗 Log Meal (Photo)"), KeyboardButton(text="🔍 Scan Barcode")],
        [KeyboardButton(text="📱 Open Dashboard", web_app=WebAppInfo(url="https://amrani-sohaib.github.io/AI-nutrition-bot/webapp/")), KeyboardButton(text="⚙️ Set Goals")],
        [KeyboardButton(text="📝 Log Text"), KeyboardButton(text="📊 Daily Journal")],
        [KeyboardButton(text="❌ Cancel / Reset")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Select an option..."
)

@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    """
    This handler receives messages with `/start` command
    """
    await state.clear() # Reset any active state
    
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Register user if not exists
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()
    
    # Get Daily Summary for the Dashboard
    summary = get_daily_summary(user_id)
    total_cals = summary['total_calories'] or 0
    
    # Create a nice welcome message
    welcome_text = (
        f"👋 <b>Hello, {message.from_user.full_name}!</b>\n\n"
        f"I'm your AI Nutrition Assistant. 🤖\n"
        f"<i>Track your meals, scan barcodes, and stay healthy!</i>\n\n"
        f"📅 <b>Today's Progress:</b>\n"
        f"🔥 Calories: <b>{total_cals}</b> kcal\n"
        f"💪 Protein: <b>{summary['total_protein'] or 0:.1f}g</b>\n"
        f"🍞 Carbs: <b>{summary['total_carbs'] or 0:.1f}g</b>\n"
        f"🥑 Fats: <b>{summary['total_fats'] or 0:.1f}g</b>\n\n"
        f"👇 <b>Choose an action below:</b>"
    )
    
    await message.answer(welcome_text, reply_markup=main_menu, parse_mode="HTML")

@dp.message(Command("dashboard"))
async def open_dashboard(message: Message):
    """
    Generates a link to the Web App with the user's ID for real-time syncing.
    """
    user_id = message.from_user.id
    
    # Sync latest data to Firebase before opening
    summary = get_daily_summary(user_id)
    logs = get_daily_logs(user_id)
    update_user_stats_in_firebase(user_id, summary, logs)
    
    # Construct URL with userId param
    base_url = "https://amrani-sohaib.github.io/AI-nutrition-bot/webapp/"
    full_url = f"{base_url}?userId={user_id}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Open Interactive Dashboard", web_app=WebAppInfo(url=full_url))]
    ])
    
    await message.answer("📊 <b>Your Personal Dashboard is ready!</b>\nClick below to view charts and details.", reply_markup=keyboard, parse_mode="HTML")

@dp.message(F.text == "❌ Cancel / Reset")
async def menu_cancel(message: Message, state: FSMContext):
    await state.clear()
    
    # Get Daily Summary for the Dashboard
    summary = get_daily_summary(message.from_user.id)
    total_cals = summary['total_calories'] or 0
    
    welcome_text = (
        f"✅ <b>Operation cancelled.</b>\n\n"
        f"📅 <b>Today's Progress:</b>\n"
        f"🔥 Calories: <b>{total_cals}</b> kcal\n"
        f"💪 Protein: <b>{summary['total_protein'] or 0:.1f}g</b>\n"
        f"🍞 Carbs: <b>{summary['total_carbs'] or 0:.1f}g</b>\n"
        f"🥑 Fats: <b>{summary['total_fats'] or 0:.1f}g</b>\n\n"
        f"👇 <b>What would you like to do next?</b>"
    )
    
    await message.answer(welcome_text, reply_markup=main_menu, parse_mode="HTML")

@dp.message(F.text == "📝 Log Text")
async def menu_log_text(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✍️ <b>Type what you ate:</b>\nExample: <i>'2 eggs, avocado toast and a coffee'</i>", parse_mode="HTML")

@dp.message(F.text == "🥗 Log Meal (Photo)")
async def menu_log_photo(message: Message, state: FSMContext):
    await state.set_state(BotStates.waiting_for_food_photo)
    await message.answer("📸 <b>Send a photo of your meal</b>\nI'll analyze the ingredients and estimate calories.", parse_mode="HTML")

@dp.message(F.text == "🔍 Scan Barcode")
async def menu_scan_barcode(message: Message, state: FSMContext):
    await state.set_state(BotStates.waiting_for_barcode)
    await message.answer(
        "Please send a clear photo of the barcode. 🏷️\n\n"
        "<b>Tips for best results:</b>\n"
        "• Ensure good lighting (no glare) 💡\n"
        "• Hold the camera steady (avoid blur) ✋\n"
        "• Make sure the barcode is fully visible within the frame 🖼️",
        parse_mode="HTML"
    )

@dp.message(F.text == "📊 Daily Journal")
async def menu_daily_journal(message: Message):
    summary = get_daily_summary(message.from_user.id)
    
    if not summary or not summary['total_calories']:
        await message.answer("You haven't logged any food today yet! 🍽️")
        return

    total_cals = summary['total_calories'] or 0
    total_prot = summary['total_protein'] or 0
    total_carbs = summary['total_carbs'] or 0
    total_fats = summary['total_fats'] or 0
    avg_score = summary['avg_health_score'] or 0
    items = summary['food_items'] or ""
    
    macro_chart = generate_text_progress_bar(total_prot, total_carbs, total_fats)
    
    text = (
        f"📅 <b>Daily Journal (Today)</b>\n\n"
        f"🍽️ <b>Items:</b> {items}\n\n"
        f"🔥 <b>Total Calories: {total_cals}</b>\n"
        f"💪 Protein: {total_prot:.1f}g\n"
        f"🍞 Carbs: {total_carbs:.1f}g\n"
        f"🥑 Fats: {total_fats:.1f}g\n"
        f"🌟 Avg Health Score: {avg_score:.1f}/10\n"
        f"{macro_chart}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 Show Daily Details", callback_data="toggle_daily_details:show")],
        [InlineKeyboardButton(text="🗑️ Manage / Delete Items", callback_data="manage_logs")],
        [InlineKeyboardButton(text="🚀 Open App Dashboard", callback_data="open_dashboard_btn")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "open_dashboard_btn")
async def open_dashboard_callback(callback: CallbackQuery):
    # Reuse the logic from the command
    await open_dashboard(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "manage_logs")
async def manage_logs_handler(callback: CallbackQuery):
    """
    Shows a list of today's logs with delete buttons.
    """
    logs = get_daily_logs(callback.from_user.id)
    
    if not logs:
        await callback.answer("No logs found for today.", show_alert=True)
        return

    keyboard_buttons = []
    for log in logs:
        # Button format: "❌ Apple (95 kcal)"
        btn_text = f"❌ {log['food_name']} ({log['calories']} kcal)"
        keyboard_buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"delete_log:{log['id']}")])
    
    # Add a "Done" button
    keyboard_buttons.append([InlineKeyboardButton(text="✅ Done", callback_data="delete_log_done")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(
        "🗑️ <b>Tap an item to delete it:</b>", 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("delete_log:"))
async def delete_log_item(callback: CallbackQuery):
    """
    Deletes a specific log item.
    """
    log_id = int(callback.data.split(":")[1])
    delete_log(log_id)
    
    # Sync to Firebase
    summary = get_daily_summary(callback.from_user.id)
    logs = get_daily_logs(callback.from_user.id)
    update_user_stats_in_firebase(callback.from_user.id, summary, logs)
    
    await callback.answer("Item deleted.")
    
    # Refresh the list
    # Check if there are any logs left
    logs = get_daily_logs(callback.from_user.id)
    if not logs:
        # If no logs left, go back to empty journal view
        await callback.message.delete()
        await callback.message.answer("📅 <b>Daily Journal (Today)</b>\n\nNo logs found for today.", parse_mode="HTML")
    else:
        # If logs remain, refresh the list
        await manage_logs_handler(callback)

@dp.callback_query(F.data == "delete_log_done")
async def delete_log_done(callback: CallbackQuery):
    """
    Returns to the main journal view.
    """
    await callback.message.delete()
    
    # Let's re-fetch summary and edit back
    summary = get_daily_summary(callback.from_user.id)
    
    # Handle empty summary gracefully
    if not summary or not summary['total_calories']:
        await callback.message.answer("📅 <b>Daily Journal (Today)</b>\n\nNo logs found for today.", parse_mode="HTML")
        return

    total_cals = summary['total_calories'] or 0
    total_prot = summary['total_protein'] or 0
    total_carbs = summary['total_carbs'] or 0
    total_fats = summary['total_fats'] or 0
    avg_score = summary['avg_health_score'] or 0
    items = summary['food_items'] or ""
    
    macro_chart = generate_text_progress_bar(total_prot, total_carbs, total_fats)
    
    text = (
        f"📅 <b>Daily Journal (Today)</b>\n\n"
        f"🍽️ <b>Items:</b> {items}\n\n"
        f"🔥 <b>Total Calories: {total_cals}</b>\n"
        f"💪 Protein: {total_prot:.1f}g\n"
        f"🍞 Carbs: {total_carbs:.1f}g\n"
        f"🥑 Fats: {total_fats:.1f}g\n"
        f"🌟 Avg Health Score: {avg_score:.1f}/10\n"
        f"{macro_chart}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 Show Daily Details", callback_data="toggle_daily_details:show")],
        [InlineKeyboardButton(text="🗑️ Manage / Delete Items", callback_data="manage_logs")]
    ])
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "confirm_clear_logs")
async def confirm_clear_logs(callback: CallbackQuery):
    """
    Asks for confirmation before clearing logs.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yes, Clear All", callback_data="clear_logs_yes"),
            InlineKeyboardButton(text="❌ No, Cancel", callback_data="clear_logs_no")
        ]
    ])
    await callback.message.edit_text("⚠️ <b>Are you sure?</b>\nThis will delete all your food logs for today.", reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "clear_logs_yes")
async def clear_logs_yes(callback: CallbackQuery):
    clear_daily_logs(callback.from_user.id)
    
    # Sync to Firebase (Empty)
    summary = get_daily_summary(callback.from_user.id)
    logs = []
    update_user_stats_in_firebase(callback.from_user.id, summary, logs)
    
    await callback.message.edit_text("✅ <b>Today's logs have been cleared.</b>", parse_mode="HTML")
    await callback.answer("Cleared!")

@dp.callback_query(F.data == "clear_logs_no")
async def clear_logs_no(callback: CallbackQuery):
    await callback.message.delete() # Just remove the confirmation message
    await callback.answer("Cancelled")

@dp.message(Command("search"))
async def search_food_handler(message: Message) -> None:
    """
    Searches for food in Open Food Facts
    Usage: /search <product name>
    """
    query = message.text.replace("/search", "").strip()
    if not query:
        await message.answer("Please provide a product name. Example: /search Nutella")
        return
        
    await message.answer(f"Searching for '{query}'... 🔍")
    product = await search_product(query)
    
    if product:
        response = (
            f"Found: {product['name']}\n"
            f"Calories: {product['calories']} kcal per 100g\n"
            f"Protein: {product['protein']}g\n"
            f"Carbs: {product['carbs']}g\n"
            f"Fats: {product['fats']}g"
        )
        await message.answer(response)
    else:
        await message.answer("Product not found.")

@dp.message(F.photo)
async def handle_photo(message: Message, state: FSMContext):
    """
    Handles photo messages based on user state (Barcode vs AI)
    """
    current_state = await state.get_state()
    
    # If user is in "Barcode Mode", we ONLY look for barcodes.
    if current_state == BotStates.waiting_for_barcode:
        await message.answer("🔍 Scanning for barcode...")
    else:
        await message.answer("👀 Analyzing food...")
    
    try:
        # Get the largest photo
        photo = message.photo[-1]
        file_id = photo.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        
        # Download file
        destination = f"temp_{file_id}.jpg"
        await bot.download_file(file_path, destination)
        
        # --- BARCODE LOGIC ---
        # Check if we should scan for barcode (Explicit state OR no state/hybrid)
        should_scan_barcode = (current_state == BotStates.waiting_for_barcode) or (current_state is None)
        
        if should_scan_barcode:
            barcode = decode_barcode(destination)
            
            if barcode:
                await message.answer(f"🏷️ Barcode detected: {barcode}\nSearching database...")
                product = await get_product_by_barcode(barcode)
                
                if product:
                    # Save product to state and ask for portion
                    await state.update_data(product=product)
                    await state.set_state(BotStates.waiting_for_portion)
                    
                    await message.answer(
                        f"✅ <b>Found: {product['name']}</b>\n"
                        f"Per 100g: {product['calories']} kcal\n\n"
                        f"⚖️ <b>How much did you eat?</b>\n"
                        f"Type the amount in grams (e.g., '200' for 200g) or just '1' for 100g.",
                        parse_mode="HTML"
                    )
                else:
                    await message.answer("😕 Barcode found, but product not in database.")
                
                # Cleanup and return (Success or Fail, we stop here if in strict barcode mode)
                if os.path.exists(destination):
                    os.remove(destination)
                return
            
            elif current_state == BotStates.waiting_for_barcode:
                # Strict mode: Failed to find barcode
                await message.answer("❌ <b>No barcode detected.</b>\n\nPlease try again with a clearer photo, or use 'Cancel' to go back.", parse_mode="HTML")
                if os.path.exists(destination):
                    os.remove(destination)
                return

        # --- AI FOOD ANALYSIS LOGIC ---
        # Only proceed if we are NOT in strict barcode mode
        if current_state == BotStates.waiting_for_barcode:
            return # Should have been handled above

        # If we are here in "None" state, it means Barcode scan failed.
        # Let the user know we are switching to AI.
        if current_state is None:
            await message.answer("⚠️ No barcode detected. Analyzing as food image... 🍎")

        # Proceed with AI
        caption = message.caption or ""
        log_data, reply = await analyze_food_image(destination, caption)
        
        # Clean up file
        if os.path.exists(destination):
            os.remove(destination)
            
        # Send the conversational reply first
        await message.answer(reply)
        
        # Log data if found
        if log_data:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            total_cals = 0
            total_prot = 0
            total_carbs = 0
            total_fats = 0
            items_found = []
            health_scores = []
            
            # Generate a unique group ID for this meal
            group_id = str(uuid.uuid4())
            
            for item in log_data:
                name = item.get('item')
                cals = item.get('calories', 0)
                prot = item.get('protein', 0)
                carbs = item.get('carbs', 0)
                fats = item.get('fats', 0)
                micros = item.get('micronutrients', 'N/A')
                score = item.get('health_score', 5)
                weight = item.get('weight_g', 'N/A')
                meal_period = item.get('meal_period', 'Snack')
                
                total_cals += cals
                total_prot += prot
                total_carbs += carbs
                total_fats += fats
                items_found.append(f"{name} ({weight}g)")
                health_scores.append(score)
                
                # Save to DB with group_id
                cursor.execute('''
                    INSERT INTO logs (user_id, food_name, calories, protein, carbs, fats, micronutrients, health_score, meal_group_id, meal_period)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (message.from_user.id, name, cals, prot, carbs, fats, micros, score, group_id, meal_period))
                
            conn.commit()
            conn.close()
            
            # Sync to Firebase
            summary = get_daily_summary(message.from_user.id)
            logs = get_daily_logs(message.from_user.id)
            update_user_stats_in_firebase(message.from_user.id, summary, logs)
            
            avg_score = sum(health_scores) / len(health_scores) if health_scores else 0
            
            # Generate text-based chart
            macro_chart = generate_text_progress_bar(total_prot, total_carbs, total_fats)
            
            # Send SYNTHESIS (Totals + Chart)
            synthese_text = (
                f"✅ <b>Logged:</b> {', '.join(items_found)}\n\n"
                f"<b>📊 Total Nutrition:</b>\n"
                f"🔥 <b>{total_cals} Calories</b>\n"
                f"💪 Protein: {total_prot:.1f}g\n"
                f"🍞 Carbs: {total_carbs:.1f}g\n"
                f"🥑 Fats: {total_fats:.1f}g\n"
                f"🌟 Health Score: {avg_score:.1f}/10\n"
                f"{macro_chart}"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📜 Show Item Details", callback_data=f"toggle_details:show:{group_id}")]
            ])
            
            # Send detailed summary
            await message.answer(synthese_text, reply_markup=keyboard, parse_mode="HTML")
            
            # Reset state
            await state.set_state(None)
            
    except Exception as e:
        logging.error(f"Error handling photo: {e}")
        await message.answer("Sorry, I had trouble seeing that picture.")

@dp.message(BotStates.waiting_for_portion)
async def process_portion_input(message: Message, state: FSMContext):
    """
    Handles the portion input after a barcode scan.
    """
    user_input = message.text.strip()
    
    # Get product from state
    data = await state.get_data()
    product = data.get("product")
    
    if not product:
        await message.answer("Session expired. Please scan again.")
        await state.clear()
        return

    # Calculate multiplier
    multiplier = 1.0
    try:
        if user_input.lower() in ['1', '100', '100g']:
            multiplier = 1.0
        else:
            # Assume input is grams
            grams = float(user_input.lower().replace('g', ''))
            multiplier = grams / 100.0
    except ValueError:
        await message.answer("Please enter a valid number (e.g. '150' for 150g).")
        return

    # Calculate final values
    final_cals = int(product['calories'] * multiplier)
    final_prot = round(product['protein'] * multiplier, 1)
    final_carbs = round(product['carbs'] * multiplier, 1)
    final_fats = round(product['fats'] * multiplier, 1)
    
    # Generate group ID
    group_id = str(uuid.uuid4())
    
    # Determine meal period based on time
    from datetime import datetime
    hour = datetime.now().hour
    if 5 <= hour < 11:
        meal_period = "Breakfast"
    elif 11 <= hour < 15:
        meal_period = "Lunch"
    elif 18 <= hour < 22:
        meal_period = "Dinner"
    else:
        meal_period = "Snack"

    # Log to DB
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO logs (user_id, food_name, calories, protein, carbs, fats, micronutrients, health_score, meal_group_id, meal_period)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (message.from_user.id, product['name'], final_cals, final_prot, final_carbs, final_fats, "From Barcode", 5, group_id, meal_period))
    
    conn.commit()
    conn.close()
    
    # Sync to Firebase
    summary = get_daily_summary(message.from_user.id)
    logs = get_daily_logs(message.from_user.id)
    update_user_stats_in_firebase(message.from_user.id, summary, logs)
    
    # Clear state
    await state.clear()
    
    # Prepare Synthesis & Details
    macro_chart = generate_text_progress_bar(final_prot, final_carbs, final_fats)
    
    synthese_text = (
        f"✅ <b>Logged: {product['name']}</b>\n"
        f"⚖️ Portion: {int(multiplier * 100)}g\n\n"
        f"<b>📊 Total Nutrition:</b>\n"
        f"🔥 <b>{final_cals} Calories</b>\n"
        f"💪 Protein: {final_prot}g\n"
        f"🍞 Carbs: {final_carbs}g\n"
        f"🥑 Fats: {final_fats}g\n"
        f"{macro_chart}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 Show Item Details", callback_data=f"toggle_details:show:{group_id}")]
    ])
    
    # Show summary
    await message.answer(synthese_text, reply_markup=keyboard, parse_mode="HTML")
    
    # Reset state
    await state.set_state(None)

@dp.message(F.text)
async def log_food_handler(message: Message, state: FSMContext) -> None:
    """
    Handler for text messages to log food or chat
    """
    user_input = message.text
    
    try:
        # Call OpenAI to process text
        log_data, reply = await process_user_message(user_input)
        
        # Send the conversational reply
        await message.answer(reply)
        
        # Log data if found
        if log_data:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            total_cals = 0
            total_prot = 0
            total_carbs = 0
            total_fats = 0
            item_names = []
            
            # Generate group ID
            group_id = str(uuid.uuid4())
            
            for item in log_data:
                name = item.get('item')
                cals = item.get('calories', 0)
                prot = item.get('protein', 0)
                carbs = item.get('carbs', 0)
                fats = item.get('fats', 0)
                micros = item.get('micronutrients', 'N/A')
                score = item.get('health_score', 5)
                meal_period = item.get('meal_period', 'Snack')
                
                total_cals += cals
                total_prot += prot
                total_carbs += carbs
                total_fats += fats
                item_names.append(name)
                
                cursor.execute('''
                    INSERT INTO logs (user_id, food_name, calories, protein, carbs, fats, micronutrients, health_score, meal_group_id, meal_period)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (message.from_user.id, name, cals, prot, carbs, fats, micros, score, group_id, meal_period))
                
            conn.commit()
            conn.close()
            
            # Sync to Firebase
            summary = get_daily_summary(message.from_user.id)
            logs = get_daily_logs(message.from_user.id)
            update_user_stats_in_firebase(message.from_user.id, summary, logs)
            
            # Generate text-based chart
            macro_chart = generate_text_progress_bar(total_prot, total_carbs, total_fats)
            
            # Send SYNTHESIS (Totals + Chart)
            synthese_text = (
                f"✅ <b>Logged:</b> {', '.join(item_names)}\n\n"
                f"<b>📊 Total Nutrition:</b>\n"
                f"🔥 <b>{total_cals} Calories</b>\n"
                f"💪 Protein: {total_prot:.1f}g\n"
                f"🍞 Carbs: {total_carbs:.1f}g\n"
                f"🥑 Fats: {total_fats:.1f}g\n"
                f"{macro_chart}"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📜 Show Item Details", callback_data=f"toggle_details:show:{group_id}")]
            ])
            
            await message.answer(synthese_text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logging.error(f"Error processing message: {e}")
        await message.answer("An error occurred while processing your request.")

@dp.message(F.content_type == "web_app_data")
async def web_app_data_handler(message: Message, state: FSMContext):
    """
    Handles data sent from the Web App (Barcode or Text Log)
    """
    logging.info(f"Received Web App Data: {message.web_app_data.data}")
    try:
        data = json.loads(message.web_app_data.data)
        
        if data.get('type') == 'barcode':
            barcode = data.get('data')
            await message.answer(f"🏷️ <b>Received Barcode:</b> {barcode}\nSearching database...", parse_mode="HTML")
            
            # Reuse the existing barcode logic
            product = await get_product_by_barcode(barcode)
            
            if product:
                # Save product to state and ask for portion
                await state.update_data(product=product)
                await state.set_state(BotStates.waiting_for_portion)
                
                await message.answer(
                    f"✅ <b>Found: {product['name']}</b>\n"
                    f"Per 100g: {product['calories']} kcal\n\n"
                    f"⚖️ <b>How much did you eat?</b>\n"
                    f"Type the amount in grams (e.g., '200' for 200g) or just '1' for 100g.",
                    parse_mode="HTML"
                )
            else:
                await message.answer("😕 Barcode found, but product not in database.")
        
        elif data.get('type') == 'text':
            text_log = data.get('data')
            await message.answer(f"📝 <b>Received Log:</b> {text_log}\nProcessing...", parse_mode="HTML")
            
            # Reuse the text logging logic
            # We need to call process_user_message manually
            # This is a bit tricky because log_food_handler expects a message object
            # We can just call the logic directly here
            
            log_data, reply = await process_user_message(text_log)
            await message.answer(reply)
            
            if log_data:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                total_cals = 0
                total_prot = 0
                total_carbs = 0
                total_fats = 0
                item_names = []
                group_id = str(uuid.uuid4())
                
                for item in log_data:
                    name = item.get('item')
                    cals = item.get('calories', 0)
                    prot = item.get('protein', 0)
                    carbs = item.get('carbs', 0)
                    fats = item.get('fats', 0)
                    micros = item.get('micronutrients', 'N/A')
                    score = item.get('health_score', 5)
                    meal_period = item.get('meal_period', 'Snack')
                    
                    total_cals += cals
                    total_prot += prot
                    total_carbs += carbs
                    total_fats += fats
                    item_names.append(name)
                    
                    cursor.execute('''
                        INSERT INTO logs (user_id, food_name, calories, protein, carbs, fats, micronutrients, health_score, meal_group_id, meal_period)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (message.from_user.id, name, cals, prot, carbs, fats, micros, score, group_id, meal_period))
                    
                conn.commit()
                conn.close()
                
                # Sync to Firebase
                summary = get_daily_summary(message.from_user.id)
                logs = get_daily_logs(message.from_user.id)
                update_user_stats_in_firebase(message.from_user.id, summary, logs)
                
                macro_chart = generate_text_progress_bar(total_prot, total_carbs, total_fats)
                
                synthese_text = (
                    f"✅ <b>Logged:</b> {', '.join(item_names)}\n\n"
                    f"<b>📊 Total Nutrition:</b>\n"
                    f"🔥 <b>{total_cals} Calories</b>\n"
                    f"💪 Protein: {total_prot:.1f}g\n"
                    f"🍞 Carbs: {total_carbs:.1f}g\n"
                    f"🥑 Fats: {total_fats:.1f}g\n"
                    f"{macro_chart}"
                )
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📜 Show Item Details", callback_data=f"toggle_details:show:{group_id}")]
                ])
                
                await message.answer(synthese_text, reply_markup=keyboard, parse_mode="HTML")

    except Exception as e:
        logging.error(f"Error handling Web App data: {e}")
        await message.answer("Error processing data from Web App.")

@dp.callback_query(F.data.startswith("toggle_details:"))
async def toggle_log_details(callback: CallbackQuery):
    """
    Toggles between Synthesis and Full Details (Accordion effect).
    Fetches data from DB using group_id to ensure persistence.
    """
    try:
        parts = callback.data.split(":")
        action = parts[1] # "show" or "hide"
        group_id = parts[2] if len(parts) > 2 else None
        
        if not group_id:
            await callback.answer("Error: Missing group ID.", show_alert=True)
            return

        # Fetch logs from DB
        logs = get_logs_by_group(group_id)
        
        if not logs:
            await callback.answer("Logs not found (might have been deleted).", show_alert=True)
            return

        # Reconstruct Data
        total_cals = 0
        total_prot = 0
        total_carbs = 0
        total_fats = 0
        items_found = []
        health_scores = []
        
        full_details = "<b>📊 Detailed Nutrition Breakdown</b>\n\n"
        
        for log in logs:
            # log keys: id, user_id, food_name, calories, protein, carbs, fats, micronutrients, health_score, created_at, meal_group_id
            name = log['food_name']
            cals = log['calories']
            prot = log['protein']
            carbs = log['carbs']
            fats = log['fats']
            micros = log['micronutrients']
            score = log['health_score']
            
            total_cals += cals
            total_prot += prot
            total_carbs += carbs
            total_fats += fats
            items_found.append(name)
            if score is not None:
                health_scores.append(score)
            
            full_details += (
                f"🍎 <b>{name}</b>\n"
                f"🔥 Calories: {cals}\n"
                f"💪 Protein: {prot}g | 🍞 Carbs: {carbs}g | 🥑 Fats: {fats}g\n"
                f"💊 Micros: {micros}\n"
                f"🌟 Health Score: {score}/10\n\n"
            )
            
        avg_score = sum(health_scores) / len(health_scores) if health_scores else 0
        macro_chart = generate_text_progress_bar(total_prot, total_carbs, total_fats)
        
        # Reconstruct Synthesis
        synthesis_text = (
            f"✅ <b>Logged:</b> {', '.join(items_found)}\n\n"
            f"<b>📊 Total Nutrition:</b>\n"
            f"🔥 <b>{total_cals} Calories</b>\n"
            f"💪 Protein: {total_prot:.1f}g\n"
            f"🍞 Carbs: {total_carbs:.1f}g\n"
            f"🥑 Fats: {total_fats:.1f}g\n"
            f"🌟 Health Score: {avg_score:.1f}/10\n"
            f"{macro_chart}"
        )

        if action == "show":
            # Expand: Show Synthesis + Details
            new_text = f"{synthesis_text}\n\n{full_details}"
            new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔼 Hide Details", callback_data=f"toggle_details:hide:{group_id}")]
            ])
            await callback.message.edit_text(new_text, reply_markup=new_keyboard, parse_mode="HTML")
            
        elif action == "hide":
            # Collapse: Show only Synthesis
            new_text = synthesis_text
            new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📜 Show Item Details", callback_data=f"toggle_details:show:{group_id}")]
            ])
            await callback.message.edit_text(new_text, reply_markup=new_keyboard, parse_mode="HTML")
        
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error in toggle_details: {e}")
        await callback.answer("An error occurred.", show_alert=True)

@dp.callback_query(F.data.startswith("toggle_daily_details:"))
async def toggle_daily_details(callback: CallbackQuery):
    """
    Toggles between Daily Synthesis and Full Daily Details.
    """
    try:
        action = callback.data.split(":")[1] # "show" or "hide"
        
        # Fetch all logs for today
        logs = get_daily_logs(callback.from_user.id)
        
        if not logs:
            await callback.answer("No logs found for today.", show_alert=True)
            return

        # Reconstruct Data
        total_cals = 0
        total_prot = 0
        total_carbs = 0
        total_fats = 0
        items_found = []
        health_scores = []
        
        full_details = "<b>📊 Daily Detailed Breakdown</b>\n\n"
        
        for log in logs:
            # log keys: id, user_id, food_name, calories, protein, carbs, fats, micronutrients, health_score, created_at, meal_group_id
            name = log['food_name']
            cals = log['calories']
            prot = log['protein']
            carbs = log['carbs']
            fats = log['fats']
            micros = log['micronutrients']
            score = log['health_score']
            
            total_cals += cals
            total_prot += prot
            total_carbs += carbs
            total_fats += fats
            items_found.append(name)
            if score is not None:
                health_scores.append(score)
            
            full_details += (
                f"🍎 <b>{name}</b>\n"
                f"🔥 Calories: {cals}\n"
                f"💪 Protein: {prot}g | 🍞 Carbs: {carbs}g | 🥑 Fats: {fats}g\n"
                f"💊 Micros: {micros}\n"
                f"🌟 Health Score: {score}/10\n\n"
            )
            
        avg_score = sum(health_scores) / len(health_scores) if health_scores else 0
        macro_chart = generate_text_progress_bar(total_prot, total_carbs, total_fats)
        
        # Reconstruct Synthesis
        synthesis_text = (
            f"📅 <b>Daily Journal (Today)</b>\n\n"
            f"🍽️ <b>Items:</b> {', '.join(items_found)}\n\n"
            f"🔥 <b>Total Calories: {total_cals}</b>\n"
            f"💪 Protein: {total_prot:.1f}g\n"
            f"🍞 Carbs: {total_carbs:.1f}g\n"
            f"🥑 Fats: {total_fats:.1f}g\n"
            f"🌟 Avg Health Score: {avg_score:.1f}/10\n"
            f"{macro_chart}"
        )

        if action == "show":
            # Expand: Show Synthesis + Details
            new_text = f"{synthesis_text}\n\n{full_details}"
            new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔼 Hide Details", callback_data="toggle_daily_details:hide")],
                [InlineKeyboardButton(text="🗑️ Manage / Delete Items", callback_data="manage_logs")]
            ])
            await callback.message.edit_text(new_text, reply_markup=new_keyboard, parse_mode="HTML")
            
        elif action == "hide":
            # Collapse: Show only Synthesis
            new_text = synthesis_text
            new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📜 Show Daily Details", callback_data="toggle_daily_details:show")],
                [InlineKeyboardButton(text="🗑️ Manage / Delete Items", callback_data="manage_logs")]
            ])
            await callback.message.edit_text(new_text, reply_markup=new_keyboard, parse_mode="HTML")
        
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error in toggle_daily_details: {e}")
        await callback.answer("An error occurred.", show_alert=True)

# --- PROFILE & GOALS HANDLERS ---

@dp.message(F.text == "⚙️ Set Goals")
async def start_goals_setup(message: Message, state: FSMContext):
    await state.clear()
    logging.info("User requested Goal Setup")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 AI Calculator (Recommended)", callback_data="goals:ai")],
        [InlineKeyboardButton(text="✍️ Manual Setup", callback_data="goals:manual")]
    ])
    await message.answer("<b>⚙️ Goal Setup</b>\n\nHow would you like to set your daily calorie and macro goals?", reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "goals:manual")
async def manual_goals_start(callback: CallbackQuery, state: FSMContext):
    logging.info("User chose Manual Goals")
    await callback.message.answer("Please enter your daily calorie goal (e.g., 2000):")
    await state.set_state(ProfileStates.waiting_for_manual_cals)
    await callback.answer()

@dp.message(ProfileStates.waiting_for_manual_cals)
async def manual_goals_finish(message: Message, state: FSMContext):
    try:
        cals = int(message.text.strip())
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET daily_calorie_goal = ? WHERE user_id = ?", (cals, message.from_user.id))
        conn.commit()
        conn.close()
        
        # Sync to Firebase
        summary = get_daily_summary(message.from_user.id)
        logs = get_daily_logs(message.from_user.id)
        update_user_stats_in_firebase(message.from_user.id, summary, logs)
        
        await message.answer(f"✅ Daily goal set to <b>{cals} kcal</b>!", parse_mode="HTML")
        await state.clear()
    except ValueError:
        await message.answer("Please enter a valid number.")

@dp.callback_query(F.data == "goals:ai")
async def ai_goals_start(callback: CallbackQuery, state: FSMContext):
    logging.info("User chose AI Goals")
    await callback.message.answer("Let's calculate your personalized goals! 🤖\n\nFirst, what is your <b>Age</b>? (e.g., 25)", parse_mode="HTML")
    await state.set_state(ProfileStates.waiting_for_age)
    await callback.answer()

@dp.message(ProfileStates.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Please enter a valid number for age.")
        return
    await state.update_data(age=int(message.text))
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Male", callback_data="gender:Male"), InlineKeyboardButton(text="Female", callback_data="gender:Female")]
    ])
    await message.answer("What is your <b>Gender</b>?", reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ProfileStates.waiting_for_gender)

@dp.callback_query(ProfileStates.waiting_for_gender, F.data.startswith("gender:"))
async def process_gender(callback: CallbackQuery, state: FSMContext):
    gender = callback.data.split(":")[1]
    await state.update_data(gender=gender)
    await callback.message.answer("What is your <b>Weight</b> in kg? (e.g., 75)", parse_mode="HTML")
    await state.set_state(ProfileStates.waiting_for_weight)
    await callback.answer()

@dp.message(ProfileStates.waiting_for_gender)
async def gender_invalid_input(message: Message):
    await message.answer("Please select an option from the buttons above. ⬆️")

@dp.message(ProfileStates.waiting_for_weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text.replace(',', '.'))
        await state.update_data(weight=weight)
        await message.answer("What is your <b>Height</b> in cm? (e.g., 180)", parse_mode="HTML")
        await state.set_state(ProfileStates.waiting_for_height)
    except ValueError:
        await message.answer("Please enter a valid number.")

@dp.message(ProfileStates.waiting_for_height)
async def process_height(message: Message, state: FSMContext):
    try:
        height = float(message.text.replace(',', '.'))
        await state.update_data(height=height)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Sedentary (Office job)", callback_data="activity:Sedentary")],
            [InlineKeyboardButton(text="Lightly Active (1-3 days/wk)", callback_data="activity:Lightly Active")],
            [InlineKeyboardButton(text="Moderately Active (3-5 days/wk)", callback_data="activity:Moderately Active")],
            [InlineKeyboardButton(text="Very Active (6-7 days/wk)", callback_data="activity:Very Active")]
        ])
        await message.answer("What is your <b>Activity Level</b>?", reply_markup=keyboard, parse_mode="HTML")
@dp.callback_query(ProfileStates.waiting_for_activity, F.data.startswith("activity:"))
async def process_activity(callback: CallbackQuery, state: FSMContext):
    activity = callback.data.split(":")[1]
    data = await state.get_data()
    
    # Save profile to DB
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET age = ?, gender = ?, weight = ?, height = ?, activity_level = ?
        WHERE user_id = ?
    ''', (data['age'], data['gender'], data['weight'], data['height'], activity, callback.from_user.id))
    conn.commit()
    
    await callback.message.answer("🔄 Calculating your personalized plan with AI...")
    
    # Call OpenAI
    goals = await calculate_daily_goals(data['age'], data['gender'], data['weight'], data['height'], activity)
    
    # Save Goal
    cursor.execute("UPDATE users SET daily_calorie_goal = ? WHERE user_id = ?", (goals['calories'], callback.from_user.id))
    conn.commit()
    conn.close()
    
    # Sync to Firebase
    summary = get_daily_summary(callback.from_user.id)
    logs = get_daily_logs(callback.from_user.id)
    update_user_stats_in_firebase(callback.from_user.id, summary, logs)
    
    await callback.message.answer(
        f"✅ <b>Plan Created!</b>\n\n"
        f"🔥 <b>Daily Calories: {goals['calories']} kcal</b>\n"
        f"💪 Protein: {goals['protein']}g\n"
        f"🍞 Carbs: {goals['carbs']}g\n"
        f"🥑 Fats: {goals['fats']}g\n\n"
        f"📝 <i>{goals['explanation']}</i>",
        parse_mode="HTML"
    )
    await state.clear()
    await callback.answer()

@dp.message(ProfileStates.waiting_for_activity)
async def activity_invalid_input(message: Message):
    await message.answer("Please select an activity level from the buttons above. ⬆️")lanation']}</i>",
        parse_mode="HTML"
    )
    await state.clear()
    await callback.answer()

async def main() -> None:
    # Initialize DB
    init_db()
    
    # Initialize Firebase
    init_firebase()
    
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
