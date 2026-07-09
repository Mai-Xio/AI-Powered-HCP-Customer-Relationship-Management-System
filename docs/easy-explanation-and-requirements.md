# Easy Explanation: AI-First HCP CRM Interaction Logger

Use this document to explain the project in simple words during your video.

## 1. The Main Idea

This is an AI-first CRM screen for logging Healthcare Professional interactions.

There are two panels:

- Left: the final interaction form.
- Right: the AI assistant.

The important rule is:

```text
The user never manually fills the left form.
The user only talks to the AI assistant.
LangGraph tools update the form.
```

So the left side is a read-only display, and the right side is the control surface.

## 2. Simple Example

User types:

```text
Met Dr. Meera Kapoor on 04/19/2025 at 07:36 PM. Discussed Prodo-X efficacy.
Positive sentiment. Shared brochure.
```

The AI fills:

- HCP name
- Date and time
- Interaction type
- Attendees
- Topics/products discussed
- Sentiment
- Materials shared
- Outcomes, if mentioned
- Follow-up actions, only if mentioned
- Summary/notes
- UTC audit timestamp

Follow-up actions are not invented just to look busy. If the user does not mention a real next step, that field stays empty.

## 3. How The System Works

Simple pipeline:

```text
User chat message
  -> React frontend
  -> Redux keeps the current draft
  -> FastAPI backend receives the message
  -> LangGraph runs the workflow
  -> Groq LLM plans which tools should run
  -> Tools update structured CRM fields
  -> FastAPI returns the updated draft
  -> Redux updates the read-only form
```

The form is not a normal editable form. It is the output of the AI workflow.

## 4. What Each Technology Does

**React** builds the split-screen UI.

**Redux Toolkit** stores the current draft, messages, loading state, save state, date/time preferences, and selected model.

**FastAPI** exposes the backend endpoints, mainly:

```text
POST /api/agent/chat
POST /api/interactions
```

**LangGraph** controls the agent workflow:

1. Planner node: ask the Groq LLM what the user wants and which tools should run.
2. Tool executor node: run the selected tools.
3. Responder node: return a useful assistant reply.

**Groq LLM** performs the AI understanding and tool planning.

**SQLAlchemy** saves the final draft to a SQL database. MySQL is the default for the assignment demo; Postgres is supported later by changing `DATABASE_URL`.

## 5. The Tools

The assignment requires at least five tools. This project has eight.

### 1. Log Interaction

Mandatory.

This extracts structured information from a natural-language prompt and fills the draft.

Example fields:

- HCP name
- Date/time
- Topics
- Products
- Sentiment
- Materials
- Outcomes
- Explicit follow-up actions

### 2. Edit Interaction

Mandatory.

This changes only the fields the user asks to change.

Example:

```text
Change sentiment to neutral. Keep everything else the same.
```

Only `sentiment` changes. HCP name, date, topics, materials, and summary are preserved.

### 3. HCP Profile Lookup

Loads profile context such as specialty, segment, territory, and communication preferences.

### 4. Compliance Guardrail

Checks for life-sciences risk terms:

- Off-label discussion
- Adverse event
- Voice note without consent

### 5. Next Best Action

Creates an internal recommendation for the agent. It does not automatically write generic advice into the visible Follow-up Actions field.

This is important because the visible CRM form should only contain defensible data.

### 6. Follow-up Scheduler

Stores a follow-up date only when the user gives one. If the user does not provide a follow-up date, the tool leaves that field empty.

### 7. Validate Interaction

Checks whether the draft has enough information to save. The validation result is kept internal so the main UI stays clean.

### 8. Interaction Summary

Creates a clean CRM-ready summary note from the structured fields.

The summary does not add generic next-step advice unless the user actually gave a follow-up action.

## 6. Save AI Draft

**Save AI Draft** means:

```text
Store the current AI-filled draft in the SQL database.
```

It does not fill the form. The form has already been filled by the AI tools. Save is just persistence.

This is useful because the reviewer can see that the AI-generated structured record can be stored as a real CRM record.

## 7. Export CSV

**Export CSV** downloads the current AI-filled draft as a CSV file.

This is useful for:

- Assignment review
- Manager handoff
- CRM import testing
- Showing that the structured data can leave the UI in a standard format

## 8. Timezone, Date, And Time Format

The app supports:

- Timezone selection
- 12h / 24h time format
- Date format selection

The storage rule is:

```text
Store the actual timestamp in UTC.
Also store timezone and display preferences.
Display the date/time in the selected format.
```

Example:

```text
User says: Met Dr. Rao yesterday at 4:30 PM IST.
Selected timezone: Asia/Kolkata
Time format: 24h
```

The backend resolves the true date and time, stores the UTC timestamp, and displays it using the selected preference.

The user can also say:

```text
Use 24-hour format and change timezone to Asia/Dubai.
```

The Edit Interaction tool updates only the time preference fields and does not overwrite CRM content.

## 9. Database Choice

For the assignment demo, use MySQL:

```powershell
docker compose -f docker-compose.mysql.yml up -d
```

```env
DATABASE_URL=mysql+pymysql://aivoa_user:aivoa_password@localhost:3306/aivoa_crm
```

Why this is good:

- MySQL is explicitly acceptable in the requirement.
- SQLAlchemy models keep the code database-portable.
- Future Postgres migration only needs:

```env
DATABASE_URL=postgresql+psycopg://aivoa_user:your_password@localhost:5432/aivoa_crm
```

The app intentionally uses MySQL/PostgreSQL only, matching the assignment documentation and video.

## 10. UI Explanation

The UI is intentionally minimal.

Removed from the main screen:

- Decorative top tool buttons.
- Non-clickable tool chips.
- Generic AI suggested follow-up links.
- Confidence rating card.

Why:

```text
Anything visible should either be required by the assignment or clearly useful.
```

The only visible utility actions are:

- Save AI Draft: saves to SQL.
- Export CSV: downloads the draft.
- Settings: timezone, date format, time format, structured mode, model status.

## 11. Requirement Coverage

| Requirement | How It Is Covered |
|---|---|
| Split-screen UI | Left read-only form, right AI assistant |
| Form cannot be filled manually | Left form inputs are read-only |
| Chat controls the form | User input goes through the assistant |
| React frontend | Built with React |
| Redux | Stores draft and UI state |
| Python backend | Backend is Python |
| FastAPI | API is FastAPI |
| LangGraph | Agent is a `StateGraph` |
| LLM required | Groq LLM plans tool calls |
| Minimum five tools | Eight tools implemented |
| Log Interaction tool | Implemented |
| Edit Interaction tool | Implemented |
| MySQL/Postgres | SQLAlchemy supports both; MySQL recommended |
| Google Inter font | Loaded in the frontend |
| Timezone and formats | Settings plus chat-edit support |
| UTC storage | `interaction_datetime_utc` is stored |
| Responsive layout | CSS uses responsive grids and breakpoints |

## 12. Short Video Script

You can say:

```text
This project is an AI-first HCP CRM interaction logger.
The left form is read-only. The field representative cannot manually fill it.
They describe the visit in the AI assistant, and a LangGraph agent uses a Groq LLM
to plan and run tools that populate the structured CRM draft.
```

For the tools:

```text
The two mandatory tools are Log Interaction and Edit Interaction.
I also added HCP Profile Lookup, Compliance Guardrail, Next Best Action,
Follow-up Scheduler, Validate Interaction, and Interaction Summary.
That gives eight LangGraph tools total.
```

For the UI:

```text
I kept the UI minimal. I removed decorative buttons and generic AI suggestions
because I only want visible elements that are required or useful.
Save AI Draft persists to SQL, Export CSV downloads the current draft,
and Settings controls date, time, timezone, and model options.
```

For edits:

```text
The Edit Interaction tool only changes fields I explicitly name.
If I say "change sentiment to neutral", it preserves all other fields.
```

For timezone:

```text
The app stores the real timestamp in UTC, but displays it in the selected timezone,
date format, and time format.
```

## 13. Best Demo Prompts

Prompt 1:

```text
Met Dr. Meera Kapoor on 04/19/2025 at 07:36 PM for a meeting. Attendees were Ravi and Neha. Discussed Prodo-X efficacy and patient adherence. Positive sentiment. Shared brochure and safety card. Outcomes were strong interest in adherence data. Follow-up actions: send approved safety data next Friday.
```

Prompt 2:

```text
Met Dr. Noor on June 4th 2026 at 2 PM. Discussed anemia. Negative sentiment. Shared a prescription.
```

Explain that Prompt 2 should not create generic visible follow-up actions.

Prompt 3:

```text
Change the HCP to Dr. Arjun Menon and sentiment to neutral. Keep everything else the same.
```

Prompt 4:

```text
Use 24-hour format and change timezone to Asia/Dubai.
```

Prompt 5:

```text
Met Dr.Amit kumar at 14:00 on 1st jan 2025 and discussed PhotonX, Posotive sentiment, dshared brochure
```
