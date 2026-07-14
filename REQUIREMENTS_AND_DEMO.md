# Assessment Requirements and Demo Guide

## Easy System Explanation

The screen has two connected sides. The user speaks or types in the AI Assistant on the right. The form on the left is read-only, so it cannot be filled manually.

For a typed message, React sends the text to FastAPI. For a voice note, the browser records a short audio file and FastAPI sends it to Groq Whisper Large V3 Turbo. The transcript returns to the message box for review. When the user selects **AI Log**, LangGraph asks the Groq LLM to understand the request and choose the correct tools. Those tools update the structured draft, and React displays the result in the left form.

```text
Voice or typed description
  -> optional Groq Whisper transcription
  -> editable chat message
  -> FastAPI
  -> Groq LLM planner inside LangGraph
  -> CRM tools
  -> structured read-only form
  -> MySQL save
```

Whisper does speech-to-text. It does not fill the form by itself. LangGraph and the planner LLM still control which CRM tools run, which preserves the main assessment requirement.

## Nine Implemented LangGraph Tools

1. `log_interaction` extracts and fills a new interaction. This is mandatory.
2. `edit_interaction` changes only the fields requested and keeps every other value. This is mandatory.
3. `lookup_hcp_profile` finds saved HCP context.
4. `compliance_guardrail` checks the note for life-sciences compliance risks.
5. `recommend_next_best_action` creates internal next-step guidance from the interaction.
6. `schedule_follow_up` stores a follow-up only when the user explicitly provides one.
7. `validate_interaction` checks whether the core CRM fields are complete.
8. `interaction_summary` creates a concise CRM summary.
9. `get_current_datetime` fetches the live date and time in the selected or explicitly requested timezone.

The requirement is a minimum of five tools. This project implements nine real registered tools.

## Voice Demo

1. Select **Voice** and allow microphone access.
2. Say: "Met Dr. Meera Kapoor today at 4:30 PM. We discussed Prodo-X efficacy and patient adherence. Sentiment was positive and I shared a brochure."
3. Select the stop button.
4. Explain that Groq Whisper Large V3 Turbo converts the audio to text.
5. Show that the transcript appears in the composer and can be reviewed.
6. Select **AI Log**.
7. Show the left form updating through the LangGraph tools.

Then demonstrate a surgical edit:

```text
Change the sentiment to neutral and the time to 5 PM. Keep everything else the same.
```

Point out that `edit_interaction` changes only those two fields.

## Requirement Justification

| Requirement | How the project satisfies it |
| --- | --- |
| Split-screen interface | Read-only interaction form on the left and AI Assistant on the right |
| Form never manually filled | Every left-side field is read-only and receives state from the assistant workflow |
| LangGraph required | The backend graph plans, executes tools, and composes the response |
| LLM required | A Groq-hosted LLM converts natural language into a structured tool plan |
| Mandatory log tool | `log_interaction` is registered and demonstrated |
| Mandatory edit tool | `edit_interaction` applies only the explicitly requested patch |
| At least five tools | Nine tools are implemented and registered |
| SQL database | Saved drafts are persisted to MySQL or PostgreSQL through SQLAlchemy |
| Responsive UI | Desktop split view becomes a stacked mobile layout without editable form controls |
| Date and time organization | Timestamps are normalized to UTC while preserving timezone and display preferences |

## Suggested 10-15 Minute Video Order

1. Summarize the task and the AI-only form rule.
2. Walk through the responsive frontend and settings.
3. Demo voice input, transcript review, and AI Log.
4. Demo all nine tools, grouping the six automatic tools shown after logging.
5. Demo `edit_interaction` with a two-field correction.
6. Show the LangGraph graph, tool registry, FastAPI routes, and React components.
7. Save the draft to MySQL and export CSV.
8. End with the requirement-justification table above.
