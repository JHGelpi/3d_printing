"""
Beveled Bracket with Countersunk Screw Holes
---------------------------------------------
40cm long × 5cm wide × 1.5cm thick
45-degree bevel on the top edges (same side as countersink)
12 countersunk screw holes distributed length-wise, skewed toward the ends
All dimensions parameterized for easy modification
"""

import math
import os

import bmesh
import bpy

# ============================================================
# PARAMETERS (edit these — all dimensions in mm)
# ============================================================
BRACKET_LENGTH = 400.0  # mm — 40cm
BRACKET_WIDTH = 50.0  # mm — 5cm
BRACKET_THICK = 15.0  # mm — 1.5cm

# Bevel configuration
BEVEL_ANGLE_DEG = 45.0  # degrees — bevel angle on top edges
BEVEL_SEGMENTS = 1  # facets per bevel (1=flat chamfer, 8+=round fillet)

# Screw holes
NUM_HOLES = 12  # total number of holes
HOLE_DIAMETER = 15.0  # mm — 1.5cm hole diameter
COUNTERSINK = True  # True = countersunk flush, False = plain through-hole
CSNK_DIAMETER = 25.0  # mm — countersink opening at the top surface
CSNK_DEPTH = 7.5  # mm — depth of countersink (half the thickness)
HOLE_SEGMENTS = 32  # cylinder/cone resolution

# Hole distribution — skewed toward ends
END_MARGIN = 20.0  # mm — first/last hole inset from bracket ends
# Skew factor: 0.0 = linear/even spacing, 1.0 = maximum concentration at ends
# Values between 0.5-0.8 give good end-biased distribution
HOLE_SKEW_FACTOR = 0.6

# ============================================================
# Derived values
# ============================================================
# Calculate bevel offset based on angle
# For a 45° bevel, offset = thickness * tan(45°) = thickness
# For other angles, adjust proportionally
BEVEL_OFFSET = BRACKET_THICK * math.tan(math.radians(BEVEL_ANGLE_DEG)) / 2

print("=" * 68)
print("  Beveled Bracket — Dimensions")
print("=" * 68)
print(f"  Length      : {BRACKET_LENGTH:.1f} mm  ({BRACKET_LENGTH / 10:.1f} cm)")
print(f"  Width       : {BRACKET_WIDTH:.1f} mm  ({BRACKET_WIDTH / 10:.1f} cm)")
print(f"  Thickness   : {BRACKET_THICK:.1f} mm  ({BRACKET_THICK / 10:.1f} cm)")
print(f"  Bevel angle : {BEVEL_ANGLE_DEG}° on top edges")
print(f"  Bevel offset: {BEVEL_OFFSET:.2f} mm × {BEVEL_SEGMENTS} segments")
csk_label = (
    f"countersunk Ø{CSNK_DIAMETER} mm × {CSNK_DEPTH} mm deep"
    if COUNTERSINK
    else "plain through-hole"
)
print(f"  Screw holes: {NUM_HOLES} holes × Ø{HOLE_DIAMETER} mm / {csk_label}")
print(f"  Hole layout: length-wise distribution, skew factor {HOLE_SKEW_FACTOR}")
print("=" * 68)


# ============================================================
# Helpers
# ============================================================
def calculate_hole_positions():
    """
    Calculate X positions for holes distributed along the bracket length.
    Uses a power curve to skew distribution toward the ends.

    Returns:
        List of (x, y) tuples for hole centers
    """
    if NUM_HOLES < 2:
        # Single hole case — center it
        return [(BRACKET_LENGTH / 2, BRACKET_WIDTH / 2)]

    holes = []
    available_length = BRACKET_LENGTH - 2 * END_MARGIN

    for i in range(NUM_HOLES):
        # Normalize position: 0.0 at first hole, 1.0 at last hole
        t = i / (NUM_HOLES - 1)

        # Apply skew using power curve
        # t_skewed goes from 0→0.5→1, with concentration at ends
        # Higher HOLE_SKEW_FACTOR = more concentration at ends
        if t <= 0.5:
            # First half: curve from 0 to 0.5
            t_skewed = 0.5 * (t * 2) ** (1 - HOLE_SKEW_FACTOR)
        else:
            # Second half: curve from 0.5 to 1.0 (mirrored)
            t_skewed = 1.0 - 0.5 * ((1 - t) * 2) ** (1 - HOLE_SKEW_FACTOR)

        x = END_MARGIN + t_skewed * available_length
        y = BRACKET_WIDTH / 2  # centered on width
        holes.append((x, y))

    return holes


def box_object(name, corners_8):
    """
    Build a manifold box bpy object from 8 (x,y,z) corner tuples.
    Corner order: bottom CCW (0-3), then top CCW (4-7) directly above.
    """
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm = bmesh.new()
    v = [bm.verts.new(co) for co in corners_8]
    for face_indices in [
        [0, 1, 2, 3],  # bottom
        [4, 7, 6, 5],  # top
        [0, 4, 5, 1],  # front  (y-min side)
        [3, 2, 6, 7],  # back   (y-max side)
        [0, 3, 7, 4],  # left   (x-min side)
        [1, 5, 6, 2],  # right  (x-max side)
    ]:
        bm.faces.new([v[i] for i in face_indices])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


# ============================================================
# Scene setup
# ============================================================
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()


# ============================================================
# 1. Create main bracket box
# ============================================================
bracket = box_object(
    "Bracket",
    [
        # Bottom face (z=0)
        (0, 0, 0),
        (BRACKET_LENGTH, 0, 0),
        (BRACKET_LENGTH, BRACKET_WIDTH, 0),
        (0, BRACKET_WIDTH, 0),
        # Top face (z=BRACKET_THICK)
        (0, 0, BRACKET_THICK),
        (BRACKET_LENGTH, 0, BRACKET_THICK),
        (BRACKET_LENGTH, BRACKET_WIDTH, BRACKET_THICK),
        (0, BRACKET_WIDTH, BRACKET_THICK),
    ],
)

bpy.context.view_layer.objects.active = bracket


# ============================================================
# 2. Bevel the top edges only (where z = BRACKET_THICK)
# ============================================================
bm_bevel = bmesh.new()
bm_bevel.from_mesh(bracket.data)

# Select only edges on the top face (where both vertices have z ≈ BRACKET_THICK)
edges_to_bevel = [
    e
    for e in bm_bevel.edges
    if all(abs(v.co.z - BRACKET_THICK) < 0.001 for v in e.verts)
]

bmesh.ops.bevel(
    bm_bevel,
    geom=edges_to_bevel,
    offset=BEVEL_OFFSET,
    segments=BEVEL_SEGMENTS,
    profile=0.5,
    affect="EDGES",
)

bm_bevel.to_mesh(bracket.data)
bm_bevel.free()


# ============================================================
# 3. Screw holes (shank + optional countersink)
# ============================================================
BOOL_EXTRA = 2.0  # mm — cutter overshoot on each end

# Taper slope for the countersink (mm of radius per mm of depth)
_csk_slope = (CSNK_DIAMETER / 2 - HOLE_DIAMETER / 2) / CSNK_DEPTH


def _make_solid_cutter(name, hx, hy, r_bottom, r_top, height, centre_z):
    """Return a manifold cylinder or frustum bpy object at (hx, hy, centre_z)."""
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm = bmesh.new()
    ret = bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=HOLE_SEGMENTS,
        radius1=r_bottom,
        radius2=r_top,
        depth=height,
    )
    bmesh.ops.translate(bm, verts=ret["verts"], vec=(hx, hy, centre_z))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def _apply_bool(target, cutter):
    mod = target.modifiers.new("Bool", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "EXACT"
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def cut_hole(target, idx, hx, hy):
    """Cut a countersunk hole at position (hx, hy)."""
    # Pass 1 — shank: simple cylinder all the way through
    shank = _make_solid_cutter(
        f"Shank_{idx:02d}",
        hx,
        hy,
        r_bottom=HOLE_DIAMETER / 2,
        r_top=HOLE_DIAMETER / 2,
        height=BRACKET_THICK + BOOL_EXTRA * 2,
        centre_z=BRACKET_THICK / 2,
    )
    _apply_bool(target, shank)

    if not COUNTERSINK:
        return

    # Pass 2 — countersink frustum: tapered cone at the top surface
    csk_depth_total = CSNK_DEPTH + BOOL_EXTRA
    csk_centre_z = BRACKET_THICK - CSNK_DEPTH / 2
    # radius1 at bottom of cutter (slightly below CSK start):
    r_bot = HOLE_DIAMETER / 2 - _csk_slope * (BOOL_EXTRA / 2)
    # radius2 at top of cutter (slightly above bracket surface):
    r_top = CSNK_DIAMETER / 2 + _csk_slope * (BOOL_EXTRA / 2)

    csk = _make_solid_cutter(
        f"CSink_{idx:02d}",
        hx,
        hy,
        r_bottom=max(r_bot, 0.1),  # guard against negative radius
        r_top=r_top,
        height=csk_depth_total,
        centre_z=csk_centre_z,
    )
    _apply_bool(target, csk)


# Calculate and cut all holes
hole_positions = calculate_hole_positions()
print(f"\nHole positions (X coordinates along {BRACKET_LENGTH}mm length):")
for idx, (hx, hy) in enumerate(hole_positions, start=1):
    print(f"  Hole {idx:2d}: X={hx:6.1f} mm")
    cut_hole(bracket, idx - 1, hx, hy)


# ============================================================
# 4. Finalize and export
# ============================================================
bpy.context.view_layer.objects.active = bracket
bracket.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, "output")
os.makedirs(output_dir, exist_ok=True)
out_path = os.path.join(output_dir, "beveled_bracket.stl")
bpy.ops.wm.stl_export(filepath=out_path)
print(f"\nExported → {out_path}")
