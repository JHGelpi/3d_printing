"""
Flat Bracket with Mid-Point Bend, Countersunk Screw Holes
----------------------------------------------------------
8" long × 4" wide × 0.5" thick
BEND_ANGLE_DEG: horizontal bend at the midpoint.
  Positive value = curves LEFT when viewed from above (CCW in top view).
  Negative value = curves RIGHT.
Beveled edges on all faces except the flat bottom face.
3 countersunk holes in a triangle pattern on each end.
Sized for #8 × 3/4" wood screws.
"""

import bpy
import bmesh
import math
import os

# ============================================================
# PARAMETERS (edit these — all dimensions in mm)
# ============================================================
BRACKET_LENGTH  = 8.0  * 25.4   # 203.2 mm — total length across both halves
BRACKET_WIDTH   = 4.0  * 25.4   # 101.6 mm
BRACKET_THICK   = 0.5  * 25.4   #  12.7 mm

BEND_ANGLE_DEG  = 22.5           # degrees — bend at midpoint
                                 #   positive → curves LEFT  (top-down view, CCW)
                                 #   negative → curves RIGHT (top-down view, CW)

BEVEL_AMOUNT    = 2.0            # mm — chamfer width (increase for dramatic bevel)
BEVEL_SEGMENTS  = 3              # facets per bevel (1=flat chamfer, 8+=round fillet)

# Screw holes — clearance for #8 × 3/4" wood screw
HOLE_DIAMETER   = 4.5            # mm — through-hole shank clearance
CSNK_DIAMETER   = 9.0            # mm — countersink top diameter
CSNK_DEPTH      = 3.5            # mm — countersink depth (screw head sits flush)
HOLE_SEGMENTS   = 32             # cylinder resolution

# Triangle pattern — measured from each end face
END_MARGIN      = 18.0           # mm — front two holes inset from end face
SIDE_MARGIN     = 18.0           # mm — outer holes inset from side edges
BACK_OFFSET     = 28.0           # mm — apex hole set back from the front pair

# ============================================================
# Derived
# ============================================================
MID         = BRACKET_LENGTH / 2          # 101.6 mm — bend X position
HW          = BRACKET_WIDTH  / 2          #  50.8 mm — half-width
BEND_ANGLE  = math.radians(BEND_ANGLE_DEG)

# Bend pivot: the front-bottom edge at the midpoint (x=MID, y=0).
# Rotating the right half around this point creates an overlap on the
# inner (back) side that the boolean union resolves into a clean join.
PIVOT_X, PIVOT_Y = MID, 0.0

print("=" * 58)
print("  Flat Bracket — Dimensions")
print("=" * 58)
print(f"  Length      : {BRACKET_LENGTH:.1f} mm  ({BRACKET_LENGTH/25.4:.2f} in)")
print(f"  Width       : {BRACKET_WIDTH:.1f} mm  ({BRACKET_WIDTH/25.4:.2f} in)")
print(f"  Thickness   : {BRACKET_THICK:.1f} mm  ({BRACKET_THICK/25.4:.3f} in)")
print(f"  Bend angle  : {BEND_ANGLE_DEG}°  ({'LEFT (CCW)' if BEND_ANGLE_DEG >= 0 else 'RIGHT (CW)'} in top view)")
print(f"  Bevel       : {BEVEL_AMOUNT} mm × {BEVEL_SEGMENTS} segments")
print(f"  Screw holes : #8 wood screw  Ø{HOLE_DIAMETER} mm shank / Ø{CSNK_DIAMETER} mm csk")
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
        [0, 1, 2, 3],        # bottom
        [4, 7, 6, 5],        # top
        [0, 4, 5, 1],        # front  (y-min side)
        [3, 2, 6, 7],        # back   (y-max side)
        [0, 3, 7, 4],        # left   (x-min side)
        [1, 5, 6, 2],        # right  (x-max side)
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
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()


# ============================================================
# 1. Left half — straight box from x=0 to x=MID
# ============================================================
left_obj = box_object("LeftHalf", [
    (0,   0,             0),
    (MID, 0,             0),
    (MID, BRACKET_WIDTH, 0),
    (0,   BRACKET_WIDTH, 0),
    (0,   0,             BRACKET_THICK),
    (MID, 0,             BRACKET_THICK),
    (MID, BRACKET_WIDTH, BRACKET_THICK),
    (0,   BRACKET_WIDTH, BRACKET_THICK),
])


# ============================================================
# 2. Right half — same box rotated BEND_ANGLE around the pivot.
#    Positive BEND_ANGLE_DEG rotates CCW (curves LEFT in top view).
# ============================================================
def rotated_right_corners():
    raw = [
        (MID,            0,             0),
        (BRACKET_LENGTH, 0,             0),
        (BRACKET_LENGTH, BRACKET_WIDTH, 0),
        (MID,            BRACKET_WIDTH, 0),
        (MID,            0,             BRACKET_THICK),
        (BRACKET_LENGTH, 0,             BRACKET_THICK),
        (BRACKET_LENGTH, BRACKET_WIDTH, BRACKET_THICK),
        (MID,            BRACKET_WIDTH, BRACKET_THICK),
    ]
    result = []
    for (x, y, z) in raw:
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
union_mod = left_obj.modifiers.new("Union", 'BOOLEAN')
union_mod.operation = 'UNION'
union_mod.object    = right_obj
union_mod.solver    = 'EXACT'
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
    e for e in bm_bevel.edges
    if not all(abs(v.co.z) < 0.001 for v in e.verts)
]

bmesh.ops.bevel(
    bm_bevel,
    geom=edges_to_bevel,
    offset=BEVEL_AMOUNT,
    segments=BEVEL_SEGMENTS,
    profile=0.5,
    affect='EDGES',
)

bm_bevel.to_mesh(bracket.data)
bm_bevel.free()


# ============================================================
# 5. Countersunk screw holes
#    Left holes: straight bracket-frame positions.
#    Right holes: pre-bend positions rotated into world space.
# ============================================================
def make_countersink_cutter(name, hx, hy):
    """Cylinder + countersink cone cutter centred at (hx, hy), full Z depth."""
    cutter_mesh = bpy.data.meshes.new(name + "_mesh")
    bm2   = bmesh.new()
    extra = 2.0   # mm overshoot each end for a clean boolean cut

    # Shank cylinder
    shank = bmesh.ops.create_cone(
        bm2, cap_ends=True, cap_tris=False, segments=HOLE_SEGMENTS,
        radius1=HOLE_DIAMETER / 2, radius2=HOLE_DIAMETER / 2,
        depth=BRACKET_THICK + extra * 2,
    )
    bmesh.ops.translate(bm2, verts=shank['verts'],
                        vec=(hx, hy, BRACKET_THICK / 2))

    # Countersink cone (wider at top)
    csk_centre_z = BRACKET_THICK - CSNK_DEPTH / 2
    csk = bmesh.ops.create_cone(
        bm2, cap_ends=True, cap_tris=False, segments=HOLE_SEGMENTS,
        radius1=HOLE_DIAMETER / 2,   # narrow end (bottom)
        radius2=CSNK_DIAMETER / 2,   # wide end   (top / flush with surface)
        depth=CSNK_DEPTH + extra,
    )
    bmesh.ops.translate(bm2, verts=csk['verts'],
                        vec=(hx, hy, csk_centre_z + extra / 2))

    bmesh.ops.recalc_face_normals(bm2, faces=bm2.faces)
    bm2.to_mesh(cutter_mesh)
    bm2.free()

    cutter_obj = bpy.data.objects.new(name, cutter_mesh)
    bpy.context.collection.objects.link(cutter_obj)
    return cutter_obj


# Left-end holes (no rotation needed)
left_holes = [
    (END_MARGIN,               SIDE_MARGIN),
    (END_MARGIN,               BRACKET_WIDTH - SIDE_MARGIN),
    (END_MARGIN + BACK_OFFSET, HW),
]

# Right-end holes: compute in straight-bracket space, then rotate
right_holes_straight = [
    (BRACKET_LENGTH - END_MARGIN,               SIDE_MARGIN),
    (BRACKET_LENGTH - END_MARGIN,               BRACKET_WIDTH - SIDE_MARGIN),
    (BRACKET_LENGTH - END_MARGIN - BACK_OFFSET, HW),
]
right_holes = [rotate_xy(x, y) for x, y in right_holes_straight]

ALL_HOLES = left_holes + right_holes

for idx, (hx, hy) in enumerate(ALL_HOLES):
    cutter   = make_countersink_cutter(f"HoleCutter_{idx:02d}", hx, hy)
    bool_mod = bracket.modifiers.new(f"BoolHole_{idx:02d}", 'BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object    = cutter
    bool_mod.solver    = 'EXACT'
    bpy.context.view_layer.objects.active = bracket
    bpy.ops.object.modifier_apply(modifier=bool_mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


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
