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

# General
This project is used to track my 3D printing models

<!-- rtk-instructions v2 -->
# RTK (Rust Token Killer) - Token-Optimized Commands

## Golden Rule

**Always prefix commands with `rtk`**. If RTK has a dedicated filter, it uses it. If not, it passes through unchanged. This means RTK is always safe to use.

**Important**: Even in command chains with `&&`, use `rtk`:
```bash
# ❌ Wrong
git add . && git commit -m "msg" && git push

# ✅ Correct
rtk git add . && rtk git commit -m "msg" && rtk git push
```

## RTK Commands by Workflow

### Build & Compile (80-90% savings)
```bash
rtk cargo build         # Cargo build output
rtk cargo check         # Cargo check output
rtk cargo clippy        # Clippy warnings grouped by file (80%)
rtk tsc                 # TypeScript errors grouped by file/code (83%)
rtk lint                # ESLint/Biome violations grouped (84%)
rtk prettier --check    # Files needing format only (70%)
rtk next build          # Next.js build with route metrics (87%)
```

### Test (90-99% savings)
```bash
rtk cargo test          # Cargo test failures only (90%)
rtk vitest run          # Vitest failures only (99.5%)
rtk playwright test     # Playwright failures only (94%)
rtk test <cmd>          # Generic test wrapper - failures only
```

### Git (59-80% savings)
```bash
rtk git status          # Compact status
rtk git log             # Compact log (works with all git flags)
rtk git diff            # Compact diff (80%)
rtk git show            # Compact show (80%)
rtk git add             # Ultra-compact confirmations (59%)
rtk git commit          # Ultra-compact confirmations (59%)
rtk git push            # Ultra-compact confirmations
rtk git pull            # Ultra-compact confirmations
rtk git branch          # Compact branch list
rtk git fetch           # Compact fetch
rtk git stash           # Compact stash
rtk git worktree        # Compact worktree
```

Note: Git passthrough works for ALL subcommands, even those not explicitly listed.

### GitHub (26-87% savings)
```bash
rtk gh pr view <num>    # Compact PR view (87%)
rtk gh pr checks        # Compact PR checks (79%)
rtk gh run list         # Compact workflow runs (82%)
rtk gh issue list       # Compact issue list (80%)
rtk gh api              # Compact API responses (26%)
```

### JavaScript/TypeScript Tooling (70-90% savings)
```bash
rtk pnpm list           # Compact dependency tree (70%)
rtk pnpm outdated       # Compact outdated packages (80%)
rtk pnpm install        # Compact install output (90%)
rtk npm run <script>    # Compact npm script output
rtk npx <cmd>           # Compact npx command output
rtk prisma              # Prisma without ASCII art (88%)
```

### Files & Search (60-75% savings)
```bash
rtk ls <path>           # Tree format, compact (65%)
rtk read <file>         # Code reading with filtering (60%)
rtk grep <pattern>      # Search grouped by file (75%)
rtk find <pattern>      # Find grouped by directory (70%)
```

### Analysis & Debug (70-90% savings)
```bash
rtk err <cmd>           # Filter errors only from any command
rtk log <file>          # Deduplicated logs with counts
rtk json <file>         # JSON structure without values
rtk deps                # Dependency overview
rtk env                 # Environment variables compact
rtk summary <cmd>       # Smart summary of command output
rtk diff                # Ultra-compact diffs
```

### Infrastructure (85% savings)
```bash
rtk docker ps           # Compact container list
rtk docker images       # Compact image list
rtk docker logs <c>     # Deduplicated logs
rtk kubectl get         # Compact resource list
rtk kubectl logs        # Deduplicated pod logs
```

### Network (65-70% savings)
```bash
rtk curl <url>          # Compact HTTP responses (70%)
rtk wget <url>          # Compact download output (65%)
```

### Meta Commands
```bash
rtk gain                # View token savings statistics
rtk gain --history      # View command history with savings
rtk discover            # Analyze Claude Code sessions for missed RTK usage
rtk proxy <cmd>         # Run command without filtering (for debugging)
rtk init                # Add RTK instructions to CLAUDE.md
rtk init --global       # Add RTK to ~/.claude/CLAUDE.md
```

## Token Savings Overview

| Category | Commands | Typical Savings |
|----------|----------|-----------------|
| Tests | vitest, playwright, cargo test | 90-99% |
| Build | next, tsc, lint, prettier | 70-87% |
| Git | status, log, diff, add, commit | 59-80% |
| GitHub | gh pr, gh run, gh issue | 26-87% |
| Package Managers | pnpm, npm, npx | 70-90% |
| Files | ls, read, grep, find | 60-75% |
| Infrastructure | docker, kubectl | 85% |
| Network | curl, wget | 65-70% |

Overall average: **60-90% token reduction** on common development operations.
<!-- /rtk-instructions -->
