# TODO / Next Steps

- **Fix Windows barcode dependency:** Resolve missing `libzbar-64.dll` for `pyzbar`; document install steps or bundle the DLL for Windows users.
- **Persist goal macros:** Currently only `daily_calorie_goal` is stored; extend schema/Firebase sync to store protein/carbs/fats targets from `calculate_daily_goals_deterministic`.
- **Add goal flow tests:** Cover FSM path for Auto-Calculate vs Manual, ensuring the generic text handler never intercepts while states are active.
- **WebApp telemetry & errors:** Add lightweight logging for failed Firestore loads and WebApp `tg.sendData` errors to improve debugging.
- **OpenAI error handling:** Add retries/rate-limit safeguards for text/photo logging and surface user-friendly fallback messages.
