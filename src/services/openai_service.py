from openai import AsyncOpenAI
import json
import base64
from src.config import OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def analyze_food_image(image_path: str, caption: str = ""):
    """
    Analyzes a food image using GPT-4o to identify items, estimate weight, and calculate macros.
    Returns a tuple: (structured_data, conversational_reply)
    """
    
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    base64_image = encode_image(image_path)

    prompt = f"""
    You are an expert AI Nutritionist. 
    1. Analyze the image and identify the food items.
    2. Estimate the weight/quantity of each item based on visual cues.
    3. Calculate the calories and macros (Protein, Carbs, Fats) for these estimated quantities.
    4. If the user provided a caption: "{caption}", use it to refine your analysis.
    
    Output Format:
    Return a JSON object with two keys:
    - "log_data": A list of objects, each containing: "item" (name), "calories" (int), "protein" (float), "carbs" (float), "fats" (float), "weight_g" (estimated grams).
    - "reply": A friendly, conversational message to the user in their language (detect from caption or default to English). Explain what you see, how you estimated the weight, and the total nutrition.
    
    Example JSON structure:
    {{
        "log_data": [
            {{"item": "Grilled Chicken", "calories": 200, "protein": 40, "carbs": 0, "fats": 5, "weight_g": 150}}
        ],
        "reply": "That looks like a delicious grilled chicken breast! I estimated it's about 150g..."
    }}
    """

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=500
        )
        
        content = response.choices[0].message.content.strip()
        # Clean up markdown
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
            
        data = json.loads(content)
        return data.get("log_data", []), data.get("reply", "I processed your image.")
        
    except Exception as e:
        print(f"Error analyzing image: {e}")
        return [], "Sorry, I had trouble analyzing that photo."

async def process_user_message(text: str):
    """
    Handles text input. Decides if it's a food log or general conversation.
    Returns: (structured_data, conversational_reply)
    """
    prompt = f"""
    You are a friendly AI Nutrition Assistant. The user sent: "{text}".
    
    Task:
    1. Determine if the user is trying to log food or just chatting.
    2. If logging food: Extract items, estimate calories/macros.
    3. If chatting: Respond helpfully.
    
    Output JSON:
    {{
        "is_food_log": boolean,
        "log_data": [ ... (same format as above, empty if not logging) ... ],
        "reply": "Your conversational response here. Adapt to the user's language and tone."
    }}
    """

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs raw JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
            
        data = json.loads(content)
        return data.get("log_data", []), data.get("reply", "I didn't understand that.")
        
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return [], "Sorry, I encountered an error."

