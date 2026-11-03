import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import { CAT_COLOR, catLabel } from "./format";
import { copy } from "./i18n";
import Deck from "./screens/Deck";
import Matches from "./screens/Matches";
import Onboarding from "./screens/Onboarding";
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
  const [tab, setTab] = useState("deck");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(!loadUser());
  const lock = useRef(false);

  const lang = user?.preferred_lang || "en";
  const t = copy[lang] || copy.en;

  const refreshMatches = useCallback(async (id) => {
    setMatches(await api.matches(id));
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

  function enter(u, nextCards, nextState) {
    localStorage.setItem(STORAGE, JSON.stringify(u));
    setUser(u);
    setCards(nextCards || []);
    setState(nextState || u.search_state || { filters: {}, focus: "" });
    setReady(true);
    setError("");
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

  if (!ready && user) {
    return <div className="boot">{t.loading}</div>;
  }

  if (!user) {
    return (
      <div className="gate">
        <Onboarding meta={meta} onDone={enter} />
      </div>
    );
  }

  const selected = new Set(state.filters?.categories || []);

  return (
    <div className="shell">
      <aside className="rail">
        <p className="brand">{t.brand}</p>
        <p className="tag">{t.tag}</p>
        <div className="who">
          <strong>{user.name || "Seeker"}</strong>
          <span>{user.has_resume ? t.resumeOn : t.noResume}</span>
          {(user.resume?.domains || []).length > 0 && (
            <span className="muted">{user.resume.domains.map((d) => catLabel(meta, d)).join(" · ")}</span>
          )}
        </div>
        <h2>{t.how}</h2>
        <p className="muted">{t.howBody}</p>
        <button type="button" className="texty" onClick={signOut}>
          {t.signout}
        </button>
      </aside>

      <main className="stage">
        <header className="top">
          <div>
            <p className="brand mobile">{t.brand}</p>
            <nav>
              <button type="button" className={tab === "deck" ? "tab on" : "tab"} onClick={() => setTab("deck")}>
                {t.deck}
              </button>
              <button type="button" className={tab === "matches" ? "tab on" : "tab"} onClick={() => setTab("matches")}>
                {t.matches}
                {matches.length > 0 && <i>{matches.length}</i>}
              </button>
            </nav>
          </div>
          <button type="button" className="texty mobile" onClick={signOut}>
            {t.signout}
          </button>
        </header>

        {notice && <p className="note">{notice}</p>}
        {error && (
          <p className="error banner" onClick={() => setError("")}>
            {error}
          </p>
        )}

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

        {tab === "matches" && (
          <Matches user={user} items={matches} meta={meta} t={t} onChange={() => refreshMatches(user.id)} />
        )}
      </main>

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
    </div>
  );
}