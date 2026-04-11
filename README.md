# 3D Printing — Parametric Model Generator

A collection of Python scripts that programmatically generate 3D models using Blender's `bpy` API. Models are exported as STL or 3MF and sliced in Bambu Studio for printing on a Bambu P2S.

---

## Why Scripts Instead of a GUI?

Parametric scripting lets you:
- Adjust dimensions, tolerances, and hole counts by changing a single constant
- Regenerate a model instantly without re-drawing it by hand
- Version-control your designs alongside your code
- Batch-produce variations (different sizes, materials, mounting patterns)

---

## Printer

| Property | Value |
|---|---|
| Printer | Bambu P2S |
| Build volume | 256 × 256 × 256 mm |
| Nozzle | 0.4 mm |
| Filament | 1.75 mm |
| Slicer | Bambu Studio |

---

## Project Structure

```
3d_printing/
├── models/               # One subdirectory per model family
│   └── <model-name>/
│       └── generate_<model>.py
├── output/               # Generated STL/3MF files (gitignored)
├── CLAUDE.md             # AI assistant context and project conventions
└── README.md
```

> Scripts are version-controlled. Exported files in `output/` are build artifacts and are gitignored.

---

## Models

### 4×4 L-Bracket (`4x4_L_Bracket.py`)

A 90° structural L-bracket with a diagonal gusset for added rigidity.

| Parameter | Value |
|---|---|
| Arm length | 101.6 mm (4 in) each |
| Width | 30 mm |
| Thickness | 5 mm |
| Screw holes | 4× M4 (2 per arm) |
| Gusset reach | 50 mm along each arm (45° bisector) |

**Tunable constants at the top of the script:**

```python
L             = 101.6   # arm length (mm)
W             = 30.0    # bracket width (mm)
T             = 5.0     # wall thickness (mm)
HOLE_D        = 4.2     # screw hole diameter (M4)
HOLE_OFFSET   = 20.0    # distance from arm tip to hole center (mm)
GUSSET_REACH  = 50.0    # diagonal gusset extent along each arm (mm)
```

---

## Running a Script

Scripts must run inside Blender's Python environment.

**Option 1 — Blender Scripting workspace (recommended for development):**
1. Open Blender
2. Switch to the **Scripting** workspace
3. Open or paste the script
4. Click **▶ Run Script**

**Option 2 — Headless CLI (for automation/CI):**
```bash
blender --background --python 4x4_L_Bracket.py
```

---

## Exporting for Bambu Studio

| Format | When to use |
|---|---|
| **STL** | Single-material prints |
| **3MF** | Multi-color, material assignments, or embedded print settings |

Always apply transforms before export:
```python
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
```

---

## Design Tolerances

| Fit type | Clearance per side |
|---|---|
| Clearance (moving parts) | +0.2 mm |
| Press fit | +0.0 – +0.1 mm |
| Minimum wall thickness | 1.2 mm (3× nozzle) |
| Minimum feature size | 0.4 mm (1× nozzle) |


## Project Overview

This project uses **Python** and **Blender's Python API (bpy)** to programmatically generate 3D models. Models are exported for slicing and printing on a **Bambu P2S** 3D printer.

## Code Merges

All code changes should come with a precise and accurate summary for github code commit comments.

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
