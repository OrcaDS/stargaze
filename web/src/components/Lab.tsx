import type { CSSProperties, Dispatch, SetStateAction } from "react";
import { answer, CLEAN, type Damage, FILTERS, lost, names, NOISE, OBJECTS, SCORES, sureWord, typoValue } from "../data";
import { STEP_LABELS, STORIES } from "../stories";
import Photo from "./Photo";
import Reader from "./Reader";
import Strip from "./Strip";

export interface LabState {
  mode: "story" | "free";
  story: number;
  step: number;
  obj: number;
  noise: number;
  mask: number;
  typo: number;
  typoTurn: number;
  last: string;
}

export const INITIAL_LAB: LabState = {
  mode: "story",
  story: 0,
  step: 0,
  obj: 0,
  noise: 0,
  mask: 0,
  typo: -1,
  typoTurn: 0,
  last: "Pick an object and start breaking its readings.",
};

/** What the page currently shows: which object, which damage, and whether answers are revealed. */
export function current(s: LabState): { obj: number; damage: Damage; ready: boolean } {
  if (s.mode === "free") return { obj: s.obj, damage: { noise: s.noise, mask: s.mask, typo: s.typo }, ready: true };
  const st = STORIES[s.story];
  return { obj: st.obj, damage: s.step >= 1 ? { noise: st.noise, mask: st.mask, typo: st.typo } : CLEAN, ready: s.step !== 1 };
}

const TYPES = ["Galaxy", "Star", "Quasar"] as const;

/** A random object index (of one type, or any), never the one already showing. */
function shuffle(current: number, type?: string): number {
  const pool = OBJECTS.flatMap((o, i) => (i !== current && (!type || o.type === type) ? [i] : []));
  return pool[Math.floor(Math.random() * pool.length)];
}

export default function Lab({
  lab,
  setLab,
  machine,
  onMachine,
}: {
  lab: LabState;
  setLab: Dispatch<SetStateAction<LabState>>;
  machine: boolean;
  onMachine: () => void;
}) {
  const { obj: oi, damage, ready } = current(lab);
  const obj = OBJECTS[oi];
  const ans = answer(oi, damage);
  const isStory = lab.mode === "story";
  const story = STORIES[lab.story];
  const free = (patch: Partial<LabState>, last: string) => setLab((s) => ({ ...s, ...patch, last }));

  const toggleFilter = (i: number) =>
    setLab((s) => {
      const off = !lost(s, i);
      return {
        ...s,
        mask: s.mask ^ (1 << i),
        typo: off && s.typo === i ? -1 : s.typo,
        last: off ? `You switched off ${FILTERS[i].name}. That slot is now empty.` : `You switched ${FILTERS[i].name} back on.`,
      };
    });
  const toggleTypo = () =>
    setLab((s) => {
      if (s.typo >= 0) return { ...s, typo: -1, last: "You fixed the typo." };
      const cands = [3, 1, 4, 0, 2].filter((i) => !lost(s, i));
      if (!cands.length) return { ...s, last: "Every colour is off, so there’s nothing to mistype. Switch one back on first." };
      const i = cands[s.typoTurn % cands.length];
      const o = OBJECTS[s.obj];
      return { ...s, typo: i, typoTurn: s.typoTurn + 1, last: `You made a typo: ${FILTERS[i].name} ${o.mags[i].toFixed(2)} became ${typoValue(o, i)}.` };
    });
  const tryIt = () =>
    setLab((s) => ({ ...s, mode: "free", obj: story.obj, noise: story.noise, mask: story.mask, typo: story.typo, last: "Same object, same damage as the story. Now change it." }));

  const sg = ans.stargaze;
  const narration = isStory
    ? story.captions[Math.min(lab.step, 2)]
    : `${lab.last} Ordinary model: ${ans.ordinary.label} (${sureWord(ans.ordinary.conf).toLowerCase()}). Stargaze: ${
        sg.label === "Not sure" ? "Not sure, so it holds back." : `${sg.label} (${sureWord(sg.conf).toLowerCase()}).`
      }`;
  const lostNames = names([0, 1, 2, 3, 4].filter((i) => lost(damage, i)));

  return (
    <section id="lab" className="relative z-10 border-y border-line bg-bg2/80 py-16 sm:py-[72px]">
      <div className="mx-auto flex max-w-[1200px] flex-col gap-7 px-4 sm:px-6">
        <div className="flex max-w-[760px] flex-col gap-2.5">
          <span className="kicker">The experiment</span>
          <h2 className="m-0 font-display text-[clamp(32px,4.4vw,48px)] leading-[1.05] font-bold">Two readers, the same measurements</h2>
          <p className="m-0 text-[19px] text-ink2">
            The <strong className="text-ink">ordinary model</strong> learned from clean, perfect measurements. <strong className="text-ink">Stargaze</strong> also
            practised on damaged copies and says “Not sure” when the clues run out. Break the readings and watch who copes.
          </p>
        </div>

        <div role="tablist" aria-label="How to explore" className="inline-flex gap-1 self-start rounded-full border border-line bg-card2 p-1">
          {(["story", "free"] as const).map((m) => (
            <button
              key={m}
              role="tab"
              aria-selected={lab.mode === m}
              onClick={() => setLab((s) => ({ ...s, mode: m }))}
              className={`min-h-12 cursor-pointer rounded-full px-5 font-bold ${lab.mode === m ? "bg-card text-ink shadow-[0_0_0_1px_var(--line)]" : "text-ink2"}`}
            >
              {m === "story" ? "Guided stories" : "Break it yourself"}
            </button>
          ))}
        </div>

        {isStory ? (
          <div className="flex flex-col gap-4">
            <div className="grid gap-3 md:grid-cols-3">
              {STORIES.map((st, i) => (
                <button
                  key={st.title}
                  aria-pressed={i === lab.story}
                  onClick={() => setLab((s) => ({ ...s, story: i, step: 0 }))}
                  className={`flex cursor-pointer flex-col gap-1 rounded-[18px] border-[1.5px] p-4 text-left transition-colors ${
                    i === lab.story ? "border-acc bg-acc/10" : "border-line bg-card2 hover:border-ink3"
                  }`}
                >
                  <span className="font-display text-xl font-bold">{st.title}</span>
                  <span className="text-sm text-ink2">{st.blurb}</span>
                </button>
              ))}
            </div>
            <div className="flex flex-col gap-3.5 rounded-[22px] border border-line bg-card px-5 py-5 sm:px-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap gap-1.5" aria-label="Steps">
                  {STEP_LABELS.map((l, i) => (
                    <span
                      key={l}
                      className={`rounded-full border px-3 py-1.5 text-[13px] font-bold transition-all ${
                        i === lab.step ? "border-ink bg-ink text-bg" : `border-line bg-card2 ${i < lab.step ? "text-ink2" : "text-ink3"}`
                      }`}
                    >
                      {l}
                    </span>
                  ))}
                </div>
                <div className="flex flex-wrap gap-2">
                  <button className="btn" disabled={lab.step === 0} onClick={() => setLab((s) => ({ ...s, step: s.step - 1 }))}>
                    Back
                  </button>
                  {lab.step < 3 ? (
                    <button className="btn primary" onClick={() => setLab((s) => ({ ...s, step: s.step + 1 }))}>
                      Next
                    </button>
                  ) : (
                    <button className="btn primary" onClick={tryIt}>
                      Try it yourself
                    </button>
                  )}
                </div>
              </div>
              <p key={`${lab.story}-${lab.step}`} className="fade m-0 text-[19px] leading-snug" aria-live="polite">
                {narration}
              </p>
              {lab.step === 3 && <p className="fade m-0 rounded-[14px] bg-acc/12 px-4 py-3.5 font-semibold">{story.take}</p>}
              <span className="text-sm text-ink2">A hand-picked example. The zoom-out below shows the average over {SCORES.objects.toLocaleString("en")} objects.</span>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-5 rounded-[22px] border border-line bg-card px-5 py-5 sm:px-6">
            <div className="flex flex-col gap-2.5">
              <span className="kicker">1 · Pick an object</span>
              <div className="flex flex-wrap gap-2">
                {TYPES.map((t) => (
                  <button
                    key={t}
                    className={`btn ${obj.type === t ? "on" : ""}`}
                    aria-pressed={obj.type === t}
                    onClick={() => {
                      const i = shuffle(lab.obj, t);
                      free({ obj: i }, `You picked a ${t.toLowerCase()}, ${OBJECTS[i].tag}.`);
                    }}
                  >
                    <span className="relative inline-block size-[22px] flex-none overflow-hidden rounded-md bg-sky">
                      <span className={t === "Galaxy" ? "o-fuzzy" : "o-point"} style={{ "--s": "12px", "--glow": t === "Quasar" ? "#b9d4ff" : "#ffe2ad" } as CSSProperties} />
                    </span>
                    {t}
                  </button>
                ))}
                <button
                  className="btn ghost"
                  onClick={() => {
                    const i = shuffle(lab.obj);
                    free({ obj: i }, `Surprise: a ${OBJECTS[i].type.toLowerCase()}, ${OBJECTS[i].tag}.`);
                  }}
                >
                  Surprise me
                </button>
              </div>
              <span className="text-sm text-ink2">Seven real objects of each kind. Tap again for another one.</span>
            </div>
            <div className="grid gap-5 md:grid-cols-3">
              <div className="flex flex-col gap-2.5">
                <span className="kicker">2 · Shake the telescope</span>
                <div className="flex flex-wrap gap-1.5" role="group" aria-label="How shaky">
                  {NOISE.map((v) => (
                    <button
                      key={v}
                      className={`btn ${v === lab.noise ? "on" : ""}`}
                      aria-pressed={v === lab.noise}
                      onClick={() => free({ noise: v }, v ? `You shook the telescope: readings are now ${v}× less precise than normal.` : "You steadied the telescope.")}
                    >
                      {v ? `${v}×` : "Steady"}
                    </button>
                  ))}
                </div>
                <span className="text-sm text-ink2">How much less precise than a normal night.</span>
              </div>
              <div className="flex flex-col gap-2.5">
                <span className="kicker">3 · Lose a colour</span>
                <p className="m-0 text-base">Tap any colour on the strip below to switch that filter off, as if it failed or a cloud passed.</p>
              </div>
              <div className="flex flex-col gap-2.5">
                <span className="kicker">4 · Make a typo</span>
                <div className="flex flex-wrap gap-2">
                  <button className={`btn ${lab.typo >= 0 ? "on" : ""}`} aria-pressed={lab.typo >= 0} onClick={toggleTypo}>
                    {lab.typo >= 0 ? "Fix the typo" : "Add a typo"}
                  </button>
                  <button className="btn ghost" onClick={() => free({ noise: 0, mask: 0, typo: -1 }, "All repaired: clean readings again.")}>
                    Reset all
                  </button>
                </div>
                <span className="text-sm text-ink2">A misplaced decimal point: 19.2 written down as 192.</span>
              </div>
            </div>
            <p key={narration} className="fade m-0 border-t border-line pt-4 text-[19px] leading-snug" aria-live="polite">
              {narration}
            </p>
          </div>
        )}

        <div className="grid items-start gap-5 lg:grid-cols-2">
          <div className="flex flex-col gap-4 rounded-[22px] border border-line bg-card p-5">
            <div className="flex flex-wrap items-start gap-4">
              <div className="w-[170px] flex-none">
                <Photo key={oi} obj={obj} machine={machine} small />
              </div>
              <div className="flex min-w-0 flex-[1_1_200px] flex-col gap-2.5">
                <span className="kicker">{isStory ? "Story object" : "Your object"}</span>
                <span className="font-display text-[22px] leading-tight font-bold [overflow-wrap:anywhere]">{obj.tag}</span>
                <span className="text-sm text-ink2">
                  The real answer, from its spectrum: <strong className="text-ink">{obj.type}</strong>. The picture is for you only.
                </span>
                <button className={`btn self-start ${machine ? "on" : ""}`} aria-pressed={machine} onClick={onMachine}>
                  See it like the machine
                </button>
              </div>
            </div>
            <div className="flex flex-col gap-2.5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="kicker text-acc">What the machine reads</span>
                <span className="text-sm text-ink2">Taller bar = brighter · {isStory ? "in “Break it yourself”, tap a colour to switch it off" : "tap a colour to switch it off"}</span>
              </div>
              <Strip obj={obj} damage={damage} revealed={ready} onToggle={isStory ? undefined : toggleFilter} />
              <span className="text-sm text-ink2">
                Astronomers write brightness as a number where smaller means brighter; the small numbers are those raw readings. From these same five filters, the
                models also work out colour differences and how sharp or fuzzy the object looks.
              </span>
              {lostNames && !isStory && <span className="sr-only">Switched off: {lostNames}</span>}
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Reader kind="ordinary" reading={ans.ordinary} obj={obj} damage={damage} truth={obj.type} ready={ready} />
            <Reader kind="stargaze" reading={sg} obj={obj} damage={damage} truth={obj.type} ready={ready} />
          </div>
        </div>
      </div>
    </section>
  );
}
