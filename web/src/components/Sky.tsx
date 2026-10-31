import type { CSSProperties } from "react";

const METEORS = [
  { top: "6%", left: "34%", dur: "17s", delay: "2s" },
  { top: "16%", left: "80%", dur: "23s", delay: "9s" },
  { top: "42%", left: "58%", dur: "29s", delay: "15s" },
  { top: "64%", left: "24%", dur: "19s", delay: "6s" },
  { top: "10%", left: "96%", dur: "31s", delay: "21s" },
];

export default function Sky() {
  return (
    <div className="sky" aria-hidden="true">
      <span className="stars s1" />
      <span className="stars s2" />
      <span className="stars s3" />
      {METEORS.map((m) => (
        <span
          key={m.left}
          className="meteor"
          style={{ top: m.top, left: m.left, "--dur": m.dur, "--delay": m.delay } as CSSProperties}
        />
      ))}
    </div>
  );
}
