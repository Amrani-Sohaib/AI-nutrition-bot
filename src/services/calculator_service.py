def calculate_daily_goals_deterministic(age, gender, weight, height, activity):
    """
    Calculates daily calorie and macro goals using the Mifflin-St Jeor equation.
    Returns a dictionary with calories, protein, carbs, fats, and an explanation.
    """
    # 1. Calculate BMR (Basal Metabolic Rate) - Mifflin-St Jeor
    # Weight in kg, Height in cm, Age in years
    if str(gender).lower().startswith('m'): # Male
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else: # Female
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
    
    # 2. Apply Activity Multiplier to get TDEE
    activity_multipliers = {
        "Sedentary": 1.2,
        "Lightly Active": 1.375,
        "Moderately Active": 1.55,
        "Very Active": 1.725
    }
    
    # Default to Sedentary if not found or partial match
    multiplier = 1.2
    for key, val in activity_multipliers.items():
        if key in str(activity):
            multiplier = val
            break
            
    tdee = int(bmr * multiplier)
    
    # 3. Calculate Macros (Standard Balanced Split: 30% P / 35% F / 35% C)
    # Protein: 4 kcal/g
    # Carbs: 4 kcal/g
    # Fats: 9 kcal/g
    
    protein_cals = tdee * 0.30
    fats_cals = tdee * 0.30
    carbs_cals = tdee * 0.40
    
    protein_g = int(protein_cals / 4)
    fats_g = int(fats_cals / 9)
    carbs_g = int(carbs_cals / 4)
    
    explanation = (
        f"Calculated using Mifflin-St Jeor equation.\n"
        f"BMR: {int(bmr)} kcal | TDEE: {tdee} kcal\n"
        f"Split: 30% Protein, 40% Carbs, 30% Fats"
    )
    
    return {
        "calories": tdee,
        "protein": protein_g,
        "carbs": carbs_g,
        "fats": fats_g,
        "explanation": explanation
    }
