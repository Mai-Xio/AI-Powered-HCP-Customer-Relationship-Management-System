import React from "react";
import {
  Activity,
  Bot,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Cpu,
  Database,
  FileDown,
  Globe2,
  Loader2,
  Paperclip,
  SendHorizonal,
  Settings2,
  Wrench,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  checkModelStatuses,
  loadModels,
  saveDraft,
  sendAgentMessage,
  setPlannerModel,
  setPreference,
} from "../features/crm/crmSlice.js";
import { downloadDraftCsv } from "../features/crm/exportCsv.js";

function shortModel(id) {
  if (!id) return "";
  return id.includes("/") ? id.split("/").pop() : id;
}

const TIMEZONES = [
  "Asia/Kolkata",
  "UTC",
  "America/New_York",
  "America/Chicago",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Berlin",
  "Asia/Dubai",
  "Asia/Singapore",
  "Australia/Sydney",
];

const DATE_FORMATS = ["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD", "DD MMM YYYY"];

function Message({ message }) {
  const isAssistant = message.role === "assistant";
  const Avatar = isAssistant ? Bot : Cpu;

  return (
    <article className={`message-row ${isAssistant ? "assistant-row" : "user-row"}`}>
      <div className="message-avatar" aria-hidden="true">
        <Avatar size={21} />
      </div>
      <div className={`message ${isAssistant ? "assistant-message" : "user-message"}`}>
        <div className="message-body">{message.content}</div>
      </div>
    </article>
  );
}

function SettingsDrawer({
  activeMode,
  canExport,
  canSave,
  devOpen,
  dispatch,
  draft,
  modelContext,
  modelStatus,
  modelStatusLoading,
  models,
  onClose,
  onExportCsv,
  plannerModel,
  preferences,
  saveStatus,
  savedInteractionId,
  setActiveMode,
  setDevOpen,
}) {
  return (
    <>
      <button className="settings-backdrop" type="button" aria-label="Close settings" onClick={onClose} />
      <aside className="settings-drawer" aria-label="Assistant Settings" aria-modal="true">
        <header className="drawer-header">
          <div>
            <Settings2 size={24} />
            <h2>Assistant Settings</h2>
          </div>
          <button className="icon-button" type="button" aria-label="Close settings" onClick={onClose}>
            <X size={20} />
          </button>
        </header>

        <section className="settings-section">
          <h3>General / Formatting</h3>
          <div className="preference-grid" aria-label="Date and time save preferences">
            <label className="preference-control">
              <span>
                <Globe2 size={14} />
                Time zone
              </span>
              <select
                value={preferences.timezone}
                onChange={(event) => dispatch(setPreference({ key: "timezone", value: event.target.value }))}
              >
                {TIMEZONES.map((timezone) => (
                  <option key={timezone} value={timezone}>
                    {timezone}
                  </option>
                ))}
              </select>
            </label>
            <label className="preference-control">
              <span>
                <CalendarDays size={14} />
                Date format
              </span>
              <select
                value={preferences.date_format}
                onChange={(event) => dispatch(setPreference({ key: "date_format", value: event.target.value }))}
              >
                {DATE_FORMATS.map((format) => (
                  <option key={format} value={format}>
                    {format}
                  </option>
                ))}
              </select>
            </label>
            <div className="time-toggle" aria-label="Time format">
              <span>
                <Clock3 size={14} />
                Time format
              </span>
              <div className="segmented-control">
                {["12h", "24h"].map((format) => (
                  <button
                    type="button"
                    key={format}
                    className={preferences.time_format === format ? "active" : ""}
                    onClick={() => dispatch(setPreference({ key: "time_format", value: format }))}
                  >
                    {format}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="settings-section">
          <h3>Input Mode</h3>
          <div className="mode-tabs" role="tablist" aria-label="Assistant input mode">
            <button
              type="button"
              role="tab"
              className={activeMode === "chat" ? "active" : ""}
              onClick={() => setActiveMode("chat")}
            >
              Chat
            </button>
            <button
              type="button"
              role="tab"
              className={activeMode === "structured" ? "active" : ""}
              onClick={() => setActiveMode("structured")}
            >
              Structured
            </button>
          </div>
        </section>

        <section className="settings-section">
          <h3>Draft / Utility</h3>
          <div className="drawer-actions">
            <button
              type="button"
              className="save-button drawer-save"
              disabled={!canSave || saveStatus === "loading"}
              onClick={() => dispatch(saveDraft())}
              title="Save the current AI-filled draft to the SQL database"
            >
              <Database size={16} />
              {saveStatus === "saved" ? `Saved #${savedInteractionId}` : "Save AI Draft"}
            </button>
            <button
              type="button"
              className="save-button export-button"
              disabled={!canExport}
              onClick={() => onExportCsv(draft)}
              title="Download the current AI-filled draft as CSV"
            >
              <FileDown size={16} />
              Export CSV
            </button>
          </div>
        </section>

        <section className="settings-section dev-section">
          <button
            type="button"
            className="dev-toggle"
            aria-expanded={devOpen}
            onClick={() => setDevOpen((open) => !open)}
          >
            <span>
              <ChevronRight size={14} className={devOpen ? "chev-open" : ""} />
              <Cpu size={15} />
              Developer Settings
            </span>
          </button>
          {devOpen ? (
            <div className="dev-body">
              <div className="dev-status-line">
                <span className={modelContext?.live_llm_enabled ? "ok" : "bad"}>
                  Live LLM: {modelContext?.live_llm_enabled ? "on" : "off"}
                </span>
                <span className={modelContext?.key_configured ? "ok" : "bad"}>
                  API key: {modelContext?.key_configured ? "configured" : "missing"}
                </span>
              </div>
              <label className="dev-model-select">
                <span>Planner model</span>
                <select
                  value={plannerModel}
                  onChange={(event) => dispatch(setPlannerModel(event.target.value))}
                >
                  <option value="">
                    Server default ({shortModel(modelContext?.active_model) || "..."})
                  </option>
                  {models.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.label} - {model.tier}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                className="dev-check"
                disabled={modelStatusLoading}
                onClick={() => dispatch(checkModelStatuses())}
              >
                {modelStatusLoading ? <Loader2 size={14} className="spin" /> : <Activity size={14} />}
                Check model status
              </button>
              <ul className="model-status-list">
                {models.map((model) => {
                  const info = modelStatus[model.id];
                  const state = info ? info.status : model.tier;
                  return (
                    <li key={model.id} title={info?.detail || model.role}>
                      <span className={`status-dot status-${info?.status || "unknown"}`} />
                      <span className="model-id">{model.label}</span>
                      <span className="model-state">
                        {state}
                        {info?.latency_ms ? ` - ${info.latency_ms}ms` : ""}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}
        </section>
      </aside>
    </>
  );
}

export default function AssistantPanel() {
  const dispatch = useDispatch();
  const {
    messages,
    status,
    saveStatus,
    savedInteractionId,
    draft,
    preferences,
    models,
    modelContext,
    modelStatus,
    modelStatusLoading,
    plannerModel,
  } = useSelector((state) => state.crm);
  const [input, setInput] = useState("");
  const [activeMode, setActiveMode] = useState("chat");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [devOpen, setDevOpen] = useState(false);
  const [structuredInput, setStructuredInput] = useState({
    hcpName: "",
    organization: "",
    product: "",
    sentiment: "Positive",
    notes: "",
    outcomes: "",
    followUp: "",
    followUpActions: "",
  });
  const scrollRef = useRef(null);

  useEffect(() => {
    dispatch(loadModels());
  }, [dispatch]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, status]);

  const canSave = Boolean(draft.hcp_name && draft.topics_discussed);
  const canExport = Boolean(draft.hcp_name || draft.topics_discussed || draft.interaction_summary);

  function submit(event) {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || status === "loading") return;
    dispatch(sendAgentMessage(trimmed));
    setInput("");
  }

  function updateStructuredField(key, value) {
    setStructuredInput((current) => ({ ...current, [key]: value }));
  }

  function submitStructured(event) {
    event.preventDefault();
    if (status === "loading") return;
    const parts = [
      structuredInput.hcpName ? `HCP Name: ${structuredInput.hcpName}` : "",
      structuredInput.organization ? `Organization: ${structuredInput.organization}` : "",
      structuredInput.product ? `Product: ${structuredInput.product}` : "",
      structuredInput.sentiment ? `Sentiment: ${structuredInput.sentiment}` : "",
      structuredInput.notes ? `Notes: ${structuredInput.notes}` : "",
      structuredInput.outcomes ? `Outcomes: ${structuredInput.outcomes}` : "",
      structuredInput.followUp ? `Follow-up: ${structuredInput.followUp}` : "",
      structuredInput.followUpActions ? `Follow-up Actions: ${structuredInput.followUpActions}` : "",
    ].filter(Boolean);
    if (!parts.length) return;
    dispatch(sendAgentMessage(`Structured assisted log request:\n${parts.join("\n")}`));
  }

  return (
    <aside className="assistant-panel" aria-label="AI Assistant">
      <header className="assistant-header">
        <div className="assistant-title-row">
          <div className="assistant-title">
            <span className="assistant-avatar" aria-hidden="true">
              <Bot size={28} />
            </span>
            <div>
              <h2>AI Assistant</h2>
              <p>Log interaction details here via chat</p>
            </div>
          </div>
          <button
            type="button"
            className="icon-button settings-toggle"
            aria-label="Open assistant settings"
            aria-expanded={settingsOpen}
            onClick={() => setSettingsOpen(true)}
          >
            <Settings2 size={20} />
          </button>
        </div>
      </header>

      {activeMode === "chat" ? (
        <div className="messages" ref={scrollRef}>
          {messages.map((message, index) => (
            <Message message={message} key={`${message.role}-${index}`} />
          ))}
          {status === "loading" ? (
            <div className="message-row assistant-row">
              <div className="message-avatar" aria-hidden="true">
                <Bot size={21} />
              </div>
              <div className="message assistant-message loading-message">
                <Loader2 size={16} className="spin" />
                Running LangGraph tools...
              </div>
            </div>
          ) : null}
        </div>
      ) : (
        <form className="structured-intake" onSubmit={submitStructured}>
          <label>
            <span>HCP Name</span>
            <input
              value={structuredInput.hcpName}
              onChange={(event) => updateStructuredField("hcpName", event.target.value)}
              placeholder="Dr. Rao"
            />
          </label>
          <label>
            <span>Organization</span>
            <input
              value={structuredInput.organization}
              onChange={(event) => updateStructuredField("organization", event.target.value)}
              placeholder="Apollo Hospital"
            />
          </label>
          <label>
            <span>Product</span>
            <input
              value={structuredInput.product}
              onChange={(event) => updateStructuredField("product", event.target.value)}
              placeholder="CardioPlus"
            />
          </label>
          <label>
            <span>Sentiment</span>
            <select
              value={structuredInput.sentiment}
              onChange={(event) => updateStructuredField("sentiment", event.target.value)}
            >
              <option>Positive</option>
              <option>Neutral</option>
              <option>Negative</option>
              <option>Mixed</option>
            </select>
          </label>
          <label className="structured-wide">
            <span>Notes</span>
            <textarea
              value={structuredInput.notes}
              onChange={(event) => updateStructuredField("notes", event.target.value)}
              placeholder="Asked for safety data and shared efficacy brochure"
            />
          </label>
          <label>
            <span>Outcomes</span>
            <input
              value={structuredInput.outcomes}
              onChange={(event) => updateStructuredField("outcomes", event.target.value)}
              placeholder="Agreed to review data"
            />
          </label>
          <label>
            <span>Follow-up</span>
            <input
              value={structuredInput.followUp}
              onChange={(event) => updateStructuredField("followUp", event.target.value)}
              placeholder="Next Friday"
            />
          </label>
          <label className="structured-wide">
            <span>Follow-up Actions</span>
            <textarea
              value={structuredInput.followUpActions}
              onChange={(event) => updateStructuredField("followUpActions", event.target.value)}
              placeholder="Send approved safety data and schedule a follow-up"
            />
          </label>
          <button className="structured-submit" type="submit" disabled={status === "loading"}>
            {status === "loading" ? <Loader2 className="spin" size={16} /> : <Wrench size={16} />}
            Validate & Log via AI
          </button>
        </form>
      )}

      <div className="assistant-bottom">
        <div className="draft-actions">
          <button
            type="button"
            className="save-button"
            disabled={!canSave || saveStatus === "loading"}
            onClick={() => dispatch(saveDraft())}
            title="Save the current AI-filled draft to the SQL database"
          >
            <Database size={16} />
            {saveStatus === "saved" ? `Saved #${savedInteractionId}` : "Save AI Draft"}
          </button>
          <button
            type="button"
            className="save-button export-button"
            disabled={!canExport}
            onClick={() => downloadDraftCsv(draft)}
            title="Download the current AI-filled draft as CSV"
          >
            <FileDown size={16} />
            Export CSV
          </button>
        </div>

        <form className={`chat-composer ${activeMode === "chat" ? "" : "hidden-composer"}`} onSubmit={submit}>
          <label className="composer-box">
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Describe interaction..."
              rows={3}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  submit(event);
                }
              }}
            />
            <Paperclip size={18} />
          </label>
          <button className="agent-submit" type="submit" disabled={status === "loading" || !input.trim()}>
            {status === "loading" ? <Loader2 className="spin" size={22} /> : <SendHorizonal size={23} />}
            <span>AI Log</span>
          </button>
        </form>
        <p className="secure-note">
          <CheckCircle2 size={15} />
          All interactions are secure and audit-ready.
        </p>
      </div>

      {settingsOpen ? (
        <SettingsDrawer
          activeMode={activeMode}
          canExport={canExport}
          canSave={canSave}
          devOpen={devOpen}
          dispatch={dispatch}
          draft={draft}
          modelContext={modelContext}
          modelStatus={modelStatus}
          modelStatusLoading={modelStatusLoading}
          models={models}
          onClose={() => setSettingsOpen(false)}
          onExportCsv={downloadDraftCsv}
          plannerModel={plannerModel}
          preferences={preferences}
          saveStatus={saveStatus}
          savedInteractionId={savedInteractionId}
          setActiveMode={setActiveMode}
          setDevOpen={setDevOpen}
        />
      ) : null}
    </aside>
  );
}
