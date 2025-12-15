import firebase_admin
from firebase_admin import credentials, firestore
import os
import logging

# Initialize Firebase Admin SDK
# NOTE: This requires a serviceAccountKey.json file in the root directory
# You can download this from Firebase Console -> Project Settings -> Service Accounts
CRED_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "serviceAccountKey.json")

db = None

def init_firebase():
    global db
    if not os.path.exists(CRED_PATH):
        logging.warning(f"⚠️ Firebase Service Account Key not found at {CRED_PATH}. Real-time sync will not work.")
        return

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(CRED_PATH)
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        logging.info("✅ Firebase Admin SDK initialized successfully.")
    except Exception as e:
        logging.error(f"❌ Failed to initialize Firebase: {e}")

def update_user_stats_in_firebase(user_id, summary_data, logs_data):
    """
    Pushes the latest user stats to Firestore.
    Structure: users/{user_id}
    """
    if db is None:
        return

    try:
        doc_ref = db.collection("users").document(str(user_id))
        
        # Format logs for Firestore
        formatted_logs = []
        for log in logs_data:
            formatted_logs.append({
                "name": log['food_name'],
                "cals": log['calories'],
                "prot": log['protein'],
                "carbs": log['carbs'],
                "fats": log['fats'],
                "score": log['health_score'],
                "period": log['meal_period'] if 'meal_period' in log.keys() else 'Snack'
            })

        data = {
            "total_cals": summary_data['total_calories'] or 0,
            "goal_cals": summary_data.get('daily_calorie_goal', 2000),
            "macros": {
                "protein": summary_data['total_protein'] or 0,
                "carbs": summary_data['total_carbs'] or 0,
                "fats": summary_data['total_fats'] or 0
            },
            "logs": formatted_logs,
            "last_updated": firestore.SERVER_TIMESTAMP
        }
        
        doc_ref.set(data, merge=True)
        logging.info(f"🔥 Synced data for user {user_id} to Firebase.")
        
    except Exception as e:
        logging.error(f"❌ Error syncing to Firebase: {e}")
