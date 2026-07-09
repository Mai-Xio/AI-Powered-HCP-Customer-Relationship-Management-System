const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }

  return response.json();
}

export function chatWithAgent(message, currentDraft, preferences, plannerModel) {
  return request("/agent/chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      current_draft: currentDraft,
      preferences,
      planner_model: plannerModel || null,
    }),
  });
}

export function saveInteraction(draft) {
  return request("/interactions", {
    method: "POST",
    body: JSON.stringify(draft),
  });
}

export function fetchModels() {
  return request("/models");
}

export function checkModels(modelIds) {
  return request("/models/check", {
    method: "POST",
    body: JSON.stringify({ model_ids: modelIds ?? null }),
  });
}
