import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import BootLoader from "./components/BootLoader";
import { CAT_COLOR, catLabel } from "./format";
import { copy } from "./i18n";
import Deck from "./screens/Deck";
import Matches from "./screens/Matches";
import Onboarding from "./screens/Onboarding";
import ResumeStudio from "./screens/ResumeStudio";
import SearchPanel from "./screens/SearchPanel";

const STORAGE = "jobswipe_user";

function loadUser() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE) || "null");
  } catch {
    return null;
  }
}

export default function App() {
  const [user, setUser] = useState(loadUser);
  const [meta, setMeta] = useState(null);
  const [cards, setCards] = useState([]);
  const [state, setState] = useState({ filters: {}, focus: "" });
  const [matches, setMatches] = useState([]);
  const [tab, setTab] = useState("deck"); // 'deck' | 'matches' | 'resume'
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(!loadUser());
  const [showAtsPrompt, setShowAtsPrompt] = useState(false);
  const lock = useRef(false);
  const fileInputRef = useRef(null);

  const lang = user?.preferred_lang || "en";
  const t = copy[lang] || copy.en;

  const refreshMatches = useCallback(async (id) => {
    try {
      setMatches(await api.matches(id));
    } catch {}
  }, []);

  useEffect(() => {
    api.meta().then(setMeta).catch(() => {});
  }, []);

  useEffect(() => {
    if (!user?.id) return undefined;
    let cancel = false;
    (async () => {
      try {
        const u = await api.getUser(user.id);
        if (cancel) return;
        const next = { ...user, ...u };
        setUser(next);
        localStorage.setItem(STORAGE, JSON.stringify(next));
        try {
          const feed = await api.feed(u.id, 15);
          if (!cancel) {
            setCards(feed.cards || []);
            setState(feed.state || { filters: {}, focus: "" });
          }
        } catch (e) {
          if (e.status !== 409) throw e;
        }
        if (!cancel) await refreshMatches(u.id);
      } catch (e) {
        if (e.status === 404) {
          localStorage.removeItem(STORAGE);
          setUser(null);
        } else if (!cancel) setError(e.message);
      } finally {
        if (!cancel) setReady(true);
      }
    })();
    return () => {
      cancel = true;
    };
  }, [user?.id]);

  function enter(u, nextCards, nextState, atsData) {
    localStorage.setItem(STORAGE, JSON.stringify(u));
    setUser(u);
    setCards(nextCards || []);
    setState(nextState || u.search_state || { filters: {}, focus: "" });
    setReady(true);
    setError("");
    if (atsData || u.ats_score) {
      setShowAtsPrompt(true);
    }
  }

  function signOut() {
    localStorage.removeItem(STORAGE);
    setUser(null);
    setCards([]);
    setMatches([]);
    setState({ filters: {}, focus: "" });
    setTab("deck");
  }

  async function browse(patch) {
    setBusy(true);
    setError("");
    try {
      const data = await api.browse(user.id, patch);
      setCards(data.cards || []);
      setState(data.state);
      setNotice("");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function toggleCategory(slug) {
    const current = new Set(state.filters?.categories || []);
    if (current.has(slug)) current.delete(slug);
    else current.add(slug);
    await browse({ categories: [...current] });
  }

  async function refine(text) {
    setBusy(true);
    setError("");
    try {
      const data = await api.refine(user.id, text);
      setCards(data.cards || []);
      setState(data.state);
      setNotice("");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function voice(blob) {
    setBusy(true);
    setError("");
    try {
      const data = await api.voice(user.id, blob, user.preferred_lang);
      setCards(data.cards || []);
      setState(data.state);
      setNotice(data.transcript ? `“${data.transcript}”` : "");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function reset() {
    setBusy(true);
    setError("");
    try {
      const data = await api.resetSearch(user.id);
      setCards(data.cards || []);
      setState(data.state);
      setNotice("");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function swipe(action) {
    if (lock.current) return;
    const card = cards[0];
    if (!card) return;
    lock.current = true;
    setBusy(true);
    setError("");
    setCards((cs) => cs.slice(1));
    try {
      const res = await api.swipe(user.id, card.job_id, action);
      if (res.match_id) refreshMatches(user.id);
    } catch (e) {
      setCards((cs) => [card, ...cs.filter((c) => c.job_id !== card.job_id)]);
      setError(e.message);
      lock.current = false;
      setBusy(false);
      return;
    }
    try {
      const feed = await api.feed(user.id, 15);
      setCards(feed.cards || []);
      setState(feed.state || state);
    } catch (e) {
      if (e.status !== 409) setError(e.message);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }

  async function handleSidebarResumeUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const res = await api.uploadResume(user.id, file);
      const next = {
        ...user,
        has_resume: true,
        resume_json: res.resume,
        ats_score: res.ats,
        resume_latex: res.latex,
      };
      setUser(next);
      localStorage.setItem(STORAGE, JSON.stringify(next));
      setShowAtsPrompt(true);
      // Refresh feed with new resume embeddings
      const feed = await api.feed(user.id, 15);
      setCards(feed.cards || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  }

  if (!ready && user) {
    return <BootLoader title={t.brand} subtitle={t.loadingProgress} />;
  }

  if (!user) {
    return (
      <div className="gate">
        <Onboarding meta={meta} onDone={enter} />
      </div>
    );
  }

  const selected = new Set(state.filters?.categories || []);
  const atsScore = user.ats_score?.overall_score;

  return (
    <div className="shell">
      {/* LEFT RAIL: Candidate Profile & ATS Indicator */}
      <aside className="rail">
        <p className="brand">{t.brand}</p>
        <p className="tag">{t.tag}</p>

        <div className="who">
          <strong>{user.name || "Seeker"}</strong>
          <span>{user.has_resume ? t.resumeOn : t.noResume}</span>
          {(user.resume?.domains || []).length > 0 && (
            <span className="muted">
              {user.resume.domains.map((d) => catLabel(meta, d)).join(" · ")}
            </span>
          )}
        </div>

        {/* ATS Resume Quick Card */}
        <div className="rail-ats-card">
          <div className="rail-ats-top">
            <span className="rail-ats-tag">{t.atsScore}</span>
            <span className="rail-ats-val">{atsScore ? `${atsScore}/100` : "Ready to check"}</span>
          </div>
          <button
            type="button"
            className="rail-ats-btn"
            onClick={() => setTab("resume")}
          >
            ✨ {t.improveResume}
          </button>
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: "none" }}
            accept="application/pdf,.pdf"
            onChange={handleSidebarResumeUpload}
          />
          <button
            type="button"
            className="rail-upload-link"
            onClick={() => fileInputRef.current?.click()}
            disabled={busy}
          >
            {user.has_resume ? "Update Resume PDF" : "Upload Resume PDF"}
          </button>
        </div>

        <h2>{t.how}</h2>
        <p className="muted">{t.howBody}</p>

        <button type="button" className="texty" onClick={signOut}>
          {t.signout}
        </button>
      </aside>

      {/* CENTER STAGE: Navigation, Feed, Matches, or Resume Studio */}
      <main className="stage">
        <header className="top">
          <div>
            <p className="brand mobile">{t.brand}</p>
            <nav className="main-nav">
              <button
                type="button"
                className={tab === "deck" ? "tab on" : "tab"}
                onClick={() => setTab("deck")}
              >
                🃏 {t.deck}
              </button>
              <button
                type="button"
                className={tab === "matches" ? "tab on" : "tab"}
                onClick={() => setTab("matches")}
              >
                ❤️ {t.matches}
                {matches.length > 0 && <i>{matches.length}</i>}
              </button>
              <button
                type="button"
                className={tab === "resume" ? "tab on" : "tab"}
                onClick={() => setTab("resume")}
              >
                📄 {t.resumeStudio}
                {atsScore && <span className="tab-score-pill">{atsScore}</span>}
              </button>
            </nav>
          </div>
          <button type="button" className="texty mobile" onClick={signOut}>
            {t.signout}
          </button>
        </header>

        {notice && <p className="note animate-fade-in">{notice}</p>}
        {error && (
          <p className="error banner animate-slide-down" onClick={() => setError("")}>
            {error}
          </p>
        )}

        {/* 1. DECK TAB */}
        {tab === "deck" && (
          <>
            <div className="chip-row" aria-label={t.categories}>
              {(meta?.categories || []).map((c) => (
                <button
                  key={c.slug}
                  type="button"
                  className={selected.has(c.slug) ? "chip-btn on" : "chip-btn"}
                  style={{ "--cat": CAT_COLOR[c.slug] || "#444" }}
                  onClick={() => toggleCategory(c.slug)}
                  disabled={busy}
                >
                  {c.label}
                  <small>{c.count || 0}</small>
                </button>
              ))}
            </div>
            <Deck user={user} cards={cards} meta={meta} t={t} busy={busy} onSwipe={swipe} />
          </>
        )}

        {/* 2. MATCHES TAB */}
        {tab === "matches" && (
          <Matches
            user={user}
            items={matches}
            meta={meta}
            t={t}
            onChange={() => refreshMatches(user.id)}
          />
        )}

        {/* 3. RESUME STUDIO & ATS TAB */}
        {tab === "resume" && (
          <ResumeStudio
            user={user}
            t={t}
            onUpdateUser={(patch) => {
              const next = { ...user, ...patch };
              setUser(next);
              localStorage.setItem(STORAGE, JSON.stringify(next));
            }}
          />
        )}
      </main>

      {/* RIGHT RAIL: Search & Narrowing Filters */}
      <aside className="rail filters">
        <SearchPanel
          t={t}
          lang={lang}
          meta={meta}
          state={state}
          busy={busy}
          onBrowse={browse}
          onRefine={refine}
          onVoice={voice}
          onReset={reset}
        />
      </aside>

      {/* ATS SCORE PROMPT MODAL (When resume is uploaded) */}
      {showAtsPrompt && user?.ats_score && (
        <div className="sheet-back" onClick={() => setShowAtsPrompt(false)}>
          <div className="sheet ats-modal-sheet" onClick={(e) => e.stopPropagation()}>
            <div className="sheet-top">
              <h3>Resume ATS Analysis</h3>
              <button type="button" className="ghost" onClick={() => setShowAtsPrompt(false)}>
                ✕
              </button>
            </div>

            <div className="ats-prompt-body">
              <div className="ats-prompt-score-row">
                <div className="score-badge-circle">
                  <span className="big-score">{user.ats_score.overall_score}</span>
                  <span className="denom">/100</span>
                </div>
                <div className="score-status-text">
                  <strong>ATS Compatibility: {user.ats_score.rating}</strong>
                  <p className="muted tiny">
                    Automated Applicant Tracking Systems scan for keywords, metrics, and clean formatting.
                  </p>
                </div>
              </div>

              <p className="ats-prompt-question">
                <strong>{t.askToImprovePrompt}</strong>
              </p>

              {(user.ats_score.improvements || []).length > 0 && (
                <div className="prompt-improvements-box">
                  <span className="box-title">Potential Improvements:</span>
                  <ul>
                    {user.ats_score.improvements.slice(0, 3).map((imp, idx) => (
                      <li key={idx}>
                        <strong>{imp.title}:</strong> {imp.description}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="row ats-prompt-actions">
                <button
                  type="button"
                  className="solid"
                  onClick={() => {
                    setShowAtsPrompt(false);
                    setTab("resume");
                  }}
                >
                  ✨ {t.yesImprove}
                </button>
                <button
                  type="button"
                  className="ghost"
                  onClick={() => {
                    setShowAtsPrompt(false);
                    setTab("deck");
                  }}
                >
                  {t.maybeLater}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}