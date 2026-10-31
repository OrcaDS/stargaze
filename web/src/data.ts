// The shipped models' real answers, precomputed by `python -m stargaze.export_demo`.
import raw from "./generated/answers.json";

export type Label = "Star" | "Galaxy" | "Quasar" | "Not sure";

export interface SkyObject {
  tag: string;
  type: Label;
  ra: number;
  dec: number;
  mags: number[]; // clean PSF magnitudes u, g, r, i, z (smaller = brighter)
  err: number[]; // their real measurement errors
  noisy: Record<string, number[]>; // the same object at each noise level, as the models got it
}

export interface Damage {
  noise: number; // multiple of the normal measurement error
  mask: number; // bit i set = filter i lost
  typo: number; // filter with a misplaced decimal point, or -1
}

export interface Reading {
  label: Label;
  conf: number; // the model's top share, 1/3 .. 1
  why: string;
}

export interface Answer {
  ordinary: Reading;
  stargaze: Reading & { unusual: boolean };
  corrected: boolean; // the input check blanked an impossible value (for both models)
}

interface Raw {
  labels: Label[];
  noise: number[];
  objects: SkyObject[];
  stories: { title: string; obj: number; noise: number; mask: number; typo: number }[];
  texts: string[];
  answers: Record<string, number[]>;
  scores: {
    // [ordinary, Stargaze answering everything, Stargaze on what it answers, % it answers]
    noise: Record<string, Score>;
    missing: Score[];
    corrupt: Score;
    objects: number;
  };
}

type Score = [number, number, number, number];

const data = raw as unknown as Raw;

export const OBJECTS = data.objects;
export const NOISE = data.noise;
export const SCORES = data.scores;
export const STORY_DAMAGE = data.stories;
export const CLEAN: Damage = { noise: 0, mask: 0, typo: -1 };

export const FILTERS = [
  { key: "u", name: "ultraviolet", label: "Ultraviolet", short: "UV" },
  { key: "g", name: "green", label: "Green", short: "Green" },
  { key: "r", name: "red", label: "Red", short: "Red" },
  { key: "i", name: "near-infrared", label: "Near-infrared", short: "Near-IR" },
  { key: "z", name: "infrared", label: "Infrared", short: "IR" },
] as const;

export const lost = (d: Damage, i: number) => ((d.mask >> i) & 1) === 1;
export const lostList = (d: Damage) => [0, 1, 2, 3, 4].filter((i) => lost(d, i));
export const typoValue = (o: SkyObject, i: number) => (o.mags[i] * 10).toFixed(1);

export function answer(obj: number, d: Damage): Answer {
  const v = data.answers[`${obj}|${d.noise}|${d.mask}|${d.typo}`];
  if (!v) throw new Error(`no precomputed answer for ${obj}|${d.noise}|${d.mask}|${d.typo}`);
  return {
    ordinary: { label: data.labels[v[0]], conf: v[1], why: data.texts[v[2]] },
    stargaze: { label: data.labels[v[3]], conf: v[4], why: data.texts[v[5]], unusual: v[6] === 1 },
    corrected: v[7] === 1,
  };
}

export const cutout = (o: SkyObject, px = 240) =>
  `https://skyserver.sdss.org/dr17/SkyServerWS/ImgCutout/getjpeg?ra=${o.ra}&dec=${o.dec}&scale=0.3&width=${px}&height=${px}`;

export function names(idx: number[]) {
  const n = idx.map((i) => FILTERS[i].name);
  return n.length <= 1 ? n.join("") : `${n.slice(0, -1).join(", ")} and ${n[n.length - 1]}`;
}

export function sureWord(conf: number) {
  return conf >= 0.9 ? "Very sure" : conf >= 0.75 ? "Sure" : conf >= 0.6 ? "Fairly sure" : "Unsure";
}
