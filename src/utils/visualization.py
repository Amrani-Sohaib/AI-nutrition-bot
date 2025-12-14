def generate_text_progress_bar(protein: float, carbs: float, fats: float) -> str:
    """
    Generates a text-based progress bar for macronutrients.
    """
    total = protein + carbs + fats
    if total == 0:
        return ""
        
    p_pct = int((protein / total) * 100)
    c_pct = int((carbs / total) * 100)
    f_pct = int((fats / total) * 100)
    
    # Helper to create a bar string
    def make_bar(pct, filled_char='adh', empty_char='░'):
        # 10 blocks total
        blocks = int(pct / 10)
        return (filled_char * blocks).ljust(10, empty_char)

    # Using different colored squares/circles for visual distinction
    bar = "\n<b>📊 Macro Distribution:</b>\n"
    bar += f"💪 Prot:  {make_bar(p_pct, '🟥', '⬜')} {p_pct}%\n"
    bar += f"🍞 Carb:  {make_bar(c_pct, '🟦', '⬜')} {c_pct}%\n"
    bar += f"🥑 Fat:   {make_bar(f_pct, '🟧', '⬜')} {f_pct}%"
    
    return bar
