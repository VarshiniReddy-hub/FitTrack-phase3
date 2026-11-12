from datetime import datetime, date, timedelta
from typing import Optional
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
ALGORITHM = "HS256"
TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fittrack.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

app = FastAPI(title="FitTrack Fitness API", version="1.0.0",
              description="Fitness tracking API with JWT authentication, workouts, goals, analytics and notifications.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Workout(Base):
    __tablename__ = "workouts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    workout_name = Column(String(100), nullable=False)
    category = Column(String(20), nullable=False)
    duration = Column(Integer, nullable=False)
    calories_burned = Column(Float, nullable=False)
    workout_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Goal(Base):
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    goal_type = Column(String(30), nullable=False)
    target_value = Column(Float, nullable=False)
    current_value = Column(Float, default=0)
    deadline = Column(Date, nullable=False)
    status = Column(String(20), default="IN_PROGRESS")
    created_at = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(120), nullable=False)
    message = Column(String(500), nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)



class WorkoutPlan(Base):
    __tablename__ = "workout_plans"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(120), nullable=False)
    description = Column(String(1000), default="")
    scheduled_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Exercise(Base):
    __tablename__ = "exercises"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, unique=True)
    category = Column(String(20), nullable=False)
    description = Column(String(1000), nullable=False)
    duration = Column(Integer, nullable=False)

class Streak(Base):
    __tablename__ = "streaks"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_workout_date = Column(Date, nullable=True)

class Badge(Base):
    __tablename__ = "badges"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), nullable=False, unique=True)
    description = Column(String(300), nullable=False)
    icon = Column(String(30), nullable=False)

class UserBadge(Base):
    __tablename__ = "user_badges"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    badge_id = Column(Integer, ForeignKey("badges.id"), nullable=False)
    earned_at = Column(DateTime, default=datetime.utcnow)



# ---------------- Phase 3: nutrition, hydration, reminders ----------------
class Meal(Base):
    __tablename__ = "meals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    meal_type = Column(String(20), nullable=False)
    food_name = Column(String(120), nullable=False)
    calories = Column(Float, nullable=False)
    protein = Column(Float, nullable=False, default=0)
    carbs = Column(Float, nullable=False, default=0)
    fats = Column(Float, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class WaterTracking(Base):
    __tablename__ = "water_tracking"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ReminderSetting(Base):
    __tablename__ = "reminder_settings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reminder_type = Column(String(20), nullable=False)
    enabled = Column(Boolean, default=True)
    reminder_time = Column(String(5), nullable=False, default="09:00")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(user_id: int):
    expires = datetime.utcnow() + timedelta(minutes=TOKEN_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expires}, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise credentials_error
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_error
    return user

class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

class LoginIn(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class WorkoutIn(BaseModel):
    workout_name: str = Field(min_length=2, max_length=100)
    category: str
    duration: int = Field(gt=0, le=1440)
    calories_burned: float = Field(ge=0, le=10000)
    workout_date: date

    @classmethod
    def validate_category(cls, value):
        return value

class WorkoutOut(WorkoutIn):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class GoalIn(BaseModel):
    goal_type: str
    target_value: float = Field(gt=0, le=1000000)
    current_value: float = Field(ge=0, le=1000000)
    deadline: date

class GoalUpdate(BaseModel):
    goal_type: Optional[str] = Field(default=None, min_length=2, max_length=30)
    target_value: Optional[float] = Field(default=None, gt=0, le=1000000)
    current_value: Optional[float] = Field(default=None, ge=0, le=1000000)
    deadline: Optional[date] = None
    status: Optional[str] = None

class GoalOut(BaseModel):
    id: int
    user_id: int
    goal_type: str
    target_value: float
    current_value: float
    deadline: date
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

def validate_category(category: str):
    if category not in {"Cardio", "Strength", "Yoga"}:
        raise HTTPException(422, "category must be Cardio, Strength, or Yoga")

def validate_goal_type(goal_type: str):
    if goal_type not in {"Weight Loss", "Muscle Gain", "Steps"}:
        raise HTTPException(422, "goal_type must be Weight Loss, Muscle Gain, or Steps")


# Seed the shared exercise library and milestone catalogue without duplicating rows.
def seed_phase2_catalogue():
    db = SessionLocal()
    try:
        if db.query(Exercise).count() == 0:
            rows = [
                ("Brisk Walking","Cardio","A steady-paced walk to build endurance.",30),
                ("Running","Cardio","A continuous run for cardiovascular fitness.",25),
                ("Cycling","Cardio","Ride at a comfortable, consistent pace.",30),
                ("Jumping Jacks","Cardio","A full-body warm-up movement.",10),
                ("Push-ups","Strength","A bodyweight upper-body strength exercise.",15),
                ("Squats","Strength","A lower-body movement targeting legs and glutes.",15),
                ("Plank","Strength","Hold a stable core position.",5),
                ("Lunges","Strength","Alternating steps to strengthen the lower body.",15),
                ("Sun Salutation","Yoga","A flowing sequence linking movement and breath.",15),
                ("Child's Pose","Yoga","A gentle resting and mobility pose.",5),
                ("Warrior Pose","Yoga","A standing posture for balance and strength.",8),
                ("Breathing Flow","Yoga","A mindful breathing and relaxation practice.",10),
            ]
            db.add_all([Exercise(name=n,category=c,description=d,duration=t) for n,c,d,t in rows])
        if db.query(Badge).count() == 0:
            rows = [
                ("First Step","Complete your first workout.","🏁"),
                ("Getting Started","Complete 5 workouts.","💪"),
                ("Consistency","Complete 10 workouts.","🔥"),
                ("Week Warrior","Maintain a 7-day workout streak.","⚡"),
                ("Goal Getter","Complete a fitness goal.","🎯"),
            ]
            db.add_all([Badge(name=n,description=d,icon=i) for n,d,i in rows])
        db.commit()
    finally:
        db.close()

seed_phase2_catalogue()

@app.get("/")
def root():
    return {"message": "FitTrack API is running", "docs": "/docs"}

@app.post("/api/auth/register", response_model=UserOut, status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter((User.username == data.username) | (User.email == data.email)).first():
        raise HTTPException(409, "Username or email already registered")
    user = User(username=data.username, email=data.email, hashed_password=hash_password(data.password))
    db.add(user); db.commit(); db.refresh(user)
    return user

@app.post("/api/auth/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Incorrect username or password")
    return {"access_token": create_token(user.id), "token_type": "bearer", "user": user}

@app.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user

@app.get("/api/workouts", response_model=list[WorkoutOut])
def list_workouts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Workout).filter(Workout.user_id == user.id).order_by(Workout.workout_date.desc(), Workout.id.desc()).all()

@app.post("/api/workouts", response_model=WorkoutOut, status_code=201)
def add_workout(data: WorkoutIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    validate_category(data.category)
    workout = Workout(**data.model_dump(), user_id=user.id)
    db.add(workout); db.commit(); db.refresh(workout)
    refresh_streak_and_badges(db, user.id)
    return workout

@app.put("/api/workouts/{workout_id}", response_model=WorkoutOut)
def update_workout(workout_id: int, data: WorkoutIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    validate_category(data.category)
    workout = db.query(Workout).filter(Workout.id == workout_id, Workout.user_id == user.id).first()
    if not workout: raise HTTPException(404, "Workout not found")
    for key, value in data.model_dump().items(): setattr(workout, key, value)
    db.commit(); db.refresh(workout)
    return workout

@app.delete("/api/workouts/{workout_id}")
def delete_workout(workout_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    workout = db.query(Workout).filter(Workout.id == workout_id, Workout.user_id == user.id).first()
    if not workout: raise HTTPException(404, "Workout not found")
    db.delete(workout); db.commit()
    refresh_streak_and_badges(db, user.id)
    return {"message": "Workout deleted"}

@app.get("/api/progress/daily")
def daily_progress(day: date = date.today(), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Workout).filter(Workout.user_id == user.id, Workout.workout_date == day).all()
    return {"date": day, "total_workouts": len(rows), "total_calories": round(sum(x.calories_burned for x in rows), 1),
            "total_duration": sum(x.duration for x in rows), "workouts": rows}

@app.get("/api/goals", response_model=list[GoalOut])
def list_goals(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Goal).filter(Goal.user_id == user.id).order_by(Goal.created_at.desc()).all()

@app.post("/api/goals", response_model=GoalOut, status_code=201)
def add_goal(data: GoalIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    validate_goal_type(data.goal_type)
    status_value = "COMPLETED" if data.current_value >= data.target_value else "IN_PROGRESS"
    goal = Goal(**data.model_dump(), user_id=user.id, status=status_value)
    db.add(goal)
    db.add(Notification(user_id=user.id, title="New goal created", message=f"Your {data.goal_type} goal has been added. Keep going!"))
    db.commit(); db.refresh(goal)
    refresh_streak_and_badges(db, user.id)
    return goal

@app.put("/api/goals/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: int, data: GoalUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if not goal: raise HTTPException(404, "Goal not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        if value is not None: setattr(goal, key, value)
    validate_goal_type(goal.goal_type)
    goal.status = "COMPLETED" if goal.current_value >= goal.target_value else "IN_PROGRESS"
    db.commit(); db.refresh(goal)
    return goal

@app.delete("/api/goals/{goal_id}")
def delete_goal(goal_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if not goal: raise HTTPException(404, "Goal not found")
    db.delete(goal); db.commit()
    return {"message": "Goal deleted"}

@app.get("/api/analytics/weekly")
def weekly_analytics(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = date.today(); start = today - timedelta(days=6)
    rows = db.query(Workout).filter(Workout.user_id == user.id, Workout.workout_date >= start, Workout.workout_date <= today).all()
    result = []
    for i in range(7):
        day = start + timedelta(days=i)
        daily = [w for w in rows if w.workout_date == day]
        result.append({"date": day.isoformat(), "day": day.strftime("%a"), "workouts": len(daily),
                       "calories": round(sum(w.calories_burned for w in daily), 1), "duration": sum(w.duration for w in daily)})
    return {"period": "weekly", "data": result, "total_workouts": sum(x["workouts"] for x in result),
            "total_calories": sum(x["calories"] for x in result)}

@app.get("/api/analytics/monthly")
def monthly_analytics(month: Optional[str] = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if month:
        try: year, mon = map(int, month.split("-")); start = date(year, mon, 1)
        except Exception: raise HTTPException(422, "month must use YYYY-MM")
    else:
        today = date.today(); start = date(today.year, today.month, 1)
    end = (date(start.year + (start.month == 12), (start.month % 12) + 1, 1) - timedelta(days=1))
    rows = db.query(Workout).filter(Workout.user_id == user.id, Workout.workout_date >= start, Workout.workout_date <= end).all()
    by_category = {}
    for w in rows: by_category[w.category] = by_category.get(w.category, 0) + w.calories_burned
    return {"period": start.strftime("%Y-%m"), "total_workouts": len(rows),
            "total_calories": round(sum(w.calories_burned for w in rows), 1),
            "total_duration": sum(w.duration for w in rows),
            "categories": [{"category": k, "calories": round(v, 1)} for k, v in by_category.items()]}

@app.get("/api/notifications", response_model=list[NotificationOut])
def notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).all()

@app.patch("/api/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(notification_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user.id).first()
    if not item: raise HTTPException(404, "Notification not found")
    item.is_read = True; db.commit(); db.refresh(item)
    return item

@app.post("/api/notifications/generate-daily-reminder")
def generate_daily_reminder(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = date.today()
    has_workout = db.query(Workout).filter(Workout.user_id == user.id, Workout.workout_date == today).first()
    if has_workout:
        message = "Great work today! Your activity has been recorded."
        title = "Workout completed"
    else:
        message = "A short walk or workout can help you stay consistent. Make time for movement today."
        title = "Daily activity reminder"
    item = Notification(user_id=user.id, title=title, message=message)
    db.add(item); db.commit(); db.refresh(item)
    return item


# ---------------- Phase 2: Workout plans ----------------
class WorkoutPlanIn(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=1000)
    scheduled_date: date

class WorkoutPlanOut(WorkoutPlanIn):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

@app.get("/api/workout-plans", response_model=list[WorkoutPlanOut])
def list_workout_plans(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user.id).order_by(WorkoutPlan.scheduled_date.asc()).all()

@app.post("/api/workout-plans", response_model=WorkoutPlanOut, status_code=201)
def create_workout_plan(data: WorkoutPlanIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plan = WorkoutPlan(**data.model_dump(), user_id=user.id)
    db.add(plan); db.commit(); db.refresh(plan)
    db.add(Notification(user_id=user.id, title="Workout scheduled", message=f"{plan.title} is scheduled for {plan.scheduled_date.isoformat()}."))
    db.commit()
    return plan

@app.delete("/api/workout-plans/{plan_id}")
def delete_workout_plan(plan_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == user.id).first()
    if not plan: raise HTTPException(404, "Workout plan not found")
    db.delete(plan); db.commit()
    return {"message": "Workout plan deleted"}

# ---------------- Phase 2: Exercise library ----------------
class ExerciseOut(BaseModel):
    id: int
    name: str
    category: str
    description: str
    duration: int
    model_config = ConfigDict(from_attributes=True)

@app.get("/api/exercises", response_model=list[ExerciseOut])
def list_exercises(search: Optional[str] = None, category: Optional[str] = None,
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Exercise)
    if search: query = query.filter(Exercise.name.ilike(f"%{search.strip()}%"))
    if category:
        if category not in {"Cardio", "Strength", "Yoga"}: raise HTTPException(422, "Invalid exercise category")
        query = query.filter(Exercise.category == category)
    return query.order_by(Exercise.category, Exercise.name).all()

class ExerciseWorkoutIn(BaseModel):
    workout_date: date
    duration: Optional[int] = Field(default=None, gt=0, le=1440)
    calories_burned: float = Field(default=0, ge=0, le=10000)

@app.post("/api/exercises/{exercise_id}/add-to-workouts", response_model=WorkoutOut, status_code=201)
def add_exercise_to_workout(exercise_id: int, data: ExerciseWorkoutIn,
                            db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise: raise HTTPException(404, "Exercise not found")
    workout = Workout(user_id=user.id, workout_name=exercise.name, category=exercise.category,
        duration=data.duration or exercise.duration, calories_burned=data.calories_burned, workout_date=data.workout_date)
    db.add(workout); db.commit(); db.refresh(workout)
    refresh_streak_and_badges(db, user.id)
    return workout

# ---------------- Phase 2: streaks and achievements ----------------
def refresh_streak_and_badges(db: Session, user_id: int):
    dates = [r[0] for r in db.query(Workout.workout_date).filter(Workout.user_id == user_id).distinct().order_by(Workout.workout_date).all()]
    current = 0
    longest_from_history = 0
    run = 0
    previous = None
    for workout_day in dates:
        run = run + 1 if previous and (workout_day - previous).days == 1 else 1
        longest_from_history = max(longest_from_history, run)
        previous = workout_day
    if dates:
        today = date.today()
        # A streak remains active through today, or through yesterday if no session has been logged today.
        if dates[-1] >= today - timedelta(days=1):
            current = 1
            for idx in range(len(dates)-1, 0, -1):
                if (dates[idx] - dates[idx-1]).days == 1: current += 1
                else: break
    streak = db.query(Streak).filter(Streak.user_id == user_id).first()
    if not streak:
        streak = Streak(user_id=user_id); db.add(streak)
    streak.current_streak = current
    streak.longest_streak = max(streak.longest_streak or 0, current, longest_from_history)
    streak.last_workout_date = dates[-1] if dates else None
    total = len(dates)  # unique active workout days, used for streak achievements
    all_workouts = db.query(Workout).filter(Workout.user_id == user_id).count()
    targets = []
    if all_workouts >= 1: targets.append("First Step")
    if all_workouts >= 5: targets.append("Getting Started")
    if all_workouts >= 10: targets.append("Consistency")
    if current >= 7: targets.append("Week Warrior")
    if db.query(Goal).filter(Goal.user_id == user_id, Goal.status == "COMPLETED").first(): targets.append("Goal Getter")
    for name in targets:
        badge = db.query(Badge).filter(Badge.name == name).first()
        earned = db.query(UserBadge).filter(UserBadge.user_id == user_id, UserBadge.badge_id == badge.id).first()
        if badge and not earned:
            db.add(UserBadge(user_id=user_id, badge_id=badge.id))
            db.add(Notification(user_id=user_id, title=f"Achievement unlocked: {badge.name}", message=badge.description))
    db.commit()

@app.get("/api/streak")
def get_streak(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    refresh_streak_and_badges(db, user.id)
    return db.query(Streak).filter(Streak.user_id == user.id).first()

@app.get("/api/badges")
def get_badges(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    refresh_streak_and_badges(db, user.id)
    rows = db.query(Badge).order_by(Badge.id).all()
    earned = {x.badge_id: x.earned_at for x in db.query(UserBadge).filter(UserBadge.user_id == user.id).all()}
    return [{"id": b.id, "name": b.name, "description": b.description, "icon": b.icon,
             "earned": b.id in earned, "earned_at": earned.get(b.id)} for b in rows]

@app.get("/api/dashboard/summary")
def phase2_dashboard_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = date.today()
    daily = db.query(Workout).filter(Workout.user_id == user.id, Workout.workout_date == today).all()
    upcoming = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user.id, WorkoutPlan.scheduled_date >= today).order_by(WorkoutPlan.scheduled_date).limit(5).all()
    goals = db.query(Goal).filter(Goal.user_id == user.id).order_by(Goal.created_at.desc()).limit(4).all()
    refresh_streak_and_badges(db, user.id)
    streak = db.query(Streak).filter(Streak.user_id == user.id).first()
    return {
        "date": today.isoformat(),
        "daily": {"workouts": len(daily), "calories": round(sum(x.calories_burned for x in daily),1), "duration": sum(x.duration for x in daily)},
        "upcoming_workouts": [{"id": x.id, "title": x.title, "description": x.description, "scheduled_date": x.scheduled_date.isoformat()} for x in upcoming],
        "goals": [{"id": x.id, "goal_type": x.goal_type, "current_value": x.current_value, "target_value": x.target_value, "status": x.status} for x in goals],
        "streak": {"current_streak": streak.current_streak, "longest_streak": streak.longest_streak}
    }

@app.get("/api/analytics/comparison")
def compare_progress(period: str = "weekly", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = date.today()
    if period not in {"weekly", "monthly"}: raise HTTPException(422, "period must be weekly or monthly")
    if period == "weekly":
        current_start = today - timedelta(days=today.weekday())
        previous_start = current_start - timedelta(days=7)
        current_end = current_start + timedelta(days=6)
        previous_end = current_start - timedelta(days=1)
    else:
        current_start = date(today.year, today.month, 1)
        previous_end = current_start - timedelta(days=1)
        previous_start = date(previous_end.year, previous_end.month, 1)
        current_end = (date(today.year + (today.month == 12), today.month % 12 + 1, 1) - timedelta(days=1))
    def aggregate(start, end):
        rows = db.query(Workout).filter(Workout.user_id == user.id, Workout.workout_date >= start, Workout.workout_date <= end).all()
        return {"workouts": len(rows), "calories": round(sum(x.calories_burned for x in rows),1), "duration": sum(x.duration for x in rows)}
    current, previous = aggregate(current_start, min(current_end, today)), aggregate(previous_start, previous_end)
    changes = {}
    for key in current:
        old = previous[key]; new = current[key]
        changes[key] = round(((new-old)/old)*100,1) if old else (100.0 if new else 0.0)
    return {"period": period, "current": current, "previous": previous, "change_percent": changes,
            "current_label": "This week" if period == "weekly" else "This month",
            "previous_label": "Last week" if period == "weekly" else "Last month"}


class MealIn(BaseModel):
    meal_type: str
    food_name: str = Field(min_length=1, max_length=120)
    calories: float = Field(ge=0, le=10000)
    protein: float = Field(default=0, ge=0, le=1000)
    carbs: float = Field(default=0, ge=0, le=1000)
    fats: float = Field(default=0, ge=0, le=1000)

class MealOut(MealIn):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class WaterIn(BaseModel):
    quantity: int = Field(gt=0, le=5000)
    date: date

class WaterOut(WaterIn):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ReminderIn(BaseModel):
    reminder_type: str
    enabled: bool = True
    reminder_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")

@app.get("/api/nutrition/meals", response_model=list[MealOut])
def list_meals(day: date = date.today(), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Meal).filter(Meal.user_id == user.id, func.date(Meal.created_at) == day.isoformat()).order_by(Meal.created_at.desc()).all()

@app.post("/api/nutrition/meals", response_model=MealOut, status_code=201)
def add_meal(data: MealIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if data.meal_type not in {"Breakfast", "Lunch", "Dinner", "Snacks"}:
        raise HTTPException(422, "meal_type must be Breakfast, Lunch, Dinner, or Snacks")
    meal = Meal(**data.model_dump(), user_id=user.id)
    db.add(meal)
    db.add(Notification(user_id=user.id, title="Meal logged", message=f"{data.food_name} added to your nutrition diary."))
    db.commit(); db.refresh(meal)
    return meal

@app.delete("/api/nutrition/meals/{meal_id}")
def delete_meal(meal_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    meal = db.query(Meal).filter(Meal.id == meal_id, Meal.user_id == user.id).first()
    if not meal: raise HTTPException(404, "Meal not found")
    db.delete(meal); db.commit()
    return {"message": "Meal deleted"}

@app.get("/api/nutrition/summary")
def nutrition_summary(day: date = date.today(), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Meal).filter(Meal.user_id == user.id, func.date(Meal.created_at) == day.isoformat()).all()
    return {"date": day.isoformat(), "meals": len(rows),
            "calories": round(sum(x.calories for x in rows),1),
            "protein": round(sum(x.protein for x in rows),1),
            "carbs": round(sum(x.carbs for x in rows),1),
            "fats": round(sum(x.fats for x in rows),1),
            "entries": rows}

@app.get("/api/water", response_model=list[WaterOut])
def list_water(day: date = date.today(), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(WaterTracking).filter(WaterTracking.user_id == user.id, WaterTracking.date == day).order_by(WaterTracking.created_at.desc()).all()

@app.post("/api/water", response_model=WaterOut, status_code=201)
def add_water(data: WaterIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = WaterTracking(**data.model_dump(), user_id=user.id)
    db.add(item); db.commit(); db.refresh(item)
    return item

@app.delete("/api/water/{entry_id}")
def delete_water(entry_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.query(WaterTracking).filter(WaterTracking.id == entry_id, WaterTracking.user_id == user.id).first()
    if not item: raise HTTPException(404, "Water entry not found")
    db.delete(item); db.commit()
    return {"message": "Water entry deleted"}

@app.get("/api/water/summary")
def water_summary(day: date = date.today(), goal_ml: int = 2000, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if goal_ml < 250 or goal_ml > 10000: raise HTTPException(422, "goal_ml must be between 250 and 10000")
    total = db.query(func.sum(WaterTracking.quantity)).filter(WaterTracking.user_id == user.id, WaterTracking.date == day).scalar() or 0
    return {"date": day.isoformat(), "consumed_ml": int(total), "goal_ml": goal_ml, "progress_percent": min(100, round(total / goal_ml * 100))}

@app.get("/api/recommendations/workouts")
def workout_recommendations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    history = db.query(Workout).filter(Workout.user_id == user.id).order_by(Workout.workout_date.desc()).limit(10).all()
    goals = db.query(Goal).filter(Goal.user_id == user.id, Goal.status != "COMPLETED").all()
    recent_categories = {w.category for w in history[:5]}
    goal_types = {g.goal_type for g in goals}
    suggestions = []
    if "Weight Loss" in goal_types:
        suggestions += [{"name":"Brisk Walking","category":"Cardio","duration":30,"reason":"Supports your weight-loss goal with steady aerobic activity."},
                        {"name":"Cycling","category":"Cardio","duration":25,"reason":"A low-impact cardio option to vary your routine."}]
    if "Muscle Gain" in goal_types:
        suggestions += [{"name":"Squats","category":"Strength","duration":20,"reason":"Build lower-body strength with controlled repetitions."},
                        {"name":"Push-ups","category":"Strength","duration":15,"reason":"A simple upper-body strength session."}]
    if not suggestions:
        suggestions = [{"name":"Brisk Walking","category":"Cardio","duration":25,"reason":"A balanced way to build consistency."},
                       {"name":"Sun Salutation","category":"Yoga","duration":15,"reason":"A mobility-focused recovery option."}]
    if len(recent_categories) >= 2:
        suggestions.append({"name":"Child's Pose","category":"Yoga","duration":8,"reason":"Add a gentle recovery session after varied recent workouts."})
    return {"based_on":"Your recent workout history and active goals","recommendations":suggestions[:4],
            "note":"Rule-based personalized suggestions; not a machine-learning or medical recommendation."}

@app.get("/api/analytics/advanced")
def advanced_analytics(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = date.today(); start = today - timedelta(days=29)
    rows = db.query(Workout).filter(Workout.user_id == user.id, Workout.workout_date >= start, Workout.workout_date <= today).all()
    trend=[]
    for i in range(30):
        d=start+timedelta(days=i); dayrows=[x for x in rows if x.workout_date==d]
        trend.append({"date":d.isoformat(),"workouts":len(dayrows),"calories":round(sum(x.calories_burned for x in dayrows),1),"minutes":sum(x.duration for x in dayrows)})
    goals=db.query(Goal).filter(Goal.user_id==user.id).all()
    completed=sum(1 for g in goals if g.status=="COMPLETED")
    active_days=len({x.workout_date for x in rows})
    return {"trend":trend,"goal_completion_rate":round(completed/len(goals)*100,1) if goals else 0,
            "completed_goals":completed,"total_goals":len(goals),"active_days":active_days,
            "consistency_percent":round(active_days/30*100,1)}

@app.get("/api/reminders")
def list_reminders(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(ReminderSetting).filter(ReminderSetting.user_id==user.id).order_by(ReminderSetting.reminder_type).all()

@app.put("/api/reminders")
def save_reminder(data: ReminderIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if data.reminder_type not in {"Workout","Meal","Water"}: raise HTTPException(422,"reminder_type must be Workout, Meal, or Water")
    row=db.query(ReminderSetting).filter(ReminderSetting.user_id==user.id,ReminderSetting.reminder_type==data.reminder_type).first()
    if not row:
        row=ReminderSetting(user_id=user.id,reminder_type=data.reminder_type); db.add(row)
    row.enabled=data.enabled; row.reminder_time=data.reminder_time
    db.commit(); db.refresh(row)
    return row

@app.get("/api/integrations/status")
def integrations_status(user: User = Depends(get_current_user)):
    return {"google_fit":{"available":False,"status":"Optional integration not configured"},
            "apple_health":{"available":False,"status":"Optional integration not configured"},
            "message":"External sync requires provider OAuth credentials and platform permissions. No external data is being synced."}
