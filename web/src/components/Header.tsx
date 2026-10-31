import { useEffect, useRef, useState } from "react";

const WORDS = [
  ["Galaxy", "Billions of stars, very far away. Looks like a fuzzy patch."],
  ["Star", "A single star in our own galaxy. A sharp point of light."],
  [
    "Quasar",
    "The core of a distant galaxy, lit up by a giant black hole. It looks like a star, which is what makes it tricky.",
  ],
  [
    "Colour filter",
    "The telescope measures brightness through five filters, from ultraviolet to infrared. Most of them see light our eyes can’t.",
  ],
];

export function Logo() {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden="true">
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4" />
      <circle cx="12" cy="12" r="2.4" fill="currentColor" />
    </svg>
  );
}

export default function Header({ dark, onTheme }: { dark: boolean; onTheme: () => void }) {
  const [open, setOpen] = useState(false);
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !panel.current?.contains(e.target as Node))
        setOpen(false);
    };
    document.addEventListener("keydown", close);
    document.addEventListener("mousedown", close);
    return () => {
      document.removeEventListener("keydown", close);
      document.removeEventListener("mousedown", close);
    };
  }, [open]);

  return (
    <header className="sticky top-0 z-20 border-b border-line bg-bg/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1200px] items-center justify-between gap-3 px-4 sm:px-6">
        <a href="#top" className="flex items-center gap-2.5 no-underline">
          <Logo />
          <span className="font-display text-[22px] font-bold">Stargaze</span>
        </a>
        <div className="relative flex items-center gap-2" ref={panel}>
          <button className="btn ghost" aria-expanded={open} onClick={() => setOpen(!open)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z" />
              <path d="M4 19V5" />
            </svg>
            Words
          </button>
          <button className="btn ghost w-11 px-0" onClick={onTheme} aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}>
            {dark ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />
              </svg>
            )}
          </button>
          {open && (
            <div role="dialog" aria-label="A few words" className="fade absolute top-14 right-0 flex w-[min(380px,calc(100vw-32px))] flex-col gap-3.5 rounded-[22px] border border-line bg-card p-5 shadow-2xl">
              <span className="kicker">A few words</span>
              <dl className="m-0 flex flex-col gap-3">
                {WORDS.map(([t, d]) => (
                  <div key={t}>
                    <dt className="font-bold">{t}</dt>
                    <dd className="m-0 mt-0.5 text-[15px] text-ink2">{d}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
