# AI Powered HCP Customer Relationship Management System

An AI-controlled HCP interaction logging system. The app helps field representatives convert natural conversation into a structured CRM record using a FastAPI backend, LangGraph tool workflow, and Groq LLM planning.

The main requirement that I fulfilled: the user does not directly fill the final CRM form. The left panel is treated as an AI-managed interaction record, while the right panel assistant logs, edits, validates, and saves the interaction through LangGraph tools.

**For this Assessment I would also like to mention the improvements I made along with implementing the required features.**

- I have noticed that the model that is required such as the <gemma2-9b-it> model has been deprecated from Groq models
and <llama-3.3-70b-versatile> model is soon to be deprecated in August. So from my previous experience in Inferencing Cloud open source AI models and Running local AI models. I have decided to Add a Developer Settings Section to Select available models via groq. We can see live status by pinging Groq server and also select one of the available models for this demo **(I only added this since this is a demo and wanted to make sure smoother working of the Application)**

**I also plan to integrate a voice mode to hook it up with Whisper Large V3 Turbo for Better user experience by enabling Voiced natural language commands for auto filling the forms. (Update: Implemented the feature, more info below)**

**Update - July 14: The planned voice mode is now implemented.**

Following the mail regarding the opportunity to revisit to make more satisfactory version till July 15th 5:00PM IST. I have made these updates

- Added voice input using Groq Whisper Large V3 Turbo, with transcript review before AI logging.
- Added live date and time handling for `today`, `now`, and explicitly requested timezones.
- Added `get_current_datetime`, bringing the project to nine registered LangGraph tools.
- Added compact chips that clearly show the tools used for each assistant response.
- Updated the default display to `DD/MM/YYYY` with 12-hour time.
- Expanded automated verification to 23 passing backend tests.

![Verified AI-controlled interaction saved to MySQL](docs/ui-ai-mysql-saved.png)

## Quick Start

### 1. Clone and open the project

```powershell
git clone https://github.com/Mai-Xio/AI-Powered-HCP-Customer-Relationship-Management-System.git
cd AI-Powered-HCP-Customer-Relationship-Management-System
```

### 2. Start MySQL

Choose either option. Docker is convenient for reviewers, while native MySQL works without Docker or virtualization.

#### Option A - Docker

```powershell
docker compose -f docker-compose.mysql.yml up -d
```

#### Option B - Native MySQL 8.4 on Windows

Install MySQL Community Server 8.4, configure it as an auto-starting Windows service on port `3306`, and run the following statements from the MySQL client:

```sql
CREATE DATABASE IF NOT EXISTS aivoa_crm
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS 'aivoa_user'@'localhost'
  IDENTIFIED BY 'aivoa_password';
CREATE USER IF NOT EXISTS 'aivoa_user'@'127.0.0.1'
  IDENTIFIED BY 'aivoa_password';
GRANT ALL PRIVILEGES ON aivoa_crm.* TO 'aivoa_user'@'localhost';
GRANT ALL PRIVILEGES ON aivoa_crm.* TO 'aivoa_user'@'127.0.0.1';
FLUSH PRIVILEGES;
```

The app creates the required tables and seeds the HCP profiles when the backend starts.

### 3. Create `.env` in the project root

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

Do not commit real API keys.

### 4. Install and run the backend

```powershell
python -m venv .venv-aivoa
.\.venv-aivoa\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. Install and run the frontend

Open a second terminal from the project root:

```powershell
cd frontend
npm ci
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

Batch flow:

```text
Up to three natural-language interaction logs
  -> FastAPI /api/agent/batch
  -> the same LangGraph planner and tools run once per record
  -> React review sheet
  -> one atomic MySQL transaction through /api/interactions/batch
```

## Key Features

- AI-controlled split-screen HCP logging interface
- Read-only final CRM form
- Chat-based interaction logging
- Structured assisted logging mode
- Surgical field correction through the Edit Interaction tool
- Timezone, date-format, and 12h/24h time-format controls
- Live timezone and formatting indicators beside Interaction Details
- UTC timestamp storage with display preferences
- AI validation and compliance guardrail checks
- Three-record batch processing with a review sheet and atomic Save All
- Save AI Draft to SQL database
- Export current AI-filled draft as CSV
- Responsive layout for desktop and mobile screens
- Google Inter font for assessment compliance

![Live timezone, date format, and time format indicators](docs/ui-format-strip.png)

![Timezone, date format, time format, and utility settings](docs/ui-settings.png)

![Batch interaction review sheet before atomic MySQL save](docs/ui-batch.png)

## How MySQL Is Used

```mermaid
flowchart LR
    A[AI-filled React draft] --> B[POST /api/interactions]
    B --> C[Pydantic validation]
    C --> D[SQLAlchemy ORM]
    D --> E[(MySQL 8.4 / InnoDB)]
    E --> F[UTC timestamp + display preferences]
```

- `hcp_profiles` stores seeded HCP context used by the profile lookup tool.
- `interactions` stores every saved AI-generated record, including the original timezone, UTC timestamp, preferred date format, and preferred time format.
- The backend health endpoint exposes `database_ready`, so database availability can be checked without guessing.
- The application account is limited to the `aivoa_crm` database instead of using the MySQL root account.

The persistence smoke test starts an isolated backend, saves a complete interaction through the real API, and requires the returned MySQL row to include an interaction ID.

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

MySQL smoke test with Docker:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify-mysql.ps1
```

MySQL smoke test with a native server already listening on port `3306`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify-mysql.ps1 -SkipCompose
```

Expected result:

```json
{
  "mysql": "local-listening",
  "backend": "ok",
  "saved_interaction_id": 1
}
```
