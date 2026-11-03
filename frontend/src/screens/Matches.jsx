import { useState } from "react";
import { api } from "../api";
import { CAT_COLOR, catLabel, salary } from "../format";

export default function Matches({ user, items, meta, t, onChange }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(null);

  async function accept(id) {
    setBusy(id);
    setError("");
    try {
      await api.accept(id);
      onChange();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  }

  if (!items.length) {
    return (
      <div className="empty card-face flat animate-fade-in">
        <span className="empty-icon">💌</span>
        <h2>{t.noMatches}</h2>
        <p className="muted">
          Swipe right or Superlike open roles to build mutual connections and interview invites!
        </p>
      </div>
    );
  }

  return (
    <div className="match-list">
      {error && <p className="error">{error}</p>}
      {items.map((m, idx) => (
        <article
          key={m.match_id}
          className="match animate-fade-in"
          style={{
            "--cat": CAT_COLOR[m.category] || "#444",
            animationDelay: `${idx * 50}ms`,
          }}
        >
          <header>
            <span className="pill">{catLabel(meta, m.category)}</span>
            <span className={m.status === "mutual" ? "status mutual" : "status"}>
              {m.status === "mutual" ? `✨ ${t.mutual}` : t.applied}
            </span>
          </header>
          <h2>{m.title}</h2>
          <p className="company">
            {m.company}
            {m.location ? ` · ${m.location}` : ""}
          </p>
          <p className="salary">{salary(m)}</p>
          {m.status !== "mutual" && (
            <>
              <button type="button" className="ghost" disabled={busy === m.match_id} onClick={() => accept(m.match_id)}>
                {t.accept}
              </button>
              <p className="muted tiny">{t.dev}</p>
            </>
          )}
          {(m.next_steps || []).length > 0 && (
            <>
              <p className="kicker">{t.next}</p>
              <ol className="steps-list">
                {m.next_steps.map((s) => (
                  <li key={s.kind + s.title}>
                    <strong>{s.title}</strong>
                    {s.detail && <span>{s.detail}</span>}
                    {s.url && (
                      <a href={s.url} target="_blank" rel="noreferrer">
                        {t.meet}
                      </a>
                    )}
                  </li>
                ))}
              </ol>
            </>
          )}
          {m.meet_url && !(m.next_steps || []).some((s) => s.url) && (
            <a href={m.meet_url} target="_blank" rel="noreferrer">
              {t.meet}
            </a>
          )}
        </article>
      ))}
    </div>
  );
}