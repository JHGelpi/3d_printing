# CLAUDE.md — 3D Printing Project

## Project Overview

This project uses **Python** and **Blender's Python API (bpy)** to programmatically generate 3D models. Models are exported for slicing and printing on a **Bambu P2S** 3D printer.

## Tech Stack

- **Python** — scripting and model generation logic
- **Blender (bpy)** — 3D model creation, manipulation, and export
- **STL / 3MF** — primary export formats for the Bambu slicer (Bambu Studio)
- **Bambu P2S** — target printer (bed size: 256mm × 256mm × 256mm)

## Running Scripts

Blender scripts must be run within the Blender Python environment. Two common approaches:

```bash
# Run a script headlessly via Blender CLI
blender --background --python your_script.py

# Run with a specific .blend file
blender model.blend --background --python your_script.py
```

Standalone Python scripts that only use standard geometry math (no bpy) can run with a normal Python interpreter.

## Project Conventions

- Each model or model family lives in its own subdirectory (e.g., `models/widget/`)
- Scripts that generate models are named descriptively (e.g., `generate_bracket.py`)
- Exported files go in an `output/` directory (gitignored)
- Parameters (dimensions, tolerances, counts) should be defined as named constants at the top of each script, not buried as magic numbers

## Export Guidelines

- Export as **STL** for simple single-material prints
- Export as **3MF** when color, material assignments, or print settings need to be embedded
- Apply all transforms before export (`bpy.ops.object.transform_apply`)
- Ensure mesh is manifold (watertight) — use the 3D Print Toolbox addon to validate

## Printer Specs — Bambu P2S

| Property | Value |
|---|---|
| Build volume | 256 × 256 × 256 mm |
| Layer height | 0.05 – 0.35 mm (typical: 0.2 mm) |
| Nozzle diameter | 0.4 mm (default) |
| Max speed | 500 mm/s |
| Filament | 1.75 mm |
| Slicer | Bambu Studio |

## Design Tolerances

- Clearance fit (moving parts): +0.2 mm per side
- Press fit: +0.0 to +0.1 mm per side
- Minimum wall thickness: 1.2 mm (3× nozzle diameter)
- Minimum feature size: ~0.4 mm (1× nozzle diameter)

## Key bpy Patterns

```python
import bpy

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Add a mesh primitive
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
obj = bpy.context.active_object

# Apply transforms before export
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Export STL
bpy.ops.wm.stl_export(filepath="output/model.stl")

# Export 3MF
bpy.ops.wm.threemf_export(filepath="output/model.3mf")
```

## Output Directory

The `output/` directory is gitignored. Generated STL/3MF files go here. Keep source scripts in version control; exports are build artifacts.
