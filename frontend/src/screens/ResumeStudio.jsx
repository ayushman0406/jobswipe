import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";

function parseClientLatex(tex) {
  if (!tex || typeof tex !== "string") return null;

  function unescapeLatex(s) {
    if (!s) return "";
    return s
      .replace(/\\&/g, "&")
      .replace(/\\%/g, "%")
      .replace(/\\\$/g, "$")
      .replace(/\\_/g, "_")
      .replace(/\\#/g, "#")
      .replace(/\\\{/g, "{")
      .replace(/\\\}/g, "}")
      .replace(/\\textasciitilde\{\}/g, "~")
      .replace(/\\textasciicircum\{\}/g, "^")
      .replace(/\\textbackslash\{\}/g, "\\");
  }

  function strip(s) {
    if (!s) return "";
    return unescapeLatex(
      s
        .replace(/%.*$/gm, "")
        .replace(/\\href\{[^}]*\}\{([^}]*)\}/g, "$1")
        .replace(/\\[a-zA-Z]+\{([^}]*)\}/g, "$1")
        .replace(/\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?/g, "")
        .replace(/\\\\/g, "\n")
    ).trim();
  }

  const result = {
    name: "",
    email: "",
    phone: "",
    location: "",
    links: {},
    summary: "",
    skills: [],
    roles: [],
    projects: [],
    education: [],
    certifications: [],
  };

  const nameMatch = tex.match(/\{\\(?:LARGE|Large|Huge)\s*\\textbf\{([^}]+)\}\}/) || tex.match(/\\textbf\{([^}]+)\}/);
  if (nameMatch) result.name = strip(nameMatch[1]);

  const emailMatch = tex.match(/mailto:([\w.-]+@[\w.-]+\.\w+)/) || tex.match(/[\w.-]+@[\w.-]+\.\w+/);
  if (emailMatch) result.email = emailMatch[1] || emailMatch[0];

  const phoneMatch = tex.match(/(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|(?:\+?91[\-\s]?)?[6-9]\d{9}/);
  if (phoneMatch) result.phone = phoneMatch[0].trim();

  const liMatch = tex.match(/\\href\{([^}]*linkedin\.com[^}]*)\}/i) || tex.match(/https?:\/\/(?:www\.)?linkedin\.com\/in\/[\w-]+/i);
  if (liMatch) result.links.linkedin = liMatch[1] || liMatch[0];

  const ghMatch = tex.match(/\\href\{([^}]*github\.com[^}]*)\}/i) || tex.match(/https?:\/\/(?:www\.)?github\.com\/[\w-]+/i);
  if (ghMatch) result.links.github = ghMatch[1] || ghMatch[0];

  const portMatch = tex.match(/\\href\{([^}]+)\}\{(?:Portfolio|Website)\}/i);
  if (portMatch) result.links.portfolio = portMatch[1];

  const sections = tex.split(/\\section\*?\{([^}]+)\}/);
  for (let i = 1; i < sections.length; i += 2) {
    const title = sections[i].toUpperCase().trim();
    const content = sections[i + 1] || "";

    if (/SUMMARY|PROFILE|OBJECTIVE/.test(title)) {
      result.summary = strip(content);
    } else if (/SKILL|COMPETENC/.test(title)) {
      const cleaned = strip(content);
      const items = [];
      const junk = new Set(["document", "article", "center", "itemize", "enumerate"]);
      cleaned.split("\n").forEach((line) => {
        const parts = line.split(/[:\-]/);
        const chunk = parts[parts.length - 1];
        chunk.split(/[,•|;]+/).forEach((token) => {
          const t = token.trim();
          if (t && !junk.has(t.toLowerCase()) && !/^\d+pt$/.test(t) && t.length > 1) {
            items.push(t);
          }
        });
      });
      result.skills = Array.from(new Set(items));
    } else if (/EXPERIENCE|WORK|EMPLOYMENT|HISTORY/.test(title)) {
      const blocks = content.split(/\\vspace\{[^}]*\}|(?=\\textbf\{[^}]+\}\s*(?:\$\|\$|\|)\s*\\textit\{)/);
      blocks.forEach((b) => {
        if (!b.trim() || b.trim().startsWith("%")) return;
        const tm = b.match(/\\textbf\{([^}]+)\}\s*(?:\$\|\$|\|)\s*\\textit\{([^}]+)\}(?:[^\\]*?\\hfill\s*([^\\]+))?/);
        const itemMatches = [...b.matchAll(/\\item\s*([^\n\\]+)/g)].map((m) => strip(m[1])).filter(Boolean);
        if (tm) {
          result.roles.push({
            title: strip(tm[1]),
            company: strip(tm[2]),
            start: strip(tm[3] || ""),
            highlights: itemMatches,
          });
        }
      });
    } else if (/PROJECT/.test(title)) {
      const blocks = content.split(/\\vspace\{[^}]*\}|(?=\\textbf\{[^}]+\}(?:\$\|\$|\||\\\\))/);
      blocks.forEach((b) => {
        if (!b.trim() || b.trim().startsWith("%")) return;
        const pm = b.match(/\\textbf\{([^}]+)\}/);
        const itemMatches = [...b.matchAll(/\\item\s*([^\n\\]+)/g)].map((m) => strip(m[1])).filter(Boolean);
        if (pm) {
          result.projects.push({
            name: strip(pm[1]),
            description: itemMatches.join(" ") || strip(b),
            highlights: itemMatches,
          });
        }
      });
    } else if (/EDUCATION/.test(title)) {
      const blocks = content.split(/\\vspace\{[^}]*\}|(?=\\textbf\{[^}]+\}\s*\\hfill)/);
      blocks.forEach((b) => {
        if (!b.trim() || b.trim().startsWith("%")) return;
        const im = b.match(/\\textbf\{([^}]+)\}(?:[^\\]*?\\hfill\s*([^\\]+))?/);
        const dm = b.match(/\\textit\{([^}]+)\}/);
        if (im) {
          result.education.push({
            institution: strip(im[1]),
            year: strip(im[2] || ""),
            degree: strip(dm ? dm[1] : ""),
          });
        }
      });
    } else if (/CERTIFICATION|ACHIEVEMENT/.test(title)) {
      const itemMatches = [...content.matchAll(/\\item\s*([^\n\\]+)/g)].map((m) => strip(m[1])).filter(Boolean);
      itemMatches.forEach((itm) => result.certifications.push({ name: itm }));
    }
  }

  return result;
}

export default function ResumeStudio({ user, t, onUpdateUser }) {
  const [ats, setAts] = useState(user.ats_score || null);
  const [latex, setLatex] = useState(user.resume_latex || "");
  const [loading, setLoading] = useState(!user.ats_score && !user.resume_latex);
  const [chatting, setChatting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [input, setInput] = useState("");
  const [activeTab, setActiveTab] = useState("preview"); // 'preview' | 'latex'
  const [copied, setCopied] = useState(false);
  const studioFileInputRef = useRef(null);

  const initialGreeting = useMemo(() => {
    if (ats?.improvements?.length) {
      const top = ats.improvements.slice(0, 3);
      const list = top.map((imp, i) => `${i + 1}. **${imp.title}**: ${imp.description}`).join("\n");
      return `Welcome! Your resume ATS score is currently **${ats.overall_score || 0}/100 (${ats.rating || "Good"})**.\n\nHere are the top areas to improve:\n${list}\n\nWhat would you like to refine? Tell me what to change or pick a prompt below!`;
    }
    return (
      t.coachGreeting ||
      "Hi! I'm your AI Resume Coach. I've analyzed your resume and generated an ATS-optimized LaTeX version. What would you like to improve?"
    );
  }, [ats?.improvements, ats?.overall_score, ats?.rating, t.coachGreeting]);

  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: initialGreeting,
      quick_prompts: (ats?.improvements || []).slice(0, 3).map((imp) => imp.prompt).length
        ? (ats?.improvements || []).slice(0, 3).map((imp) => imp.prompt)
        : [
            "Add quantifiable metrics (% & numbers) to my work experience",
            "Add missing technical skills and tools",
            "Refine executive summary for high ATS matching",
          ],
    },
  ]);

  const chatEndRef = useRef(null);

  // Sync greeting when ats loads
  useEffect(() => {
    if (ats?.improvements?.length && messages.length === 1 && messages[0].role === "assistant") {
      const top = ats.improvements.slice(0, 3);
      const list = top.map((imp, i) => `${i + 1}. **${imp.title}**: ${imp.description}`).join("\n");
      setMessages([
        {
          role: "assistant",
          content: `Welcome! Your resume ATS score is currently **${ats.overall_score || 0}/100 (${ats.rating || "Good"})**.\n\nHere are the top areas to improve:\n${list}\n\nWhat would you like to refine? Tell me what to change or pick a prompt below!`,
          quick_prompts: top.map((imp) => imp.prompt),
        },
      ]);
    }
  }, [ats?.improvements, ats?.overall_score, ats?.rating]);

  useEffect(() => {
    if (!ats || !latex) {
      setLoading(true);
      api
        .getAts(user.id)
        .then((res) => {
          if (res.ats) setAts(res.ats);
          if (res.latex) setLatex(res.latex);
          if (onUpdateUser) {
            onUpdateUser({
              ats_score: res.ats,
              resume_latex: res.latex,
              resume: res.resume || user.resume,
            });
          }
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [user.id]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chatting]);

  // Real-time client-side parsed resume for live preview
  const displayResume = useMemo(() => {
    const base = user.resume || {};
    if (!latex) return base;
    const parsed = parseClientLatex(latex);
    if (!parsed) return base;
    return {
      ...base,
      name: parsed.name || base.name || user.name,
      email: parsed.email || base.email || user.email,
      phone: parsed.phone || base.phone,
      location: parsed.location || base.location,
      summary: parsed.summary || base.summary,
      links: { ...(base.links || {}), ...(parsed.links || {}) },
      skills: parsed.skills?.length ? parsed.skills : (base.skills || []),
      roles: parsed.roles?.length ? parsed.roles : (base.roles || []),
      projects: parsed.projects?.length ? parsed.projects : (base.projects || []),
      education: parsed.education?.length ? parsed.education : (base.education || []),
      certifications: parsed.certifications?.length ? parsed.certifications : (base.certifications || []),
    };
  }, [latex, user.resume, user.name, user.email]);

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
      if (res.ats) setAts(res.ats);
      if (onUpdateUser) {
        onUpdateUser({
          ats_score: res.ats || ats,
          resume_latex: res.latex || latex,
          resume: res.resume || user.resume,
        });
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
      if (onUpdateUser) {
        onUpdateUser({
          ats_score: res.ats,
          resume_latex: latex,
          resume: res.resume || user.resume,
        });
      }
    } catch (e) {
      alert("Failed to save LaTeX: " + e.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleStudioUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const res = await api.uploadResume(user.id, file);
      if (res.ats) setAts(res.ats);
      if (res.latex) setLatex(res.latex);
      if (onUpdateUser) {
        onUpdateUser({
          has_resume: true,
          ats_score: res.ats,
          resume_latex: res.latex,
          resume: res.resume,
        });
      }
    } catch (err) {
      alert("Upload failed: " + err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
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
    a.download = `${(displayResume.name || user.name || "resume").toLowerCase().replace(/\s+/g, "_")}.tex`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  const score = ats?.overall_score ?? 0;
  const rating = ats?.rating || (latex ? "Good" : "No Resume");
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
              placeholder={t.chatPlaceholder || "Ask AI to add skills, rewrite bullets, quantify metrics…"}
              disabled={chatting}
            />
            <button type="submit" className="solid send-btn" disabled={chatting || !input.trim()}>
              Send
            </button>
          </form>
        </div>
      </section>

      {/* RIGHT COLUMN: Interactive LaTeX Editor & Live Formatted Preview */}
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
              <input
                type="file"
                ref={studioFileInputRef}
                style={{ display: "none" }}
                accept="application/pdf,.pdf"
                onChange={handleStudioUpload}
              />
              <button
                type="button"
                className="ghost-btn"
                onClick={() => studioFileInputRef.current?.click()}
                disabled={uploading}
                title="Upload PDF Resume"
              >
                {uploading ? "Parsing…" : "📤 Upload PDF"}
              </button>
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
                  placeholder="% Paste or write your LaTeX resume here..."
                />
              </div>
            ) : (
              <div className="formatted-preview">
                {/* Formatted Resume Preview */}
                <article className="resume-paper">
                  <header className="res-header">
                    <h1>{displayResume.name || "Your Name"}</h1>
                    <p className="res-contact">
                      {[
                        displayResume.email,
                        displayResume.phone,
                        displayResume.location,
                        displayResume.links?.linkedin,
                        displayResume.links?.github,
                        displayResume.links?.portfolio,
                      ]
                        .filter(Boolean)
                        .join("  •  ")}
                    </p>
                  </header>

                  {displayResume.summary && (
                    <section className="res-section">
                      <h3>PROFESSIONAL SUMMARY</h3>
                      <p className="res-summary">{displayResume.summary}</p>
                    </section>
                  )}

                  {(displayResume.skills || []).length > 0 && (
                    <section className="res-section">
                      <h3>TECHNICAL & DOMAIN SKILLS</h3>
                      <div className="res-skills-list">
                        {displayResume.skills.map((s) => (
                          <span key={s} className="res-skill-pill">
                            {s}
                          </span>
                        ))}
                      </div>
                    </section>
                  )}

                  {(displayResume.roles || []).length > 0 && (
                    <section className="res-section">
                      <h3>WORK EXPERIENCE</h3>
                      {displayResume.roles.map((r, i) => (
                        <div key={i} className="res-role-block">
                          <div className="role-top">
                            <strong>{r.title}</strong>
                            <span className="role-meta">
                              {r.company ? `${r.company} · ` : ""}{r.start || ""} {r.end ? `- ${r.end}` : ""}
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

                  {(displayResume.projects || []).length > 0 && (
                    <section className="res-section">
                      <h3>KEY PROJECTS</h3>
                      {displayResume.projects.map((p, i) => (
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

                  {(displayResume.education || []).length > 0 && (
                    <section className="res-section">
                      <h3>EDUCATION</h3>
                      {displayResume.education.map((e, i) => (
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

                  {(displayResume.certifications || []).length > 0 && (
                    <section className="res-section">
                      <h3>CERTIFICATIONS</h3>
                      <ul className="res-bullets">
                        {displayResume.certifications.map((c, i) => (
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
