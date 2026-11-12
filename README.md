# FitTrack – Phase 3: Smart Features & Advanced Analytics

A full-stack fitness platform built with FastAPI, SQLite, SQLAlchemy, JWT authentication, React, Vite, and Recharts. Phase 3 extends Phase 2 while retaining its workout journal, goals, planner, exercise library, streaks, badges, comparison reports, and notifications.

## Phase 3 features

- **Nutrition diary:** log Breakfast, Lunch, Dinner, and Snacks with calories, protein, carbs, and fats; view daily totals and remove entries.
- **Water tracker:** log water in millilitres, set a daily goal, view progress, and remove entries.
- **Workout recommendations:** goal- and recent-activity-based rule engine suggests workouts. This is transparent rule-based logic, not a hosted generative-AI service or a machine-learning model.
- **Workout timer:** live session timer with start/stop/reset; stopping a session saves duration and an estimated calorie value to the existing workout journal.
- **Advanced analytics:** 30-day activity trends, goal completion rate, active days, and consistency percentage.
- **Reminder settings:** save workout, meal, and water reminder preferences and times. These are in-app preferences; background push/email delivery is not configured.
- **External integration status:** Google Fit and Apple Health are listed as optional and not connected. OAuth credentials, platform permissions, and provider-specific implementation are required before syncing real data.

## Retained Phase 1 and Phase 2 features

JWT registration/login, protected workout CRUD, goals, daily/weekly/monthly analytics, notifications, workout plans, exercise library, progress comparison, streak tracking, achievements, and dashboard summary.

## Requirements

- Python 3.10+
- Node.js 18+ and npm

## Run backend (Windows PowerShell)

```powershell
cd "$HOME\OneDrive\Documents\FitTrack-Phase3\backend"
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend\.env` and set a long random `SECRET_KEY`, then run:

```powershell
uvicorn app.main:app --reload --port 8000
```

Swagger: http://127.0.0.1:8000/docs

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Run frontend (second PowerShell terminal)

```powershell
cd "$HOME\OneDrive\Documents\FitTrack-Phase3\frontend"
npm install
npm run dev
```

Open http://localhost:5173

## Phase 3 API endpoints

All user-specific endpoints require `Authorization: Bearer <JWT>` and are scoped to the authenticated user.

| Feature | Endpoints |
|---|---|
| Meals | `GET/POST /api/nutrition/meals`, `GET /api/nutrition/summary`, `DELETE /api/nutrition/meals/{meal_id}` |
| Water | `GET/POST /api/water`, `GET /api/water/summary`, `DELETE /api/water/{entry_id}` |
| Recommendations | `GET /api/recommendations/workouts` |
| Advanced analytics | `GET /api/analytics/advanced` |
| Reminder preferences | `GET/PUT /api/reminders` |
| Integration status | `GET /api/integrations/status` |

Timer sessions are saved through the existing `POST /api/workouts` endpoint.

## Suggested Swagger test sequence

1. Register or log in using `/api/auth/register` and `/api/auth/login`.
2. Click **Authorize** and provide the bearer token.
3. Add a meal with a valid meal type and check `/api/nutrition/summary`.
4. Log water and check `/api/water/summary`.
5. Create a goal and a few workouts, then check `/api/recommendations/workouts` and `/api/analytics/advanced`.
6. Save reminder preferences using `/api/reminders`.
7. Check `/api/integrations/status` to confirm optional providers are not configured.

## Database, migration, and security notes

- SQLAlchemy creates the new Phase 3 tables (`meals`, `water_tracking`, `reminder_settings`) at startup without dropping existing tables.
- If upgrading an existing Phase 2 installation, back up `backend\fittrack.db` before starting Phase 3. Keep the same database file to retain users, workouts, goals, and Phase 2 records.
- `.env`, SQLite databases, virtual environments, and `node_modules` are excluded from this ZIP. `.env.example` is provided.
- Passwords are hashed and user data endpoints validate JWT identity and ownership. Pydantic validates request fields.
- Nutrition values are user-entered estimates; workout calorie estimates are approximate. FitTrack is a learning/demo project, not a medical device.
