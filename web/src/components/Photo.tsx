import { type CSSProperties, useState } from "react";
import { cutout, type SkyObject } from "../data";

// The picture is for people only: it comes straight from SDSS and never reaches a model.
export default function Photo({ obj, machine, small = false }: { obj: SkyObject; machine: boolean; small?: boolean }) {
  const [failed, setFailed] = useState(false);
  const point = obj.type !== "Galaxy";
  return (
    <div className="relative aspect-square w-full overflow-hidden rounded-[18px] bg-sky shadow-[inset_0_0_0_1px_rgb(255_255_255/0.06)]">
      <div className={`scene ${machine ? "machine" : ""} ${failed ? "sketch" : ""}`}>
        {failed ? (
          <span
            className={point ? "o-point" : "o-fuzzy"}
            style={{ "--s": small ? "30px" : "40px", "--glow": obj.type === "Quasar" ? "#b9d4ff" : "#ffe2ad" } as CSSProperties}
          />
        ) : (
          <img
            src={cutout(obj)}
            alt={`Telescope photo of ${obj.tag}`}
            className="h-full w-full object-cover"
            onError={() => setFailed(true)}
          />
        )}
      </div>
      {machine && (
        <div className="fade absolute inset-0 flex items-center justify-center p-4 text-center text-[15px] font-semibold text-[#eaedf5]">
          {small ? "Hidden. The models never get this." : "Hidden. The models never get the picture, only what the five filters measured."}
        </div>
      )}
      <span className="absolute right-2.5 bottom-2.5 left-2.5 rounded-lg bg-black/45 px-2 py-1 text-[11px] text-[#c9cfdd]">
        {failed ? "Sketch: the photo couldn’t load" : obj.tag}
      </span>
    </div>
  );
}
