"""
Flat Bracket with Mid-Point Bend, Countersunk Screw Holes
----------------------------------------------------------
8" long × 4" wide × 0.5" thick
BEND_ANGLE_DEG: horizontal bend at the midpoint.
  Positive value = curves LEFT when viewed from above (CCW in top view).
  Negative value = curves RIGHT.
Beveled edges on all faces except the flat bottom face.
3 screw holes in a triangle pattern on each end.
COUNTERSINK = True  → countersunk (#8 screw head sits flush with top face)
COUNTERSINK = False → plain through-hole only
Sized for #8 × 3/4" wood screws.
"""

import math
import os

import bmesh
import bpy

# ============================================================
# PARAMETERS (edit these — all dimensions in mm)
# ============================================================
BRACKET_LENGTH = 8.0 * 25.4  # 203.2 mm — total length across both halves
BRACKET_WIDTH = 4.0 * 25.4  # 101.6 mm
BRACKET_THICK = 0.5 * 25.4  #  12.7 mm

BEND_ANGLE_DEG = 22.5  # degrees — bend at midpoint
#   positive → curves LEFT  (top-down view, CCW)
#   negative → curves RIGHT (top-down view, CW)

# BEVEL_AMOUNT    = 2.0            # mm — chamfer width (increase for dramatic bevel)
BEVEL_AMOUNT = 5.0  # mm — chamfer width (increase for dramatic bevel)
# BEVEL_SEGMENTS  = 3              # facets per bevel (1=flat chamfer, 8+=round fillet)
BEVEL_SEGMENTS = 1  # facets per bevel (1=flat chamfer, 8+=round fillet)

# Screw holes — clearance for #8 × 3/4" wood screw
COUNTERSINK = True  # True = countersunk flush, False = plain through-hole
HOLE_DIAMETER = 4.5  # mm — shank clearance diameter
CSNK_DIAMETER = 9.0  # mm — countersink opening at the top surface
CSNK_DEPTH = 3.5  # mm — depth of countersink (screw head sits flush)
HOLE_SEGMENTS = 32  # cylinder/cone resolution

# Triangle pattern — measured from each end face
END_MARGIN = 18.0  # mm — front two holes inset from end face
SIDE_MARGIN = 18.0  # mm — outer holes inset from side edges
BACK_OFFSET = 28.0  # mm — apex hole set back from the front pair

# ============================================================
# Derived
# ============================================================
MID = BRACKET_LENGTH / 2  # 101.6 mm — bend X position
HW = BRACKET_WIDTH / 2  #  50.8 mm — half-width
BEND_ANGLE = math.radians(BEND_ANGLE_DEG)

# Bend pivot: the front-bottom edge at the midpoint (x=MID, y=0).
# Rotating the right half around this point creates an overlap on the
# inner (back) side that the boolean union resolves into a clean join.
PIVOT_X, PIVOT_Y = MID, 0.0

print("=" * 58)
print("  Flat Bracket — Dimensions")
print("=" * 58)
print(f"  Length      : {BRACKET_LENGTH:.1f} mm  ({BRACKET_LENGTH / 25.4:.2f} in)")
print(f"  Width       : {BRACKET_WIDTH:.1f} mm  ({BRACKET_WIDTH / 25.4:.2f} in)")
print(f"  Thickness   : {BRACKET_THICK:.1f} mm  ({BRACKET_THICK / 25.4:.3f} in)")
print(
    f"  Bend angle  : {BEND_ANGLE_DEG}°  ({'LEFT (CCW)' if BEND_ANGLE_DEG >= 0 else 'RIGHT (CW)'} in top view)"
)
print(f"  Bevel       : {BEVEL_AMOUNT} mm × {BEVEL_SEGMENTS} segments")
csk_label = (
    f"countersunk Ø{CSNK_DIAMETER} mm × {CSNK_DEPTH} mm deep"
    if COUNTERSINK
    else "plain through-hole"
)
print(f"  Screw holes : #8 wood screw  Ø{HOLE_DIAMETER} mm shank / {csk_label}")
print("=" * 58)


# ============================================================
# Helpers
# ============================================================
def rotate_xy(x, y, angle=BEND_ANGLE, px=PIVOT_X, py=PIVOT_Y):
    """Rotate point (x, y) around (px, py) by angle (radians, CCW)."""
    dx, dy = x - px, y - py
    rx = px + dx * math.cos(angle) - dy * math.sin(angle)
    ry = py + dx * math.sin(angle) + dy * math.cos(angle)
    return rx, ry


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
# 1. Left half — straight box from x=0 to x=MID
# ============================================================
left_obj = box_object(
    "LeftHalf",
    [
        (0, 0, 0),
        (MID, 0, 0),
        (MID, BRACKET_WIDTH, 0),
        (0, BRACKET_WIDTH, 0),
        (0, 0, BRACKET_THICK),
        (MID, 0, BRACKET_THICK),
        (MID, BRACKET_WIDTH, BRACKET_THICK),
        (0, BRACKET_WIDTH, BRACKET_THICK),
    ],
)


# ============================================================
# 2. Right half — same box rotated BEND_ANGLE around the pivot.
#    Positive BEND_ANGLE_DEG rotates CCW (curves LEFT in top view).
# ============================================================
def rotated_right_corners():
    raw = [
        (MID, 0, 0),
        (BRACKET_LENGTH, 0, 0),
        (BRACKET_LENGTH, BRACKET_WIDTH, 0),
        (MID, BRACKET_WIDTH, 0),
        (MID, 0, BRACKET_THICK),
        (BRACKET_LENGTH, 0, BRACKET_THICK),
        (BRACKET_LENGTH, BRACKET_WIDTH, BRACKET_THICK),
        (MID, BRACKET_WIDTH, BRACKET_THICK),
    ]
    result = []
    for x, y, z in raw:
        rx, ry = rotate_xy(x, y)
        result.append((rx, ry, z))
    return result


right_obj = box_object("RightHalf", rotated_right_corners())


# ============================================================
# 3. Boolean union — merges the overlap at the inner bend corner
#    into a clean, solid single mesh.
# ============================================================
bpy.context.view_layer.objects.active = left_obj
left_obj.select_set(True)
union_mod = left_obj.modifiers.new("Union", "BOOLEAN")
union_mod.operation = "UNION"
union_mod.object = right_obj
union_mod.solver = "EXACT"
bpy.ops.object.modifier_apply(modifier=union_mod.name)
bpy.data.objects.remove(right_obj, do_unlink=True)

bracket = left_obj
bracket.name = "Bracket"
bpy.context.view_layer.objects.active = bracket


# ============================================================
# 4. Bevel all edges EXCEPT the bottom face (Z ≈ 0).
#    Uses bmesh.ops.bevel directly — avoids version-specific
#    layer APIs (bevel_weight was removed in Blender 4.0).
# ============================================================
bm_bevel = bmesh.new()
bm_bevel.from_mesh(bracket.data)

edges_to_bevel = [
    e for e in bm_bevel.edges if not all(abs(v.co.z) < 0.001 for v in e.verts)
]

bmesh.ops.bevel(
    bm_bevel,
    geom=edges_to_bevel,
    offset=BEVEL_AMOUNT,
    segments=BEVEL_SEGMENTS,
    profile=0.5,
    affect="EDGES",
)

bm_bevel.to_mesh(bracket.data)
bm_bevel.free()


# ============================================================
# 5. Screw holes (shank + optional countersink)
#
#    Each hole is cut in two separate boolean passes so every cutter
#    is a simple, individually-manifold solid.  Blender's boolean engine
#    silently fails on non-manifold cutters (e.g. two disconnected
#    primitives sharing a mesh), which was the root cause of missing CSKs.
#
#    Countersink geometry note:
#      The frustum slope is computed so the opening is exactly
#      CSNK_DIAMETER at z = BRACKET_THICK (the top surface).
#      A small overshoot on each end ensures clean intersection.
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

    # Pass 2 — countersink frustum: tapered cone at the top surface.
    # Extend BOOL_EXTRA/2 beyond each end of the CSK zone so the
    # intersection is clean.  Slope is preserved so the diameter is
    # exactly CSNK_DIAMETER at z = BRACKET_THICK (the real surface).
    csk_depth_total = CSNK_DEPTH + BOOL_EXTRA  # full cutter height
    csk_centre_z = BRACKET_THICK - CSNK_DEPTH / 2  # mid-point of CSK zone
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


# Left-end holes (no rotation needed)
left_holes = [
    (END_MARGIN, SIDE_MARGIN),
    (END_MARGIN, BRACKET_WIDTH - SIDE_MARGIN),
    (END_MARGIN + BACK_OFFSET, HW),
]

# Right-end holes: defined in straight-bracket space then rotated
right_holes_straight = [
    (BRACKET_LENGTH - END_MARGIN, SIDE_MARGIN),
    (BRACKET_LENGTH - END_MARGIN, BRACKET_WIDTH - SIDE_MARGIN),
    (BRACKET_LENGTH - END_MARGIN - BACK_OFFSET, HW),
]
right_holes = [rotate_xy(x, y) for x, y in right_holes_straight]

ALL_HOLES = left_holes + right_holes

for idx, (hx, hy) in enumerate(ALL_HOLES):
    cut_hole(bracket, idx, hx, hy)


# ============================================================
# 6. Finalise and export
# ============================================================
bpy.context.view_layer.objects.active = bracket
bracket.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, "output")
os.makedirs(output_dir, exist_ok=True)
out_path = os.path.join(output_dir, "flat_bracket.stl")
bpy.ops.wm.stl_export(filepath=out_path)
print(f"Exported → {out_path}")
