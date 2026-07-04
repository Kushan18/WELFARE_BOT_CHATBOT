# WelfareBot

Full-stack WelfareBot application with React frontend and FastAPI backend.

## Project Structure

```
welfare_2-backend/
├── frontend/          # React frontend
├── agent/            # LangGraph agent logic
├── scraper/          # Scheme scraping modules
├── rag/              # RAG retrieval modules
├── main.py           # FastAPI backend
└── requirements.txt  # Python dependencies
```

## Quick Start

```bash
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\Activate  # Windows
# or: source venv/bin/activate  # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browsers
playwright install chromium

# 4. Set up environment variables
copy .env.example .env
# Edit .env with your actual keys

# 5. Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

## Setup Instructions

1. Create virtual environment:
```bash
python -m venv venv
```

2. Activate virtual environment:
- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- Windows (CMD): `.venv\Scripts\activate.bat`
- macOS/Linux: `source venv/bin/activate`

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers (for myscheme scraping):
```bash
playwright install chromium
```

5. Set up environment variables:
```bash
copy .env.example .env
# Edit .env with your actual keys:
# GROQ_API_KEY=YOUR_GROQ_KEY
# MONGODB_URI=YOUR_MONGODB_CONNECTION_STRING
# ADMIN_API_KEY=admin-secret-key-123
```

6. Run development server:
```bash
uvicorn main:app --reload
```

The API will be available at http://127.0.0.1:8000.

## API Endpoints

### Core Endpoints
- `GET /health` - Health check
- `POST /chat` - Chat endpoint with session management
- `GET /schemes` - Get all schemes

### Voice Input
- `POST /voice-input` - Upload audio for transcription (requires STT integration)

### Email Reminders
- `POST /send-reminder` - Send immediate reminder
- `POST /schedule-reminder` - Schedule reminder for specific date
- `GET /reminders/{session_id}` - Get user's reminders

### Admin Dashboard (Requires API Key)
All admin endpoints require `X-Admin-API-Key` header with the value from `ADMIN_API_KEY` environment variable.

- `GET /admin/users` - Get all users
- `GET /admin/conversations` - Get all conversations
- `GET /admin/analytics` - Get analytics data
- `DELETE /admin/users/{session_id}` - Delete user
- `PUT /admin/schemes` - Add new scheme
- `DELETE /admin/schemes/{scheme_id}` - Delete scheme

Example admin request:
```bash
curl -X GET "http://127.0.0.1:8000/admin/users" -H "X-Admin-API-Key: admin-secret-key-123"
```

## Features

- **Onboarding Flow**: Name extraction, language preference, profile collection (including email), confirmation
- **Scheme Matching**: Eligibility-based scheme recommendations
- **Confidence Scoring**: Query confidence evaluation
- **Session Persistence**: MongoDB-based session management
- **Conversation History**: Full chat history storage
- **Automated Scraping**: APScheduler runs scraper every 3 days
- **Multi-language Support**: English, Hindi, Telugu, Tamil, Kannada
- **Admin Authentication**: API key-based authentication for admin endpoints

## Scraping

The scraper runs automatically every 3 days via APScheduler. To manually trigger scraping:
```bash
python -m scraper.seed
```

To force refresh (clear new_schemes first):
```bash
python -m scraper.seed --force
```

## Database Collections

- `users` - User profiles and session data (includes email)
- `schemes` - Live, verified welfare schemes
- `new_schemes` - Scraped schemes pending admin verification
- `raw_schemes` - Raw unprocessed scrape data
- `conversations` - Chat history
- `reminders` - Scheduled reminders

## Deployment on Render

This project is configured to run as a **single unified service** on Render (hosting both the React frontend SPA and the FastAPI python backend together).

### Step-by-Step Render Setup

1. **Create a New Web Service**:
   - Log in to your [Render Dashboard](https://dashboard.render.com).
   - Click **New +** and select **Web Service**.
   - Connect your GitHub repository (`WELFARE_BOT_F10`).

2. **Configure Environment Variables**:
   Under the **Environment** tab, add the following variables:
   - `GROQ_API_KEY`: Your official Groq API key.
   - `MONGODB_URI`: Your MongoDB Connection String.
   - `ADMIN_API_KEY`: The secret key used to access the Admin Control Panel (e.g. `admin-secret-key-123`).
   - `PYTHON_VERSION`: `3.10.0` (or your preferred Python version).

3. **Define Build & Run Commands**:
   - **Build Command**:
     ```bash
     cd frontend && npm install && npm run build && cd .. && pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     uvicorn main:app --host 0.0.0.0 --port $PORT
     ```

4. **Verify Container Optimization (Cold Starts)**:
   - **Instant Boot (under 1.5 seconds)**: ChromaDB and Sentence-Transformers are fully lazy-loaded. When Render boots up your container, the app starts instantly and passes Render's HTTP startup health check before loading large AI weights.
   - **Request Timeout Protection**: The frontend chat client uses a 120-second Axios request timeout (instead of the standard 30s) to comfortably wait for Render's free tier containers to wake up from a cold-start sleep.

5. **Playwright/Scraper Note**:
   - Playwright requires browser binaries to run. If you intend to run the automatic web scraper on Render, add `playwright install chromium` to your Build Command:
     ```bash
     cd frontend && npm install && npm run build && cd .. && pip install -r requirements.txt && playwright install chromium
     ```
   - *Note: Playwright might require additional system libraries on standard Linux VMs. If browser installation fails, you can run without the background scraper by omitting the playwright install command.*
