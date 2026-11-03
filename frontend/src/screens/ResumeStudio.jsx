import { useEffect, useRef, useState } from "react";
import { api } from "../api";

export default function ResumeStudio({ user, t, onUpdateUser }) {
  const [ats, setAts] = useState(user.ats_score || null);
  const [latex, setLatex] = useState(user.resume_latex || "");
  const [loading, setLoading] = useState(!user.ats_score);
  const [chatting, setChatting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [input, setInput] = useState("");
  const [activeTab, setActiveTab] = useState("preview"); // 'preview' | 'latex'
  const [copied, setCopied] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        t.coachGreeting ||
        "Hi! I'm your AI Resume Coach. I've analyzed your resume and generated an ATS-optimized LaTeX version. What would you like to improve?",
      quick_prompts: [
        "Add quantifiable metrics (% & numbers) to my work experience",
        "Add missing technical skills and tools",
        "Refine executive summary for high ATS matching",
      ],
    },
  ]);

  const chatEndRef = useRef(null);

  useEffect(() => {
    if (!ats || !latex) {
      setLoading(true);
      api
        .getAts(user.id)
        .then((res) => {
          if (res.ats) setAts(res.ats);
          if (res.latex) setLatex(res.latex);
          if (onUpdateUser) onUpdateUser({ ats_score: res.ats, resume_latex: res.latex });
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [user.id]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chatting]);

  async function handleSend(textToSend) {
    const query = (textToSend || input).trim();
    if (!query || chatting) return;

    setInput("");
    const newHistory = [...messages, { role: "user", content: query }];
    setMessages(newHistory);
    setChatting(true);

    try {
      const res = await api.improveResumeChat(user.id, query, latex, newHistory);
      if (res.latex) setLatex(res.latex);
      if (res.ats) {
        setAts(res.ats);
        if (onUpdateUser) onUpdateUser({ ats_score: res.ats, resume_latex: res.latex });
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.reply || "I have updated your LaTeX resume according to your request.",
          changes_made: res.changes_made || [],
          quick_prompts: res.quick_prompts || [],
        },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Sorry, I encountered an error: ${e.message}. Please try again.`,
        },
      ]);
    } finally {
      setChatting(false);
    }
  }

  async function saveManualLatex() {
    setSaving(true);
    try {
      const res = await api.updateLatex(user.id, latex);
      if (res.ats) setAts(res.ats);
      if (onUpdateUser) onUpdateUser({ ats_score: res.ats, resume_latex: latex });
    } catch (e) {
      alert("Failed to save LaTeX: " + e.message);
    } finally {
      setSaving(false);
    }
  }

  function copyToClipboard() {
    navigator.clipboard.writeText(latex);
    setCopied(true);
    setTimeout(() => setCopied(false), 2200);
  }

  function downloadTex() {
    const blob = new Blob([latex], { type: "text/x-tex;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(user.name || "resume").toLowerCase().replace(/\s+/g, "_")}.tex`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  const score = ats?.overall_score ?? 0;
  const rating = ats?.rating || "Pending";
  const scoreColor = score >= 80 ? "var(--good)" : score >= 60 ? "var(--super)" : "var(--accent)";

  return (
    <div className="studio-layout">
      {/* LEFT COLUMN: ATS Score & AI Chat Coach */}
      <section className="studio-left">
        {/* ATS Score Overview Card */}
        <div className="ats-card">
          <div className="ats-header">
            <div>
              <p className="kicker-small">{t.atsScore}</p>
              <h2>
                <span style={{ color: scoreColor }}>{score}</span>
                <span className="ats-total">/100</span>
              </h2>
              <span className="badge-rating" style={{ "--badge-color": scoreColor }}>
                {rating}
              </span>
            </div>

            {/* Circular score gauge */}
            <div className="score-ring-wrap" aria-hidden="true">
              <svg className="score-ring" width="80" height="80" viewBox="0 0 80 80">
                <circle cx="40" cy="40" r="34" className="ring-bg" />
                <circle
                  cx="40"
                  cy="40"
                  r="34"
                  className="ring-progress"
                  style={{
                    stroke: scoreColor,
                    strokeDashoffset: 213.6 - (213.6 * score) / 100,
                  }}
                />
              </svg>
              <span className="ring-label">{score}%</span>
            </div>
          </div>

          {/* Category breakdown bars */}
          {ats?.breakdown && (
            <div className="ats-breakdown">
              {Object.entries(ats.breakdown).map(([key, item]) => {
                const pct = Math.round((item.score / item.max) * 100);
                const title = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
                return (
                  <div key={key} className="breakdown-row" title={item.feedback}>
                    <div className="breakdown-meta">
                      <span>{title}</span>
                      <small>
                        {item.score}/{item.max}
                      </small>
                    </div>
                    <div className="breakdown-bar-bg">
                      <div className="breakdown-bar-fill" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Actionable recommendations */}
          {(ats?.improvements || []).length > 0 && (
            <div className="improvements-list">
              <p className="kicker-small">Top Recommended Improvements</p>
              {ats.improvements.slice(0, 3).map((imp, idx) => (
                <div key={idx} className="improvement-item">
                  <div className="imp-text">
                    <strong>{imp.title}</strong>
                    <p>{imp.description}</p>
                  </div>
                  <button
                    type="button"
                    className="imp-apply-btn"
                    onClick={() => handleSend(imp.prompt)}
                    disabled={chatting}
                  >
                    ⚡ Fix with AI
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* AI Resume Coach Chat Interface */}
        <div className="coach-chat-card">
          <header className="chat-header">
            <span className="coach-avatar">🤖</span>
            <div>
              <h3>AI Resume Coach</h3>
              <p className="coach-status">
                {chatting ? "Editing LaTeX & recalculating ATS score…" : "Online · Ready to polish"}
              </p>
            </div>
          </header>

          <div className="chat-messages">
            {messages.map((m, idx) => (
              <div key={idx} className={`chat-bubble ${m.role}`}>
                <p className="bubble-text">{m.content}</p>

                {/* Bullet list of changes made */}
                {(m.changes_made || []).length > 0 && (
                  <div className="changes-box">
                    <strong>✨ Key changes applied:</strong>
                    <ul>
                      {m.changes_made.map((ch, i) => (
                        <li key={i}>{ch}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Quick action chips */}
                {(m.quick_prompts || []).length > 0 && (
                  <div className="quick-prompts">
                    {m.quick_prompts.map((qp, i) => (
                      <button
                        key={i}
                        type="button"
                        className="quick-chip"
                        onClick={() => handleSend(qp)}
                        disabled={chatting}
                      >
                        {qp}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {chatting && (
              <div className="chat-bubble assistant typing">
                <span className="dot" />
                <span className="dot" />
                <span className="dot" />
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <form
            className="chat-input-bar"
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t.chatPlaceholder}
              disabled={chatting}
            />
            <button type="submit" className="solid send-btn" disabled={chatting || !input.trim()}>
              Send
            </button>
          </form>
        </div>
      </section>

      {/* RIGHT COLUMN: Interactive LaTeX Editor & Live Preview */}
      <section className="studio-right">
        <div className="editor-card">
          <header className="editor-header">
            <div className="editor-tabs">
              <button
                type="button"
                className={`tab-btn ${activeTab === "preview" ? "on" : ""}`}
                onClick={() => setActiveTab("preview")}
              >
                {t.viewFormatted}
              </button>
              <button
                type="button"
                className={`tab-btn ${activeTab === "latex" ? "on" : ""}`}
                onClick={() => setActiveTab("latex")}
              >
                {t.viewLatex}
              </button>
            </div>

            <div className="editor-actions">
              <button type="button" className="ghost-btn" onClick={copyToClipboard} title="Copy LaTeX code">
                {copied ? t.copied : t.copyLatex}
              </button>
              <button type="button" className="ghost-btn" onClick={downloadTex} title="Download .tex file">
                {t.downloadTex}
              </button>
              {activeTab === "latex" && (
                <button type="button" className="solid-btn" onClick={saveManualLatex} disabled={saving}>
                  {saving ? "Saving…" : "Save & Re-score"}
                </button>
              )}
            </div>
          </header>

          <div className="editor-content">
            {activeTab === "latex" ? (
              <div className="latex-editor-wrap">
                <textarea
                  className="latex-textarea"
                  value={latex}
                  onChange={(e) => setLatex(e.target.value)}
                  spellCheck="false"
                  aria-label="LaTeX Resume Code"
                />
              </div>
            ) : (
              <div className="formatted-preview">
                {/* Formatted Resume Preview */}
                <article className="resume-paper">
                  <header className="res-header">
                    <h1>{user.resume?.name || user.name || "Your Name"}</h1>
                    <p className="res-contact">
                      {[
                        user.resume?.email || user.email,
                        user.resume?.phone,
                        user.resume?.location,
                        user.resume?.links?.linkedin,
                        user.resume?.links?.github,
                      ]
                        .filter(Boolean)
                        .join("  •  ")}
                    </p>
                  </header>

                  {user.resume?.summary && (
                    <section className="res-section">
                      <h3>PROFESSIONAL SUMMARY</h3>
                      <p className="res-summary">{user.resume.summary}</p>
                    </section>
                  )}

                  <section className="res-section">
                    <h3>TECHNICAL & DOMAIN SKILLS</h3>
                    <div className="res-skills-list">
                      {(user.resume?.skills || []).map((s) => (
                        <span key={s} className="res-skill-pill">
                          {s}
                        </span>
                      ))}
                    </div>
                  </section>

                  {(user.resume?.roles || []).length > 0 && (
                    <section className="res-section">
                      <h3>WORK EXPERIENCE</h3>
                      {user.resume.roles.map((r, i) => (
                        <div key={i} className="res-role-block">
                          <div className="role-top">
                            <strong>{r.title}</strong>
                            <span className="role-meta">
                              {r.company} · {r.start || ""} - {r.end || "Present"}
                            </span>
                          </div>
                          {(r.highlights || []).length > 0 && (
                            <ul className="res-bullets">
                              {r.highlights.map((h, hi) => (
                                <li key={hi}>{h}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ))}
                    </section>
                  )}

                  {(user.resume?.projects || []).length > 0 && (
                    <section className="res-section">
                      <h3>KEY PROJECTS</h3>
                      {user.resume.projects.map((p, i) => (
                        <div key={i} className="res-role-block">
                          <div className="role-top">
                            <strong>{p.name}</strong>
                            <span className="role-meta">
                              {(p.tech || []).join(", ")}
                            </span>
                          </div>
                          <p className="res-proj-desc">{p.description}</p>
                        </div>
                      ))}
                    </section>
                  )}

                  {(user.resume?.education || []).length > 0 && (
                    <section className="res-section">
                      <h3>EDUCATION</h3>
                      {user.resume.education.map((e, i) => (
                        <div key={i} className="res-edu-row">
                          <div>
                            <strong>{e.institution}</strong>
                            <p>
                              {e.degree}
                              {e.field_of_study ? ` in ${e.field_of_study}` : ""}
                            </p>
                          </div>
                          <span className="edu-year">{e.year}</span>
                        </div>
                      ))}
                    </section>
                  )}

                  {(user.resume?.certifications || []).length > 0 && (
                    <section className="res-section">
                      <h3>CERTIFICATIONS</h3>
                      <ul className="res-bullets">
                        {user.resume.certifications.map((c, i) => (
                          <li key={i}>
                            <strong>{typeof c === "string" ? c : c.name}</strong>
                            {c.issuer ? ` (${c.issuer})` : ""}
                            {c.year ? ` — ${c.year}` : ""}
                          </li>
                        ))}
                      </ul>
                    </section>
                  )}
                </article>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
