# Video Walkthrough Script

Use this as a natural guide for a 10 to 15 minute submission video.

## Before Recording

Start the backend and frontend:

```powershell
cd C:\Users\Devi\Documents\Jobs\backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
cd C:\Users\Devi\Documents\Jobs\frontend
npm run dev
```

Open <http://127.0.0.1:5173>.

Open Settings once and check:

- Timezone/date/time format controls are visible.
- Developer Settings can show model status.
- The UI is clean: no fake top buttons, no decorative chips, no generic suggested follow-up section.

## 1. Introduction

Say:

```text
Hi, I am [your name], and this is my submission for the Full Stack Developer AI Applications role.
I built an AI-first HCP CRM interaction logger.

The main rule from the assignment is that the user should not manually fill the form.
So the left panel is read-only, and the right panel is the AI assistant.
Every update to the form goes through a LangGraph workflow and Groq LLM tool calls.
```

## 2. First Log Demo

Paste:

```text
Met Dr. Meera Kapoor on 04/19/2025 at 7:36 PM for a meeting. Attendees were Ravi and Neha. Discussed Prodo-X efficacy and patient adherence. Positive sentiment. Shared brochure and safety card. Outcomes were strong interest in adherence data. Follow-up actions: send approved safety data next Friday.
```

After it fills, say:

```text
The form populated itself. I did not click or type into any field on the left.
The AI extracted HCP name, date, time, attendees, topics, sentiment, materials, outcomes, and the explicit follow-up action.

Because I gave a real follow-up action in the prompt, the Follow-up Actions field is filled.
If I do not provide one, the app does not invent generic next steps.
```

## 3. Show No Generic Follow-Up Filler

Paste:

```text
Met Dr. Noor on June 4th 2026 at 2 PM. Discussed anemia. Negative sentiment. Shared a prescription.
```

Say:

```text
This prompt has no real next step.
The backend still runs its internal Next Best Action tool for the LangGraph workflow,
but the visible Follow-up Actions field stays empty because the user did not provide a defensible action.
That keeps the CRM record honest.
```

## 4. Edit Tool Demo

Paste:

```text
Change the HCP to Dr. Arjun Menon and sentiment to neutral. Keep everything else the same.
```

Say:

```text
This demonstrates the second mandatory tool, Edit Interaction.
Only the HCP and sentiment changed.
The date, time, topics, materials, and other fields were preserved.
This is important because corrections also have to happen through the assistant, not by manually editing the form.
```

## 5. Date, Time, And Timezone Demo

Paste:

```text
Use 24-hour format and change timezone to Asia/Dubai.
```

Say:

```text
The display preference changed through the AI assistant.
The app stores the actual interaction timestamp in UTC, while also storing the timezone and display preferences.
That makes it useful for regional field teams and audit-safe CRM logging.
```

You can also open Settings and show:

- Timezone dropdown
- Date format dropdown
- 12h / 24h toggle

## 6. Save And CSV Export

Click **Save AI Draft**.

Say:

```text
Save AI Draft persists the current AI-filled draft to the SQL database.
It is not manual form filling; it is the storage step after the AI tools produce the structured record.
```

Click **Export CSV**.

Say:

```text
Export CSV downloads the current AI-filled draft as a standard CSV file.
That is useful for review, handoff, or import testing.
```

## 7. Code Walkthrough

Open `backend/app/agent/graph.py`.

Say:

```text
This is the LangGraph agent.
It has a planner node, a tool executor node, and a responder node.
The planner calls the Groq LLM and asks for a strict JSON tool plan.
The executor runs the selected structured tools and updates the draft.
```

Open `backend/app/agent/tools.py`.

Say:

```text
These are the tools.
The assignment required at least five tools, including Log Interaction and Edit Interaction.
I implemented eight: Log Interaction, Edit Interaction, HCP Profile Lookup,
Compliance Guardrail, Next Best Action, Follow-up Scheduler, Validate Interaction, and Interaction Summary.
```

Open `frontend/src/components/InteractionForm.jsx`.

Say:

```text
This is the read-only form.
The user cannot type here. It only displays the Redux draft returned by the backend.
```

Open `frontend/src/components/AssistantPanel.jsx`.

Say:

```text
This is the assistant panel.
It sends the user message to the FastAPI backend, supports settings,
saves the draft to SQL, and exports the current draft to CSV.
```

## 8. Database Explanation

Say:

```text
For the final demo I use MySQL because the assignment allows MySQL or Postgres.
The app uses SQLAlchemy, so the same models also support Postgres later by changing DATABASE_URL.
There is no SQLite fallback in the runtime path, so the database story matches the assignment docs.
```

Show the `.env` shape without exposing real keys:

```env
DATABASE_URL=mysql+pymysql://aivoa_user:aivoa_password@localhost:3306/aivoa_crm
AIVOA_USE_LIVE_LLM=true
GROQ_MODEL=openai/gpt-oss-120b
GROQ_FALLBACK_MODEL=openai/gpt-oss-20b
```

## 9. Model Explanation

Say:

```text
The original brief mentioned gemma2 and llama models.
I use one standard GROQ_API_KEY for all Groq model calls,
and I also added a Developer Settings panel because Groq model availability changes.
The current default is a working Groq model, and the status checker helps avoid demo failure.
```

Do not show real API keys.

## 10. Closing

Say:

```text
To summarize, this is not just a form UI.
It is an AI-controlled CRM workflow.
React and Redux handle the interface, FastAPI handles the API,
LangGraph controls the agent, Groq LLM plans the tools,
and the tools produce clean structured CRM data.

The form remains read-only, edits are surgical, date/time storage is audit-friendly,
and the UI stays minimal so every visible element has a clear purpose.
```

## Quick Prompt List

```text
Met Dr. Meera Kapoor on 04/19/2025 at 7:36 PM for a meeting. Attendees were Ravi and Neha. Discussed Prodo-X efficacy and patient adherence. Positive sentiment. Shared brochure and safety card. Outcomes were strong interest in adherence data. Follow-up actions: send approved safety data next Friday.
```

```text
Met Dr. Noor on June 4th 2026 at 2 PM. Discussed anemia. Negative sentiment. Shared a prescription.
```

```text
Change the HCP to Dr. Arjun Menon and sentiment to neutral. Keep everything else the same.
```

```text
Use 24-hour format and change timezone to Asia/Dubai.
```

```text
Met Dr.Amit kumar at 14:00 on 1st jan 2025 and discussed PhotonX, Posotive sentiment, dshared brochure
```
