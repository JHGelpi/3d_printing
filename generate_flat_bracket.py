"""
Flat Bracket with Countersunk Screw Holes
------------------------------------------
8" long × 4" wide × 0.5" thick
Beveled edges on all faces
3 countersunk holes in a triangle pattern on each end
Sized for #8 × 3/4" wood screws
"""

import bpy
import bmesh
import math
import os

# ============================================================
# PARAMETERS (edit these — all dimensions in mm)
# ============================================================
BRACKET_LENGTH  = 8.0  * 25.4   # 203.2 mm
BRACKET_WIDTH   = 4.0  * 25.4   # 101.6 mm
BRACKET_THICK   = 0.5  * 25.4   #  12.7 mm

BEVEL_AMOUNT    = 2.0            # mm — chamfer width on all edges
BEVEL_SEGMENTS  = 3              # facets per bevel (higher = rounder)

# Screw holes — clearance for #8 × 3/4" wood screw
HOLE_DIAMETER   = 4.5            # mm — through-hole (shank clearance)
CSNK_DIAMETER   = 9.0            # mm — countersink top diameter
CSNK_DEPTH      = 3.5            # mm — countersink depth (flush with screw head)
HOLE_SEGMENTS   = 32             # cylinder resolution

# Triangle pattern offsets (from each end face, per side)
END_MARGIN      = 18.0           # mm — front pair of holes inset from end face
SIDE_MARGIN     = 18.0           # mm — outer holes inset from side edges
BACK_OFFSET     = 28.0           # mm — apex hole set back from front pair
                                 #  → forms a clear isosceles triangle

# ============================================================
# Derived hole positions
# X along length (0 = left end), Y along width (0 = front edge)
# Z = 0 at bottom face of bracket
# ============================================================
HW = BRACKET_WIDTH / 2  # half-width

left_holes = [
    (END_MARGIN,               SIDE_MARGIN),                   # front-left
    (END_MARGIN,               BRACKET_WIDTH - SIDE_MARGIN),   # front-right
    (END_MARGIN + BACK_OFFSET, HW),                            # apex (centre)
]
right_holes = [
    (BRACKET_LENGTH - END_MARGIN,               SIDE_MARGIN),
    (BRACKET_LENGTH - END_MARGIN,               BRACKET_WIDTH - SIDE_MARGIN),
    (BRACKET_LENGTH - END_MARGIN - BACK_OFFSET, HW),
]
ALL_HOLES = left_holes + right_holes

# ============================================================
# Sanity checks
# ============================================================
assert BRACKET_LENGTH <= 256, "Exceeds Bambu P2S bed length"
assert BRACKET_WIDTH  <= 256, "Exceeds Bambu P2S bed width"
assert BRACKET_THICK  <= 256, "Exceeds Bambu P2S bed height"
for hx, hy in ALL_HOLES:
    assert SIDE_MARGIN >= CSNK_DIAMETER / 2 + 3, \
        "Countersink too close to edge — increase SIDE_MARGIN"

print("=" * 55)
print("  Flat Bracket — Dimensions")
print("=" * 55)
print(f"  Length : {BRACKET_LENGTH:.1f} mm  ({BRACKET_LENGTH/25.4:.2f} in)")
print(f"  Width  : {BRACKET_WIDTH:.1f} mm  ({BRACKET_WIDTH/25.4:.2f} in)")
print(f"  Thick  : {BRACKET_THICK:.1f} mm  ({BRACKET_THICK/25.4:.3f} in)")
print(f"  Holes  : {len(ALL_HOLES)} total  ({len(left_holes)} per end)")
print(f"  Screw  : #8 wood screw  (Ø{HOLE_DIAMETER} mm shank, Ø{CSNK_DIAMETER} mm csk)")
print("=" * 55)

# ============================================================
# Scene setup
# ============================================================
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()


# ============================================================
# 1. Create bracket body via bmesh
# ============================================================
mesh = bpy.data.meshes.new("BracketMesh")
bm   = bmesh.new()

# Simple box: origin at corner (0,0,0) → (L, W, T)
verts = [
    bm.verts.new((0,              0,             0)),
    bm.verts.new((BRACKET_LENGTH, 0,             0)),
    bm.verts.new((BRACKET_LENGTH, BRACKET_WIDTH, 0)),
    bm.verts.new((0,              BRACKET_WIDTH, 0)),
    bm.verts.new((0,              0,             BRACKET_THICK)),
    bm.verts.new((BRACKET_LENGTH, 0,             BRACKET_THICK)),
    bm.verts.new((BRACKET_LENGTH, BRACKET_WIDTH, BRACKET_THICK)),
    bm.verts.new((0,              BRACKET_WIDTH, BRACKET_THICK)),
]
faces = [
    [verts[0], verts[1], verts[2], verts[3]],  # bottom
    [verts[4], verts[7], verts[6], verts[5]],  # top
    [verts[0], verts[4], verts[5], verts[1]],  # front
    [verts[2], verts[6], verts[7], verts[3]],  # back
    [verts[0], verts[3], verts[7], verts[4]],  # left
    [verts[1], verts[5], verts[6], verts[2]],  # right
]
for f in faces:
    bm.faces.new(f)

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(mesh)
bm.free()

bracket = bpy.data.objects.new("Bracket", mesh)
bpy.context.collection.objects.link(bracket)
bpy.context.view_layer.objects.active = bracket
bracket.select_set(True)

# ============================================================
# 2. Bevel all edges EXCEPT the bottom face
#    Uses bmesh.ops.bevel directly — no modifier, no version-specific
#    layer APIs (avoids the bevel_weight removal in Blender 4.0+).
# ============================================================
bm_bevel = bmesh.new()
bm_bevel.from_mesh(bracket.data)

# Include every edge whose vertices are NOT all at Z ≈ 0 (bottom face)
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
# 3. Boolean-cut countersunk holes
# ============================================================
def make_countersink_cutter(name, hx, hy):
    """
    Create a combined mesh: countersink cone on top of shank cylinder.
    The cutter is taller than the bracket so it punches fully through.
    """
    cutter_mesh = bpy.data.meshes.new(name + "_mesh")
    bm2 = bmesh.new()

    extra = 2.0  # mm overshoot on each end to ensure clean boolean

    # --- shank cylinder (full height + overshoot) ---
    r_shank = HOLE_DIAMETER / 2
    shank = bmesh.ops.create_cone(
        bm2,
        cap_ends=True, cap_tris=False,
        segments=HOLE_SEGMENTS,
        radius1=r_shank,
        radius2=r_shank,
        depth=BRACKET_THICK + extra * 2,
    )
    # Translate ONLY the shank verts; create_cone centres at origin
    bmesh.ops.translate(bm2, verts=shank['verts'],
                        vec=(hx, hy, BRACKET_THICK / 2))

    # --- countersink cone (top of bracket, pointing upward) ---
    # Top radius = CSNK_DIAMETER/2, bottom radius = HOLE_DIAMETER/2
    r_top        = CSNK_DIAMETER / 2
    csk_centre_z = BRACKET_THICK - CSNK_DEPTH / 2
    csk = bmesh.ops.create_cone(
        bm2,
        cap_ends=True, cap_tris=False,
        segments=HOLE_SEGMENTS,
        radius1=HOLE_DIAMETER / 2,   # bottom of cone (narrow)
        radius2=r_top,               # top of cone (wide)
        depth=CSNK_DEPTH + extra,
    )
    # Translate ONLY the cone verts — shank verts are already in place
    bmesh.ops.translate(bm2, verts=csk['verts'],
                        vec=(hx, hy, csk_centre_z + extra / 2))

    bmesh.ops.recalc_face_normals(bm2, faces=bm2.faces)
    bm2.to_mesh(cutter_mesh)
    bm2.free()

    cutter_obj = bpy.data.objects.new(name, cutter_mesh)
    bpy.context.collection.objects.link(cutter_obj)
    return cutter_obj


for idx, (hx, hy) in enumerate(ALL_HOLES):
    cutter = make_countersink_cutter(f"HoleCutter_{idx:02d}", hx, hy)
    bool_mod = bracket.modifiers.new(f"BoolHole_{idx:02d}", 'BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object    = cutter
    bool_mod.solver    = 'EXACT'
    bpy.context.view_layer.objects.active = bracket
    bpy.ops.object.modifier_apply(modifier=bool_mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)

# ============================================================
# 4. Finalise and export
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
