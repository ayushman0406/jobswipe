import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { CAT_COLOR, catLabel, salary } from "../format";

export default function Deck({ user, cards, meta, t, busy, onSwipe }) {
  const [why, setWhy] = useState(null);
  const [whyFor, setWhyFor] = useState(null);
  const [whyError, setWhyError] = useState("");
  const [whyBusy, setWhyBusy] = useState(false);
  const [swipeCmd, setSwipeCmd] = useState(null);

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

  function handleActionClick(action) {
    if (busy || !top || swipeCmd) return;
    setSwipeCmd({ action, id: top.job_id });
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
        {busy && cards.length === 0 && (
          <div className="empty card-face skeleton-face">
            <div className="skel-banner shimmer" />
            <div className="skel-body">
              <div className="skel-line w80 shimmer" />
              <div className="skel-line w50 shimmer" />
              <div className="skel-line w100 shimmer" />
              <div className="skel-line w70 shimmer" />
            </div>
            <p className="loading-hint">{t.loading}</p>
          </div>
        )}
        {cards.slice(0, 3).map((job, i) => (
          <SwipeCard
            key={job.job_id}
            job={job}
            index={i}
            active={i === 0 && !busy}
            meta={meta}
            t={t}
            programmaticAction={i === 0 && swipeCmd?.id === job.job_id ? swipeCmd.action : null}
            onGone={(action) => {
              setSwipeCmd(null);
              onSwipe(action);
            }}
            onWhy={() => openWhy(job)}
          />
        ))}
      </div>
      {top && (
        <div className="actions">
          <button
            type="button"
            className="act pass"
            onClick={() => handleActionClick("pass")}
            disabled={busy || Boolean(swipeCmd)}
            aria-label={t.pass}
          >
            <span className="act-icon">✕</span>
            <span>{t.pass}</span>
          </button>
          <button
            type="button"
            className="act super"
            onClick={() => handleActionClick("superlike")}
            disabled={busy || Boolean(swipeCmd)}
            aria-label={t.super}
          >
            <span className="act-icon">★</span>
            <span>{t.super}</span>
          </button>
          <button
            type="button"
            className="act like"
            onClick={() => handleActionClick("like")}
            disabled={busy || Boolean(swipeCmd)}
            aria-label={t.like}
          >
            <span className="act-icon">♥</span>
            <span>{t.like}</span>
          </button>
        </div>
      )}
      {whyFor && (
        <div className="sheet-back" onClick={() => setWhyFor(null)}>
          <div className="sheet" onClick={(e) => e.stopPropagation()}>
            <div className="sheet-top">
              <div>
                <span className="pill-small" style={{ "--cat": CAT_COLOR[whyFor.category] || "#444" }}>
                  {catLabel(meta, whyFor.category)}
                </span>
                <h3>{whyFor.title}</h3>
                <p className="company">{whyFor.company}</p>
              </div>
              <button type="button" className="ghost" onClick={() => setWhyFor(null)}>
                {t.close}
              </button>
            </div>
            {whyBusy && (
              <div className="why-skel-wrap">
                <div className="skel-line w80 shimmer" />
                <div className="skel-line w100 shimmer" />
                <div className="skel-line w60 shimmer" />
              </div>
            )}
            {whyError && (
              <div className="why-error-row">
                <p className="error">{whyError}</p>
                <button type="button" className="ghost retry-btn" onClick={() => openWhy(whyFor)}>
                  ↺ {t.retry || "Retry"}
                </button>
              </div>
            )}
            {why?.coach_error && <p className="muted">{why.coach_error}</p>}
            {why && !whyBusy && (
              <>
                {(why.why || []).length > 0 && (
                  <ul className="why-list">
                    {why.why.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                )}
                {why.tip && <p className="tip">💡 {why.tip}</p>}
                <p className="kicker">{t.fits}</p>
                <div className="chips">
                  {(why.matched_skills || []).length ? (
                    why.matched_skills.map((s) => (
                      <span key={s} className="chip good">
                        ✓ {s}
                      </span>
                    ))
                  ) : (
                    <span className="muted">—</span>
                  )}
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

function SwipeCard({ job, index, active, meta, t, programmaticAction, onGone, onWhy }) {
  const drag = useRef(null);
  const gone = useRef(false);
  const [pos, setPos] = useState({ x: 0, y: 0, fly: false, resetting: false });
  const [photoLoaded, setPhotoLoaded] = useState(false);

  useEffect(() => {
    if (!active) return undefined;
    function onKey(e) {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.isContentEditable) return;
      if (e.key === "ArrowLeft") fly("pass");
      if (e.key === "ArrowRight") fly("like");
      if (e.key === "ArrowUp") fly("superlike");
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, job.job_id]);

  useEffect(() => {
    if (programmaticAction && active) {
      fly(programmaticAction);
    }
  }, [programmaticAction, active]);

  function fly(action) {
    if (gone.current) return;
    gone.current = true;
    const x = action === "pass" ? -560 : action === "like" ? 560 : 0;
    const y = action === "superlike" ? -640 : 30;
    setPos({ x, y, fly: true, resetting: false });
    window.setTimeout(() => onGone(action), 220);
  }

  function down(e) {
    if (!active || drag.current) return;
    drag.current = {
      pid: e.pointerId,
      sx: e.clientX,
      sy: e.clientY,
      x: 0,
      y: 0,
      startTime: Date.now(),
    };
    setPos((p) => ({ ...p, resetting: false }));
    e.currentTarget.setPointerCapture(e.pointerId);
  }

  function move(e) {
    if (!drag.current || drag.current.pid !== e.pointerId) return;
    const rawX = e.clientX - drag.current.sx;
    const rawY = e.clientY - drag.current.sy;
    // Downward drag gets elastic damping
    const y = rawY > 0 ? rawY * 0.45 : rawY;
    const x = rawX;
    drag.current.x = x;
    drag.current.y = y;
    setPos({ x, y, fly: false, resetting: false });
  }

  function up(e) {
    if (!drag.current || drag.current.pid !== e.pointerId) return;
    const { x, y, startTime } = drag.current;
    const timeTaken = Math.max(1, Date.now() - (startTime || Date.now()));
    const velX = Math.abs(x) / timeTaken;
    const velY = Math.abs(y) / timeTaken;
    drag.current = null;

    // Velocity-based flick (>0.22 px/ms) or distance thresholds
    if ((y < -110 || (y < -50 && velY > 0.22)) && Math.abs(x) < 90) {
      fly("superlike");
    } else if (x > 110 || (x > 45 && velX > 0.22)) {
      fly("like");
    } else if (x < -110 || (x < -45 && velX > 0.22)) {
      fly("pass");
    } else {
      // Responsive spring return
      setPos({ x: 0, y: 0, fly: false, resetting: true });
    }
  }

  const color = CAT_COLOR[job.category] || "#444";
  const rot = (pos.x / 16) * (1 - Math.min(0.4, Math.abs(pos.x) / 1000));
  const stack = index === 0 ? "" : `translateY(${index * 12}px) scale(${1 - index * 0.045})`;
  const transform = index === 0 ? `translate(${pos.x}px, ${pos.y}px) rotate(${rot}deg)` : stack;

  // Dynamic stamp feedback based on drag position
  const likeOpacity = index === 0 ? Math.min(1, Math.max(0, (pos.x - 20) / 70)) : 0;
  const passOpacity = index === 0 ? Math.min(1, Math.max(0, (-pos.x - 20) / 70)) : 0;
  const superOpacity = index === 0 && Math.abs(pos.x) < 70 ? Math.min(1, Math.max(0, (-pos.y - 30) / 70)) : 0;

  return (
    <article
      className={`card-face ${pos.fly ? "fly" : ""} ${pos.resetting ? "resetting" : ""}`}
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
      {/* 1. Curated photo banner & hiring overlay */}
      <div className="card-photo-banner">
        {!photoLoaded && <div className="skel-banner shimmer card-photo-skel" />}
        <img
          src={job.photo_url || "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=800&q=80"}
          alt={job.title}
          className={`card-photo ${photoLoaded ? "loaded" : "loading"}`}
          loading="lazy"
          onLoad={() => setPhotoLoaded(true)}
          onError={(e) => {
            setPhotoLoaded(true);
            e.currentTarget.src = "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=800&q=80";
          }}
        />
        <div className="photo-scrim" />
        <div className="photo-badge">✨ {t.weAreHiring}</div>
        <div className="photo-match-badge">{job.match_pct}% match</div>
      </div>

      {/* 2. Company Identity & Monogram */}
      <div className="company-invite-row">
        <img
          src={job.company_logo || `https://ui-avatars.com/api/?name=${encodeURIComponent(job.company || "Co")}&background=1c1612&color=fffdf8&bold=true&size=128`}
          alt={job.company}
          className="company-logo"
          onError={(e) => {
            e.currentTarget.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(job.company || "Co")}&background=1c1612&color=fffdf8&bold=true&size=128`;
          }}
        />
        <div className="company-details">
          <div className="company-name-row">
            <span className="company-name">{job.company}</span>
            <span className="verified-badge" title="Verified Company">✓</span>
          </div>
          <span className="pill-small" style={{ "--cat": color }}>
            {catLabel(meta, job.category)}
          </span>
        </div>
      </div>

      {/* 3. Company hiring invitation quote */}
      {job.hiring_quote && (
        <div className="hiring-callout">
          <span className="hiring-icon">👋</span>
          <p className="hiring-text">“{job.hiring_quote}”</p>
        </div>
      )}

      {/* 4. Role Title & Compensation */}
      <h2 className="job-title">{job.title}</h2>
      <p className="salary">{salary(job)}</p>

      {/* 5. Key Facts Tags */}
      <ul className="facts">
        <li>
          {job.location}
          {job.remote ? " · remote" : ""}
        </li>
        {job.shift && <li>{job.shift}</li>}
        <li>{job.employment_type}</li>
        {job.education && <li>{job.education}</li>}
        <li>
          {job.openings} {t.openings}
        </li>
        {job.industry && <li>{job.industry}</li>}
      </ul>

      {/* 6. Description */}
      <p className="desc">{job.description}</p>

      {/* 7. Skills Chips */}
      <div className="chips">
        {(job.skills || []).slice(0, 6).map((s) => (
          <span key={s} className={job.matched_skills?.includes(s) ? "chip good" : "chip"}>
            {s}
          </span>
        ))}
      </div>

      {/* 8. Benefits & Languages */}
      {(job.benefits || []).length > 0 && <p className="benefits">{job.benefits.join(" · ")}</p>}
      {(job.languages || []).length > 0 && <p className="langs">{job.languages.join(" · ")}</p>}

      {/* 9. Why fit button */}
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

      {/* 10. Dynamic Tactile Stamp Feedback */}
      {index === 0 && likeOpacity > 0 && (
        <span
          className="stamp like"
          style={{
            opacity: likeOpacity,
            transform: `rotate(12deg) scale(${0.88 + 0.16 * likeOpacity})`,
          }}
        >
          {t.like}
        </span>
      )}
      {index === 0 && passOpacity > 0 && (
        <span
          className="stamp pass"
          style={{
            opacity: passOpacity,
            transform: `rotate(-12deg) scale(${0.88 + 0.16 * passOpacity})`,
          }}
        >
          {t.pass}
        </span>
      )}
      {index === 0 && superOpacity > 0 && (
        <span
          className="stamp super"
          style={{
            opacity: superOpacity,
            transform: `scale(${0.88 + 0.16 * superOpacity})`,
          }}
        >
          {t.super}
        </span>
      )}
    </article>
  );
}