import { useRef, useState } from "react";
import { PAY_OPTIONS } from "../format";

export default function SearchPanel({
  t,
  lang,
  meta,
  state,
  busy,
  onBrowse,
  onRefine,
  onVoice,
  onReset,
}) {
  const [text, setText] = useState("");
  const [listening, setListening] = useState(false);
  const [micError, setMicError] = useState("");
  const recRef = useRef(null);

  const filters = state?.filters || {};
  const shifts = meta?.shifts || ["day", "night", "rotational", "flexible"];

  async function submit(e) {
    e.preventDefault();
    const q = text.trim();
    if (!q) return;
    await onRefine(q);
    setText("");
  }

  async function toggleVoice() {
    if (listening && recRef.current) {
      recRef.current.stop();
      return;
    }
    setMicError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      const chunks = [];
      rec.ondataavailable = (e) => {
        if (e.data.size) chunks.push(e.data);
      };
      rec.onstop = async () => {
        stream.getTracks().forEach((tr) => tr.stop());
        setListening(false);
        recRef.current = null;
        const blob = new Blob(chunks, { type: rec.mimeType || "audio/webm" });
        if (blob.size) await onVoice(blob);
      };
      recRef.current = rec;
      rec.start();
      setListening(true);
      window.setTimeout(() => {
        if (rec.state === "recording") rec.stop();
      }, 20000);
    } catch (e) {
      setListening(false);
      setMicError(e.message || "Microphone blocked");
    }
  }

  return (
    <section className="panel">
      <h2>{t.filters}</h2>
      <label>
        {t.city}
        <select
          value={(filters.locations || [])[0] || ""}
          onChange={(e) =>
            onBrowse({ locations: e.target.value ? [e.target.value] : [] })
          }
          disabled={busy}
        >
          <option value="">{t.anyCity}</option>
          {(meta?.cities || []).map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </label>
      <label>
        {t.shift}
        <select
          value={(filters.shifts || [])[0] || ""}
          onChange={(e) =>
            onBrowse({ shifts: e.target.value ? [e.target.value] : [] })
          }
          disabled={busy}
        >
          <option value="">{t.anyShift}</option>
          {shifts.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>
      <label>
        {t.minPay}
        <select
          value={filters.min_salary || 0}
          onChange={(e) => onBrowse({ min_salary: Number(e.target.value) })}
          disabled={busy}
        >
          {PAY_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>

      <form onSubmit={submit}>
        <label>
          {t.search}
          <textarea
            rows={3}
            value={text}
            placeholder={t.searchPh}
            onChange={(e) => setText(e.target.value)}
          />
        </label>
        <div className="row tight">
          <button
            type="submit"
            className="solid"
            disabled={busy || !text.trim()}
          >
            {t.continue}
          </button>
          <button
            type="button"
            className={listening ? "ghost hot" : "ghost"}
            onClick={toggleVoice}
            disabled={busy}
          >
            {listening ? t.listening : t.voice}
          </button>
        </div>
      </form>
      {micError && <p className="error">{micError}</p>}

      {state?.focus && (
        <p className="focus">
          <span>{t.focus}</span> {state.focus}
        </p>
      )}
      <button type="button" className="texty" onClick={onReset} disabled={busy}>
        {t.reset}
      </button>
    </section>
  );
}
