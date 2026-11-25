# Making your own model: a beginner's guide

You don't need to know how to program. A **shape file** is a short text file that describes what to build, such as how long the body is or what colour the head is. The generator turns it into real LEGO pieces from a set you own.

There are three ways to make a shape file. Pick whichever sounds easiest:

1. **[Fill in the numbers](#way-1-fill-in-the-numbers-easiest)**: change sizes and colour names in a ready-made animal. No AI or programming needed.
2. **[Ask an AI chatbot](#way-2-ask-an-ai-chatbot)** such as ChatGPT or Claude to write one for you.
3. **[Let an AI coding tool do everything](#way-3-let-an-ai-coding-tool-do-everything)**: it writes the shape, builds it, looks at the result and fixes it.

Start with [one-time setup](#one-time-setup) whichever way you choose.

---

## One-time setup

You'll type a few commands into a window called a **terminal**. Copy them exactly.

1. **Install Python** (free) from [python.org/downloads](https://www.python.org/downloads/).
   - On Windows, tick **"Add python.exe to PATH"** on the first screen of the installer.
2. **Download this project.**
   1. On the GitHub page, click the green **Code** button, then **Download ZIP**.
   2. Unzip it somewhere easy to find, like your Documents folder.
3. **Open a terminal in that folder.**
   - **Windows:** open the folder, click the address bar at the top, type `cmd` and press Enter.
   - **Mac:** right-click the folder and choose **New Terminal at Folder**. If you don't see that option, open the Terminal app, type `cd ` (with a space after it), drag the folder into the window and press Enter.
4. **Install the helpers and download the parts data** (about 100 MB, once). Type:
   ```
   pip install -r requirements.txt
   python get_data.py
   ```
   On a Mac, use `pip3` and `python3` instead of `pip` and `python`, here and everywhere below.
5. **Optional:** for printable step-by-step instructions, install [LeoCAD](https://www.leocad.org) (free).

## What set will you build from?

You need the set's number, like `11045-1`. Look your set up on [rebrickable.com](https://rebrickable.com), where its number is shown at the top of the page. Most LEGO set numbers just get `-1` added on the end.

On the set's Rebrickable page, check which **colours** it has a lot of. Your model can only use those colours. A box of mostly bricks, like the **11045 Classic** boxes, needs `--bricks-only` in the commands below.

---

## Way 1: fill in the numbers (easiest)

1. **Make your own copy of the template.**
   1. Open the `shapes` folder.
   2. Copy `my_animal.py` and rename the copy, for example `my_dog.py`.
2. **Open your copy in a plain text editor:** Notepad on Windows, or TextEdit on a Mac (choose **Format → Make Plain Text**). Near the top is a block of settings:

   ```
   BODY_LENGTH = 10      # studs, nose-to-tail direction
   BODY_WIDTH = 6        # studs, side to side
   ...
   BODY_COLOUR = 'nougat'
   ```

   Only change the numbers and the colour names in quotes. Everything after `#` on a line is just a note.

   | Setting | What it does | Good range |
   |---|---|---|
   | `BODY_LENGTH`, `BODY_WIDTH` | Body size in **studs** (the bumps: a 2x4 brick is 2 by 4 studs) | 6–16, 4–10 |
   | `BODY_HEIGHT` | Body height in **bricks** | 2–5 |
   | `ROUNDNESS` | 2 = round, 3 = rounded, 6 = boxy | 2–6 |
   | `LEG_HEIGHT`, `LEG_THICKNESS` | Legs: bricks tall, studs thick (0 = no legs) | 0–4, 2–3 |
   | `HEAD_LENGTH`, `HEAD_WIDTH`, `HEAD_HEIGHT` | Head size (studs, studs, bricks) | 3–6, 3–6, 2–4 |
   | `HEAD_RAISE` | How far the head pokes up above the body, in bricks | 0–3 |
   | `SNOUT`, `EARS`, `TAIL` | Snout and tail length in studs; ears 1 = on, 0 = off | 0–2 |
   | `..._COLOUR` | Colour names, such as `'white'`, `'black'`, `'nougat'`, `'pink'`, `'lime'`, `'golden'` | the full list is further down in the file |

3. **Save, then preview it.** This takes a few seconds and doesn't use any LEGO pieces yet:
   ```
   python preview_shape.py shapes/my_dog.py --bricks-only
   ```
   Open `shapes/my_dog_preview.png` to see a blocky picture from two sides. Adjust the numbers and preview again until you like it.
4. **Build it with real pieces from your set:**
   ```
   python make_model.py 11045-1 shapes/my_dog.py out/my_dog.ldr --scale 1 --bricks-only --render --instructions
   ```
   This takes a few minutes. In the `out` folder you'll get:
   - `my_dog.png`: a picture of the real model.
   - `my_dog.ldr`: the model file, which opens in LeoCAD or BrickLink Studio.
   - `my_dog-instructions/instructions.html`: the build instructions.

Want something other than a four-legged animal? Use Way 2 or 3, or copy one of the other shapes in the folder (`pig.py`, `highland.py`, `sauropod.py`, `turtle.py`) and change its numbers.

---

## Way 2: ask an AI chatbot

Chatbots like ChatGPT, Claude or Gemini can write shape files well if you give them the rules. Copy the whole message below, fill in the parts in [brackets], and paste it into the chat.

> **Copy from here:**
>
> I'm using a LEGO model generator that builds a shape out of the parts of one LEGO set. Please write me a **shape file** (a short Python file) for: **[describe what you want, e.g. "a sitting cat, orange with a white chest"]**. I'm building it from set **[set number]**, which has these colours: **[list the main colours, e.g. white, black, red, medium nougat]**.
>
> Rules for the shape file:
> - The first line must be `GRID = (NX, NZ, NY)`, the size of the build space in cells. NX is length and NZ is width, in studs. NY is height in plates (3 plates = 1 brick). Leave a few cells of spare room on every side.
> - Set `TITLE = '...'`, `solid` (a True/False numpy array of filled cells), `col` (a same-shaped array of Rebrickable colour ids) and `KEYC` (a tuple of the colour ids that matter).
> - Some names are already defined for you; don't import them:
>   - `np`, `os`, and `X`, `Y`, `Z`: arrays of each cell's centre position, with shape (NX, NY, NZ).
>   - `SC`, the scale.
>   - `ell(centre, radii)` for an ellipsoid, and `sell(centre, radii, p)` for a rounded box (bigger p is boxier).
>   - `box(lo, hi)`.
>   - `studs(n)`, which turns n studs into shape units, and `snap(v)`, which moves a position onto a stud boundary.
> - Units are LDraw units *before* scaling: 20 = 1 stud wide, 8 = 1 plate tall, 24 = 1 brick tall. Divide by `SC` to work in real sizes: one stud is `studs(1)` and one brick is `24 / SC`. +Y is up from the table at Y = 0, and the front of the model faces −X or −Z.
> - Colour ids are Rebrickable ids: 0 black, 15 white, 4 red, 1 blue, 14 yellow, 2 green, 27 lime, 5 dark pink, 29 bright pink, 19 tan, 84 medium nougat, 70 reddish brown, 191 bright light orange, 71 light grey, 72 dark grey.
> - **Rules for a model that holds together** (these matter most):
>   - Make every feature at least 2 studs wide. Thinner bits disappear.
>   - Make features whole bricks tall. A helper like `band = lambda n: (Y > n*B) & (Y < (n+1)*B)` with `B = 24/SC` selects one brick layer.
>   - Bricks only hold by clicking onto bricks directly above or below. Anything that sticks out sideways (ears, horns, a tail, a snout) must have bricks above or below it to click into. Otherwise the generator removes it as loose. Put ears *on top of* the head, and let a snout overlap the face by at least one stud.
>   - Give the body straight sides. A layer that bulges out past the layers above and below it falls off.
>   - Make legs at least 2x2 studs, and run them one brick up into the body.
>   - Overlap joined parts (head and body, legs and body) by at least 2 studs.
> - Put a short comment at the top listing any settings I can change.
>
> Reply with only the file contents.

**Then:**
1. Save the reply as a new file in the `shapes` folder, for example `shapes/cat.py`.
   - In Notepad, choose **Save as type: All files**, so it isn't saved as `cat.py.txt`.
2. Preview it:
   ```
   python preview_shape.py shapes/cat.py --bricks-only
   ```
3. Show the chatbot the preview picture and say what to change, for example "the tail is too thin" or "make the ears bigger". Paste back any error message too. Repeat until it looks right.
4. Build it as in Way 1, step 4. Start with `--scale 1` and change the number if the model comes out too big or too small.
5. If the build summary says pieces were **"loose (removed)"**, tell the chatbot which part is missing from the picture. Ask it to give that part bricks above or below it to click onto.

---

## Way 3: let an AI coding tool do everything

AI coding tools can open this folder, write the shape, run the generator, look at the pictures and fix problems on their own. Examples are Claude Code, Cursor, GitHub Copilot and Codex.

The folder includes an instruction file for them, [AGENTS.md](AGENTS.md); Claude Code reads it through [CLAUDE.md](CLAUDE.md). Open the folder in the tool and ask in plain words, for example:

> *Make me a giraffe I can build from LEGO set 11045-1, and make the instructions.*

> *I own sets 21349 and 11045. Which one makes a better penguin?*

> *Make a cat and a dog that both build from one 11045 box.*

---

## Reading the results

When you run `make_model.py`, it builds several versions (called seeds) and keeps the best one. Each line of its summary tells you:

| It says | It means | Want |
|---|---|---|
| **pieces** | How many LEGO pieces the model uses | — |
| **loose (removed)** | Pieces that weren't clicked onto anything, which were left out | 0 |
| **cells unfilled** | Parts of the shape it ran out of bricks for | 0 |
| **off-colour** | Pieces that show in the wrong colour because the set ran short | 0 |

## When something goes wrong

| Problem | Fix |
|---|---|
| `python` isn't recognised | Reinstall Python and tick **Add to PATH**. On a Mac, type `python3`. |
| "Rebrickable data not found" | Run `python get_data.py` first. |
| A part is missing from the picture (ear, tail, eye) | It had nothing to click onto. Put it on top of something, or make it wider or taller. |
| Lots of **cells unfilled** | The model is too big for the set. Use a smaller `--scale` (try 0.8) or smaller sizes. |
| Lots of **off-colour** pieces | The set doesn't have enough of that colour. Pick a colour the set has more of. |
| The model looks lumpy or wrong | Try more seeds: add `--seeds 1-8`. Or change the shape a little and preview again. |
| "unknown colour" | Use a name from the `COLOURS` list in `my_animal.py`. |
| The model is too small or blocky | Make it bigger with `--scale`, or use bigger sizes. Small features need room. |

## Words used here

- **Stud**: one bump on top of a LEGO brick. Also used as a unit of width: a 2x4 brick is 2 studs by 4 studs.
- **Brick / plate**: a normal brick is 3 plates tall. Plates are the thin pieces.
- **Set number**: the number on the LEGO box, as written on [Rebrickable](https://rebrickable.com), such as `11045-1`.
- **Scale**: how big the model is built. Use 1 with `my_animal.py`; other shapes list a good scale in the README.
- **Seed**: a different random attempt at the same model. More seeds take longer, but give a better chance of a clean build.
