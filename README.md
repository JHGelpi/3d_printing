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
