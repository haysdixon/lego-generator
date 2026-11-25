# Guide for AI coding agents

This repo builds new LEGO models from one set's parts. Users are often non-technical: they describe an animal and a set number in plain words. Your job is to write the shape, build it, check it, fix it, and hand back the files.

## Setup check

- `data/inventory_parts.csv.gz` and `ldraw/LDConfig.ldr` must exist. If they don't, run `python get_data.py`.
- Build instructions need LeoCAD. If `--instructions` fails with "LeoCAD not found", tell the user to install it from https://www.leocad.org, or set `LEOCAD`.
- Use the same Python the user would (`python`, or `python3` on macOS, or `py -3` on Windows).

## Workflow

1. **Pick the set and colours.**
   - Find the set number (`NNNNN-1`) and the colours it has plenty of. Search `data/inventory_parts.csv.gz` and `data/colors.csv.gz` (Rebrickable ids).
   - If the user owns several sets, or asks which set to buy: `python generator/find_sets.py shape SHAPE.py --top 20`. For `my_animal.py` copies, add `--scales 1`.
   - If the set is mostly bricks with few plates (for example, the 11045 Classic boxes), use `--bricks-only` everywhere.
2. **Write the shape** in `shapes/NAME.py`.
   - For a four-legged animal, prefer copying `shapes/my_animal.py` and changing its settings. It is built to hold together.
   - Otherwise, start from the closest example: `pig.py`, `highland.py`, `holstein.py`, `sauropod.py` or `turtle.py`.
3. **Preview** with `python preview_shape.py shapes/NAME.py [--scale S] [--bricks-only]` and look at the PNG yourself. It takes seconds. Fix proportions here before building.
4. **Build:** `python make_model.py SET shapes/NAME.py out/NAME.ldr --scale S [--bricks-only] --render`. Read the per-seed summary, then look at `out/NAME.png`.
5. **Iterate until the best seed has 0 loose, 0 unfilled and 0 off-colour,** and the render clearly reads as the animal. Then rerun with `--instructions`.
6. **Hand back:** the `.png`, `.ldr` and `NAME-instructions/instructions.html` paths, the piece count, and the exact command used.

## Shape file contract

- The first line is `GRID = (NX, NZ, NY)`: cells are 1 stud in x and z, and 1 plate in y. Keep 2+ cells of margin.
- Set `TITLE`, `solid` (a bool array of shape `(NX, NY, NZ)`), `col` (int Rebrickable colour ids, same shape) and `KEYC` (a tuple of important colours).
- Provided names, which you must not import:
  - `np`, `os`, and `X`, `Y`, `Z` (cell centres in raw units).
  - `SC` (the scale).
  - `ell(c, r)`, `sell(c, r, p)` and `box(lo, hi)`.
  - `studs(n)` (raw units for n studs) and `snap(v)` (onto a stud boundary).
- Raw units are LDraw units before scaling: 20 per stud, 8 per plate, 24 per brick. The grid sees `raw * SC`. So write sizes as `studs(n)` and `B = 24 / SC` to keep them right at any scale.
- Y = 0 is the table and +Y is up. Pick a front (−X or −Z) and say so in a comment.
- Expose tweakables as env settings, read with `os.environ.get('NAME', default)`. Users set them with `--var NAME=VALUE`.

## Rules that decide whether a model holds together

These come from building the examples. Breaking them shows up as "loose (removed)".

- **Connections are vertical only.** A piece is attached only through studs into the piece directly above or below it. Anything held only from the side gets removed: tails, snouts, ears, eyes, horns.
  - Put ears and horns *on top of* cells that exist in the layer below. `pig.py` does this with the `headtop` footprint.
  - A horn or tail can overhang by 1 stud if its inner end sits on top of the body. See the horns in `highland.py`.
  - Eyes need head bricks above *and* below their layer. See the 3-brick-tall head in `sauropod.py`.
- **Straight sides, not bulges.** In brick-only builds, a layer wider than the layers above and below has an outer ring that can fall off. Use straight walls and round only the plan view and the top layer. The `rounded()` helper in `my_animal.py` does this.
- **Whole bricks** for brick-only sets. Size features in multiples of `B = 24 / SC` and align them to brick bands: `band(n) = (Y > n*B) & (Y < (n+1)*B)`.
- **Minimum size.** Make features at least 2 studs wide. Legs should be 2x2 studs, snapped with `snap()`, and should reach one brick into the body.
- **Overlap joined parts.** Overlap head and body, or neck and body, by at least 2 studs in plan, so bricks span the join.
- **Colours.** The set's colour counts are a hard limit.
  - A visible colour the set lacks becomes off-colour. Use `--colmap A=B` or choose another colour.
  - Big areas of one colour can run the set dry. Hidden interior cells can be any colour: the generator fills the inside with spare pieces.
  - Some sets have only 4 of a large brick per colour, such as the 2x6 in 11045.

## Reading results

- **SUMMARY fields** (in `out/_runs/NAME_SEED.log`):
  - `pieces`.
  - `dropped`: loose pieces removed. These are listed on the next line as (part, colour, layer), and layer // 3 is the brick band.
  - `missing`: cells left unfilled.
  - `wrongcolour`: visible pieces in the wrong colour.
  - `edits`.
  - `components`: clumps before removal; 1 means nothing was loose.
- **The dropped list is your best clue.** Its layer and colour tell you which feature fell off.
- **More seeds** (`--seeds 1-8`) find cleaner builds. If every seed drops the same feature, fix the shape; don't add seeds.
- **Several models from one box:**
  - Build them in order with `--after earlier.ldr ...`. This builds each model from only the bricks left over.
  - Build the models that need scarce bricks first.
  - Check the total with the per-part counts against the set inventory if the user asks.

## Don'ts

- Don't edit `generator/` to fix one shape's problem. Change the shape.
- Don't claim prices, set contents or availability without reading them from `data/`, or from a page you actually opened.
- Don't put the user's personal details in files that might be shared.
