import React from "react";
import {
  CalendarDays,
  ChevronDown,
  Clock3,
  Gift,
  Leaf,
  MessageSquareText,
  NotebookText,
  PackageCheck,
  Sparkles,
  Stethoscope,
  UserRound,
  UsersRound,
} from "lucide-react";

function listText(items) {
  return items?.length ? items.join(", ") : "";
}

function firstNonEmpty(...values) {
  return values.find((value) => typeof value === "string" && value.trim()) || "";
}

function ReadField({ label, value, placeholder, icon: Icon, trailing, className = "" }) {
  return (
    <label className={`field ${className}`}>
      <span className="field-label">{label}</span>
      <span className={`field-control ${Icon ? "has-icon" : ""} ${trailing ? "has-trailing" : ""}`}>
        {Icon ? <Icon size={19} className="field-icon" /> : null}
        <input readOnly value={value ?? ""} placeholder={placeholder} aria-readonly="true" />
        {trailing ?? null}
      </span>
    </label>
  );
}

function ReadArea({ label, value, placeholder, icon: Icon }) {
  return (
    <label className="field field-wide">
      <span className="field-label">{label}</span>
      <span className={`area-control ${Icon ? "has-icon" : ""}`}>
        {Icon ? <Icon size={19} className="field-icon area-icon" /> : null}
        <textarea readOnly value={value ?? ""} placeholder={placeholder} aria-readonly="true" />
      </span>
    </label>
  );
}

function SentimentCard({ value }) {
  return (
    <ReadField
      label="Sentiment"
      value={value}
      placeholder="Neutral"
      icon={MessageSquareText}
      trailing={<ChevronDown size={18} className="field-icon trailing" />}
    />
  );
}

export default function InteractionForm({ draft }) {
  const summary = firstNonEmpty(
    draft.interaction_summary,
    draft.outcomes,
    draft.topics_discussed,
  );
  const itemsShared = [listText(draft.materials_shared), listText(draft.samples_distributed)]
    .filter(Boolean)
    .join(", ");

  return (
    <section className="form-panel" aria-label="Log HCP Interaction">
      <div className="leaf-watermark" aria-hidden="true">
        <Leaf size={168} />
      </div>

      <header className="form-hero">
        <div className="brand-mark" aria-hidden="true">
          <Leaf size={36} />
        </div>
        <div className="form-heading">
          <div className="title-line">
            <h1>Log HCP Interaction</h1>
            <span className="controlled-badge">
              <Sparkles size={16} />
              AI-controlled
            </span>
          </div>
        </div>
      </header>

      <div className="section-title-row">
        <h2>
          <Gift size={20} />
          Interaction Details
        </h2>
        <span />
      </div>

      <div className="form-grid">
        <ReadField label="HCP Name" value={draft.hcp_name} placeholder="Search or select HCP..." icon={UserRound} />
        <ReadField
          label="Interaction Type"
          value={draft.interaction_type}
          placeholder="Meeting"
          icon={UsersRound}
          trailing={<ChevronDown size={18} className="field-icon trailing" />}
        />
        <ReadField
          label="Date"
          value={draft.interaction_date}
          placeholder="MM/DD/YYYY"
          icon={CalendarDays}
        />
        <ReadField
          label="Time"
          value={draft.interaction_time}
          placeholder="HH:MM AM"
          icon={Clock3}
        />
        <ReadField
          label="Attendees"
          value={listText(draft.attendees)}
          placeholder="Enter names or search..."
          icon={UsersRound}
        />
        <SentimentCard value={draft.sentiment} />
      </div>

      <ReadField
        label="Products / Topics Discussed"
        value={firstNonEmpty(listText(draft.products_discussed), draft.topics_discussed)}
        placeholder="Enter key discussion points..."
        icon={MessageSquareText}
        className="field-compact"
      />

      <ReadField
        label="Items Shared"
        value={itemsShared}
        placeholder="No materials or samples captured..."
        icon={Gift}
        className="field-compact"
      />

      <ReadArea
        label="Summary / Notes"
        value={summary}
        placeholder="AI-generated CRM-ready notes..."
        icon={NotebookText}
      />

      <div className="two-column outcomes-grid">
        <ReadArea label="Outcomes" value={draft.outcomes} placeholder="Key outcomes or agreements..." icon={Stethoscope} />
        <ReadArea
          label="Follow-up Actions"
          value={draft.follow_up_actions}
          placeholder="Enter next steps or tasks..."
          icon={PackageCheck}
        />
      </div>
    </section>
  );
}
