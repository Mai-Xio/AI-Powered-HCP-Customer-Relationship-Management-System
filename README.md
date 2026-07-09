# AI Powered HCP Customer Relationship Management System

An AI-controlled HCP interaction logging system built for the AIVOA Full Stack Developer AI Applications assessment. The app helps field representatives convert natural conversation into a structured CRM record using a FastAPI backend, LangGraph tool workflow, and Groq LLM planning.

The main rule is simple: the user does not directly fill the final CRM form. The left panel is treated as an AI-managed interaction record, while the right panel assistant logs, edits, validates, and saves the interaction through LangGraph tools.

**For this Assessment I would also like to mention the improvements I made along with implementing the required features.**

- I have noticed that the model that is required such as the <gemma2-9b-it model> has been deprecated from Groq models
and <llama-3.3-70b-versatile> is soon to be deprecated in August. So from my previous experience in Inferencing Cloud open source AI models and Running local AI models. I have decided to Add a Developer Settings Section to Select available models via groq. We can see live status by pinging Groq server and also select one of the available models for this demo (I only added this since this is a demo and wanted to make sure smoother working of the Application)

**I also plan to integrate a voice mode to hook it up with Whisper Large V3 Turbo for Better user experience by enabling Voiced natural language commands for auto filling the forms.**

![Split-screen UI](docs/ui-verified.png)

## Quick Start

### 1. Clone and open the project

```powershell
git clone https://github.com/Mai-Xio/AI-Powered-HCP-Customer-Relationship-Management-System.git
cd AI-Powered-HCP-Customer-Relationship-Management-System
```

### 2. Start MySQL

```powershell
docker compose -f docker-compose.mysql.yml up -d
```

### 3. Create `.env` in the project root

```env
GROQ_API_KEY=your_groq_api_key
AIVOA_USE_LIVE_LLM=true
AIVOA_COMPOSE_WITH_LLM=false
AIVOA_GROQ_CALLS_PER_MINUTE=6
GROQ_MODEL=openai/gpt-oss-120b
GROQ_FALLBACK_MODEL=openai/gpt-oss-20b
DATABASE_URL=mysql+pymysql://aivoa_user:aivoa_password@localhost:3306/aivoa_crm
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
```

Do not commit real API keys.

### 4. Install and run the backend

```powershell
python -m venv .venv-aivoa
.\.venv-aivoa\Scripts\Activate.ps1
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. Install and run the frontend

Open a second terminal from the project root:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open the app:

```text
http://127.0.0.1:5173
```

## What the App Does

The application provides a split-screen AI-first CRM experience:

- Left side: read-only HCP interaction record.
- Right side: AI assistant for logging and editing interaction details.
- LangGraph: routes the request, selects tools, and updates the structured draft.
- Groq LLM: creates the tool plan from natural language.
- SQL database: stores AI-generated drafts and saved interactions.

Core flow:

```text
User message
  -> React assistant panel
  -> Redux action
  -> FastAPI /api/agent/chat
  -> LangGraph planner node
  -> Groq LLM creates a strict JSON tool plan
  -> LangGraph tool executor node
  -> CRM tools update the interaction draft
  -> LangGraph responder node
  -> Redux refreshes the read-only form
```

## Key Features

- AI-controlled split-screen HCP logging interface
- Read-only final CRM form
- Chat-based interaction logging
- Structured assisted logging mode
- Surgical field correction through the Edit Interaction tool
- Timezone, date-format, and 12h/24h time-format controls
- UTC timestamp storage with display preferences
- AI validation and compliance guardrail checks
- Save AI Draft to SQL database
- Export current AI-filled draft as CSV
- Responsive layout for desktop and mobile screens
- Google Inter font for assessment compliance

## Verification

Backend tests:

```powershell
cd backend
pytest
```

Frontend build:

```powershell
cd frontend
npm run build
```

MySQL smoke test after setting up Docker Desktop:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify-mysql.ps1
```
