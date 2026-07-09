import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { chatWithAgent, checkModels, fetchModels, saveInteraction } from "./api.js";

function defaultTimezone() {
  const resolved = Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Kolkata";
  return resolved === "Asia/Calcutta" ? "Asia/Kolkata" : resolved;
}

export const emptyDraft = {
  hcp_name: "",
  specialty: "",
  organization: "",
  interaction_type: "Meeting",
  interaction_date: "",
  interaction_time: "",
  interaction_datetime_utc: null,
  interaction_timezone: defaultTimezone(),
  original_timezone: defaultTimezone(),
  date_format: "MM/DD/YYYY",
  time_format: "12h",
  time_format_preference: "12h",
  attendees: [],
  topics_discussed: "",
  products_discussed: [],
  sentiment: "",
  materials_shared: [],
  samples_distributed: [],
  outcomes: "",
  follow_up_actions: "",
  suggested_follow_ups: [],
  hcp_questions: "",
  objections: "",
  commitments: "",
  next_steps: "",
  follow_up_date: "",
  interaction_summary: "",
  completion_status: "Needs Review",
  confidence_score: 0,
  compliance_flags: [],
  ai_confidence: "",
};

const DATE_FORMATS = {
  "MM/DD/YYYY": {
    regex: /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/,
    parts: (match) => ({ month: match[1], day: match[2], year: match[3] }),
  },
  "DD/MM/YYYY": {
    regex: /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/,
    parts: (match) => ({ day: match[1], month: match[2], year: match[3] }),
  },
  "YYYY-MM-DD": {
    regex: /^(\d{4})-(\d{1,2})-(\d{1,2})$/,
    parts: (match) => ({ year: match[1], month: match[2], day: match[3] }),
  },
  "DD MMM YYYY": {
    regex: /^(\d{1,2})\s([A-Za-z]{3})\s(\d{4})$/,
    parts: (match) => ({
      day: match[1],
      month: String(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].indexOf(match[2]) + 1),
      year: match[3],
    }),
  },
};

function pad(value) {
  return String(value).padStart(2, "0");
}

function parseDateValue(value, format) {
  if (!value) return null;
  const parser = DATE_FORMATS[format];
  if (!parser) return null;
  const match = value.match(parser.regex);
  if (!match) return null;
  const parts = parser.parts(match);
  const month = Number(parts.month);
  const day = Number(parts.day);
  const year = Number(parts.year);
  if (!month || !day || !year || month > 12 || day > 31) return null;
  return { year, month, day };
}

function formatDateValue(parts, format) {
  if (!parts) return "";
  const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  if (format === "DD/MM/YYYY") return `${pad(parts.day)}/${pad(parts.month)}/${parts.year}`;
  if (format === "YYYY-MM-DD") return `${parts.year}-${pad(parts.month)}-${pad(parts.day)}`;
  if (format === "DD MMM YYYY") return `${pad(parts.day)} ${monthNames[parts.month - 1]} ${parts.year}`;
  return `${pad(parts.month)}/${pad(parts.day)}/${parts.year}`;
}

function parseTimeValue(value, format) {
  if (!value) return null;
  const trimmed = value.trim().toUpperCase();
  if (format === "24h") {
    const match = trimmed.match(/^(\d{1,2}):(\d{2})$/);
    if (!match) return null;
    return { hour: Number(match[1]), minute: Number(match[2]) };
  }
  const match = trimmed.match(/^(\d{1,2}):(\d{2})\s(AM|PM)$/);
  if (!match) return null;
  let hour = Number(match[1]);
  if (match[3] === "PM" && hour !== 12) hour += 12;
  if (match[3] === "AM" && hour === 12) hour = 0;
  return { hour, minute: Number(match[2]) };
}

function formatTimeValue(parts, format) {
  if (!parts) return "";
  if (format === "24h") return `${pad(parts.hour)}:${pad(parts.minute)}`;
  const suffix = parts.hour >= 12 ? "PM" : "AM";
  const hour = parts.hour % 12 || 12;
  return `${pad(hour)}:${pad(parts.minute)} ${suffix}`;
}

function reformatDraftForPreference(draft, key, value) {
  if (key === "date_format") {
    const oldFormat = draft.date_format || "MM/DD/YYYY";
    const interactionDate = parseDateValue(draft.interaction_date, oldFormat);
    const followUpDate = parseDateValue(draft.follow_up_date, oldFormat);
    if (interactionDate) draft.interaction_date = formatDateValue(interactionDate, value);
    if (followUpDate) draft.follow_up_date = formatDateValue(followUpDate, value);
    draft.date_format = value;
  }
  if (key === "time_format") {
    const oldFormat = draft.time_format || "12h";
    const interactionTime = parseTimeValue(draft.interaction_time, oldFormat);
    if (interactionTime) draft.interaction_time = formatTimeValue(interactionTime, value);
    draft.time_format = value;
    draft.time_format_preference = value;
  }
  if (key === "timezone") {
    draft.interaction_timezone = value;
    draft.original_timezone = value;
  }
}

export const sendAgentMessage = createAsyncThunk(
  "crm/sendAgentMessage",
  async (message, { getState }) => {
    const { draft, preferences, plannerModel } = getState().crm;
    return chatWithAgent(message, draft, preferences, plannerModel);
  },
);

export const saveDraft = createAsyncThunk("crm/saveDraft", async (_, { getState }) => {
  const { draft } = getState().crm;
  return saveInteraction(draft);
});

export const loadModels = createAsyncThunk("crm/loadModels", async () => fetchModels());

export const checkModelStatuses = createAsyncThunk(
  "crm/checkModelStatuses",
  async (modelIds) => checkModels(modelIds),
);

const initialState = {
  draft: emptyDraft,
  preferences: {
    timezone: defaultTimezone(),
    date_format: "MM/DD/YYYY",
    time_format: "12h",
  },
  messages: [
    {
      role: "assistant",
      content:
        'Log interaction details here (e.g., "Met Dr. Smith, discussed Product X efficacy, positive sentiment, shared brochure") or ask for help.',
      tools: [],
    },
  ],
  lastToolTrace: [],
  plannerMode: "llm",
  plannerModel: "", // "" = use the server's configured default model
  lastPlannerModel: "",
  models: [],
  modelContext: null, // { active_model, fallback_model, live_llm_enabled, key_configured }
  modelStatus: {}, // id -> { status, latency_ms, detail }
  modelStatusLoading: false,
  status: "idle",
  saveStatus: "idle",
  error: "",
  savedInteractionId: null,
};

const crmSlice = createSlice({
  name: "crm",
  initialState,
  reducers: {
    resetDraft(state) {
      state.draft = {
        ...emptyDraft,
        interaction_timezone: state.preferences.timezone,
        original_timezone: state.preferences.timezone,
        date_format: state.preferences.date_format,
        time_format: state.preferences.time_format,
        time_format_preference: state.preferences.time_format,
      };
      state.lastToolTrace = [];
      state.savedInteractionId = null;
    },
    setPreference(state, action) {
      const { key, value } = action.payload;
      state.preferences[key] = value;
      reformatDraftForPreference(state.draft, key, value);
    },
    setPlannerModel(state, action) {
      state.plannerModel = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendAgentMessage.pending, (state, action) => {
        state.status = "loading";
        state.error = "";
        state.messages.push({ role: "user", content: action.meta.arg, tools: [] });
      })
      .addCase(sendAgentMessage.fulfilled, (state, action) => {
        state.status = "idle";
        state.draft = action.payload.draft;
        state.preferences = {
          timezone: action.payload.draft.interaction_timezone || state.preferences.timezone,
          date_format: action.payload.draft.date_format || state.preferences.date_format,
          time_format: action.payload.draft.time_format || action.payload.draft.time_format_preference || state.preferences.time_format,
        };
        state.lastToolTrace = action.payload.tool_trace;
        state.plannerMode = action.payload.planner_mode || "llm";
        state.lastPlannerModel = action.payload.planner_model || "";
        state.messages.push({
          role: "assistant",
          content: action.payload.assistant_message,
          tools: action.payload.tool_trace,
          mode: action.payload.planner_mode || "llm",
          model: action.payload.planner_model || "",
        });
      })
      .addCase(sendAgentMessage.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error.message ?? "Agent request failed";
        state.messages.push({
          role: "assistant",
          content: "I could not reach the AI service. Check that the FastAPI backend is running.",
          tools: [],
        });
      })
      .addCase(loadModels.fulfilled, (state, action) => {
        state.models = action.payload.models || [];
        state.modelContext = {
          active_model: action.payload.active_model,
          fallback_model: action.payload.fallback_model,
          live_llm_enabled: action.payload.live_llm_enabled,
          key_configured: action.payload.key_configured,
        };
      })
      .addCase(checkModelStatuses.pending, (state) => {
        state.modelStatusLoading = true;
      })
      .addCase(checkModelStatuses.fulfilled, (state, action) => {
        state.modelStatusLoading = false;
        for (const result of action.payload.results || []) {
          state.modelStatus[result.id] = result;
        }
      })
      .addCase(checkModelStatuses.rejected, (state) => {
        state.modelStatusLoading = false;
      })
      .addCase(saveDraft.pending, (state) => {
        state.saveStatus = "loading";
      })
      .addCase(saveDraft.fulfilled, (state, action) => {
        state.saveStatus = "saved";
        state.savedInteractionId = action.payload.id;
      })
      .addCase(saveDraft.rejected, (state, action) => {
        state.saveStatus = "failed";
        state.error = action.error.message ?? "Save failed";
      });
  },
});

export const { resetDraft, setPreference, setPlannerModel } = crmSlice.actions;
export default crmSlice.reducer;
