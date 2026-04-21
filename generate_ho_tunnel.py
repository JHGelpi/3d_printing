"""
HO Scale Ceiling Tunnel — bpy Generator  (v2)
----------------------------------------------
Generates a decorative tunnel for an HO scale model railroad.

Assembly overview:
  • The 1×6 board (0.75" × 5.5" actual) is the tunnel floor, hung from the ceiling.
  • The tunnel body wraps around the board and track — open at both ends.
  • A solid floor panel (Z = 0) has four countersunk screw holes to fasten the
    tunnel onto the 1×6 board from below (countersinks on exterior bottom face).
  • A solid ceiling panel at the top (Z = TOTAL_H) has no holes.
  • Decorative end portals are taller than the side walls (7" vs 3").
  • Each end portal has an arched train opening and a smaller decorative arch window.
  • Three rectangular windows per side wall.
  • L-shaped mounting brackets extend above the ceiling on each side wall near each end.
    Vertical part is flush with wall; horizontal part (2" long) extends inward.
    Screw holes are on the BOTTOM face of horizontal extension (along tunnel axis).

Coordinate system (all mm, origin at tunnel floor exterior face):
  Y  =  along track  (tunnel length)
  X  =  across track (tunnel width)
  Z  =  vertical up  (Z = 0 at exterior floor face,  Z = WALL_T at interior floor)

Print notes (Bambu P2S, 256 × 256 × 256 mm):
  FloorPanel / CeilingPanel : 241 × 152 mm — print flat    ✓
  Side walls                : 241 × ~102 mm — print flat   ✓
  End portals               : 152 × 178 mm — print flat    ✓
  L-brackets                : ~51 × 51 mm — print flat (L side down)  ✓
  (All components fit individually; full assembled height exceeds bed.)
"""

import math
import os

import bmesh
import bpy

# ════════════════════════════════════════════════════════════════
#  PARAMETERS  —  all dimensions in mm
# ════════════════════════════════════════════════════════════════

# ── Tunnel shell ──────────────────────────────────────────────────
TUNNEL_LEN = 241.3  # mm (9.5") — outer length along Y (track axis)
TUNNEL_W = 152.4  # mm (6.0") — outer width along X
WALL_T = 5.5  # mm (0.22") — all wall / panel thickness
SIDE_H = 82.6  # mm (3.25") — interior clear height (0.25" track + 3.0" train)

# ── End portals ───────────────────────────────────────────────────
PORTAL_H = 177.8  # mm (7.0") — end facade total height

# ── Train arch opening (each end portal) ──────────────────────────
#    Must clear HO trains — typical max ~40 mm wide × 50 mm tall
ARCH_W = 88.9  # mm (3.5") — opening width
ARCH_SPRING_H = 63.5  # mm (2.5") — rectangular height below spring line
ARCH_R = ARCH_W / 2  # mm — semicircle radius

# ── Decorative arch window (upper portal section) ─────────────────
DECO_W = 63.5  # mm (2.5")
DECO_SPRING_H = 12.7  # mm (0.5")
DECO_R = DECO_W / 2  # mm

# ── Side wall windows (3 per side) ────────────────────────────────
SIDE_WIN_WIDTHS = [50.8, 38.1, 50.8]  # mm (2.0", 1.5", 2.0")
SIDE_WIN_H = 25.4  # mm (1.0") — window height
SIDE_WIN_Z_BOT = 12.7  # mm (0.5") — window bottom above INTERIOR floor

# ── Floor panel screw holes ────────────────────────────────────────
# Countersink opens on the exterior (bottom) face of the floor panel (Z = 0).
# Screw head sits flush with the exterior floor.  Adjust to your fastener.
FLOOR_SHANK_D = 6.35  # mm (0.25") — shaft / shank clearance diameter
FLOOR_CSK_D = 12.7  # mm (0.5") — countersink outer diameter at surface
FLOOR_CSK_DEPTH = 3.5  # mm — countersink depth
# 4 hole positions (X, Y) — symmetric about centre, one near each corner
FLOOR_SCREW_POS = [
    (-38.1, 88.9),  # mm (-1.5", 3.5")
    (38.1, 88.9),  # mm (1.5", 3.5")
    (-38.1, -88.9),  # mm (-1.5", -3.5")
    (38.1, -88.9),  # mm (1.5", -3.5")
]

# ── Mounting brackets ──────────────────────────────────────────────
# L-shaped brackets: vertical part flush with side wall, horizontal extension at top
# extending inward.  Screw holes on the BOTTOM face of horizontal extension.
# Heights can be set independently for each of the 4 brackets:
# Total distance from bracket top to floor top = 260 mm
BRKT_HEIGHTS = {
    ("Left", "Front"): 171.9,  # mm (6.77") — Left-Front bracket height
    ("Left", "Back"): 171.9,  # mm (6.77") — Left-Back bracket height
    ("Right", "Front"): 171.9,  # mm (6.77") — Right-Front bracket height
    ("Right", "Back"): 171.9,  # mm (6.77") — Right-Back bracket height
}
BRKT_LEN = 50.8  # mm (2.0") — bracket length along Y (tunnel axis)
BRKT_HORIZ_EXT = (
    # -50.8
    -55
)  # mm (2.0") — horizontal extension inward from wall (negative = inward)
BRKT_SHANK_D = 4.57  # mm (0.18") — bracket screw shank diameter
BRKT_CSK_D = 8.89  # mm (0.35") — bracket countersink outer diameter
BRKT_CSK_DEPTH = 2.0  # mm — bracket countersink depth
BRKT_SCREW_N = 3  # screw holes per bracket
# Hole positioning controls:
#   BRKT_HOLE_END_MARGIN: distance from front/back edges to first/last hole (along Y)
#   BRKT_HOLE_X_OFFSET: shift holes along X (+ = toward tunnel center, - = toward wall)
BRKT_HOLE_END_MARGIN = 7.62  # mm (0.3") — margin from each end (front/back) along Y
BRKT_HOLE_X_OFFSET = -16.5  # mm (-0.25") — offset from center of horizontal extension
# Transom support (45° triangular gusset for structural strength):
BRKT_TRANSOM_SIZE = (
    40.0  # mm — length along both vertical and horizontal edges of transom
)

# ── Bracket attachment (for modular printing) ─────────────────────
# Brackets attach to ceiling via mounting tabs with bolt holes
BRKT_TAB_WIDTH = 100.0  # mm — width of mounting tab extending from bracket leg
# BRKT_TAB_LENGTH = 30.0  # mm — length of mounting tab along Y axis
BRKT_TAB_LENGTH = 50.0  # mm — length of mounting tab along Y axis
BRKT_TAB_THICKNESS = 5.5  # mm — same as WALL_T for flush mounting
BRKT_TAB_INWARD_OFFSET = (
    5.0  # mm — additional inward offset for tab position (+ = more inward)
)
BRKT_BOLT_HOLES = 2  # number of bolt holes per bracket tab
BRKT_BOLT_D = 4.0  # mm — bolt hole diameter (for M4 bolts)
BRKT_BOLT_SPACING = 20.0  # mm — spacing between bolt holes along Y

# ── Pitch configuration ───────────────────────────────────────────
# Pitch (grade) of floor board as "rise over run" percentage.
# This tilts the floor panel along the Y-axis (tunnel length).
# Positive = rising from Back (-Y) to Front (+Y).
# NOTE: Ceiling brackets remain flat (0 degrees).
PITCH_PERCENT = 3.0  # percent — 3% = 3 units rise per 100 units run

# ── Mesh quality ──────────────────────────────────────────────────
ARCH_SEGS = 32
HOLE_SEGS = 32
BOOL_EXTRA = 2.0  # mm — cutter overshoot for clean boolean results

# ── Derived constants ─────────────────────────────────────────────
TOTAL_H = WALL_T + SIDE_H + WALL_T  # Z = 0 (floor ext) → TOTAL_H (ceiling ext)
INNER_LEN = TUNNEL_LEN - 2 * WALL_T  # Y clear span between portal inner faces
INNER_W = TUNNEL_W - 2 * WALL_T  # X interior clear width
PITCH_ANGLE_RAD = math.atan(
    PITCH_PERCENT / 100.0
)  # radians — pitch angle for rotations


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


def link_to(col, obj):
    """Move obj into collection col (unlink from scene root if needed)."""
    col.objects.link(obj)
    try:
        bpy.context.scene.collection.objects.unlink(obj)
    except RuntimeError:
        pass
    return obj


def make_cone_cutter(name, cx, cy, cz, r_bot, r_top, height, segs=HOLE_SEGS):
    """
    Solid frustum (or cylinder when r_bot == r_top) centred at (cx, cy, cz).
    Aligned with Z; radius1 = bottom cap, radius2 = top cap.
    """
    bm = bmesh.new()
    ret = bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=segs,
        radius1=r_bot,
        radius2=r_top,
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


def cut_csunk_down(target, name, cx, cy, top_z, depth, shank_d, csk_d, csk_depth):
    """
    Cut a countersunk hole going DOWN from top_z through 'depth' mm of material.
    The countersink widens at the top face (top_z) — screw head recessed there.

    Two-pass approach (from generate_flat_bracket.py pattern):
      Pass 1 — straight shank cylinder through full depth.
      Pass 2 — conical frustum at the top face only.
    """
    slope = (csk_d / 2 - shank_d / 2) / csk_depth

    # Pass 1: shank (straight, full depth + overshoot both ends)
    shank_h = depth + 2 * BOOL_EXTRA
    shank_cz = top_z - depth / 2
    shank = make_cone_cutter(
        f"{name}_shank",
        cx,
        cy,
        shank_cz,
        shank_d / 2,
        shank_d / 2,
        shank_h,
    )
    bool_diff(target, shank)

    # Pass 2: countersink frustum (wide at top, narrow at depth)
    csk_h = csk_depth + BOOL_EXTRA
    csk_cz = top_z - csk_depth / 2
    r_top_v = csk_d / 2 + slope * (BOOL_EXTRA / 2)  # slightly wider above surface
    r_bot_v = max(shank_d / 2 - slope * (BOOL_EXTRA / 2), 0.01)
    csk = make_cone_cutter(
        f"{name}_csk",
        cx,
        cy,
        csk_cz,
        r_bot_v,
        r_top_v,
        csk_h,
    )
    bool_diff(target, csk)


def cut_csunk_up(target, name, cx, cy, bottom_z, depth, shank_d, csk_d, csk_depth):
    """
    Cut a countersunk hole going UP from bottom_z through 'depth' mm of material.
    The countersink widens at the bottom face (bottom_z) — screw head recessed there.

    Two-pass approach (from generate_flat_bracket.py pattern):
      Pass 1 — straight shank cylinder through full depth.
      Pass 2 — conical frustum at the bottom face only.
    """
    slope = (csk_d / 2 - shank_d / 2) / csk_depth

    # Pass 1: shank (straight, full depth + overshoot both ends)
    shank_h = depth + 2 * BOOL_EXTRA
    shank_cz = bottom_z + depth / 2
    shank = make_cone_cutter(
        f"{name}_shank",
        cx,
        cy,
        shank_cz,
        shank_d / 2,
        shank_d / 2,
        shank_h,
    )
    bool_diff(target, shank)

    # Pass 2: countersink frustum (wide at bottom, narrow at depth)
    csk_h = csk_depth + BOOL_EXTRA
    csk_cz = bottom_z + csk_depth / 2
    r_bot_v = csk_d / 2 + slope * (BOOL_EXTRA / 2)  # wide at bottom
    r_top_v = max(shank_d / 2 - slope * (BOOL_EXTRA / 2), 0.01)  # narrow at top
    csk = make_cone_cutter(
        f"{name}_csk",
        cx,
        cy,
        csk_cz,
        r_bot_v,
        r_top_v,
        csk_h,
    )
    bool_diff(target, csk)


def make_arch_cutter(name, w, spring_h, r, depth, segs=ARCH_SEGS):
    """
    Solid arch cutter: rectangle [w × spring_h] topped with a semicircle
    of radius r.  Extruded along Y by 'depth', base profile at Z = 0.
    """
    bm = bmesh.new()

    pts = [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, spring_h)]
    for i in range(1, segs):
        a = math.pi * i / segs
        pts.append((r * math.cos(math.pi - a), spring_h + r * math.sin(a)))
    pts.append((-w / 2, spring_h))

    y0, y1 = -depth / 2, depth / 2
    front = [bm.verts.new((x, y0, z)) for x, z in pts]
    back = [bm.verts.new((x, y1, z)) for x, z in pts]
    bm.verts.ensure_lookup_table()

    n = len(pts)
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([front[i], back[i], back[j], front[j]])

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def make_45deg_transom(name, cx, cy, cz, size, length, x_direction):
    """
    Create a 45-degree triangular transom support (gusset).

    Triangular cross-section in XZ plane, extruded along Y.
    - Right angle at origin of triangle
    - 45-degree hypotenuse
    - size: length along both X and Z edges from the corner (equal for 45°)
    - length: extrusion along Y axis
    - x_direction: +1 for extending +X, -1 for extending -X

    Position (cx, cy, cz) is the inner corner where vertical meets horizontal.
    """
    bm = bmesh.new()

    # Define the triangular profile vertices (right-angle triangle)
    # Front face (Y = -length/2)
    y0 = -length / 2
    # Back face (Y = +length/2)
    y1 = length / 2

    # Triangle vertices in local XZ plane (before positioning):
    # Corner at (0, 0), extends along X (signed) and -Z (downward along vertical leg)
    v0 = (0, 0)  # Right angle corner
    v1 = (size * x_direction, 0)  # Along X (horizontal edge, inward)
    v2 = (0, -size)  # Along -Z (vertical edge, downward)

    # Create front and back faces
    front = [
        bm.verts.new((cx + v0[0], cy + y0, cz + v0[1])),
        bm.verts.new((cx + v1[0], cy + y0, cz + v1[1])),
        bm.verts.new((cx + v2[0], cy + y0, cz + v2[1])),
    ]
    back = [
        bm.verts.new((cx + v0[0], cy + y1, cz + v0[1])),
        bm.verts.new((cx + v1[0], cy + y1, cz + v1[1])),
        bm.verts.new((cx + v2[0], cy + y1, cz + v2[1])),
    ]

    bm.verts.ensure_lookup_table()

    # Create faces
    bm.faces.new(front)  # Front triangle
    bm.faces.new(list(reversed(back)))  # Back triangle

    # Side faces (3 rectangular faces connecting front and back)
    bm.faces.new([front[0], back[0], back[1], front[1]])  # Bottom
    bm.faces.new([front[1], back[1], back[2], front[2]])  # Hypotenuse
    bm.faces.new([front[2], back[2], back[0], front[0]])  # Vertical edge

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
col = bpy.data.collections.new("HO_Tunnel")
bpy.context.scene.collection.children.link(col)


# ── 1. FLOOR PANEL ────────────────────────────────────────────────
# Solid slab at Z = 0 → WALL_T.
# Four countersunk screw holes; heads recessed into the exterior bottom face (Z = 0).
# Rotated to match floor board pitch.

floor = box("FloorPanel", 0, 0, WALL_T / 2, TUNNEL_W, TUNNEL_LEN, WALL_T)
link_to(col, floor)

# Rotate floor panel to match floor board pitch (around X-axis to tilt along Y)
floor.rotation_euler = (PITCH_ANGLE_RAD, 0, 0)
bpy.context.view_layer.objects.active = floor
floor.select_set(True)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
floor.select_set(False)

for i, (sx, sy) in enumerate(FLOOR_SCREW_POS):
    # Adjust Z for pitch: as Y increases (toward +Y/Front), Z increases due to pitch
    # Floor panel is rotated around its center (0, 0, WALL_T/2)
    dz_from_pitch = sy * math.tan(PITCH_ANGLE_RAD)
    floor_bottom_z = 0 + dz_from_pitch

    cut_csunk_up(
        floor,
        f"FloorHole_{i}",
        sx,
        sy,
        floor_bottom_z,
        WALL_T,
        FLOOR_SHANK_D,
        FLOOR_CSK_D,
        FLOOR_CSK_DEPTH,
    )


# ── 2. CEILING PANEL ───────────────────────────────────────────────
# Solid slab at Z = TOTAL_H - WALL_T → TOTAL_H.
# Bolt holes for bracket attachment.

ceiling = box("CeilingPanel", 0, 0, TOTAL_H - WALL_T / 2, TUNNEL_W, TUNNEL_LEN, WALL_T)
link_to(col, ceiling)

# Add bracket mounting bolt holes through ceiling panel
for side_label, wx in [
    ("Left", -(TUNNEL_W / 2 - WALL_T / 2)),
    ("Right", TUNNEL_W / 2 - WALL_T / 2),
]:
    for end_label, by in [
        ("Front", TUNNEL_LEN / 2 - BRKT_LEN / 2),
        ("Back", -(TUNNEL_LEN / 2 - BRKT_LEN / 2)),
    ]:
        # Calculate tab center position (matching bracket tab)
        # Tab extends inward from inner edge of vertical leg
        if side_label == "Left":
            tab_cx = wx + WALL_T + BRKT_TAB_INWARD_OFFSET
        else:  # Right
            tab_cx = wx - WALL_T - BRKT_TAB_INWARD_OFFSET

        # Add bolt holes at same positions as bracket tab holes
        for bi in range(BRKT_BOLT_HOLES):
            if BRKT_BOLT_HOLES == 1:
                bolt_y = by
            else:
                spacing = BRKT_BOLT_SPACING
                bolt_y = by - spacing / 2 + bi * spacing

            ceiling_hole = make_cone_cutter(
                f"CeilingBoltHole_{side_label}_{end_label}_{bi}",
                tab_cx,
                bolt_y,
                TOTAL_H - WALL_T / 2,
                BRKT_BOLT_D / 2,
                BRKT_BOLT_D / 2,
                WALL_T + 2 * BOOL_EXTRA,
            )
            bool_diff(ceiling, ceiling_hole)


# ── 3. SIDE WALLS (Left & Right) ──────────────────────────────────
# Full exterior height TOTAL_H (floor to ceiling).
# Three rectangular windows with bottoms 0.5" above the interior floor.

total_win_w = sum(SIDE_WIN_WIDTHS)
gap = (INNER_LEN - total_win_w) / 4.0  # 4 equal gaps (edges + between windows)

for side_label, wx in [
    ("Left", -(TUNNEL_W / 2 - WALL_T / 2)),
    ("Right", TUNNEL_W / 2 - WALL_T / 2),
]:
    wall = box(
        f"SideWall_{side_label}", wx, 0, TOTAL_H / 2, WALL_T, TUNNEL_LEN, TOTAL_H
    )
    link_to(col, wall)

    y_cursor = -INNER_LEN / 2 + gap
    for wi, ww in enumerate(SIDE_WIN_WIDTHS):
        win_cy = y_cursor + ww / 2
        # Z measured from exterior floor; interior floor is at WALL_T
        win_cz = WALL_T + SIDE_WIN_Z_BOT + SIDE_WIN_H / 2
        cutter = box(
            f"Win_{side_label}_{wi}", wx, win_cy, win_cz, WALL_T * 3, ww, SIDE_WIN_H
        )
        bool_diff(wall, cutter)
        y_cursor += ww + gap


# ── 4. END PORTALS (Front & Back) ─────────────────────────────────
# 7" tall decorative facades. Train arch base at Z = 0 (exterior floor).
# Deco arch window sits above the tunnel ceiling level.

DECO_Z_BASE = TOTAL_H + 19.05  # mm (0.75") — base of deco arch; verify < PORTAL_H

for end_label, py in [
    ("Front", TUNNEL_LEN / 2 - WALL_T / 2),
    ("Back", -(TUNNEL_LEN / 2 - WALL_T / 2)),
]:
    portal = box(f"Portal_{end_label}", 0, py, PORTAL_H / 2, TUNNEL_W, WALL_T, PORTAL_H)
    link_to(col, portal)

    # Train arch opening (base at Z = 0)
    train_arch = make_arch_cutter(
        f"TrainArch_{end_label}", ARCH_W, ARCH_SPRING_H, ARCH_R, WALL_T * 3
    )
    train_arch.location = (0, py, 0)
    bool_diff(portal, train_arch)

    # Decorative arch window (above tunnel ceiling)
    deco_arch = make_arch_cutter(
        f"DecoArch_{end_label}", DECO_W, DECO_SPRING_H, DECO_R, WALL_T * 3
    )
    deco_arch.location = (0, py, DECO_Z_BASE)
    bool_diff(portal, deco_arch)


# ── 5. MOUNTING BRACKETS ──────────────────────────────────────────
# L-shaped brackets rising above the ceiling panel, one near each
# end of each side wall (4 total).
#
# • Vertical part: flush with side wall, extends upward from ceiling
# • Horizontal part: at top of vertical, extends inward (toward tunnel center)
# • Screw holes on the BOTTOM face of horizontal part, along Y (parallel to tunnel axis)
# • All holes countersunk (heads recessed into bottom face)

for side_label, wx in [
    ("Left", -(TUNNEL_W / 2 - WALL_T / 2)),
    ("Right", TUNNEL_W / 2 - WALL_T / 2),
]:
    for end_label, by in [
        ("Front", TUNNEL_LEN / 2 - BRKT_LEN / 2),
        ("Back", -(TUNNEL_LEN / 2 - BRKT_LEN / 2)),
    ]:
        # Get the height for this specific bracket
        brkt_height = BRKT_HEIGHTS[(side_label, end_label)]

        # Vertical part: flush with side wall, sits directly on ceiling
        # Bottom of leg is at ceiling level (TOTAL_H)
        vert_cz = TOTAL_H + brkt_height / 2
        brkt_vert = box(
            f"BracketVert_{side_label}_{end_label}",
            wx,
            by,
            vert_cz,
            WALL_T,
            BRKT_LEN,
            brkt_height,
        )

        # Add mounting tab at ceiling level for bolt attachment
        # Tab sits ON TOP of the ceiling panel (outside the tunnel)
        # Tab has SAME WIDTH as leg (WALL_T) and extends INWARD from inner edge of leg
        # Tab and leg are touching (adjacent) to form one seamless piece
        if side_label == "Left":
            # Left: tab extends inward (+X) from inner edge of leg
            # Inner edge of leg is at: wx + WALL_T/2
            # Tab center: wx + WALL_T/2 + WALL_T/2 + offset = wx + WALL_T + offset
            tab_cx = wx + WALL_T + BRKT_TAB_INWARD_OFFSET
        else:  # Right
            # Right: tab extends inward (-X) from inner edge of leg
            # Inner edge of leg is at: wx - WALL_T/2
            # Tab center: wx - WALL_T/2 - WALL_T/2 - offset = wx - WALL_T - offset
            tab_cx = wx - WALL_T - BRKT_TAB_INWARD_OFFSET

        tab_cz = (
            TOTAL_H + BRKT_TAB_THICKNESS / 2
        )  # On top of ceiling panel, same Z as bottom of leg

        mounting_tab = box(
            f"MountingTab_{side_label}_{end_label}",
            tab_cx,
            by,
            tab_cz,
            BRKT_TAB_WIDTH,  # Width of mounting tab (configurable parameter)
            BRKT_TAB_LENGTH,
            BRKT_TAB_THICKNESS,
        )

        # Add bolt holes through mounting tab
        for bi in range(BRKT_BOLT_HOLES):
            if BRKT_BOLT_HOLES == 1:
                bolt_y = by
            else:
                spacing = BRKT_BOLT_SPACING
                bolt_y = by - spacing / 2 + bi * spacing

            bolt_hole = make_cone_cutter(
                f"TabBoltHole_{side_label}_{end_label}_{bi}",
                tab_cx,
                bolt_y,
                tab_cz,
                BRKT_BOLT_D / 2,
                BRKT_BOLT_D / 2,
                BRKT_TAB_THICKNESS + 2 * BOOL_EXTRA,
            )
            bool_diff(mounting_tab, bolt_hole)

        # Union mounting tab with vertical bracket leg
        bool_union(brkt_vert, mounting_tab)

        # Horizontal part: extends inward from top of vertical part
        # For left wall: extends toward +X (inward)
        # For right wall: extends toward -X (inward)
        if side_label == "Left":
            # Inner edge of vertical part is at: wx + WALL_T/2
            # Center of horizontal extension: wx + WALL_T/2 + BRKT_HORIZ_EXT/2
            horiz_cx = wx + WALL_T / 2 + BRKT_HORIZ_EXT / 2
        else:  # Right
            # Inner edge of vertical part is at: wx - WALL_T/2
            # Center of horizontal extension: wx - WALL_T/2 - BRKT_HORIZ_EXT/2
            horiz_cx = wx - WALL_T / 2 - BRKT_HORIZ_EXT / 2

        # Create horizontal bracket at final position (flat, no pitch)
        # Hole X offset: toward tunnel center for left, away from center for right
        if side_label == "Left":
            hole_x_offset = BRKT_HOLE_X_OFFSET  # Toward center
        else:  # Right
            hole_x_offset = -BRKT_HOLE_X_OFFSET  # Toward center (from right side)

        brkt_horiz = box(
            f"BracketHoriz_{side_label}_{end_label}",
            horiz_cx,
            by,
            TOTAL_H + brkt_height - WALL_T / 2,
            BRKT_HORIZ_EXT,
            BRKT_LEN,
            WALL_T,
        )

        # Cut screw holes (bracket is flat - 0 degree pitch)
        available_len = BRKT_LEN - 2 * BRKT_HOLE_END_MARGIN
        horiz_bottom_z = TOTAL_H + brkt_height - WALL_T

        for hi in range(BRKT_SCREW_N):
            if BRKT_SCREW_N == 1:
                # Single hole: centered
                hy = by
            else:
                # Multiple holes: evenly spaced between margins
                spacing = available_len / (BRKT_SCREW_N - 1)
                hy = by - BRKT_LEN / 2 + BRKT_HOLE_END_MARGIN + hi * spacing

            # Hole X position
            if side_label == "Left":
                hole_x = horiz_cx + hole_x_offset
            else:  # Right
                hole_x = horiz_cx + hole_x_offset  # Already negated above

            cut_csunk_up(
                brkt_horiz,
                f"BrktHole_{side_label}_{end_label}_{hi}",
                hole_x,
                hy,
                horiz_bottom_z,  # Flat surface - same Z for all holes
                WALL_T,
                BRKT_SHANK_D,
                BRKT_CSK_D,
                BRKT_CSK_DEPTH,
            )

        # Add 45-degree transom support (triangular gusset) for structural strength
        # Position at inner corner where vertical meets horizontal
        # Transom fills the INTERIOR angle of the L-bracket
        if side_label == "Left":
            # Left side: horizontal extends +X, so transom extends -X (back along vertical)
            transom_cx = wx + WALL_T / 2  # Inner edge of vertical part
            x_dir = -1  # Extend -X (toward the vertical wall)
        else:  # Right
            # Right side: horizontal extends -X, so transom extends +X (back along vertical)
            transom_cx = wx - WALL_T / 2  # Inner edge of vertical part
            x_dir = 1  # Extend +X (toward the vertical wall)

        transom_cz = (
            TOTAL_H + brkt_height - WALL_T
        )  # Bottom of horizontal part (junction)

        transom = make_45deg_transom(
            f"Transom_{side_label}_{end_label}",
            transom_cx,
            by,
            transom_cz,
            BRKT_TRANSOM_SIZE,  # size along both edges (equal for 45°)
            BRKT_LEN,  # length along Y
            x_dir,  # direction: +1 or -1
        )

        # Cut the same screw holes through the transom gusset
        # Re-use the same hole positions calculated earlier
        for hi in range(BRKT_SCREW_N):
            if BRKT_SCREW_N == 1:
                hy = by
            else:
                spacing = available_len / (BRKT_SCREW_N - 1)
                hy = by - BRKT_LEN / 2 + BRKT_HOLE_END_MARGIN + hi * spacing

            if side_label == "Left":
                hole_x = horiz_cx + hole_x_offset
            else:  # Right
                hole_x = horiz_cx + hole_x_offset

            cut_csunk_up(
                transom,
                f"TransomHole_{side_label}_{end_label}_{hi}",
                hole_x,
                hy,
                horiz_bottom_z,  # Same Z as horizontal bracket holes
                WALL_T,  # Depth through transom (same as horizontal bracket thickness)
                BRKT_SHANK_D,
                BRKT_CSK_D,
                BRKT_CSK_DEPTH,
            )

        # Union vertical, horizontal, and transom parts into reinforced L-shape
        bool_union(brkt_vert, brkt_horiz)
        bool_union(brkt_vert, transom)
        brkt = brkt_vert
        brkt.name = f"Bracket_{side_label}_{end_label}"
        link_to(col, brkt)


# ════════════════════════════════════════════════════════════════
#  EXPORT EACH PART AS STL
# ════════════════════════════════════════════════════════════════

script_dir = os.path.dirname(os.path.abspath(__file__))
# If running from within a .blend file, use the parent directory
if script_dir.endswith(".blend"):
    script_dir = os.path.dirname(script_dir)
output_dir = os.path.join(script_dir, "output")
os.makedirs(output_dir, exist_ok=True)

bpy.ops.object.select_all(action="DESELECT")
for obj in col.objects:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    out_path = os.path.join(output_dir, f"{obj.name}.stl")
    bpy.ops.wm.stl_export(filepath=out_path, export_selected_objects=True)
    obj.select_set(False)

print("=" * 62)
print("  HO Tunnel — build complete (v2)")
print("=" * 62)
print(f"  Tunnel length         : {TUNNEL_LEN:.1f} mm")
print(f"  Tunnel width          : {TUNNEL_W:.1f} mm")
print(f"  Interior clear height : {SIDE_H:.1f} mm")
print(f"  Total exterior height : {TOTAL_H:.1f} mm")
print(f"  Portal height         : {PORTAL_H:.1f} mm")
print(
    f"  Pitch (grade)         : {PITCH_PERCENT:.1f}% ({PITCH_ANGLE_RAD * 180 / math.pi:.3f}°)"
)
print(
    f"  Train arch            : {ARCH_W:.1f} mm wide × {ARCH_SPRING_H + ARCH_R:.1f} mm tall"
)
print(
    f"  Floor screw holes     : Ø{FLOOR_SHANK_D:.2f} mm shank / "
    f"CSK Ø{FLOOR_CSK_D:.2f} mm × {len(FLOOR_SCREW_POS)}"
)
print(f"  Bracket heights:")
for (side, end), height in BRKT_HEIGHTS.items():
    print(f"    {side:5s}-{end:5s}: {height:.1f} mm")
print(f"  Bracket extension     : {abs(BRKT_HORIZ_EXT):.1f} mm")
print(
    f"  Bracket screw holes   : Ø{BRKT_SHANK_D:.2f} mm × {BRKT_SCREW_N} per bracket × 4 brackets"
)
print(f"  Output dir            : {output_dir}")
print("=" * 62)
