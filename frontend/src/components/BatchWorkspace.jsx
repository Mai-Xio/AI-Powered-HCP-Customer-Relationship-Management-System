import React, { useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Database,
  Loader2,
  RotateCcw,
  Rows3,
  WandSparkles,
} from "lucide-react";
import { useDispatch, useSelector } from "react-redux";
import {
  clearBatch,
  processBatchLogs,
  saveBatchLogs,
} from "../features/crm/crmSlice.js";

const MAX_BATCH_ITEMS = 3;

function parseEntries(value) {
  return value
    .split(/\r?\n/)
    .map((entry) => entry.trim())
    .filter(Boolean);
}

function displayWhen(draft) {
  return [draft?.interaction_date, draft?.interaction_time].filter(Boolean).join(" | ") || "Needs review";
}

function displayFocus(draft) {
  return draft?.products_discussed?.join(", ") || draft?.topics_discussed || "Needs review";
}

function BatchResultRow({ item }) {
  const response = item.response;
  const draft = response?.draft;
  const tools = response?.tool_trace || [];
  const toolNames = tools.map((tool) => tool.label).join(", ");
  const failed = Boolean(item.error || !response);

  return (
    <div className={`batch-result-row ${failed ? "batch-row-error" : ""}`} role="row">
      <div className="batch-cell batch-hcp" role="cell">
        <span className="batch-cell-label">HCP</span>
        <strong>{draft?.hcp_name || "Not identified"}</strong>
      </div>
      <div className="batch-cell" role="cell">
        <span className="batch-cell-label">When</span>
        <span>{displayWhen(draft)}</span>
      </div>
      <div className="batch-cell" role="cell">
        <span className="batch-cell-label">Sentiment</span>
        <span>{draft?.sentiment || "Not captured"}</span>
      </div>
      <div className="batch-cell batch-focus" role="cell" title={draft?.topics_discussed || ""}>
        <span className="batch-cell-label">Focus</span>
        <span>{displayFocus(draft)}</span>
      </div>
      <div className="batch-cell" role="cell" title={toolNames || "No tools completed"}>
        <span className="batch-cell-label">Tools</span>
        <span>{tools.length ? `${tools.length} used` : "None"}</span>
      </div>
      <div className="batch-cell batch-status" role="cell" title={item.error || response?.assistant_message || ""}>
        <span className="batch-cell-label">Status</span>
        <span className={failed ? "status-error" : "status-ready"}>
          {failed ? <AlertCircle size={14} /> : <CheckCircle2 size={14} />}
          {failed ? "Needs review" : draft?.completion_status || "Ready"}
        </span>
      </div>
    </div>
  );
}

export default function BatchWorkspace() {
  const dispatch = useDispatch();
  const {
    batchResults,
    batchStatus,
    batchSaveStatus,
    batchSavedIds,
    batchError,
  } = useSelector((state) => state.crm);
  const [input, setInput] = useState("");
  const entries = useMemo(() => parseEntries(input), [input]);
  const validResults = batchResults.filter(
    (item) => item.response && !item.error && item.response.draft.completion_status === "Validated",
  );
  const isProcessing = batchStatus === "loading";
  const isSaving = batchSaveStatus === "loading";
  const isOverLimit = entries.length > MAX_BATCH_ITEMS;

  function processBatch() {
    if (!entries.length || isOverLimit || isProcessing) return;
    dispatch(processBatchLogs(entries));
  }

  function clearWorkspace() {
    setInput("");
    dispatch(clearBatch());
  }

  return (
    <section className="batch-workspace" aria-labelledby="batch-title">
      <header className="batch-header">
        <div className="batch-title-group">
          <span className="batch-icon" aria-hidden="true"><Rows3 size={21} /></span>
          <div>
            <h2 id="batch-title">Batch Interaction Workspace</h2>
            <p>Multiple AI-managed records, one review sheet</p>
          </div>
        </div>
        <div className="batch-header-actions">
          <span className={`batch-limit ${isOverLimit ? "batch-limit-over" : ""}`}>
            {entries.length} / {MAX_BATCH_ITEMS}
          </span>
          <button
            className="icon-button batch-reset"
            type="button"
            onClick={clearWorkspace}
            title="Clear batch workspace"
            aria-label="Clear batch workspace"
            disabled={!input && !batchResults.length}
          >
            <RotateCcw size={17} />
          </button>
        </div>
      </header>

      <div className="batch-layout">
        <div className="batch-input-pane">
          <label htmlFor="batch-log-input">Interaction logs</label>
          <textarea
            id="batch-log-input"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder={"Met Dr. Rao today, discussed CardioPlus efficacy, positive sentiment, shared brochure.\nMet Dr. Shah yesterday at 4 PM, discussed affordability, neutral sentiment.\nCalled Dr. Menon this morning, reviewed renal dosing and scheduled a follow-up next Monday."}
            rows={7}
          />
          <button
            className="batch-process-button"
            type="button"
            onClick={processBatch}
            disabled={!entries.length || isOverLimit || isProcessing}
          >
            {isProcessing ? <Loader2 size={17} className="spin" /> : <WandSparkles size={17} />}
            {isProcessing ? "Processing records..." : "Process with AI"}
          </button>
          {batchError ? <p className="batch-error"><AlertCircle size={14} />{batchError}</p> : null}
        </div>

        <div className="batch-results-pane">
          <div className="batch-results-toolbar">
            <div>
              <strong>Review sheet</strong>
              <span>{batchResults.length ? `${validResults.length} ready` : "No processed records"}</span>
            </div>
            <button
              className="save-button batch-save-button"
              type="button"
              disabled={!validResults.length || isSaving || batchSaveStatus === "saved"}
              onClick={() => dispatch(saveBatchLogs())}
            >
              {isSaving ? <Loader2 size={16} className="spin" /> : <Database size={16} />}
              {batchSaveStatus === "saved"
                ? `Saved ${batchSavedIds.length}`
                : "Save All"}
            </button>
          </div>

          <div className="batch-table" role="table" aria-label="Batch interaction review sheet">
            <div className="batch-table-head" role="row">
              <span role="columnheader">HCP</span>
              <span role="columnheader">When</span>
              <span role="columnheader">Sentiment</span>
              <span role="columnheader">Focus</span>
              <span role="columnheader">Tools</span>
              <span role="columnheader">Status</span>
            </div>
            {batchResults.length ? (
              batchResults.map((item, index) => <BatchResultRow item={item} key={`${index}-${item.source_text}`} />)
            ) : (
              <div className="batch-empty">
                <Rows3 size={22} />
                <span>Processed interactions will appear here.</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
