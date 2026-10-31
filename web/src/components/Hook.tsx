import { useState } from "react";
import { CLEAN, OBJECTS } from "../data";
import Photo from "./Photo";
import Strip from "./Strip";

type Kind = "Star" | "Galaxy" | "Quasar";
const GUESSES: Kind[] = ["Star", "Galaxy", "Quasar"];

/** [headline, explanation] for a guess, given the object's real type. */
function verdict(guess: Kind, truth: Kind): [string, string] {
  if (guess === truth)
    return {
      Star: ["Spot on.", "A sharp point of light, like most stars."],
      Galaxy: ["Spot on.", "That fuzzy patch is the giveaway."],
      Quasar: ["Spot on.", "Most people say star: quasars look just like them."],
    }[truth] as [string, string];
  if (truth === "Galaxy") return ["Not quite.", "Stars and quasars look like sharp points. This one is a fuzzy patch."];
  if (guess === "Galaxy") return ["Not quite.", "Galaxies look like fuzzy patches. This is a sharp point of light."];
  if (truth === "Quasar")
    return ["Good guess, and a very common one.", "It does look like a star. The ordinary model makes the same mistake once two of its readings go missing (the first story below)."];
  return ["Not quite, but a fair guess.", "In a photo, a quasar and a star both look like a sharp point of light."];
}

const REVEAL: Record<Kind, string> = {
  Star: "It’s a star: a sun in our own galaxy, close enough to show as a single point.",
  Galaxy: "It’s a galaxy: billions of stars so far away they blur into one fuzzy patch.",
  Quasar: "It’s a quasar: the blazing core of a distant galaxy, lit up by a giant black hole.",
};

export default function Hook({ machine, onMachine }: { machine: boolean; onMachine: () => void }) {
  const [guess, setGuess] = useState<Kind | null>(null);
  const [obj] = useState(() => OBJECTS[Math.floor(Math.random() * OBJECTS.length)]); // a new one each visit
  const truth = obj.type as Kind;
  return (
    <section id="top" className="relative z-10 py-16 sm:py-20">
      <div className="mx-auto grid max-w-[1200px] items-center gap-12 px-4 sm:px-6 lg:grid-cols-2">
        <div className="flex flex-col gap-5">
          <span className="kicker">A quick game</span>
          <h1 className="m-0 font-display text-[clamp(40px,6vw,68px)] leading-[1.02] font-bold">Star, galaxy or quasar?</h1>
          <p className="m-0 max-w-[30ch] text-[21px] text-ink2">You can see the picture. The computer can’t.</p>
          {!guess ? (
            <div className="flex flex-col gap-3">
              <span className="font-bold">What’s your guess?</span>
              <div className="flex flex-wrap gap-2.5">
                {GUESSES.map((g) => (
                  <button key={g} className="btn min-h-[52px] px-6 text-lg" onClick={() => setGuess(g)}>
                    {g}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="fade flex flex-col gap-4">
              <p className="m-0 text-[19px]">
                <strong>{verdict(guess, truth)[0]}</strong> {verdict(guess, truth)[1]}
              </p>
              <p className="m-0 text-ink2">{REVEAL[truth]} Astronomers confirmed it by splitting its light into a detailed spectrum.</p>
              <p className="m-0 text-[19px] font-semibold">
                But the computer never sees this picture. All it gets is what five colour filters measured, like the readings underneath.
              </p>
              <div className="flex flex-wrap gap-2.5">
                <a className="btn primary" href="#lab">
                  Now break the readings
                </a>
                <button className={`btn ${machine ? "on" : ""}`} aria-pressed={machine} onClick={onMachine}>
                  See it like the machine
                </button>
              </div>
            </div>
          )}
        </div>
        <div className="mx-auto flex w-full max-w-[460px] flex-col gap-3.5">
          <Photo obj={obj} machine={machine} />
          <span className="text-sm text-ink2">The picture is for your eyes only. Neither model ever sees it.</span>
          {guess && (
            <div className="fade flex flex-col gap-3 rounded-[22px] border border-line bg-card p-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="kicker text-acc">What the machine reads</span>
                <span className="text-sm text-ink2">Taller bar = brighter</span>
              </div>
              <Strip obj={obj} damage={CLEAN} compact grow />
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
