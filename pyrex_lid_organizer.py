"""
Pyrex Lid Organizer — Cabinet Insert
=====================================
Organizes round Pyrex lids (2.5"–4.25" dia.) standing upright, bookshelf-style.

Cabinet space : 15" W × 10" D × 9" H  →  381 × 254 × 228.6 mm
Lids          : 2.5"–4.25" dia. (63.5–107.95 mm), 0.5" (12.7 mm) thick, no knob
Layout        : 22 slots total — two identical 11-slot modules printed separately
Orientation   : Lids stand upright on edge; reach in from the front

HOW TO USE IN BLENDER:
  1. Open Blender 5.0 → Scripting workspace
  2. Open or paste this file, then click ▶ Run Script
  3. Two modules appear side-by-side in the viewport
  4. Print each module separately on the Bambu P2S
  5. Place modules flush side-by-side in the cabinet (combined width ≈ 380 mm)

PRINT NOTES:
  • Print flat (bottom face on bed) — footprint is ~190 × 254 mm, fits P2S bed
  • Each module is identical; no mirroring needed
  • Join the two modules with a dab of CA glue or a small clamp

CUSTOMIZATION (edit constants below):
  SLOT_W     — slot width; increase if lids feel tight
  WALL_T     — wall and divider thickness
  N_SLOTS    — slots per module
  GROOVE_D   — V-groove depth (deeper = more stable, less clearance)
  INNER_H    — slot height above the floor
  DEPTH      — front-to-back depth of the organizer
"""

import bpy
import bmesh

# ── PARAMETERS ──────────────────────────────────────────────────────────────
LID_THICK   = 12.7    # 0.5 in  — lid thickness (reference only)
LID_MAX_DIA = 107.95  # 4.25 in — maximum lid diameter (reference only)

SLOT_W      = 14.0    # slot width: LID_THICK + 1.3 mm clearance
WALL_T      = 3.0     # wall and divider thickness (min printable: 1.2 mm)
N_SLOTS     = 11      # slots per module  →  2 × 11 = 22 total

FLOOR_T     = 10.0    # floor slab thickness (must exceed GROOVE_D)
GROOVE_D    = 7.0     # V-groove depth; 45° sides, SLOT_W wide at top
INNER_H     = 120.0   # slot height above floor (LID_MAX_DIA + ~12 mm clearance)
DEPTH       = 254.0   # front-to-back depth (10 inches)

MODULE_GAP  = 20.0    # display gap between modules in viewport (not physical)
# ── DERIVED ─────────────────────────────────────────────────────────────────
SLOT_PITCH  = SLOT_W + WALL_T                  # 17 mm center-to-center
MODULE_W    = N_SLOTS * SLOT_PITCH + WALL_T    # 190 mm  (11×17 + 3)
MODULE_H    = FLOOR_T + INNER_H                # 130 mm
# ────────────────────────────────────────────────────────────────────────────


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)


def set_units_mm():
    scene = bpy.context.scene
    scene.unit_settings.system       = 'METRIC'
    scene.unit_settings.scale_length = 0.001
    scene.unit_settings.length_unit  = 'MILLIMETERS'


def add_box(name, x, y, z, w, d, h) -> bpy.types.Object:
    """
    Create a rectangular box with its corner at (x, y, z)
    and dimensions (w, d, h) in X, Y, Z respectively.
    """
    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=(x + w / 2, y + d / 2, z + h / 2)
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (w, d, h)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def boolean_diff(base: bpy.types.Object, cutter: bpy.types.Object) -> None:
    """Boolean-subtract cutter from base, then delete the cutter."""
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = base
    base.select_set(True)

    mod = base.modifiers.new(name="BoolDiff", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object    = cutter
    mod.solver    = 'EXACT'

    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def make_vgroove_cutter(name, cx, y_start, y_end) -> bpy.types.Object:
    """
    Build a triangular prism that, when subtracted from the floor,
    produces a V-groove running front-to-back.

    Cross-section in XZ (at any Y slice):

        z = FLOOR_T  ──────●───────●──────   ← floor top surface
                           │╲     ╱│
                           │  ╲ ╱  │         (45° walls)
        z = FLOOR_T        │   ●   │         ← apex
            - GROOVE_D     └───────┘

        ← SLOT_W (14 mm) →

    The cutter base extends 0.1 mm above the floor surface so the
    boolean always cleanly pierces the face.
    """
    mesh = bpy.data.meshes.new(name + "Mesh")
    obj  = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    bm = bmesh.new()

    z_top  = FLOOR_T + 0.1      # slightly above floor surface
    z_apex = FLOOR_T - GROOVE_D # bottom of the V
    hw     = SLOT_W / 2         # half-width of groove = 7 mm  (gives 45°)

    # Front triangle (at y_start)
    fL = bm.verts.new((cx - hw, y_start, z_top))
    fR = bm.verts.new((cx + hw, y_start, z_top))
    fA = bm.verts.new((cx,      y_start, z_apex))

    # Back triangle (at y_end)
    bL = bm.verts.new((cx - hw, y_end, z_top))
    bR = bm.verts.new((cx + hw, y_end, z_top))
    bA = bm.verts.new((cx,      y_end, z_apex))

    bm.faces.new([fL, fA, fR])       # front  (normal toward -Y)
    bm.faces.new([bL, bR, bA])       # back   (normal toward +Y)
    bm.faces.new([fL, fR, bR, bL])   # top    (base of V, normal toward +Z)
    bm.faces.new([fL, bL, bA, fA])   # left wall
    bm.faces.new([fR, fA, bA, bR])   # right wall

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    return obj


def build_module(name: str, x_offset: float = 0.0) -> bpy.types.Object:
    """
    Build one organizer module.

    Strategy: start with a solid rectangular block, then subtract:
      1. N_SLOTS slot pockets  — open at the front (y=0) and top (z=MODULE_H)
                                  closed at the back by a WALL_T-thick rear stop
      2. N_SLOTS V-grooves     — cut into the floor so lids self-center

    Resulting structure (cross-section viewed from above, Y = depth):

        ┌──┬──────┬──┬──────┬──┐   ← back wall (y = DEPTH)
        │  │ slot │  │ slot │  │
        │  │      │  │      │  │
        │  │      │  │      │  │
        └──┴──────┴──┴──────┴──┘   ← front, open (y = 0)
        wall divider wall …

    Module dimensions:
        Width  : MODULE_W = N_SLOTS × SLOT_PITCH + WALL_T = 190 mm
        Depth  : DEPTH = 254 mm
        Height : MODULE_H = FLOOR_T + INNER_H = 130 mm
    """
    # ── 1. Solid body ────────────────────────────────────────────────────────
    body = add_box(name, x_offset, 0, 0, MODULE_W, DEPTH, MODULE_H)

    # ── 2. Cut slot pockets ──────────────────────────────────────────────────
    # Each pocket removes the material between the dividers/walls,
    # from the front face to WALL_T short of the back (rear stop),
    # and from the top of the floor up through the top of the module.
    pocket_depth  = DEPTH - WALL_T          # 251 mm  (leaves back stop)
    pocket_height = INNER_H + 1.0           # 121 mm  (+1 ensures clean top cut)

    for i in range(N_SLOTS):
        px = x_offset + WALL_T + i * SLOT_PITCH
        pocket = add_box(
            f"_pkt_{name}_{i}",
            px, -0.1, FLOOR_T,              # -0.1 in Y: ensures front face cut
            SLOT_W, pocket_depth + 0.1, pocket_height
        )
        boolean_diff(body, pocket)

    # ── 3. Cut V-grooves into the floor ──────────────────────────────────────
    # Groove runs the full depth so lids are supported regardless of placement.
    for i in range(N_SLOTS):
        cx = x_offset + WALL_T + i * SLOT_PITCH + SLOT_W / 2
        groove = make_vgroove_cutter(f"_grv_{name}_{i}", cx, -0.1, DEPTH + 0.1)
        boolean_diff(body, groove)

    return body


def main():
    clear_scene()
    set_units_mm()

    # Build Module L (left) and Module R (right)
    # In Blender they are shown with a gap; when printing, place flush together.
    mod_l = build_module("Module_L", x_offset=0.0)
    mod_r = build_module("Module_R", x_offset=MODULE_W + MODULE_GAP)

    # Deselect all, then select both for easy inspection
    bpy.ops.object.select_all(action='DESELECT')
    mod_l.select_set(True)
    mod_r.select_set(True)
    bpy.context.view_layer.objects.active = mod_l

    # Zoom viewport to fit
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            region = next((r for r in area.regions if r.type == 'WINDOW'), None)
            if region:
                with bpy.context.temp_override(area=area, region=region):
                    bpy.ops.view3d.view_all()
            break

    total_slots = N_SLOTS * 2
    print("=" * 58)
    print("  Pyrex Lid Organizer — generated!")
    print(f"  Modules    : 2 × {MODULE_W:.0f} mm wide — print each separately")
    print(f"  Total slots: {total_slots}  ({N_SLOTS} per module)")
    print(f"  Slot width : {SLOT_W:.1f} mm  |  Pitch : {SLOT_PITCH:.0f} mm")
    print(f"  Module H   : {MODULE_H:.0f} mm  |  Depth : {DEPTH:.0f} mm")
    print(f"  V-groove   : {SLOT_W:.0f} mm wide × {GROOVE_D:.0f} mm deep (45°)")
    print(f"  Lid range  : up to {LID_MAX_DIA:.1f} mm dia, {LID_THICK:.1f} mm thick")
    print(f"  Cabinet fit: {MODULE_W * 2:.0f} mm W × {DEPTH:.0f} mm D × {MODULE_H:.0f} mm H")
    print("=" * 58)
    print("  Assembly:")
    print("  • Print Module_L and Module_R separately (flat on bed)")
    print("  • Place flush side-by-side; join with CA glue or clamp")
    print("  • Export each via File > Export > STL or 3MF")
    print("=" * 58)


main()
