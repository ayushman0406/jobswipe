const BASE = import.meta.env.VITE_API_URL || "/api";

async function req(path, opts = {}) {
  let res;
  try {
    res = await fetch(BASE + path, opts);
  } catch {
    throw new Error("Can't reach the API. Start the backend on port 8000.");
  }
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }
  if (!res.ok) {
    const detail = data?.detail;
    const msg = typeof detail === "string" ? detail : res.statusText || "Request failed";
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  return data;
}

function json(body) {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export const api = {
  meta: () => req("/meta"),
  createUser: (body) => req("/users", json(body)),
  getUser: (id) => req(`/users/${id}`),
  uploadResume: (id, file) => {
    const fd = new FormData();
    fd.append("file", file);
    return req(`/users/${id}/resume`, { method: "POST", body: fd });
  },
  feed: (id, limit = 15) => req(`/users/${id}/feed?limit=${limit}`),
  browse: (id, body) => req(`/users/${id}/browse?limit=15`, json(body)),
  swipe: (id, job_id, action) => req(`/users/${id}/swipe`, json({ job_id, action })),
  why: (id, jobId) => req(`/users/${id}/jobs/${jobId}/why`),
  refine: (id, text) => req(`/users/${id}/search/refine`, json({ text })),
  voice: (id, blob, lang) => {
    const fd = new FormData();
    const type = blob.type || "audio/webm";
    const ext = type.includes("mp4") ? "m4a" : type.includes("ogg") ? "ogg" : "webm";
    fd.append("audio", blob, `speech.${ext}`);
    const q = lang ? `?lang=${encodeURIComponent(lang)}` : "";
    return req(`/users/${id}/search/voice${q}`, { method: "POST", body: fd });
  },
  resetSearch: (id) => req(`/users/${id}/search`, { method: "DELETE" }),
  matches: (id) => req(`/users/${id}/matches`),
  accept: (mid) => req(`/dev/matches/${mid}/provider-accept`, { method: "POST" }),
  getAts: (id) => req(`/users/${id}/resume/ats`),
  updateLatex: (id, latex) =>
    req(`/users/${id}/resume/latex`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ latex }),
    }),
  improveResumeChat: (id, message, currentLatex, chatHistory = []) =>
    req(
      `/users/${id}/resume/improve-chat`,
      json({ message, current_latex: currentLatex, chat_history: chatHistory })
    ),
};