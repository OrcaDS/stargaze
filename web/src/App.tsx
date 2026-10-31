import { useEffect, useState } from "react";
import Flow from "./components/Flow";
import Header from "./components/Header";
import Hook from "./components/Hook";
import Lab, { current, INITIAL_LAB } from "./components/Lab";
import Sky from "./components/Sky";
import ZoomOut from "./components/ZoomOut";

function initialTheme(): "dark" | "light" {
  try {
    const saved = localStorage.getItem("stargaze-theme");
    if (saved === "dark" || saved === "light") return saved;
  } catch {
    /* storage can be blocked; fall back to the system setting */
  }
  return window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export default function App() {
  const [theme, setTheme] = useState(initialTheme);
  const [machine, setMachine] = useState(false);
  const [lab, setLab] = useState(INITIAL_LAB);
  useEffect(() => {
    try {
      localStorage.setItem("stargaze-theme", theme);
    } catch {
      /* ignore */
    }
    document.documentElement.style.colorScheme = theme;
  }, [theme]);
  const toggleMachine = () => setMachine((m) => !m);

  return (
    <div className={`sg relative ${theme === "light" ? "light" : ""}`}>
      <Sky />
      <Header dark={theme === "dark"} onTheme={() => setTheme(theme === "dark" ? "light" : "dark")} />
      <main>
        <Hook machine={machine} onMachine={toggleMachine} />
        <Lab lab={lab} setLab={setLab} machine={machine} onMachine={toggleMachine} />
        <ZoomOut damage={current(lab).damage} />
        <Flow />
      </main>
      <footer className="relative z-10 border-t border-line py-8 pb-12">
        <div className="mx-auto flex max-w-[1200px] flex-wrap justify-between gap-4 px-4 text-sm text-ink2 sm:px-6">
          <span>
            Stargaze sorts objects using only what five colour filters measured in the Sloan Digital Sky Survey (DR17). It never looks at a picture. Photos: SDSS.
          </span>
          <span>Built on free tools.</span>
        </div>
      </footer>
    </div>
  );
}
