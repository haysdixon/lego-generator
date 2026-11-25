# Fill-in templates, built from LEGO 11045

Each model is one of the `shapes/my_*.py` templates with its default settings, built from its own 11045 Creative Colorful Bricks box. These are separate builds, not all six from one box. Every one came out clean: no loose pieces, nothing unfilled, every colour right, and no cells changed.

| Model | Template | Bricks | Steps | Instructions |
|---|---|---|---|---|
| Four-legged animal | [my_animal.py](../../../shapes/my_animal.py) | 48 | 7 | [animal-instructions](animal-instructions/instructions.html) |
| Mug | [my_mug.py](../../../shapes/my_mug.py) | 64 | 5 | [mug-instructions](mug-instructions/instructions.html) |
| Heart | [my_heart.py](../../../shapes/my_heart.py) | 33 | 10 | [heart-instructions](heart-instructions/instructions.html) |
| House | [my_house.py](../../../shapes/my_house.py) | 139 | 10 | [house-instructions](house-instructions/instructions.html) |
| Car | [my_car.py](../../../shapes/my_car.py) | 64 | 5 | [car-instructions](car-instructions/instructions.html) |
| HELLO in block letters | [my_letters.py](../../../shapes/my_letters.py) | 94 | 9 | [letters-instructions](letters-instructions/instructions.html) |

To rebuild one:

```
python make_model.py 11045-1 shapes/my_house.py out/house.ldr --scale 1 --bricks-only --seeds 1-8 --render --instructions
```

Some steps show bricks of another colour inside a model. They are hidden fillers and don't show once it's built.
