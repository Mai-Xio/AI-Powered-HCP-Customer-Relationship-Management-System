export const CSV_FIELDS = [
  ["HCP Name", "hcp_name"],
  ["Specialty", "specialty"],
  ["Organization", "organization"],
  ["Interaction Type", "interaction_type"],
  ["Date", "interaction_date"],
  ["Time", "interaction_time"],
  ["Stored UTC Timestamp", "interaction_datetime_utc"],
  ["Timezone", "interaction_timezone"],
  ["Date Format", "date_format"],
  ["Time Format", "time_format"],
  ["Attendees", "attendees"],
  ["Products Discussed", "products_discussed"],
  ["Topics Discussed", "topics_discussed"],
  ["Sentiment", "sentiment"],
  ["Materials Shared", "materials_shared"],
  ["Samples Distributed", "samples_distributed"],
  ["Outcomes", "outcomes"],
  ["Follow-up Actions", "follow_up_actions"],
  ["Follow-up Date", "follow_up_date"],
  ["Summary / Notes", "interaction_summary"],
  ["Compliance Flags", "compliance_flags"],
  ["Completion Status", "completion_status"],
];

export function csvCell(value) {
  const normalized = Array.isArray(value) ? value.join("; ") : value ?? "";
  return `"${String(normalized).replace(/"/g, '""')}"`;
}

export function buildDraftCsv(draft) {
  const headers = CSV_FIELDS.map(([label]) => csvCell(label)).join(",");
  const values = CSV_FIELDS.map(([, key]) => csvCell(draft[key])).join(",");
  return `${headers}\r\n${values}\r\n`;
}

export function draftCsvFilename(draft) {
  const name = (draft.hcp_name || "hcp-interaction")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return `${name || "hcp-interaction"}-draft.csv`;
}

export function downloadDraftCsv(draft) {
  const blob = new Blob([buildDraftCsv(draft)], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = draftCsvFilename(draft);
  document.body.appendChild(link);
  link.click();
  URL.revokeObjectURL(link.href);
  link.remove();
}
