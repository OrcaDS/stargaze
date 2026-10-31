import type { ReactNode } from "react";

// The pipeline, left to right and top to bottom. Coordinates are px inside a 1152 x 892 board;
// on narrow screens the board scrolls sideways.
interface Card {
  x: number;
  y: number;
  w?: number;
  h: number;
  kicker: string;
  title?: string;
  color?: string;
  accent?: boolean;
  dashed?: boolean;
  children: ReactNode;
}

const CARDS: Card[] = [
  { x: 0, y: 48, h: 148, kicker: "Data source", title: "SDSS DR17", children: "The Sloan Digital Sky Survey: real objects whose type was confirmed from a spectrum." },
  { x: 304, y: 48, h: 148, kicker: "Layer 1", title: "Bronze", color: "var(--bronze)", children: "A raw, untouched copy, pulled in chunks. Release, query and date are recorded." },
  { x: 608, y: 48, h: 148, kicker: "Layer 2", title: "Silver", color: "var(--silver)", children: "Cleaned: “−9999” missing-value codes become blanks; one row per object." },
  { x: 912, y: 48, h: 148, kicker: "Layer 3", title: "Gold", color: "var(--gold)", children: "Ready to learn from: impossible values blanked, errors capped, colours worked out." },
  { x: 0, y: 388, h: 160, kicker: "Split", title: "70 · 15 · 15", children: "70% to learn from, 15% to tune settings on, 15% held back as the final test." },
  {
    x: 304,
    y: 364,
    h: 208,
    kicker: "What the models read",
    title: "15 numbers",
    children: "All from the five filters: 5 brightness readings, 4 colour differences and 5 sharp-or-fuzzy measures. An input check blanks impossible values first. Never the distance or IDs.",
  },
  { x: 608, y: 290, h: 148, kicker: "Model", title: "Stargaze", accent: true, children: "Gradient-boosted decision trees, also practised on damaged copies: noise, lost colours, typos." },
  { x: 608, y: 498, h: 148, kicker: "Model", title: "Ordinary", children: "The same kind of trees (scikit-learn HistGradientBoosting), learned from clean copies only." },
  { x: 912, y: 288, h: 152, kicker: "Stargaze only", title: "Trust layer", accent: true, children: "Re-tuned sureness, an unusual-input detector and a weak-pattern rule. Too unsure → “Not sure”." },
  { x: 912, y: 500, h: 144, kicker: "Prediction", title: "An answer", children: "Star, galaxy, quasar or “Not sure”, plus how sure it is." },
  {
    x: 0,
    y: 740,
    w: 544,
    h: 136,
    kicker: "House rules",
    dashed: true,
    children: "Damaged copies are made after the split, from learning rows only. Settings are tuned on the 15% tuning set, never on the test. “Not sure” never counts as right.",
  },
  { x: 608, y: 740, h: 136, kicker: "Tested", title: "Scored once", children: "On 37,775 held-back objects, plus a check on a second survey (DESI DR1)." },
  { x: 912, y: 740, h: 136, kicker: "Served", title: "This page", children: "Every answer here was worked out in advance by the real models. Free to host, nothing to run." },
];

// [x1, y1, x2, y2, arrowhead, stargaze colour]
const LINES: [number, number, number, number, boolean, boolean?][] = [
  [240, 122, 303, 122, true],
  [544, 122, 607, 122, true],
  [848, 122, 911, 122, true],
  [1032, 196, 1032, 244, false],
  [1032, 244, 120, 244, false],
  [120, 244, 120, 387, true],
  [240, 468, 303, 468, true],
  [544, 468, 576, 468, false],
  [576, 364, 576, 572, false],
  [576, 364, 607, 364, true],
  [576, 572, 607, 572, true],
  [848, 364, 911, 364, true, true],
  [848, 572, 911, 572, true],
  [1032, 440, 1032, 499, true, true],
  [1032, 644, 1032, 700, false],
  [728, 700, 1032, 700, false],
  [728, 700, 728, 739, true],
  [1032, 700, 1032, 739, true],
];

export default function Flow() {
  return (
    <section id="flow" className="relative z-10 border-t border-line bg-bg2/70 py-16 sm:py-20">
      <div className="mx-auto flex max-w-[1200px] flex-col gap-7 px-4 sm:px-6">
        <div className="flex max-w-[760px] flex-col gap-2.5">
          <span className="kicker">Under the hood</span>
          <h2 className="m-0 font-display text-[clamp(32px,4.4vw,48px)] leading-[1.05] font-bold">How it all flows</h2>
          <p className="m-0 text-[19px] text-ink2">
            From the telescope’s records to an answer: the data is cleaned in three layers (bronze, silver, gold), split, learned from by two models, and only Stargaze’s
            answers pass through a final trust check.
          </p>
        </div>
        <div className="overflow-x-auto pb-2">
          <div className="relative h-[892px] w-[1152px]">
            <div className="absolute top-0 left-[280px] h-[220px] w-[872px] rounded-[22px] border border-dashed border-line" style={{ background: "color-mix(in oklab, var(--gold) 6%, transparent)" }} />
            <span className="kicker absolute top-4 left-[300px] text-[11px]">Medallion layers · cleaner at each step</span>
            <svg className="absolute inset-0" width="1152" height="892" aria-hidden="true">
              <defs>
                {[
                  ["head", "var(--ink3)"],
                  ["head-acc", "var(--acc)"],
                ].map(([id, c]) => (
                  <marker key={id} id={id} orient="auto" markerWidth="5" markerHeight="5" refX="2" refY="2" overflow="visible">
                    <path d="M0 0 L4 2 L0 4 Z" fill={c} />
                  </marker>
                ))}
              </defs>
              {LINES.map(([x1, y1, x2, y2, head, acc], i) => {
                // stop the line under the arrowhead so the tip lands 1px short of the card
                const dx = Math.sign(x2 - x1) * (head ? 4 : 0);
                const dy = Math.sign(y2 - y1) * (head ? 4 : 0);
                return (
                  <line
                    key={i}
                    x1={x1}
                    y1={y1}
                    x2={x2 - dx}
                    y2={y2 - dy}
                    stroke={acc ? "var(--acc)" : "var(--ink3)"}
                    strokeWidth="2"
                    strokeLinecap="round"
                    markerEnd={head ? `url(#${acc ? "head-acc" : "head"})` : undefined}
                  />
                );
              })}
            </svg>
            {CARDS.map((c) => (
              <div
                key={c.kicker + (c.title ?? "")}
                className={`absolute box-border flex items-center rounded-[14px] border px-3.5 py-3 text-sm leading-5 text-ink2 ${c.dashed ? "border-dashed border-line" : "bg-card"} ${
                  c.accent ? "border-acc/60" : c.dashed ? "" : "border-line"
                }`}
                style={{ left: c.x, top: c.y, width: c.w ?? 240, height: c.h }}
              >
                <span>
                  <span className={`text-[11px] font-bold tracking-[0.08em] uppercase ${c.kicker === "Stargaze only" ? "text-acc" : "text-ink3"}`}>{c.kicker}</span>
                  <br />
                  {c.title && (
                    <>
                      <b className="font-display text-[17px] text-ink" style={c.color ? { color: c.color } : undefined}>
                        {c.title}
                      </b>
                      <br />
                    </>
                  )}
                  {c.children}
                </span>
              </div>
            ))}
          </div>
        </div>
        <span className="text-sm text-ink2 md:hidden">Scroll the diagram sideways.</span>
      </div>
    </section>
  );
}
