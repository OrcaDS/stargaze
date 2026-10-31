import type { CSSProperties } from "react";
import { type Damage, FILTERS, lost, type SkyObject, typoValue } from "../data";

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/** The five readings as bars (taller = brighter), with any damage drawn on the bars themselves. */
export default function Strip({
  obj,
  damage,
  revealed = true,
  onToggle,
  compact = false,
  grow = false,
}: {
  obj: SkyObject;
  damage: Damage;
  revealed?: boolean; // the input check's stamp shows once the readers have answered
  onToggle?: (i: number) => void;
  compact?: boolean;
  grow?: boolean;
}) {
  const n = damage.noise;
  return (
    <div className={`grid grid-cols-5 gap-1.5 sm:gap-2 ${grow ? "grow" : ""}`}>
      {FILTERS.map((f, i) => {
        const miss = lost(damage, i);
        const typo = damage.typo === i;
        const m = obj.noisy[String(n)][i];
        const sig = obj.err[i] * n;
        // Display scale: magnitude 25 = empty, 15 = full (smaller magnitude = brighter).
        const h = typo ? 0 : clamp((25 - m) * 10, 4, 100);
        const band = n ? clamp(Math.max(sig * 10, n * 1.5), 0, 40) : 0;
        const blur = miss ? 0 : n >= 5 ? n * 0.42 : n * 0.2;
        const val = miss
          ? "no reading"
          : typo
            ? `${typoValue(obj, i)} ?!`
            : n
              ? `${m.toFixed(1)} ±${sig < 0.1 ? sig.toFixed(2) : sig.toFixed(1)}`
              : obj.mags[i].toFixed(2);
        const cls = `slot ${miss ? "is-missing" : ""} ${typo ? "is-typo" : ""}`;
        const style = { "--fc": `var(--f-${f.key})` } as CSSProperties;
        const body = (
          <>
            <span className="well" style={{ height: compact ? 110 : 150 }}>
              {band > 0 && !miss && !typo && (
                <span className="band" style={{ bottom: `${Math.max(0, h - band)}%`, height: `${band * 2}%`, filter: `blur(${blur}px)` }} />
              )}
              <span
                className="bar"
                style={{ height: `${h}%`, filter: `blur(${blur}px)`, "--amp": `${miss || typo ? 0 : n * 0.9}px`, "--dur": `${1.3 + i * 0.21}s` } as CSSProperties}
              />
              {miss && <span className="fade absolute right-0 bottom-[36%] left-0 block text-xs leading-tight font-bold text-ink3">no<br />reading</span>}
              {typo && revealed && <span className="stamp">Impossible<br />removed</span>}
            </span>
            {!compact && <span className="relative mx-1.5 block h-[52px]">{typo && <span className="plunge" />}</span>}
            <span className={`flex items-center justify-center gap-1 text-[11.5px] font-bold whitespace-nowrap sm:text-[13px] ${miss ? "opacity-55" : ""}`}>
              <span className="inline-block size-2 flex-none rounded-full" style={{ background: "var(--fc)" }} />
              {f.short}
            </span>
            <span className={`block min-h-[18px] font-mono text-[10.5px] sm:text-xs ${typo ? "font-semibold text-warn" : "text-ink2"}`}>{val}</span>
          </>
        );
        return onToggle ? (
          <button
            key={f.key}
            className={cls}
            style={style}
            onClick={() => onToggle(i)}
            aria-pressed={!miss}
            aria-label={`${f.label}: ${miss ? "switched off" : val}. Tap to switch ${miss ? "on" : "off"}.`}
          >
            {body}
          </button>
        ) : (
          <div key={f.key} className={cls} style={style} aria-label={`${f.label}: ${val}`}>
            {body}
          </div>
        );
      })}
    </div>
  );
}
