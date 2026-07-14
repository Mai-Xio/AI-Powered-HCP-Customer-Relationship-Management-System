# AI-Powered HCP Customer Relationship Management System

Assessment submission for the AIVOA Full Stack Developer - AI Applications role.

This project converts a representative's natural-language or voice description into a structured HCP interaction record. The form is intentionally read-only: every change is made by the AI assistant through a Groq LLM planner, LangGraph, and registered CRM tools.

![AI-controlled HCP interaction interface](docs/ui-verified.png)

## Assessment Requirement

The application uses a split-screen interface:

- **Left:** read-only HCP interaction record.
- **Right:** AI assistant for logging and editing through chat or voice.
- **Control rule:** the user never manually fills the final form.
- **AI orchestration:** Groq LLM planning and LangGraph tool execution.
- **Persistence:** MySQL or PostgreSQL through SQLAlchemy.

The assessment requires at least five LangGraph tools, including `log_interaction` and `edit_interaction`. This implementation provides nine registered tools.

## Implemented LangGraph Tools

| Tool | Purpose |
| --- | --- |
| `log_interaction` | Mandatory tool that fills a new interaction from natural language |
| `edit_interaction` | Mandatory tool that changes only explicitly requested fields |
| `lookup_hcp_profile` | Retrieves HCP specialty, segment, territory, and preferences |
| `compliance_guardrail` | Checks for adverse-event, off-label, and consent risks |
| `recommend_next_best_action` | Produces internal next-action guidance from interaction context |
| `schedule_follow_up` | Preserves or stores an explicitly requested follow-up date |
| `validate_interaction` | Checks required CRM fields and completion status |
| `interaction_summary` | Creates a concise CRM-ready summary |
| `get_current_datetime` | Fetches live date/time in the selected or requested timezone |

## Key Features

- AI-controlled, read-only CRM form
- Natural-language logging and surgical field editing
- Voice transcription with Groq `whisper-large-v3-turbo`
- Transcript review before the LangGraph workflow runs
- Live handling of `today`, `yesterday`, `tomorrow`, and `now`
- Explicit timezone recognition, including city and timezone requests
- Default `DD/MM/YYYY` date format and 12-hour time format
- User-selectable timezone, date format, and 12h/24h time format
- UTC timestamp storage with original timezone and display preferences
- Compliance, validation, HCP lookup, summary, and follow-up tools
- Compact per-message chips showing the LangGraph tools that actually ran
- MySQL/PostgreSQL persistence and CSV export
- Responsive desktop, tablet, and mobile layout
- Google Inter font

## How It Works

```text
Typed message or recorded voice note
  -> Groq Whisper transcription (voice only)
  -> Editable assistant composer
  -> FastAPI /api/agent/chat
  -> Groq LLM creates a structured tool plan
  -> LangGraph executes registered CRM tools
  -> Normalization resolves names, dates, times, and timezones
  -> React updates the read-only form
  -> User saves the AI draft to MySQL/PostgreSQL
```

Whisper performs speech-to-text only. It does not fill the form directly. The reviewed transcript follows the same LLM and LangGraph workflow as typed input.

## Technology Stack

### Frontend

- React 19
- Redux Toolkit
- Vite
- Lucide React icons
- Responsive CSS and Google Inter

### Backend

- Python 3.12
- FastAPI
- LangGraph 1.2.9
- LangChain Groq
- Pydantic
- SQLAlchemy
- MySQL with PyMySQL or PostgreSQL with Psycopg

### AI

- Groq-hosted planner model with a configurable fallback
- Groq Whisper Large V3 Turbo for multilingual speech-to-text
- Strict structured tool-plan output
- Local request budgets to protect Groq free-tier limits

## Quick Start

### 1. Clone the repository

```powershell
git clone https://github.com/Mai-Xio/AI-Powered-HCP-Customer-Relationship-Management-System.git
cd AI-Powered-HCP-Customer-Relationship-Management-System
```

### 2. Create the environment file

Create `.env` in the project root:

```env
GROQ_API_KEY=your_groq_api_key
AIVOA_USE_LIVE_LLM=true
AIVOA_COMPOSE_WITH_LLM=false
AIVOA_GROQ_CALLS_PER_MINUTE=6
AIVOA_VOICE_CALLS_PER_MINUTE=4
GROQ_MODEL=openai/gpt-oss-120b
GROQ_FALLBACK_MODEL=openai/gpt-oss-20b
GROQ_TRANSCRIPTION_MODEL=whisper-large-v3-turbo
DATABASE_URL=mysql+pymysql://aivoa_user:aivoa_password@localhost:3306/aivoa_crm
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
```

Never commit real API keys. `.env` is excluded by `.gitignore`.

### 3. Start MySQL

Start Docker Desktop, then run:

```powershell
docker compose -f docker-compose.mysql.yml up -d
```

### 4. Create the Python virtual environment

```powershell
python -m venv .venv-aivoa
.\.venv-aivoa\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```

### 5. Start the backend

```powershell
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend health check: `http://127.0.0.1:8000/health`

### 6. Start the frontend

Open a second PowerShell terminal in the project root:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Demo Prompts

### Log a new interaction

```text
Met Dr. Meera Kapoor today at 4:30 PM. We discussed Prodo-X efficacy and patient adherence. Sentiment was positive and I shared a brochure.
```

### Edit only selected fields

```text
Change the sentiment to neutral and the time to 5 PM. Keep everything else the same.
```

### Use a named timezone and live time

```text
Met Dr. Rao today at the current time in Dubai. Discussed CardioPlus efficacy, positive sentiment, and shared a brochure.
```

### Fetch live date and time

```text
What is today's date and current time in London?
```

### Change display preferences through AI

```text
Use 24-hour time, show dates as YYYY-MM-DD, and change the timezone to Asia/Singapore.
```

## Voice Input

1. Select **Voice** in the assistant composer.
2. Allow microphone access.
3. Describe the HCP interaction.
4. Select stop.
5. Review or correct the transcript.
6. Select **AI Log** to run the LangGraph workflow.

Browser recordings are limited to two minutes and backend uploads to 20 MB. Audio is sent to Groq for transcription and is not stored by this application.

## Verification

Backend test suite:

```powershell
cd backend
..\.venv-aivoa\Scripts\python.exe -m pytest
```

Expected result: `20 passed`.

Frontend production build:

```powershell
cd frontend
npm run build
```

MySQL smoke test:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify-mysql.ps1
```

## Requirement Coverage

| Requirement | Implementation |
| --- | --- |
| Split-screen form and assistant | Responsive React form panel and assistant panel |
| Form cannot be filled manually | All final form controls are read-only |
| LangGraph required | Planner, tool-executor, and responder graph nodes |
| LLM required | Groq LLM generates structured tool plans |
| Mandatory log tool | Registered `log_interaction` tool |
| Mandatory edit tool | Registered `edit_interaction` with field-level patching |
| Minimum five tools | Nine registered and test-covered tools |
| SQL database | MySQL/PostgreSQL through SQLAlchemy |
| Responsive interface | Desktop split view and stacked mobile layout |
| Date/time organization | Live timezone resolution, UTC storage, and display preferences |

## Project Structure

```text
backend/
  app/
    agent/          LangGraph, planner, and registered tools
    main.py         FastAPI routes
    speech.py       Groq Whisper transcription service
    models.py       SQLAlchemy database models
  tests/            Agent, normalization, database, and speech tests
frontend/
  src/
    components/     Read-only form and AI assistant
    features/crm/   Redux state, API client, and CSV export
docs/               UI evidence
scripts/            MySQL verification script
REQUIREMENTS_AND_DEMO.md
```

## Video Guide

See [`REQUIREMENTS_AND_DEMO.md`](REQUIREMENTS_AND_DEMO.md) for the easy explanation, tool-by-tool demonstration, requirement justification, and suggested 10-15 minute video order.
