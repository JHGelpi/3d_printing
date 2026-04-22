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

# ── Interlocking joint (for splitting panel into two printable pieces) ───
ENABLE_INTERLOCK = True  # Set to False to generate single-piece panel
INTERLOCK_TYPE = "tongue_groove"  # tongue and groove joint (invisible when assembled)
TONGUE_HEIGHT = 2.0  # mm — height of the tongue/groove at base (must be < PANEL_THICKNESS)
TONGUE_DEPTH = 3.0  # mm — how deep the tongue extends into the mating piece
TONGUE_TAPER_ANGLE = 15.0  # degrees — taper angle for V-shape (0 = straight, 15-30 typical)
INTERLOCK_CLEARANCE = 0.2  # mm — printing tolerance gap for fit

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


def make_tongue_or_groove(name, cx, cy, cz, width, panel_thickness, is_tongue=True):
    """
    Creates a V-shaped tongue or groove for tongue-and-groove joint.
    The joint is centered in the panel thickness so it's invisible when assembled.
    The V-shape provides mechanical locking strength.

    Parameters:
    - cx, cy, cz: center position of the joint
    - width: width of the panel (X dimension)
    - panel_thickness: thickness of the panel (Z dimension)
    - is_tongue: True for protruding tongue, False for groove cavity

    Returns object for boolean operations (union for tongue, diff for groove)
    """
    # Calculate taper based on angle
    taper_angle_rad = math.radians(TONGUE_TAPER_ANGLE)
    # Height increase over the depth due to taper (on each side, top and bottom)
    taper_expansion = TONGUE_DEPTH * math.tan(taper_angle_rad)

    # Tongue dimensions (centered in panel thickness)
    base_height = TONGUE_HEIGHT - INTERLOCK_CLEARANCE if is_tongue else TONGUE_HEIGHT
    tongue_depth = TONGUE_DEPTH - INTERLOCK_CLEARANCE if is_tongue else TONGUE_DEPTH

    # Tip height (wider due to V-shape taper)
    tip_height = base_height + 2 * taper_expansion  # Expands on both top and bottom

    # Create V-shaped profile using bmesh
    bm = bmesh.new()

    # The tongue/groove is centered in Z, recessed from both surfaces
    # This makes it invisible from top and bottom

    if is_tongue:
        # Create tapered tongue: narrow at base, wide at tip
        # Profile in YZ plane, extruded along X

        # Base edge (at panel edge, Y=0)
        base_z_half = base_height / 2
        # Tip edge (at Y=tongue_depth)
        tip_z_half = tip_height / 2

        # Y positions
        y_base = cy
        y_tip = cy + tongue_depth

        # Create vertices for front face (X = -width/2)
        x_front = cx - width / 2
        v0_front = bm.verts.new((x_front, y_base, cz - base_z_half))  # Base bottom
        v1_front = bm.verts.new((x_front, y_base, cz + base_z_half))  # Base top
        v2_front = bm.verts.new((x_front, y_tip, cz + tip_z_half))    # Tip top
        v3_front = bm.verts.new((x_front, y_tip, cz - tip_z_half))    # Tip bottom

        # Create vertices for back face (X = +width/2)
        x_back = cx + width / 2
        v0_back = bm.verts.new((x_back, y_base, cz - base_z_half))
        v1_back = bm.verts.new((x_back, y_base, cz + base_z_half))
        v2_back = bm.verts.new((x_back, y_tip, cz + tip_z_half))
        v3_back = bm.verts.new((x_back, y_tip, cz - tip_z_half))

    else:
        # Create tapered groove: narrow at opening, wide at bottom
        # This matches the tongue profile (narrow base slides in, wide tip locks at bottom)

        # Opening edge (at panel edge, Y=0) - narrower (matches tongue base)
        opening_z_half = base_height / 2
        # Bottom edge (at Y=tongue_depth) - wider (matches tongue tip)
        bottom_z_half = tip_height / 2

        # Y positions
        y_opening = cy
        y_bottom = cy + tongue_depth

        # Add extra width for clean boolean cut
        x_front = cx - width / 2 - BOOL_EXTRA
        x_back = cx + width / 2 + BOOL_EXTRA

        # Create vertices for front face
        v0_front = bm.verts.new((x_front, y_opening, cz - opening_z_half))  # Opening bottom
        v1_front = bm.verts.new((x_front, y_opening, cz + opening_z_half))  # Opening top
        v2_front = bm.verts.new((x_front, y_bottom, cz + bottom_z_half))    # Bottom top
        v3_front = bm.verts.new((x_front, y_bottom, cz - bottom_z_half))    # Bottom bottom

        # Create vertices for back face
        v0_back = bm.verts.new((x_back, y_opening, cz - opening_z_half))
        v1_back = bm.verts.new((x_back, y_opening, cz + opening_z_half))
        v2_back = bm.verts.new((x_back, y_bottom, cz + bottom_z_half))
        v3_back = bm.verts.new((x_back, y_bottom, cz - bottom_z_half))

    # Create faces
    bm.faces.new([v0_front, v1_front, v2_front, v3_front])  # Front face
    bm.faces.new([v0_back, v3_back, v2_back, v1_back])      # Back face (reversed)
    bm.faces.new([v0_front, v0_back, v1_back, v1_front])    # Base edge
    bm.faces.new([v1_front, v1_back, v2_back, v2_front])    # Top slope
    bm.faces.new([v2_front, v2_back, v3_back, v3_front])    # Tip edge
    bm.faces.new([v3_front, v3_back, v0_back, v0_front])    # Bottom slope

    bm.verts.ensure_lookup_table()
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


# ── 1. MAIN PANEL (split into two interlocking pieces if enabled) ────

if ENABLE_INTERLOCK:
    # Create two panel halves with interlocking joint
    half_length = PANEL_LENGTH / 2

    # Panel Half 1 (negative Y side, -Y to 0)
    panel_half1 = box(
        "Panel_Half1",
        0,
        -half_length / 2,
        0,
        PANEL_WIDTH,
        half_length,
        PANEL_THICKNESS,
    )
    col.objects.link(panel_half1)
    try:
        bpy.context.scene.collection.objects.unlink(panel_half1)
    except RuntimeError:
        pass

    # Panel Half 2 (positive Y side, 0 to +Y)
    panel_half2 = box(
        "Panel_Half2",
        0,
        half_length / 2,
        0,
        PANEL_WIDTH,
        half_length,
        PANEL_THICKNESS,
    )
    col.objects.link(panel_half2)
    try:
        bpy.context.scene.collection.objects.unlink(panel_half2)
    except RuntimeError:
        pass

    # Add tongue and groove joint at Y=0
    # Half 1 (negative Y) gets protruding tongue
    tongue = make_tongue_or_groove(
        "Tongue",
        0,  # Centered in X
        0,  # At the split line Y=0
        0,  # Centered in Z
        PANEL_WIDTH,  # Full width
        PANEL_THICKNESS,  # Panel thickness
        is_tongue=True,
    )
    bool_union(panel_half1, tongue)

    # Half 2 (positive Y) gets groove cavity to receive the tongue
    groove = make_tongue_or_groove(
        "Groove",
        0,
        0,
        0,
        PANEL_WIDTH,
        PANEL_THICKNESS,
        is_tongue=False,
    )
    bool_diff(panel_half2, groove)

    # Store both halves for later processing
    panels = [panel_half1, panel_half2]

else:
    # Single piece panel (no interlock)
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
    panels = [panel]


# ── 2. SEMI-CIRCLE CUTOUT ────────────────────────────────────────
# Cut semi-circle notch on the +X edge (right long edge) for cable routing
# The cutout is centered at Y=HOLE_Y_POSITION, cuts into the edge like a scoop

# Create a cylinder cutter oriented along the Z axis (through panel thickness)
# Position it so half is inside the panel edge, half is outside
radius = HOLE_DIAMETER / 2
hole_cx = PANEL_WIDTH / 2  # At the +X edge
hole_cy = HOLE_Y_POSITION  # Position along Y axis
hole_cz = 0  # At mid-thickness of panel

semicircle_cutter = make_cylinder_cutter(
    "SemicircleCutout",
    hole_cx,
    hole_cy,
    hole_cz,
    radius,
    PANEL_THICKNESS + 2 * BOOL_EXTRA,  # Cut through entire thickness
)

# Apply cutout to the appropriate panel(s)
# If split, only apply to the half that contains the hole position
if ENABLE_INTERLOCK:
    if hole_cy < 0:
        bool_diff(panel_half1, semicircle_cutter)
    else:
        bool_diff(panel_half2, semicircle_cutter)
else:
    bool_diff(panels[0], semicircle_cutter)


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

    # Protruding bracket part (extends perpendicular to panel, downward in Z)
    # Flush with the +X edge, extends downward from bottom of panel
    # The panel edge itself forms one side of the "L"
    bracket_cx = (
        PANEL_WIDTH / 2 - BRACKET_THICKNESS / 2
    )  # Flush with +X edge (inside edge)
    bracket_cy = bracket_y  # Position along Y axis
    bracket_cz = (
        -PANEL_THICKNESS / 2 - BRACKET_HORIZ_LENGTH / 2
    )  # Extends downward from panel bottom

    bracket = box(
        f"Bracket{i}",
        bracket_cx,
        bracket_cy,
        bracket_cz,
        BRACKET_THICKNESS,  # Thickness in X (flush with edge)
        BRACKET_HORIZ_WIDTH,  # Width in Y (along edge)
        BRACKET_HORIZ_LENGTH,  # Length in Z (perpendicular protrusion)
    )

    # Add screw holes if requested
    if BRACKET_SCREW_HOLES > 0:
        # Add holes through the bracket for mounting screws (through Z direction)
        for h in range(BRACKET_SCREW_HOLES):
            if BRACKET_SCREW_HOLES == 1:
                hole_y = bracket_y
            else:
                hole_spacing = BRACKET_HORIZ_WIDTH * 0.6 / (BRACKET_SCREW_HOLES - 1)
                hole_y = bracket_y - (BRACKET_HORIZ_WIDTH * 0.3) + h * hole_spacing

            # Rotate the cylinder to go through the bracket thickness (in X direction)
            # Create cylinder along Z, then we'll rotate it to go through X
            screw_hole = make_cylinder_cutter(
                f"Bracket{i}_ScrewHole{h}",
                bracket_cx,
                hole_y,
                bracket_cz,
                BRACKET_SCREW_D / 2,
                BRACKET_THICKNESS + 2 * BOOL_EXTRA,
            )
            # Rotate to make hole go through X direction (through bracket thickness)
            screw_hole.rotation_euler = (0, math.pi / 2, 0)
            bpy.context.view_layer.objects.active = screw_hole
            screw_hole.select_set(True)
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
            screw_hole.select_set(False)
            bool_diff(bracket, screw_hole)

    # Union bracket with the appropriate panel half
    if ENABLE_INTERLOCK:
        # Determine which half this bracket belongs to based on Y position
        if bracket_y < 0:
            bool_union(panel_half1, bracket)
        else:
            bool_union(panel_half2, bracket)
    else:
        bool_union(panels[0], bracket)


# ════════════════════════════════════════════════════════════════
#  EXPORT STL
# ════════════════════════════════════════════════════════════════

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir.endswith(".blend"):
    script_dir = os.path.dirname(script_dir)
output_dir = os.path.join(script_dir, "output")
os.makedirs(output_dir, exist_ok=True)

bpy.ops.object.select_all(action="DESELECT")

# Export each panel piece
export_files = []
for panel_obj in panels:
    panel_obj.select_set(True)
    bpy.context.view_layer.objects.active = panel_obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    out_path = os.path.join(output_dir, f"{panel_obj.name}.stl")
    bpy.ops.wm.stl_export(filepath=out_path, export_selected_objects=True)
    export_files.append(out_path)
    panel_obj.select_set(False)

print("=" * 62)
print("  Panel with L-Brackets — build complete")
print("=" * 62)
print(
    f"  Panel dimensions      : {PANEL_WIDTH:.2f} × {PANEL_LENGTH:.2f} × {PANEL_THICKNESS:.2f} mm"
)
print(f"  Semi-circle cutout    : Ø{HOLE_DIAMETER:.2f} mm")
print(f"  Number of brackets    : {NUM_BRACKETS}")
print(f"  Bracket dimensions    : {BRACKET_HORIZ_WIDTH:.2f} × {BRACKET_HORIZ_LENGTH:.2f} mm")
print(f"  Screw holes/bracket   : {BRACKET_SCREW_HOLES}")
if ENABLE_INTERLOCK:
    print(f"  Interlocking joint    : {INTERLOCK_TYPE} (V-shaped)")
    print(f"    Tongue height (base): {TONGUE_HEIGHT:.2f} mm")
    print(f"    Tongue depth        : {TONGUE_DEPTH:.2f} mm")
    print(f"    Taper angle         : {TONGUE_TAPER_ANGLE:.1f}°")
    print(f"    Print clearance     : {INTERLOCK_CLEARANCE:.2f} mm")
    print(f"  Split into pieces     : 2")
else:
    print(f"  Split into pieces     : 1 (single piece)")
print(f"  Output files          :")
for f in export_files:
    print(f"    {f}")
print("=" * 62)
