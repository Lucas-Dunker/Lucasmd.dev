// Shared by AsciiHead.astro's frontmatter (poster frame) and its client script
// (playback), so both render the clip from exactly the same geometry.
import data from "./frames.json";

const raw = data as unknown as {
  cols: number;
  rows: number;
  fps: number;
  palette: string[];
  frames: string[];
};

export const { cols, fps, palette } = raw;

// Frame wire format (see src/scripts/generate.py): one string per frame, rows
// separated by "\n", and within a row the colour runs separated by "|", each
// run being a one-char tag followed by its glyphs. Tags: "0".."N" index into
// `palette`, "w" is the white sunglasses shine, " " is background. A blank row
// is the empty string -- trailing background runs are dropped, so a row is
// inked exactly when it is non-empty.
//
// It decodes to a handful of strings rather than the ~43k two-element arrays a
// JSON-of-runs costs. Over the wire the two are within 2KB of each other once
// gzipped; the difference is the parse and allocation the browser does.
const SEP = "|";

// generate.py centres a single crop window on the ink centroid and pads it, so
// the window can open with rows that are blank in every frame. Those render as
// dead lines above the head and push everything below it down the page.
const grid = raw.frames.map((f) => f.split("\n"));
let top = 0;
while (top < raw.rows - 1 && grid.every((f) => f[top] === "")) top++;

export const frames = grid.map((f) => f.slice(top));
export const rows = raw.rows - top;

const rowToHtml = (row: string) =>
  row === ""
    ? ""
    : row
        .split(SEP)
        .map((run) => {
          const text = run.slice(1);
          if (run[0] === " ") return text;
          const cls = run[0] === "w" ? "cw" : "c" + run[0];
          return `<span class="${cls}">${text}</span>`;
        })
        .join("");

export const frameToHtml = (frame: string[]) => frame.map(rowToHtml).join("\n");

// Length of the white shine, used to pick the poster frame.
export const shineLength = (frame: string[]) =>
  frame.reduce(
    (n, row) =>
      row
        .split(SEP)
        .reduce((m, run) => m + (run[0] === "w" ? run.length - 1 : 0), n),
    0,
  );
