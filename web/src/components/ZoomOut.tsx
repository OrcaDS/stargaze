import { type Damage, lostList, SCORES } from "../data";

const X0 = 44;
const W = 280;
const y = (score: number) => 176 - score * 1.6;
const NOISE_LEVELS = [0, 1, 2, 3, 5, 8];
const noiseX = (n: number) => X0 + (n / 8) * W;
const missX = (k: number) => X0 + k * 70;

function Chart({
  title,
  sub,
  label,
  ticks,
  ord,
  sg,
  here,
  answered,
  sgBelow = false,
}: {
  title: string;
  sub: string;
  label: string;
  ticks: { x: number; t: string }[];
  ord: { x: number; s: number }[];
  sg: { x: number; s: number }[];
  here: { x: number; o: number; s: number };
  answered: [number, number]; // Stargaze's score on the objects it answers, and % it answers, at "here"
  sgBelow?: boolean; // put the Stargaze end label under its line when the line climbs into it
}) {
  const pts = (p: { x: number; s: number }[]) => p.map((q) => `${q.x},${y(q.s)}`).join(" ");
  const last = (p: { x: number; s: number }[]) => p[p.length - 1];
  return (
    <figure className="m-0 flex flex-col gap-2.5 rounded-[22px] border border-line bg-card p-5">
      <figcaption className="flex flex-col gap-0.5">
        <span className="font-display text-xl font-bold">{title}</span>
        <span className="text-sm text-ink2">{sub}</span>
      </figcaption>
      <svg viewBox="0 0 340 210" className="block h-auto w-full" role="img" aria-label={label}>
        <g stroke="var(--line)" strokeWidth="1">
          {[16, 56, 96, 136, 176].map((v) => (
            <line key={v} x1={X0} y1={v} x2={324} y2={v} />
          ))}
        </g>
        <g fill="var(--ink3)" fontSize="11" textAnchor="end">
          {[100, 75, 50, 25, 0].map((v) => (
            <text key={v} x="36" y={y(v) + 4}>
              {v}
            </text>
          ))}
        </g>
        <g fill="var(--ink3)" fontSize="11" textAnchor="middle">
          {ticks.map((t) => (
            <text key={t.t} x={t.x} y="196">
              {t.t}
            </text>
          ))}
        </g>
        <line x1={here.x} y1="10" x2={here.x} y2="178" stroke="var(--warn)" strokeWidth="2.5" style={{ transition: "all .6s" }} />
        <polyline points={pts(ord)} fill="none" stroke="var(--ink2)" strokeWidth="2.5" strokeDasharray="6 5" />
        <polyline points={pts(sg)} fill="none" stroke="var(--acc)" strokeWidth="3.5" strokeLinejoin="round" />
        <circle cx={here.x} cy={y(here.o)} r="5.5" fill="var(--card)" stroke="var(--ink2)" strokeWidth="2.5" style={{ transition: "all .6s" }} />
        <circle cx={here.x} cy={y(here.s)} r="5.5" fill="var(--acc)" style={{ transition: "all .6s" }} />
        <text x="322" y={y(last(sg).s) + (sgBelow ? 18 : -8)} textAnchor="end" fill="var(--acc)" fontSize="12" fontWeight="700">
          Stargaze {last(sg).s}
        </text>
        <text x="322" y={Math.min(170, y(last(ord).s) + 18)} textAnchor="end" fill="var(--ink2)" fontSize="12" fontWeight="700">
          Ordinary {last(ord).s}
        </text>
      </svg>
      <p className="m-0 text-sm text-ink2" aria-live="polite">
        Allowed to say “Not sure”, Stargaze scores <strong className="text-acc">{answered[0]}</strong> on the{" "}
        <strong className="text-ink">{answered[1]}%</strong> of objects it answers here.
      </p>
    </figure>
  );
}

export default function ZoomOut({ damage }: { damage: Damage }) {
  const n = damage.noise;
  const mc = lostList(damage).length;
  const [no, ns, nf, nc] = SCORES.noise[String(n)];
  const [mo, ms, mf, mcov] = SCORES.missing[Math.min(mc, 4)];
  const parts: string[] = [];
  if (n) parts.push(`${n}× noise: ordinary ${no}, Stargaze ${ns}`);
  if (mc) parts.push(`${mc} colour${mc > 1 ? "s" : ""} lost: ordinary ${mo}, Stargaze ${ms}${mc > 4 ? " (4 is the most tested)" : ""}`);
  if (damage.typo >= 0) parts.push("a typo: see the Typos box");
  let here = `You are here: ${parts.length ? parts.join(" · ") : `clean data, ordinary ${SCORES.noise["0"][0]}, Stargaze ${SCORES.noise["0"][1]}`}`;
  if (n && mc) here += ". You’ve mixed two kinds of damage; each chart shows one kind on its own.";
  const [clo, cls] = SCORES.noise["0"];
  const [co, cs] = SCORES.corrupt;

  return (
    <section id="scale" className="relative z-10 py-16 sm:py-20">
      <div className="mx-auto flex max-w-[1200px] flex-col gap-7 px-4 sm:px-6">
        <div className="flex max-w-[760px] flex-col gap-2.5">
          <span className="kicker">Zoom out</span>
          <h2 className="m-0 font-display text-[clamp(32px,4.4vw,48px)] leading-[1.05] font-bold">It wasn’t a fluke</h2>
          <p className="m-0 text-[19px] text-ink2">
            The same experiment on <strong className="text-ink">{SCORES.objects.toLocaleString("en")} objects</strong> neither model saw while learning. On perfect data
            they’re nearly tied, {clo} to {cls}: Stargaze gives up almost nothing. Break the data and it pulls far ahead.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap gap-4 text-sm text-ink2">
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-6 border-t-[3px] border-acc" />
              Stargaze
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-6 border-t-[3px] border-dashed border-ink2" />
              Ordinary model
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-3.5 w-[3px] bg-warn" />
              You are here
            </span>
          </div>
          <p className="m-0 text-sm font-semibold" aria-live="polite">
            {here}
          </p>
        </div>
        <div className="grid gap-5 md:grid-cols-2">
          <Chart
            title="A shakier telescope"
            sub="Score as the readings get less precise"
            label={`Noise: ordinary falls from ${clo} to ${SCORES.noise["8"][0]} at 8 times normal noise; Stargaze from ${cls} to ${SCORES.noise["8"][1]}.`}
            ticks={NOISE_LEVELS.map((v) => ({ x: noiseX(v), t: v ? `${v}×` : "clean" }))}
            ord={NOISE_LEVELS.map((v) => ({ x: noiseX(v), s: SCORES.noise[String(v)][0] }))}
            sg={NOISE_LEVELS.map((v) => ({ x: noiseX(v), s: SCORES.noise[String(v)][1] }))}
            here={{ x: noiseX(n), o: no, s: ns }}
            answered={[nf, nc]}
          />
          <Chart
            title="Colours lost"
            sub="Score by how many of the five filters are missing"
            label={`Missing colours: ordinary falls from ${clo} to ${SCORES.missing[4][0]} with four missing; Stargaze from ${cls} to ${SCORES.missing[4][1]}.`}
            ticks={[0, 1, 2, 3, 4].map((k) => ({ x: missX(k), t: k ? String(k) : "none" }))}
            ord={SCORES.missing.map((p, k) => ({ x: missX(k), s: p[0] }))}
            sg={SCORES.missing.map((p, k) => ({ x: missX(k), s: p[1] }))}
            here={{ x: missX(Math.min(mc, 4)), o: mo, s: ms }}
            answered={[mf, mcov]}
            sgBelow
          />
        </div>
        <div className="grid gap-5 md:grid-cols-2">
          <div className={`flex flex-col gap-2 rounded-[22px] border bg-card p-5 transition-all ${damage.typo >= 0 ? "border-warn shadow-[0_0_0_3px_var(--warn-bg)]" : "border-line"}`}>
            <span className="font-display text-xl font-bold">Typos</span>
            <span className="text-sm text-ink2">5 in every 100 objects get one impossible value</span>
            <div className="flex items-baseline gap-7">
              <span>
                <span className="font-display text-4xl font-bold text-ink2">{co}</span> <span className="text-sm text-ink2">ordinary</span>
              </span>
              <span>
                <span className="font-display text-4xl font-bold text-acc">{cs}</span> <span className="text-sm text-ink2">Stargaze</span>
              </span>
            </div>
            <span className="text-sm text-ink2">Spread thinly, typos barely hurt either model on average: the input check blanks them for both. The story above shows what one in the wrong place can do.</span>
          </div>
          <div className="flex flex-col gap-2 rounded-[22px] border border-line p-5">
            <span className="font-display text-xl font-bold">How the score works</span>
            <p className="m-0 text-sm text-ink2">
              Out of 100: how often it’s right, with stars, galaxies and quasars counting equally. For these scores Stargaze had to answer every object, with no “Not sure” allowed,
              so it gets no credit for holding back. The line under each chart shows the other side: allowed to say “Not sure”, it’s right more often on the
              objects it does answer, and the share it answers shrinks as the data gets worse.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
