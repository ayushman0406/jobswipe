import { useEffect, useState } from "react";

const STEPS = [
  "Connecting to JobSwipe network…",
  "Scanning open roles across verified employers…",
  "Calibrating your match preferences…",
  "Shuffling the deck with top matches…",
];

export default function BootLoader({ title = "JobSwipe", subtitle }) {
  const [stepIdx, setStepIdx] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setStepIdx((i) => (i + 1) % STEPS.length);
    }, 1800);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="boot-screen" role="status" aria-live="polite">
      <div className="boot-cards" aria-hidden="true">
        <div className="boot-card card-back-2" />
        <div className="boot-card card-back-1" />
        <div className="boot-card card-front">
          <span className="boot-badge">JobSwipe</span>
          <div className="boot-avatar-row">
            <span className="boot-avatar" />
            <div className="boot-lines">
              <span className="boot-line w60" />
              <span className="boot-line w40" />
            </div>
          </div>
        </div>
      </div>

      <div className="boot-content">
        <h1 className="boot-brand">{title}</h1>
        {subtitle && <p className="boot-kicker">{subtitle}</p>}
        <p className="boot-status" key={stepIdx}>
          {STEPS[stepIdx]}
        </p>
        <div className="boot-progress" aria-hidden="true">
          <div className="boot-bar" />
        </div>
      </div>
    </div>
  );
}
