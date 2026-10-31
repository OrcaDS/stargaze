import type { CSSProperties } from "react";
import { type Damage, FILTERS, lost, lostList, type Reading, type SkyObject, sureWord, typoValue } from "../data";

type Kind = "ordinary" | "stargaze";

const ABOUT: Record<Kind, [string, string]> = {
  ordinary: ["Ordinary model", "Learned only from clean, complete measurements. A fair, normally trained model."],
  stargaze: ["Stargaze", "The same kind of model, also practised on damaged copies, and allowed to say “Not sure”."],
};

function note(kind: Kind, obj: SkyObject, d: Damage, ready: boolean) {
  const mc = lostList(d).length;
  const v = d.typo >= 0 ? typoValue(obj, d.typo) : "";
  if (kind === "ordinary") {
    if (d.typo >= 0) return `The input check blanked ${v}. It was never taught what a gap means.`;
    if (mc) return `${mc} empty slot${mc > 1 ? "s" : ""}. It was never taught what that means.`;
    return d.noise ? "Takes every wobbly number as exact." : "Reads every measurement, as given.";
  }
  if (!ready) return "Checking what it got…";
  if (d.typo >= 0) return `The input check blanked ${v}. It practised with gaps.`;
  if (mc) return `Noticed ${mc} missing. It practised with gaps.`;
  return d.noise ? "Knows the readings are shaky: it practised on shaky copies." : "All measurements look possible.";
}

export default function Reader({
  kind,
  reading,
  obj,
  damage,
  truth,
  ready,
}: {
  kind: Kind;
  reading: Reading;
  obj: SkyObject;
  damage: Damage;
  truth: string;
  ready: boolean;
}) {
  const [name, blurb] = ABOUT[kind];
  const not = reading.label === "Not sure";
  const right = !not && reading.label === truth;
  const wrong = !not && !right;
  const sure = reading.conf >= 0.85;
  // Needle: a three-way answer's top share runs from 1/3 (pure guess) to 1 (certain).
  const t = ready ? Math.max(0, (reading.conf - 1 / 3) / (2 / 3)) : 0;
  return (
    <article
      className={`reader flex flex-col gap-3.5 rounded-[22px] border bg-card p-5 transition-[border-color,box-shadow] duration-400 ${
        ready && wrong && sure ? "danger" : kind === "stargaze" ? "border-acc/55" : "border-line"
      }`}
    >
      <div className="flex flex-col gap-1">
        <span className="font-display text-[22px] font-bold">{name}</span>
        <span className="text-sm text-ink2">{blurb}</span>
      </div>
      <div className="flex flex-col gap-1.5">
        <span className="kicker text-[11.5px]">What it got</span>
        <div className="grid grid-cols-5 gap-1.5">
          {FILTERS.map((f, i) => {
            const cls = lost(damage, i) ? "in gap" : damage.typo === i ? (ready ? "in removed" : "in bad") : "in";
            return (
              <span key={f.key} className={cls} style={{ "--fc": `var(--f-${f.key})` } as CSSProperties} title={f.label}>
                {damage.typo === i ? (ready ? "×" : "!") : ""}
              </span>
            );
          })}
        </div>
        <span className="text-sm text-ink2">{note(kind, obj, damage, ready)}</span>
      </div>
      <div aria-live="polite" className="flex min-h-[64px] flex-col justify-center gap-1.5">
        <span className="kicker text-[11.5px]">Its answer</span>
        {ready ? (
          <span key={reading.label} className={`answer font-display text-4xl leading-none font-bold sm:text-[44px] ${not ? "text-unsure" : ""}`}>
            {reading.label}
          </span>
        ) : (
          <span className="pending font-display text-4xl leading-none font-bold text-ink3 sm:text-[44px]">Thinking…</span>
        )}
      </div>
      <div>
        <div className="flex items-end gap-3.5">
          <div className="relative h-[78px] w-[150px] flex-none overflow-hidden" role="img" aria-label={ready ? `How sure: ${not ? "not sure enough to answer" : sureWord(reading.conf)}` : "Waiting"}>
            <span className="absolute top-0 left-0 size-[150px] rounded-full border-[12px] border-card2 shadow-[inset_0_0_0_1px_var(--line)]" />
            <span className="needle absolute bottom-0 left-[73px] h-16 w-1 rounded-sm bg-ink" style={{ transform: `rotate(${-90 + t * 180}deg)` }} />
            <span className="absolute -bottom-[9px] left-[66px] size-[18px] rounded-full bg-ink" />
          </div>
          <div className="flex flex-col gap-0.5 pb-0.5">
            <span className="kicker text-[11px]">How sure</span>
            <span className="text-lg font-bold">{!ready ? "…" : not ? "Not sure enough" : sureWord(reading.conf)}</span>
          </div>
        </div>
        <div className="mt-1 flex w-[150px] justify-between text-sm text-ink2">
          <span>guessing</span>
          <span>certain</span>
        </div>
      </div>
      <p className="m-0 min-h-12 text-base">{ready ? reading.why : "Tap Next to see its answer."}</p>
      {ready && (
        <span className={`fade inline-flex items-center gap-2 self-start rounded-full px-3.5 py-1.5 text-[15px] font-bold ${right ? "v-right" : wrong ? "v-wrong" : "v-held"}`}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            {right ? <path d="M5 12.5l4.5 4.5L19 7.5" /> : wrong ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M5 12h14" />}
          </svg>
          {right ? "Right" : wrong ? (sure ? "Wrong, and very sure" : "Wrong") : "Held back · not counted as right"}
        </span>
      )}
    </article>
  );
}
