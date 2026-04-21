"""
Panel with L-Brackets — bpy Generator
----------------------------------------------
Generates a rectangular panel with semi-circle hole and mounting L-brackets.

Features:
  • Rectangular panel with configurable dimensions
  • Semi-circle hole on one long edge (for cable routing, etc.)
  • Two L-brackets flush with the same long edge for mounting
  • All dimensions fully parameterized

Coordinate system (all mm):
  X = panel width (short dimension)
  Y = panel length (long dimension)
  Z = panel thickness (vertical)
  Origin at panel center
"""

import math
import os

import bmesh
import bpy

# ════════════════════════════════════════════════════════════════
#  PARAMETERS  —  all dimensions in mm
# ════════════════════════════════════════════════════════════════

# ── Main panel ────────────────────────────────────────────────────
PANEL_WIDTH = 130  # mm (5.125 cm) — short dimension (X)
PANEL_LENGTH = 431.8  # mm (43.18 cm) — long dimension (Y)
PANEL_THICKNESS = 5.0  # mm (0.5 cm) — panel thickness (Z)

# ── Semi-circle cutout ────────────────────────────────────────────
# Cutout is on the +X edge (right long edge), for cable routing
HOLE_DIAMETER = 12.7  # mm (1.27 cm) — diameter of semi-circle cutout
HOLE_Y_POSITION = 0.0  # mm — position along Y axis (0 = centered)

# ── L-brackets ────────────────────────────────────────────────────
# Two L-brackets on the +X edge (same edge as semi-circle cutout)
# Brackets are flush with the edge and protrude perpendicular to panel
NUM_BRACKETS = 2  # number of L-brackets
BRACKET_SPACING = 300.0  # mm — distance between bracket centers along Y
BRACKET_THICKNESS = 5.0  # mm — bracket wall thickness (same as panel for flush fit)

# Vertical part (attached to panel face)
BRACKET_VERT_WIDTH = 30.0  # mm — width along Y axis
BRACKET_VERT_HEIGHT = 20.0  # mm — height along Z axis (how far it extends from panel)

# Horizontal part (protruding perpendicular to panel)
BRACKET_HORIZ_LENGTH = 20.0  # mm — length along X axis (protrusion distance)
BRACKET_HORIZ_WIDTH = 30.0  # mm — width along Y axis (same as vertical for continuity)

# Optional: screw holes in brackets (set to 0 to disable)
BRACKET_SCREW_HOLES = 1  # number of screw holes per bracket (0 = none)
BRACKET_SCREW_D = 4.0  # mm — screw hole diameter

# ── Mesh quality ──────────────────────────────────────────────────
HOLE_SEGS = 32
BOOL_EXTRA = 2.0  # mm — cutter overshoot for clean boolean results


# ════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for datablock in (bpy.data.meshes, bpy.data.materials, bpy.data.curves):
        for item in datablock:
            datablock.remove(item)


def box(name, cx, cy, cz, sx, sy, sz):
    """Box centred at (cx, cy, cz) with full dimensions (sx, sy, sz)."""
    bpy.ops.mesh.primitive_cube_add(location=(cx, cy, cz))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (sx / 2, sy / 2, sz / 2)
    bpy.ops.object.transform_apply(scale=True)
    return obj


def bool_diff(target, cutter):
    """Subtract cutter from target in-place, then remove cutter."""
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    cutter.hide_viewport = False
    mod = target.modifiers.new("Bool", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "EXACT"
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def bool_union(target, obj_to_merge):
    """Union obj_to_merge into target in-place, then remove obj_to_merge."""
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    obj_to_merge.hide_viewport = False
    mod = target.modifiers.new("BoolUnion", "BOOLEAN")
    mod.operation = "UNION"
    mod.object = obj_to_merge
    mod.solver = "EXACT"
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(obj_to_merge, do_unlink=True)


def make_cylinder_cutter(name, cx, cy, cz, radius, height, segs=HOLE_SEGS):
    """
    Solid cylinder centred at (cx, cy, cz), aligned with Z axis.
    """
    bm = bmesh.new()
    ret = bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=segs,
        radius1=radius,
        radius2=radius,
        depth=height,
    )
    bmesh.ops.translate(bm, verts=ret["verts"], vec=(cx, cy, cz))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def make_semicircle_cutter(name, cx, cy, cz, diameter, depth, segs=HOLE_SEGS):
    """
    Creates a half-cylinder cutter for a semi-circle hole on the edge.
    The flat face is at Y = cy, and the curved part extends in -Y direction.
    Aligned with X axis (horizontal).

    Parameters:
    - cx, cy, cz: center position (cy is at the edge)
    - diameter: diameter of the semi-circle
    - depth: depth along X axis (panel width)
    - segs: number of segments for the curve
    """
    radius = diameter / 2
    bm = bmesh.new()

    # Create half-circle profile in YZ plane
    # Front face (X = -depth/2) and back face (X = +depth/2)
    x0, x1 = -depth / 2, depth / 2

    # Create vertices for semi-circle (180 degrees)
    front_verts = []
    back_verts = []

    # Start at one end of diameter (Y=0, Z=-radius)
    front_verts.append(bm.verts.new((cx + x0, cy, cz - radius)))
    back_verts.append(bm.verts.new((cx + x1, cy, cz - radius)))

    # Add vertices along the arc (from bottom to top)
    for i in range(1, segs):
        angle = math.pi * i / segs  # 0 to π
        y_offset = -radius * math.cos(angle)  # Extends in -Y
        z_offset = -radius * math.sin(angle)  # Goes from -radius to +radius
        front_verts.append(bm.verts.new((cx + x0, cy + y_offset, cz + z_offset)))
        back_verts.append(bm.verts.new((cx + x1, cy + y_offset, cz + z_offset)))

    # End at other end of diameter (Y=0, Z=+radius)
    front_verts.append(bm.verts.new((cx + x0, cy, cz + radius)))
    back_verts.append(bm.verts.new((cx + x1, cy, cz + radius)))

    bm.verts.ensure_lookup_table()

    n = len(front_verts)

    # Create front and back faces
    bm.faces.new(front_verts)
    bm.faces.new(list(reversed(back_verts)))

    # Create side faces
    for i in range(n - 1):
        bm.faces.new(
            [front_verts[i], back_verts[i], back_verts[i + 1], front_verts[i + 1]]
        )

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


# ════════════════════════════════════════════════════════════════
#  BUILD
# ════════════════════════════════════════════════════════════════

clear_scene()
col = bpy.data.collections.new("Panel_Assembly")
bpy.context.scene.collection.children.link(col)


# ── 1. MAIN PANEL ─────────────────────────────────────────────────
# Rectangular slab centered at origin

panel = box(
    "Panel",
    0,
    0,
    0,
    PANEL_WIDTH,
    PANEL_LENGTH,
    PANEL_THICKNESS,
)
col.objects.link(panel)
try:
    bpy.context.scene.collection.objects.unlink(panel)
except RuntimeError:
    pass


# ── 2. SEMI-CIRCLE CUTOUT ────────────────────────────────────────
# Cut semi-circle notch on the +X edge (right long edge) for cable routing
# The cutout is centered at Y=0, cuts into the edge like a scoop

# Create a cylinder cutter oriented along the Z axis (through panel thickness)
# Position it so half is inside the panel edge, half is outside
radius = HOLE_DIAMETER / 2
hole_cx = PANEL_WIDTH / 2  # At the +X edge
hole_cy = HOLE_Y_POSITION  # Centered along Y (0 = middle of panel)
hole_cz = 0  # At mid-thickness of panel

semicircle_cutter = make_cylinder_cutter(
    "SemicircleCutout",
    hole_cx,
    hole_cy,
    hole_cz,
    radius,
    PANEL_THICKNESS + 2 * BOOL_EXTRA,  # Cut through entire thickness
)
bool_diff(panel, semicircle_cutter)


# ── 3. L-BRACKETS ─────────────────────────────────────────────────
# Two L-brackets on the +X edge (right long edge), evenly spaced
# Brackets protrude in +X direction (perpendicular to panel edge)
# The "L" is formed by the panel face and the protruding bracket piece

for i in range(NUM_BRACKETS):
    if NUM_BRACKETS == 1:
        bracket_y = 0  # Single bracket at center
    else:
        # Evenly space brackets along Y axis
        bracket_y = -BRACKET_SPACING / 2 + i * BRACKET_SPACING

    # Protruding bracket part (extends outward from +X edge of panel)
    # Sits on top of the panel face, flush with the +X edge
    # The panel face itself forms one side of the "L"
    bracket_cx = (
        PANEL_WIDTH / 2 + BRACKET_HORIZ_LENGTH / 2
    )  # Protrudes outward from edge
    bracket_cy = bracket_y  # Position along Y axis
    bracket_cz = (
        PANEL_THICKNESS / 2 + BRACKET_THICKNESS / 2
    )  # Sits on top of panel

    bracket = box(
        f"Bracket{i}",
        bracket_cx,
        bracket_cy,
        bracket_cz,
        BRACKET_HORIZ_LENGTH,  # Length in X (protrusion)
        BRACKET_HORIZ_WIDTH,  # Width in Y
        BRACKET_THICKNESS,  # Thickness in Z
    )

    # Add screw holes if requested
    if BRACKET_SCREW_HOLES > 0:
        # Add holes through the bracket for mounting screws
        for h in range(BRACKET_SCREW_HOLES):
            if BRACKET_SCREW_HOLES == 1:
                hole_y = bracket_y
            else:
                hole_spacing = BRACKET_HORIZ_WIDTH * 0.6 / (BRACKET_SCREW_HOLES - 1)
                hole_y = bracket_y - (BRACKET_HORIZ_WIDTH * 0.3) + h * hole_spacing

            screw_hole = make_cylinder_cutter(
                f"Bracket{i}_ScrewHole{h}",
                bracket_cx,
                hole_y,
                bracket_cz,
                BRACKET_SCREW_D / 2,
                BRACKET_THICKNESS + 2 * BOOL_EXTRA,
            )
            bool_diff(bracket, screw_hole)

    # Union bracket with panel
    bool_union(panel, bracket)


# ════════════════════════════════════════════════════════════════
#  EXPORT STL
# ════════════════════════════════════════════════════════════════

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir.endswith(".blend"):
    script_dir = os.path.dirname(script_dir)
output_dir = os.path.join(script_dir, "output")
os.makedirs(output_dir, exist_ok=True)

bpy.ops.object.select_all(action="DESELECT")
panel.select_set(True)
bpy.context.view_layer.objects.active = panel
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
out_path = os.path.join(output_dir, "panel_with_brackets.stl")
bpy.ops.wm.stl_export(filepath=out_path, export_selected_objects=True)

print("=" * 62)
print("  Panel with L-Brackets — build complete")
print("=" * 62)
print(
    f"  Panel dimensions      : {PANEL_WIDTH:.2f} × {PANEL_LENGTH:.2f} × {PANEL_THICKNESS:.2f} mm"
)
print(f"  Semi-circle hole      : Ø{HOLE_DIAMETER:.2f} mm")
print(f"  Number of brackets    : {NUM_BRACKETS}")
print(
    f"  Bracket vertical size : {BRACKET_VERT_WIDTH:.2f} × {BRACKET_VERT_HEIGHT:.2f} mm"
)
print(
    f"  Bracket horizontal    : {BRACKET_HORIZ_WIDTH:.2f} × {BRACKET_HORIZ_LENGTH:.2f} mm"
)
print(f"  Screw holes/bracket   : {BRACKET_SCREW_HOLES}")
print(f"  Output file           : {out_path}")
print("=" * 62)
