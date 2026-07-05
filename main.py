from db_utils import get_mongo_client
import sys
import os
import logging
import traceback
import asyncio
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("pymongo").setLevel(logging.WARNING)

# Ensure module path works when running via uvicorn
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# FastAPI application
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

# Groq client
from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY environment variable not set")
groq_client = Groq(api_key=GROQ_API_KEY)

# Admin API Key for authentication
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "admin-secret-key-123")
api_key_header = APIKeyHeader(name="X-Admin-API-Key", auto_error=False)

async def verify_admin_key(api_key: str = Depends(api_key_header)):
    """Verify admin API key for protected endpoints."""
    if api_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin API key"
        )
    return api_key

# MongoDB connections
import motor.motor_asyncio
import re
from urllib.parse import quote_plus, unquote_plus

MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI environment variable not set")

def escape_mongodb_uri(uri: str) -> str:
    match = re.match(r"^(mongodb(?:\+srv)?://)(.*)@(.*)$", uri)
    if match:
        prefix, userpass, rest = match.groups()
        if ":" in userpass:
            user, pwd = userpass.split(":", 1)
            user = quote_plus(unquote_plus(user))
            pwd = quote_plus(unquote_plus(pwd))
            return f"{prefix}{user}:{pwd}@{rest}"
        else:
            user = quote_plus(unquote_plus(userpass))
            return f"{prefix}{user}@{rest}"
    return uri

MONGODB_URI = escape_mongodb_uri(MONGODB_URI)

# Synchronous client for quick reads/writes
sync_mongo_client = get_mongo_client(MONGODB_URI)

# Asynchronous client removed to fix event loop hanging issues completely

# Collections
sync_users_collection = sync_mongo_client["welfarebot"]["users"]
sync_deleted_users_collection = sync_mongo_client["welfarebot"]["deleted_users"]
sync_schemes_collection = sync_mongo_client["welfarebot"]["schemes"]
sync_conversations_collection = sync_mongo_client["welfarebot"]["conversations"]
sync_feedbacks_collection = sync_mongo_client["welfarebot"]["feedbacks"]
sync_reminders_collection = sync_mongo_client["welfarebot"]["reminders"]

# Build LangGraph
from agent.graph import build_graph

welfare_graph = build_graph(groq_client, sync_users_collection, sync_schemes_collection)

# Scraper + scheduler (moved to top so they're defined before any endpoint uses them)
from scraper.manager import run_scraper
from apscheduler.schedulers.background import BackgroundScheduler
from backend.admin_routes import router as admin_router
from scripts.enrich_raw import run_enrichment
from scripts.auto_verify_complete import auto_verify_complete

scheduler = BackgroundScheduler()
# scheduler.add_job(run_scraper, "interval", days=3, id="scraper_job")
# scheduler.add_job(run_enrichment, "cron", hour=2, minute=0, id="enrich_job")
# scheduler.add_job(auto_verify_complete, "cron", hour=3, minute=0, id="auto_verify_job")
# scheduler.start()

# FastAPI app instance
app = FastAPI(title="WelfareBot Backend")
app.include_router(admin_router)

@app.on_event("startup")
async def startup_event():
    # Warm up SentenceTransformer model in a separate thread so it doesn't block startup
    # Disabled on Free Tier to prevent Out Of Memory (OOM) crashes
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    show_form_choice: Optional[bool] = None
    show_pin_popup: Optional[bool] = None
    pin_mode: Optional[str] = None
    pin_lockout_until: Optional[str] = None
    clear_session: Optional[bool] = None
    chips: Optional[List[str]] = None
    apply_link: Optional[str] = None
    show_apply_button: Optional[bool] = None
    confidence_score: Optional[int] = None


class SubmitProfileRequest(BaseModel):
    session_id: str
    name: str
    language_preference: str
    state: str
    occupation: str
    caste_category: str
    gender: str
    age: str
    income_bracket: str
    land_size: Optional[str] = ""
    email: Optional[str] = ""


class FeedbackRequest(BaseModel):
    session_id: str
    user_name: Optional[str] = "Unknown"
    rating: int
    opinion: Optional[str] = ""
    suggestion: Optional[str] = ""


# Helper function to generate chips dynamically
def generate_chips(onboarding_step: str, user_doc: dict, intent: str = None, schemes: list = None, message: str = "") -> List[str]:
    """Generate suggestion chips based on conversation state."""
    chips = []
    
    # Load user's language and translations
    lang = user_doc.get("language_preference", "en")
    from agent.nodes import get_trans
    trans = get_trans(lang)
    
    # Check intent first for scheme_query and FAQ
    if intent == "scheme_query" and schemes:
        # Add scheme names as chips
        for scheme in schemes[:10]:
            chips.append(scheme.get("name", "Unknown Scheme"))
        
        ask_else_word = {
            "en": "Ask Something Else",
            "hi": "कुछ और पूछें",
            "te": "మరొకటి అడగండి",
            "ta": "வேறொன்று கேளுங்கள்",
            "kn": "ಬೇರೆ ಏನನ್ನಾದರೂ ಕೇಳಿ"
        }.get(lang, "Ask Something Else")
        chips.append(ask_else_word)
        
        # If user selected a scheme (message matches scheme name), add Apply Now
        if schemes and any(s.get("name", "").lower() in message.lower() for s in schemes):
            chips.append("Apply Now")
    elif intent == "faq":
        find_my_schemes_word = {
            "en": "Find My Schemes",
            "hi": "मेरी योजनाएं खोजें",
            "te": "నా పథకాలను కనుగొను",
            "ta": "என் திட்டங்களைக் காண்க",
            "kn": "ನನ್ನ ಯೋಜನೆಗಳನ್ನು ಹುಡುಕಿ"
        }.get(lang, "Find My Schemes")
        ask_else_word = {
            "en": "Ask Something Else",
            "hi": "कुछ और पूछें",
            "te": "మరొకటి అడగండి",
            "ta": "வேறொன்று கேளுங்கள்",
            "kn": "ಬೇರೆ ಏನನ್ನಾದರೂ ಕೇಳಿ"
        }.get(lang, "Ask Something Else")
        chips.extend([find_my_schemes_word, ask_else_word])
    # Then check onboarding steps
    elif onboarding_step == "name":
        chips.extend(["English", "हिंदी", "తెలుగు", "தமிழ்", "ಕನ್ನಡ"])
    elif onboarding_step == "language_preference":
        chips.extend([trans.get("fill_form_chip", "📝 Fill Form"), trans.get("chat_instead_chip", "💬 Chat Instead")])
    elif onboarding_step == "form_chat_choice":
        chips.extend([trans.get("fill_form_chip", "📝 Fill Form"), trans.get("chat_instead_chip", "💬 Chat Instead")])
    elif onboarding_step == "state":
        chips.extend(trans.get("states", ["Andhra Pradesh", "Telangana", "Delhi", "Maharashtra", "Tamil Nadu"]))
    elif onboarding_step == "occupation":
        chips.extend(trans.get("occupations", ["Student", "Farmer", "Daily Wage Worker", "Government Employee", "Business"]))
    elif onboarding_step == "caste_category":
        chips.extend(trans.get("castes", ["General", "OBC", "SC", "ST", "EWS"]))
    elif onboarding_step == "gender":
        chips.extend(trans.get("genders", ["Male", "Female", "Other"]))
    elif onboarding_step == "age":
        chips.extend(["18-25", "26-35", "36-50", "50+"])
    elif onboarding_step == "income_bracket":
        chips.extend(trans.get("incomes", ["Below 1 Lakh", "1-2.5 Lakh", "2.5-5 Lakh", "5-10 Lakh", "Above 10 Lakh"]))
    elif onboarding_step == "land_size":
        chips.extend(trans.get("lands", ["0", "1-2 acres", "3-5 acres", "5+ acres"]))
    elif onboarding_step == "email":
        chips.extend([trans.get("skip_email_chip", "Skip Email")])
    elif onboarding_step == "confirmation":
        chips.extend([trans.get("yes", "Yes"), trans.get("no", "No")])
    
    # Always add Start Over at the end
    chips.append("Start Over")
    
    return chips

# Endpoints
@app.post("/submit-profile")
async def submit_profile(req: SubmitProfileRequest):
    """Handle profile form submission, normalize inputs, and transition to confirmation."""
    try:
        from agent.nodes import normalize_to_english, normalize_lang_code
        
        # Get language preference and normalize it
        lang_code = normalize_lang_code(req.language_preference)
        
        # Normalize fields to English counterparts
        state_en = normalize_to_english("state", req.state, lang_code)
        occupation_en = normalize_to_english("occupation", req.occupation, lang_code)
        caste_en = normalize_to_english("caste_category", req.caste_category, lang_code)
        gender_en = normalize_to_english("gender", req.gender, lang_code)
        income_en = normalize_to_english("income_bracket", req.income_bracket, lang_code)
        
        # Update user profile
        profile_data = {
            "session_id": req.session_id,
            "name": req.name,
            "language_preference": lang_code,
            "state": state_en,
            "occupation": occupation_en,
            "caste_category": caste_en,
            "gender": gender_en,
            "age": req.age,
            "income_bracket": income_en,
            "onboarding_step": "confirmation",
            "confirmation_step": "awaiting_confirmation",
            "editing_field": None
        }
        if req.land_size:
            land_en = normalize_to_english("land_size", req.land_size, lang_code)
            profile_data["land_size"] = land_en
        if req.email:
            profile_data["email"] = req.email
        
        sync_users_collection.update_one(
            {"session_id": req.session_id},
            {"$set": profile_data},
            upsert=True
        )
        
        return {"status": "success", "message": "Profile details saved, awaiting confirmation."}
    except Exception as e:
        logger.error(f"Submit profile error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Handle feedback form submission from users."""
    try:
        feedback_data = {
            "session_id": req.session_id,
            "user_name": req.user_name,
            "rating": req.rating,
            "opinion": req.opinion,
            "suggestion": req.suggestion,
            "timestamp": datetime.now().isoformat()
        }
        sync_feedbacks_collection.insert_one(feedback_data)
        return {"status": "success", "message": "Feedback submitted successfully."}
    except Exception as e:
        logger.error(f"Submit feedback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/voice-input")
async def voice_input(file: UploadFile = File(...)):
    """Handle voice input - transcribe audio and return text with detected language using Groq Whisper."""
    temp_path = f"temp_audio_{int(time.time())}.webm"
    try:
        # Read audio file
        audio_data = await file.read()
        
        # Save to temporary file
        with open(temp_path, "wb") as f:
            f.write(audio_data)
        
        # Call Groq Whisper translation (translates any language to English text)
        with open(temp_path, "rb") as audio_file:
            translation = groq_client.audio.translations.create(
                file=audio_file,
                model="whisper-large-v3"
            )
            transcribed_text = translation.text
            
        from agent.languages import detect_language
        detected_lang = detect_language(transcribed_text) if transcribed_text else "en"
        
        return {
            "transcribed_text": transcribed_text,
            "detected_language": detected_lang,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Voice input error: {e}")
        return {
            "transcribed_text": "",
            "detected_language": "en",
            "status": "error",
            "error": str(e)
        }
    finally:
        # Clean up temp file
        import os
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

@app.post("/send-reminder")
async def send_reminder(session_id: str = Form(...), message: str = Form(...)):
    """Send an email reminder to a user about schemes or deadlines."""
    try:
        # Get user details
        user_doc = sync_users_collection.find_one({"session_id": session_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user has email
        user_email = user_doc.get("email")
        if not user_email:
            return {
                "status": "error",
                "message": "User email not found. Please provide email in profile."
            }
        
        # For demo purposes, we'll log the email instead of actually sending
        # In production, integrate with SMTP service like SendGrid, AWS SES, etc.
        logger.info(f"EMAIL REMINDER - To: {user_email}, Message: {message}")
        
        return {
            "status": "success",
            "message": f"Reminder queued for {user_email}",
            "email": user_email
        }
    except Exception as e:
        logger.error(f"Send reminder error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/schedule-reminder")
async def schedule_reminder(session_id: str = Form(...), reminder_date: str = Form(...), message: str = Form(...)):
    """Schedule a reminder for a specific date."""
    try:
        # Parse reminder date
        try:
            reminder_dt = datetime.fromisoformat(reminder_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DD HH:MM:SS)")
        
        # Get user details
        user_doc = sync_users_collection.find_one({"session_id": session_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Store reminder in database
        reminder_doc = {
            "session_id": session_id,
            "email": user_doc.get("email"),
            "reminder_date": reminder_dt,
            "message": message,
            "sent": False,
            "created_at": datetime.utcnow()
        }
        
        # Create reminders collection if it doesn't exist
        sync_users_collection.database.create_collection("reminders")
        reminders_collection = sync_users_collection.database["reminders"]
        
        reminders_collection.insert_one(reminder_doc)
        
        return {
            "status": "success",
            "message": f"Reminder scheduled for {reminder_date}",
            "reminder_date": reminder_date
        }
    except Exception as e:
        logger.error(f"Schedule reminder error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reminders/{session_id}")
async def get_reminders(session_id: str):
    """Get all reminders for a user."""
    try:
        reminders_collection = sync_users_collection.database["reminders"]
        reminders = list(reminders_collection.find({"session_id": session_id}, {"_id": 0}))
        return {"reminders": reminders}
    except Exception as e:
        logger.error(f"Get reminders error: {e}")
        return {"reminders": []}

# Admin Dashboard Endpoints
@app.get("/admin/users")
def list_users(limit: int = 100, admin_key: str = Depends(verify_admin_key)):
    """Get all users for admin dashboard."""
    try:
        users = list(sync_users_collection.find({}, {"_id": 0}))
        return {"users": users, "count": len(users)}
    except Exception as e:
        logger.error(f"Get users error: {e}")
        return {"users": [], "count": 0}

@app.get("/admin/conversations")
def list_conversations(limit: int = 100, admin_key: str = Depends(verify_admin_key)):
    """Get all conversations for admin dashboard."""
    try:
        conversations = list(sync_conversations_collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))
        return {"conversations": conversations, "count": len(conversations)}
    except Exception as e:
        logger.error(f"Get conversations error: {e}")
        return {"conversations": [], "count": 0}

@app.get("/admin/analytics")
def get_analytics(admin_key: str = Depends(verify_admin_key)):
    """Get analytics data for admin dashboard."""
    try:
        # User statistics
        total_users = sync_users_collection.estimated_document_count()
        completed_onboarding = sync_users_collection.count_documents({"onboarding_step": "complete"})
        
        # Conversation statistics
        total_conversations = sync_conversations_collection.estimated_document_count()
        
        # Scheme statistics
        db = sync_mongo_client["welfarebot"]
        
        verified_query = {"verified": True}
        unverified_query = {"$or": [{"verified": False}, {"verified": {"$exists": False}}]}
        
        verified_count = (
            sync_schemes_collection.count_documents(verified_query) +
            db["raw_schemes"].count_documents(verified_query) +
            db["new_schemes"].count_documents(verified_query)
        )
        
        unverified_count = (
            sync_schemes_collection.count_documents(unverified_query) +
            db["raw_schemes"].count_documents(unverified_query) +
            db["new_schemes"].count_documents(unverified_query)
        )
        
        deleted_count = db["deleted_schemes"].count_documents({})
        total_schemes = verified_count + unverified_count
        
        # Recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_users = sync_users_collection.count_documents({"created_at": {"$gte": yesterday}})
        recent_conversations = sync_conversations_collection.count_documents({"timestamp": {"$gte": yesterday}})
        
        return {
            "users": {
                "total": total_users,
                "completed_onboarding": completed_onboarding,
                "recent": recent_users
            },
            "conversations": {
                "total": total_conversations,
                "recent": recent_conversations
            },
            "schemes": {
                "total": total_schemes,
                "verified": verified_count,
                "unverified": unverified_count,
                "deleted": deleted_count
            }
        }
    except Exception as e:
        logger.error(f"Get analytics error: {e}")
        return {"error": str(e)}

@app.delete("/admin/users/legacy")
async def delete_legacy_users(admin_key: str = Depends(verify_admin_key)):
    """Delete all users who do not have a phone_number (legacy)."""
    try:
        query = {"$or": [{"phone_number": {"$exists": False}}, {"phone_number": None}, {"phone_number": ""}]}
        legacy_users = list(sync_users_collection.find(query))
        if legacy_users:
            sync_deleted_users_collection.insert_many(legacy_users)
            sync_users_collection.delete_many(query)
        return {"status": "success", "deleted_count": len(legacy_users)}
    except Exception as e:
        logger.error(f"Delete legacy users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/admin/users/{session_id}/pin")
async def change_user_pin(session_id: str, payload: dict, admin_key: str = Depends(verify_admin_key)):
    """Change a user's PIN."""
    try:
        new_pin = payload.get("pin")
        if not new_pin:
            raise HTTPException(status_code=400, detail="PIN is required")
        
        result = sync_users_collection.update_one(
            {"session_id": session_id},
            {"$set": {"pin": new_pin}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
            
        return {"status": "success", "message": "PIN updated successfully"}
    except Exception as e:
        logger.error(f"Update user pin error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/users/{session_id}")
async def delete_user(session_id: str, admin_key: str = Depends(verify_admin_key)):
    """Delete a user (soft delete, moves to deleted_users)."""
    try:
        user_doc = sync_users_collection.find_one({"session_id": session_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
            
        sync_deleted_users_collection.insert_one(user_doc)
        sync_users_collection.delete_one({"session_id": session_id})
        return {"status": "success", "message": "User moved to deleted"}
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/deleted_users")
async def get_deleted_users(admin_key: str = Depends(verify_admin_key)):
    """Get all deleted users."""
    try:
        users = list(sync_deleted_users_collection.find({}, {"_id": 0}))
        return users
    except Exception as e:
        logger.error(f"Get deleted users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/deleted_users/{session_id}/restore")
async def restore_deleted_user(session_id: str, admin_key: str = Depends(verify_admin_key)):
    """Restore a deleted user."""
    try:
        user_doc = sync_deleted_users_collection.find_one({"session_id": session_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="Deleted user not found")
        
        user_doc.pop("_id", None)
        sync_users_collection.insert_one(user_doc)
        sync_deleted_users_collection.delete_one({"session_id": session_id})
        return {"status": "success", "message": "User restored"}
    except Exception as e:
        logger.error(f"Restore user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/deleted_users/{session_id}/hard")
async def hard_delete_user(session_id: str, admin_key: str = Depends(verify_admin_key)):
    """Permanently delete a user."""
    try:
        result = sync_deleted_users_collection.delete_one({"session_id": session_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Deleted user not found")
        return {"status": "success", "message": "User permanently deleted"}
    except Exception as e:
        logger.error(f"Hard delete user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/admin/schemes")
async def add_scheme(scheme: dict, admin_key: str = Depends(verify_admin_key)):
    """Add a new scheme (admin only)."""
    try:
        sync_schemes_collection.insert_one(scheme)
        return {"status": "success", "message": "Scheme added"}
    except Exception as e:
        logger.error(f"Add scheme error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/schemes/{scheme_id}")
async def delete_scheme(scheme_id: str, admin_key: str = Depends(verify_admin_key)):
    """Delete a scheme (admin only)."""
    try:
        result = sync_schemes_collection.delete_one({"_id": scheme_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Scheme not found")
        return {"status": "success", "message": "Scheme deleted"}
    except Exception as e:
        logger.error(f"Delete scheme error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "running", "db": "connected"}


@app.get("/schemes")
async def get_schemes():
    schemes = list(sync_schemes_collection.find({}, {"_id": 0}))
    return {"schemes": schemes}


# Serve React frontend (SPA)
# Mount static files - only if build exists
import os.path
frontend_build_exists = os.path.exists("frontend/build")
if frontend_build_exists:
    try:
        app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")
        if os.path.exists("frontend/build/favicon.ico"):
            app.mount("/favicon.ico", StaticFiles(directory="frontend/build"), name="favicon")
        logger.info("Frontend static files mounted successfully")
    except Exception as e:
        logger.warning(f"Could not mount static files: {e}")
else:
    logger.warning("Frontend build directory not found - serving API only")

@app.get("/")
async def serve_react():
    if frontend_build_exists:
        try:
            return FileResponse("frontend/build/index.html")
        except Exception as e:
            logger.warning(f"Could not serve index.html: {e}")
    return {"status": "backend_running", "message": "API endpoints available"}

@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """Catch all routes for React SPA routing"""
    # Don't catch API routes
    if full_path.startswith("chat") or full_path.startswith("voice") or full_path.startswith("send-reminder") or full_path.startswith("schedule-reminder") or full_path.startswith("reminders") or full_path.startswith("health") or full_path.startswith("schemes") or full_path.startswith("session"):
        raise HTTPException(status_code=404, detail="Not found")
    if frontend_build_exists:
        try:
            return FileResponse("frontend/build/index.html")
        except Exception as e:
            logger.warning(f"Could not serve index.html: {e}")
    raise HTTPException(status_code=404, detail="Frontend not built yet")

# Admin UI endpoint
@app.get("/admin")
async def admin_panel():
    if frontend_build_exists:
        return FileResponse("frontend/build/index.html")
    else:
        raise HTTPException(status_code=404, detail="Frontend not built yet")


@app.get("/session")
def get_session(session_id: str):
    user = sync_users_collection.find_one({"session_id": session_id})
    if user and "_id" in user:
        user["_id"] = str(user["_id"])
    return {"session_id": session_id, "profile": user or {}}





@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        session_id = request.session_id
        message = request.message.strip()

        if not message:
            return ChatResponse(reply="Please say something.")

        user_doc = sync_users_collection.find_one({"session_id": session_id}) or {}
        onboarding_step = user_doc.get("onboarding_step", "name")

        history_cursor = sync_conversations_collection.find({"session_id": session_id}).sort("timestamp", -1).limit(4)
        chat_history = list(history_cursor)[::-1]

        state = {
            "session_id": session_id,
            "message": message,
            "history": chat_history,
            "user_profile": user_doc,
            "intent": None,
            "reply": None,
            "show_form_choice": None,
            "clear_session": None,
            "chips": None,
            "apply_link": None,
            "confirmation_step": user_doc.get("confirmation_step"),
            "editing_field": user_doc.get("editing_field"),
        }

        result = welfare_graph.invoke(state)

        reply = result.get("reply", "Sorry, couldn't process that.")
        show_form_choice = result.get("show_form_choice", False)
        show_pin_popup = result.get("show_pin_popup", False)
        pin_mode = result.get("pin_mode", None)
        pin_lockout_until = result.get("pin_lockout_until", None)
        clear_session = result.get("clear_session", False)
        apply_link = result.get("apply_link")
        
        # Load updated user_doc
        updated_user_doc = sync_users_collection.find_one({"session_id": session_id}) or {}
        result_onboarding_step = result.get("onboarding_step") or updated_user_doc.get("onboarding_step", onboarding_step)
        result_intent = result.get("intent")
        result_schemes = result.get("schemes")

        # Determine chips
        chips = result.get("chips")
        if chips is None:
            chips = generate_chips(result_onboarding_step, updated_user_doc, result_intent, result_schemes, message)
        
        # Ensure Start Over is strictly the last chip
        cleaned_chips = []
        if chips:
            cleaned_chips = [c for c in chips if c != "Start Over"]
        cleaned_chips.append("Start Over")

        sync_conversations_collection.insert_one({
            "session_id": session_id,
            "user_message": message,
            "bot_reply": reply,
            "intent": result_intent,
            "chips": cleaned_chips,
            "apply_link": apply_link or "",
            "show_apply_button": result.get("show_apply_button", False),
            "confidence_score": result.get("confidence_score"),
            "timestamp": datetime.utcnow()
        })

        return ChatResponse(
            reply=reply,
            show_form_choice=show_form_choice,
            show_pin_popup=show_pin_popup,
            pin_mode=pin_mode,
            pin_lockout_until=pin_lockout_until,
            clear_session=clear_session,
            chips=cleaned_chips,
            apply_link=apply_link,
            show_apply_button=result.get("show_apply_button", False),
            confidence_score=result.get("confidence_score")
        )
    except Exception as e:
        logging.error(f"Chat endpoint error: {e}")
        return ChatResponse(reply=f"Error: {str(e)}")


from fastapi.responses import JSONResponse

@app.get("/conversation/{session_id}")
def get_conversation_history(session_id: str):
    """Fetch the full conversation history for a given session and return JSON."""
    try:
        cursor = sync_conversations_collection.find({"session_id": session_id}).sort("timestamp", 1).limit(100)
        convs = list(cursor)
        
        formatted_messages = []
        for c in convs:
            user_time = c.get("timestamp")
            bot_time = user_time
            if isinstance(user_time, datetime):
                user_time = user_time.isoformat()
                bot_time = (c.get("timestamp") + timedelta(seconds=1)).isoformat()
            formatted_messages.append({
                "id": f"u_{c.get('_id') or user_time}",
                "role": "user",
                "text": c.get("user_message", ""),
                "timestamp": user_time,
            })
            formatted_messages.append({
                "id": f"b_{c.get('_id') or bot_time}",
                "role": "bot",
                "text": c.get("bot_reply", ""),
                "chips": c.get("chips", []),
                "apply_link": c.get("apply_link", ""),
                "confidence_score": c.get("confidence_score"),
                "timestamp": bot_time,
            })
        return JSONResponse(content={"session_id": session_id, "messages": formatted_messages})
    except Exception as e:
        logger.error(f"Error fetching conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Startup diagnostics
print("\n" + "=" * 50)
print("WELFAREBOT BACKEND READY (Groq-only)")
print("=" * 50)
print(f"[OK] Groq client: {groq_client}")
print(f"[OK] MongoDB connected: {sync_mongo_client}")
print(f"[OK] Users collection: {sync_users_collection}")
print(f"[OK] Schemes collection: {sync_schemes_collection}")
print(f"[OK] LangGraph: {welfare_graph}")

print("=" * 50 + "\n")

# -------------------- API ENDPOINTS --------------------

# Existing staging endpoint
@app.get("/staging")
async def get_staging():
    client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGODB_URI"))
    db = client.get_default_database()
    cursor = db.staging.find({"status": "pending"}).sort("scraped_at", -1).limit(100)
    return await cursor.to_list(length=100)





# Endpoint to manually trigger scraper
@app.post("/scraper/run")
async def trigger_scraper():
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, run_scraper)
    return {"status": "scraper started", "message": "Check /staging in 1-2 minutes"}