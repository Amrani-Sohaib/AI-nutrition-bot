import asyncio
import logging
import sys
import os

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from src.config import TELEGRAM_BOT_TOKEN
from src.database.db import init_db, get_db_connection
from src.services.openai_service import process_user_message, analyze_food_image
from src.services.off_service import search_product

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Register user if not exists
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()
    
    await message.answer(f"Hello, {message.from_user.full_name}! I'm your AI Nutrition Bot. \n\nJust tell me what you ate (e.g., '2 eggs and a toast') or send me a photo of your meal! 📸")

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
async def handle_photo(message: Message):
    """
    Handles photo messages for food analysis
    """
    await message.answer("Looking at your delicious food... 📸")
    
    try:
        # Get the largest photo
        photo = message.photo[-1]
        file_id = photo.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        
        # Download file
        destination = f"temp_{file_id}.jpg"
        await bot.download_file(file_path, destination)
        
        # Analyze with OpenAI
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
            
            for item in log_data:
                name = item.get('item')
                cals = item.get('calories', 0)
                prot = item.get('protein', 0)
                carbs = item.get('carbs', 0)
                fats = item.get('fats', 0)
                
                cursor.execute('''
                    INSERT INTO logs (user_id, food_name, calories, protein, carbs, fats)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (message.from_user.id, name, cals, prot, carbs, fats))
                
            conn.commit()
            conn.close()
            
    except Exception as e:
        logging.error(f"Error handling photo: {e}")
        await message.answer("Sorry, I had trouble seeing that picture.")

@dp.message(F.text)
async def log_food_handler(message: Message) -> None:
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
            
            for item in log_data:
                name = item.get('item')
                cals = item.get('calories', 0)
                prot = item.get('protein', 0)
                carbs = item.get('carbs', 0)
                fats = item.get('fats', 0)
                
                cursor.execute('''
                    INSERT INTO logs (user_id, food_name, calories, protein, carbs, fats)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (message.from_user.id, name, cals, prot, carbs, fats))
                
            conn.commit()
            conn.close()
        
    except Exception as e:
        logging.error(f"Error processing message: {e}")
        await message.answer("An error occurred while processing your request.")

async def main() -> None:
    # Initialize DB
    init_db()
    
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
