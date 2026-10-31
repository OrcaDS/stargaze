import { STORY_DAMAGE } from "./data";

// Hand-picked examples (both models right when clean, the ordinary model confidently wrong once
// broken). The exporter's test checks the real answers still tell these stories.
const TEXT = [
  {
    blurb: "A cloud wipes out a quasar’s green and red readings.",
    captions: [
      "A quasar with all five readings. Both readers get it right.",
      "A cloud drifts past: green and red are lost. Those two slots are now empty. Not zero, just nothing.",
      "The ordinary model is very sure it’s a star. Stargaze still says quasar.",
    ],
    take: "Two missing colours pushed the ordinary model into a confident wrong answer. Stargaze had practised with gaps, so it wasn’t thrown.",
  },
  {
    blurb: "A galaxy measured with a badly shaking telescope.",
    captions: [
      "A galaxy, measured cleanly. Both readers get it right.",
      "Now the telescope shakes: every reading is 8 times less precise than normal. Each bar could be anywhere in its fuzzy range.",
      "The ordinary model reads the wobble as a star. Stargaze still says galaxy.",
    ],
    take: "Shaky numbers fooled the ordinary model. Stargaze had practised on shaky copies and still found the galaxy.",
  },
  {
    blurb: "One quasar reading gets a misplaced decimal point.",
    captions: [
      "A quasar, cleanly measured. Both readers get it right.",
      "Someone writes near-infrared as 180.1 instead of 18.01. One misplaced decimal point, and the reading drops off the scale.",
      "The input check spots the impossible value and blanks it for both readers. The ordinary model has never seen a gap and says galaxy. Stargaze still says quasar.",
    ],
    take: "Catching the typo wasn’t enough: the blank it leaves still fooled the ordinary model. Stargaze had practised with gaps and kept its answer.",
  },
];

export const STORIES = STORY_DAMAGE.map((s, i) => ({ ...s, ...TEXT[i] }));
export const STEP_LABELS = ["1 Clean", "2 Damage", "3 Reactions", "4 Takeaway"];
