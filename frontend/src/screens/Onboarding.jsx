import { useState } from "react";
import { api } from "../api";
import { CAT_COLOR } from "../format";
import { copy } from "../i18n";

export default function Onboarding({ meta, onDone }) {
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [lang, setLang] = useState("en");
  const [cats, setCats] = useState([]);
  const [city, setCity] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const t = copy[lang] || copy.en;

  const categories = meta?.categories || [];

  function toggle(slug) {
    setCats((cur) => (cur.includes(slug) ? cur.filter((c) => c !== slug) : [...cur, slug]));
  }

  async function finish() {
    setBusy(true);
    setError("");
    try {
      const user = await api.createUser({ name: name.trim(), email: email.trim(), preferred_lang: lang });
      if (file) await api.uploadResume(user.id, file);
      const body = {};
      if (cats.length) body.categories = cats;
      if (city) body.locations = [city];
      const deck = await api.browse(user.id, body);
      onDone({ ...user, has_resume: Boolean(file), search_state: deck.state }, deck.cards, deck.state);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="onboard">
      <p className="eyebrow">JobSwipe</p>
      <h1>{step === 0 ? t.hello : step === 1 ? t.pick : t.resumeTitle}</h1>
      <p className="lede">{step === 0 ? t.helloHint : step === 1 ? t.pickHint : t.resumeHint}</p>
      <div className="steps" aria-hidden="true">
        {[0, 1, 2].map((n) => (
          <span key={n} className={n <= step ? "on" : ""} />
        ))}
      </div>

      {step === 0 && (
        <div className="form">
          <label>
            {t.name}
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Himanshu" autoFocus />
          </label>
          <label>
            {t.email}
            <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@email.com" />
          </label>
          <label>
            {t.lang}
            <select value={lang} onChange={(e) => setLang(e.target.value)}>
              <option value="en">English</option>
              <option value="hi">हिन्दी</option>
              <option value="kn">ಕನ್ನಡ</option>
            </select>
          </label>
        </div>
      )}

      {step === 1 && (
        <div className="cat-grid">
          {categories.map((c) => (
            <button
              key={c.slug}
              type="button"
              className={cats.includes(c.slug) ? "cat on" : "cat"}
              style={{ "--cat": CAT_COLOR[c.slug] || "#444" }}
              onClick={() => toggle(c.slug)}
            >
              <strong>{c.label}</strong>
              <span>{c.blurb}</span>
            </button>
          ))}
          {!categories.length && <p className="muted">{t.unseeded}</p>}
        </div>
      )}

      {step === 2 && (
        <div className="form">
          <label>
            {t.city}
            <select value={city} onChange={(e) => setCity(e.target.value)}>
              <option value="">{t.anyCity}</option>
              {(meta?.cities || []).map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <label className="file">
            {t.upload}
            <input
              type="file"
              accept="application/pdf,.pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            <em>{file ? file.name : "PDF"}</em>
          </label>
        </div>
      )}

      {error && <p className="error">{error}</p>}

      <div className="row">
        {step > 0 && (
          <button type="button" className="ghost" onClick={() => setStep((s) => s - 1)} disabled={busy}>
            {t.back}
          </button>
        )}
        {step < 2 && (
          <button
            type="button"
            className="solid"
            disabled={step === 0 && !name.trim()}
            onClick={() => setStep((s) => s + 1)}
          >
            {t.continue}
          </button>
        )}
        {step === 2 && (
          <button
            type="button"
            className="solid"
            disabled={busy || (!file && cats.length === 0)}
            onClick={finish}
          >
            {busy ? t.loading : t.start}
          </button>
        )}
      </div>
    </div>
  );
}