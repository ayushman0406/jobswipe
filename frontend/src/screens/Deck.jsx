import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { CAT_COLOR, catLabel, salary } from "../format";

export default function Deck({ user, cards, meta, t, busy, onSwipe }) {
  const [why, setWhy] = useState(null);
  const [whyFor, setWhyFor] = useState(null);
  const [whyError, setWhyError] = useState("");
  const [whyBusy, setWhyBusy] = useState(false);

  async function openWhy(job) {
    setWhyFor(job);
    setWhy(null);
    setWhyError("");
    setWhyBusy(true);
    try {
      setWhy(await api.why(user.id, job.job_id));
    } catch (e) {
      setWhyError(e.message);
    } finally {
      setWhyBusy(false);
    }
  }

  const top = cards[0];

  return (
    <div className="deck">
      <div className="stack">
        {cards.length === 0 && !busy && (
          <div className="empty card-face">
            <h2>{t.empty}</h2>
            {meta && meta.jobs === 0 && <p>{t.unseeded}</p>}
          </div>
        )}
        {busy && cards.length === 0 && <div className="empty card-face">{t.loading}</div>}
        {cards.slice(0, 3).map((job, i) => (
          <SwipeCard
            key={job.job_id}
            job={job}
            index={i}
            active={i === 0 && !busy}
            meta={meta}
            t={t}
            onGone={(action) => onSwipe(action)}
            onWhy={() => openWhy(job)}
          />
        ))}
      </div>
      {top && (
        <div className="actions">
          <button type="button" className="act pass" onClick={() => onSwipe("pass")} disabled={busy}>
            {t.pass}
          </button>
          <button type="button" className="act super" onClick={() => onSwipe("superlike")} disabled={busy}>
            {t.super}
          </button>
          <button type="button" className="act like" onClick={() => onSwipe("like")} disabled={busy}>
            {t.like}
          </button>
        </div>
      )}
      {whyFor && (
        <div className="sheet-back" onClick={() => setWhyFor(null)}>
          <div className="sheet" onClick={(e) => e.stopPropagation()}>
            <div className="sheet-top">
              <h3>{whyFor.title}</h3>
              <button type="button" className="ghost" onClick={() => setWhyFor(null)}>
                {t.close}
              </button>
            </div>
            {whyBusy && <p className="muted">{t.loading}</p>}
            {whyError && <p className="error">{whyError}</p>}
            {why?.coach_error && <p className="muted">{why.coach_error}</p>}
            {why && (
              <>
                {(why.why || []).length > 0 && (
                  <ul className="why-list">
                    {why.why.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                )}
                {why.tip && <p className="tip">{why.tip}</p>}
                <p className="kicker">{t.fits}</p>
                <div className="chips">
                  {(why.matched_skills || []).length
                    ? why.matched_skills.map((s) => (
                        <span key={s} className="chip good">
                          {s}
                        </span>
                      ))
                    : <span className="muted">—</span>}
                </div>
                <p className="kicker">{t.missing}</p>
                <div className="chips">
                  {(why.gaps || []).map((s) => (
                    <span key={s} className="chip">
                      {s}
                    </span>
                  ))}
                  {(why.missing_skills || []).slice(0, 6).map((s) => (
                    <span key={s} className="chip">
                      {s}
                    </span>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function SwipeCard({ job, index, active, meta, t, onGone, onWhy }) {
  const drag = useRef(null);
  const gone = useRef(false);
  const [pos, setPos] = useState({ x: 0, y: 0, fly: false });

  useEffect(() => {
    if (!active) return undefined;
    function onKey(e) {
      if (e.key === "ArrowLeft") fly("pass");
      if (e.key === "ArrowRight") fly("like");
      if (e.key === "ArrowUp") fly("superlike");
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, job.job_id]);

  function fly(action) {
    if (gone.current) return;
    gone.current = true;
    const x = action === "pass" ? -560 : action === "like" ? 560 : 0;
    const y = action === "superlike" ? -640 : 30;
    setPos({ x, y, fly: true });
    window.setTimeout(() => onGone(action), 200);
  }

  function down(e) {
    if (!active) return;
    drag.current = { pid: e.pointerId, sx: e.clientX, sy: e.clientY, x: 0, y: 0 };
    e.currentTarget.setPointerCapture(e.pointerId);
  }
  function move(e) {
    if (!drag.current || drag.current.pid !== e.pointerId) return;
    const x = e.clientX - drag.current.sx;
    const y = e.clientY - drag.current.sy;
    drag.current.x = x;
    drag.current.y = y;
    setPos({ x, y, fly: false });
  }
  function up(e) {
    if (!drag.current || drag.current.pid !== e.pointerId) return;
    const { x, y } = drag.current;
    drag.current = null;
    if (y < -120 && Math.abs(x) < 90) fly("superlike");
    else if (x > 120) fly("like");
    else if (x < -120) fly("pass");
    else setPos({ x: 0, y: 0, fly: false });
  }

  const color = CAT_COLOR[job.category] || "#444";
  const rot = pos.x / 18;
  const stack = index === 0 ? "" : `translateY(${index * 12}px) scale(${1 - index * 0.045})`;
  const transform = index === 0 ? `translate(${pos.x}px, ${pos.y}px) rotate(${rot}deg)` : stack;

  return (
    <article
      className={pos.fly ? "card-face fly" : "card-face"}
      style={{
        zIndex: 30 - index,
        transform,
        "--cat": color,
        pointerEvents: index === 0 ? "auto" : "none",
      }}
      onPointerDown={down}
      onPointerMove={move}
      onPointerUp={up}
      onPointerCancel={up}
    >
      <header className="card-top">
        <span className="pill">{catLabel(meta, job.category)}</span>
        <span className="match">{job.match_pct}%</span>
      </header>
      <h2>{job.title}</h2>
      <p className="company">{job.company}</p>
      <p className="salary">{salary(job)}</p>
      <ul className="facts">
        <li>{job.location}{job.remote ? " · remote" : ""}</li>
        {job.shift && <li>{job.shift}</li>}
        <li>{job.employment_type}</li>
        {job.education && <li>{job.education}</li>}
        <li>
          {job.openings} {t.openings}
        </li>
        {job.industry && <li>{job.industry}</li>}
      </ul>
      <p className="desc">{job.description}</p>
      <div className="chips">
        {(job.skills || []).slice(0, 6).map((s) => (
          <span key={s} className={job.matched_skills?.includes(s) ? "chip good" : "chip"}>
            {s}
          </span>
        ))}
      </div>
      {(job.benefits || []).length > 0 && (
        <p className="benefits">{job.benefits.join(" · ")}</p>
      )}
      {(job.languages || []).length > 0 && (
        <p className="langs">{job.languages.join(" · ")}</p>
      )}
      <button
        type="button"
        className="why"
        onPointerDown={(e) => e.stopPropagation()}
        onClick={(e) => {
          e.stopPropagation();
          onWhy();
        }}
      >
        {t.why}
      </button>
      {index === 0 && Math.abs(pos.x) > 40 && (
        <span className={pos.x > 0 ? "stamp like" : "stamp pass"}>{pos.x > 0 ? t.like : t.pass}</span>
      )}
    </article>
  );
}