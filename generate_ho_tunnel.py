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
    Screw holes are on the TOP face of horizontal extension (along tunnel axis).

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
#  PARAMETERS  —  edit these; all dimensions in mm unless noted
# ════════════════════════════════════════════════════════════════

IN = 25.4  # mm per inch

# ── Tunnel shell ──────────────────────────────────────────────────
TUNNEL_LEN    = 9.5  * IN   # 241.3 mm — outer length along Y (track axis)
TUNNEL_W      = 6.0  * IN   # 152.4 mm — outer width along X
WALL_T        = 0.5  * IN   #  12.7 mm — all wall / panel thickness
SIDE_H        = 3.0  * IN   #  76.2 mm — interior clear height

# ── End portals ───────────────────────────────────────────────────
PORTAL_H      = 7.0  * IN   # 177.8 mm — end facade total height

# ── Train arch opening (each end portal) ──────────────────────────
#    Must clear HO trains — typical max ~40 mm wide × 50 mm tall
ARCH_W        = 3.5  * IN   #  88.9 mm — opening width
ARCH_SPRING_H = 2.5  * IN   #  63.5 mm — rectangular height below spring line
ARCH_R        = ARCH_W / 2  #  44.45 mm — semicircle radius

# ── Decorative arch window (upper portal section) ─────────────────
DECO_W        = 2.5  * IN   #  63.5 mm
DECO_SPRING_H = 0.5  * IN   #  12.7 mm
DECO_R        = DECO_W / 2  #  31.75 mm

# ── Side wall windows (3 per side: 2" / 1.5" / 2") ───────────────
SIDE_WIN_WIDTHS  = [2.0 * IN, 1.5 * IN, 2.0 * IN]
SIDE_WIN_H       = 1.0 * IN   #  25.4 mm — window height
SIDE_WIN_Z_BOT   = 0.5 * IN   #  12.7 mm — window bottom above INTERIOR floor

# ── Floor panel screw holes ────────────────────────────────────────
# Countersink opens on the exterior (bottom) face of the floor panel (Z = 0).
# Screw head sits flush with the exterior floor.  Adjust to your fastener.
FLOOR_SHANK_D    = 0.25 * IN  #   6.35 mm — shaft / shank clearance diameter
FLOOR_CSK_D      = 0.5  * IN  #  12.7  mm — countersink outer diameter at surface
FLOOR_CSK_DEPTH  = 3.5         # mm       — countersink depth
# 4 hole positions (X, Y) — symmetric about centre, one near each corner
FLOOR_SCREW_POS  = [
    (-1.5 * IN,  3.5 * IN),
    ( 1.5 * IN,  3.5 * IN),
    (-1.5 * IN, -3.5 * IN),
    ( 1.5 * IN, -3.5 * IN),
]

# ── Mounting brackets ──────────────────────────────────────────────
# L-shaped brackets: vertical part flush with side wall, horizontal extension at top
# extending inward.  Screw holes on the TOP face of horizontal extension.
BRKT_HEIGHT    = 1.0  * IN   #  25.4 mm — vertical height above ceiling
BRKT_LEN       = 2.0  * IN   #  50.8 mm — bracket length along Y (tunnel axis)
BRKT_HORIZ_EXT = 2.0  * IN   #  50.8 mm — horizontal extension inward from wall
BRKT_SHANK_D   = 0.18 * IN   #   4.57 mm — bracket screw shank diameter
BRKT_CSK_D     = 0.35 * IN   #   8.89 mm — bracket countersink outer diameter
BRKT_CSK_DEPTH = 2.0          # mm       — bracket countersink depth
BRKT_SCREW_N   = 3            # screw holes per bracket

# ── Mesh quality ──────────────────────────────────────────────────
ARCH_SEGS  = 32
HOLE_SEGS  = 32
BOOL_EXTRA = 2.0   # mm — cutter overshoot for clean boolean results

# ── Derived constants ─────────────────────────────────────────────
TOTAL_H   = WALL_T + SIDE_H + WALL_T  # Z = 0 (floor ext) → TOTAL_H (ceiling ext)
INNER_LEN = TUNNEL_LEN - 2 * WALL_T   # Y clear span between portal inner faces
INNER_W   = TUNNEL_W   - 2 * WALL_T   # X interior clear width


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
        bm, cap_ends=True, cap_tris=False,
        segments=segs, radius1=r_bot, radius2=r_top, depth=height,
    )
    bmesh.ops.translate(bm, verts=ret["verts"], vec=(cx, cy, cz))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def cut_csunk_down(target, name, cx, cy, top_z, depth,
                   shank_d, csk_d, csk_depth):
    """
    Cut a countersunk hole going DOWN from top_z through 'depth' mm of material.
    The countersink widens at the top face (top_z) — screw head recessed there.

    Two-pass approach (from generate_flat_bracket.py pattern):
      Pass 1 — straight shank cylinder through full depth.
      Pass 2 — conical frustum at the top face only.
    """
    slope = (csk_d / 2 - shank_d / 2) / csk_depth

    # Pass 1: shank (straight, full depth + overshoot both ends)
    shank_h  = depth + 2 * BOOL_EXTRA
    shank_cz = top_z - depth / 2
    shank = make_cone_cutter(
        f"{name}_shank", cx, cy, shank_cz,
        shank_d / 2, shank_d / 2, shank_h,
    )
    bool_diff(target, shank)

    # Pass 2: countersink frustum (wide at top, narrow at depth)
    csk_h   = csk_depth + BOOL_EXTRA
    csk_cz  = top_z - csk_depth / 2
    r_top_v = csk_d / 2 + slope * (BOOL_EXTRA / 2)          # slightly wider above surface
    r_bot_v = max(shank_d / 2 - slope * (BOOL_EXTRA / 2), 0.01)
    csk = make_cone_cutter(
        f"{name}_csk", cx, cy, csk_cz,
        r_bot_v, r_top_v, csk_h,
    )
    bool_diff(target, csk)


def cut_csunk_up(target, name, cx, cy, bottom_z, depth,
                 shank_d, csk_d, csk_depth):
    """
    Cut a countersunk hole going UP from bottom_z through 'depth' mm of material.
    The countersink widens at the bottom face (bottom_z) — screw head recessed there.

    Two-pass approach (from generate_flat_bracket.py pattern):
      Pass 1 — straight shank cylinder through full depth.
      Pass 2 — conical frustum at the bottom face only.
    """
    slope = (csk_d / 2 - shank_d / 2) / csk_depth

    # Pass 1: shank (straight, full depth + overshoot both ends)
    shank_h  = depth + 2 * BOOL_EXTRA
    shank_cz = bottom_z + depth / 2
    shank = make_cone_cutter(
        f"{name}_shank", cx, cy, shank_cz,
        shank_d / 2, shank_d / 2, shank_h,
    )
    bool_diff(target, shank)

    # Pass 2: countersink frustum (wide at bottom, narrow at depth)
    csk_h   = csk_depth + BOOL_EXTRA
    csk_cz  = bottom_z + csk_depth / 2
    r_bot_v = csk_d / 2 + slope * (BOOL_EXTRA / 2)          # wide at bottom
    r_top_v = max(shank_d / 2 - slope * (BOOL_EXTRA / 2), 0.01)  # narrow at top
    csk = make_cone_cutter(
        f"{name}_csk", cx, cy, csk_cz,
        r_bot_v, r_top_v, csk_h,
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
    back  = [bm.verts.new((x, y1, z)) for x, z in pts]
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


# ════════════════════════════════════════════════════════════════
#  BUILD
# ════════════════════════════════════════════════════════════════

clear_scene()
col = bpy.data.collections.new("HO_Tunnel")
bpy.context.scene.collection.children.link(col)


# ── 1. FLOOR PANEL ────────────────────────────────────────────────
# Solid slab at Z = 0 → WALL_T.
# Four countersunk screw holes; heads recessed into the exterior bottom face (Z = 0).

floor = box("FloorPanel", 0, 0, WALL_T / 2, TUNNEL_W, TUNNEL_LEN, WALL_T)
link_to(col, floor)

for i, (sx, sy) in enumerate(FLOOR_SCREW_POS):
    cut_csunk_up(floor, f"FloorHole_{i}", sx, sy,
                 0, WALL_T,
                 FLOOR_SHANK_D, FLOOR_CSK_D, FLOOR_CSK_DEPTH)


# ── 2. CEILING PANEL (solid — no holes) ────────────────────────────
# Solid slab at Z = TOTAL_H - WALL_T → TOTAL_H.

ceiling = box("CeilingPanel",
              0, 0, TOTAL_H - WALL_T / 2,
              TUNNEL_W, TUNNEL_LEN, WALL_T)
link_to(col, ceiling)


# ── 3. SIDE WALLS (Left & Right) ──────────────────────────────────
# Full exterior height TOTAL_H (floor to ceiling).
# Three rectangular windows with bottoms 0.5" above the interior floor.

total_win_w = sum(SIDE_WIN_WIDTHS)
gap = (INNER_LEN - total_win_w) / 4.0   # 4 equal gaps (edges + between windows)

for side_label, wx in [("Left",  -(TUNNEL_W / 2 - WALL_T / 2)),
                        ("Right",   TUNNEL_W / 2 - WALL_T / 2)]:
    wall = box(f"SideWall_{side_label}",
               wx, 0, TOTAL_H / 2,
               WALL_T, TUNNEL_LEN, TOTAL_H)
    link_to(col, wall)

    y_cursor = -INNER_LEN / 2 + gap
    for wi, ww in enumerate(SIDE_WIN_WIDTHS):
        win_cy = y_cursor + ww / 2
        # Z measured from exterior floor; interior floor is at WALL_T
        win_cz = WALL_T + SIDE_WIN_Z_BOT + SIDE_WIN_H / 2
        cutter = box(f"Win_{side_label}_{wi}",
                     wx, win_cy, win_cz,
                     WALL_T * 3, ww, SIDE_WIN_H)
        bool_diff(wall, cutter)
        y_cursor += ww + gap


# ── 4. END PORTALS (Front & Back) ─────────────────────────────────
# 7" tall decorative facades. Train arch base at Z = 0 (exterior floor).
# Deco arch window sits above the tunnel ceiling level.

DECO_Z_BASE = TOTAL_H + 0.75 * IN   # base of deco arch; verify < PORTAL_H

for end_label, py in [("Front",  TUNNEL_LEN / 2 - WALL_T / 2),
                       ("Back",  -(TUNNEL_LEN / 2 - WALL_T / 2))]:
    portal = box(f"Portal_{end_label}",
                 0, py, PORTAL_H / 2,
                 TUNNEL_W, WALL_T, PORTAL_H)
    link_to(col, portal)

    # Train arch opening (base at Z = 0)
    train_arch = make_arch_cutter(f"TrainArch_{end_label}",
                                   ARCH_W, ARCH_SPRING_H, ARCH_R,
                                   WALL_T * 3)
    train_arch.location = (0, py, 0)
    bool_diff(portal, train_arch)

    # Decorative arch window (above tunnel ceiling)
    deco_arch = make_arch_cutter(f"DecoArch_{end_label}",
                                  DECO_W, DECO_SPRING_H, DECO_R,
                                  WALL_T * 3)
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

BRKT_TOP_Z = TOTAL_H + BRKT_HEIGHT   # Z of bracket top face

for side_label, wx in [("Left",  -(TUNNEL_W / 2 - WALL_T / 2)),
                        ("Right",   TUNNEL_W / 2 - WALL_T / 2)]:
    for end_label, by in [("Front",  TUNNEL_LEN / 2 - BRKT_LEN / 2),
                            ("Back",  -(TUNNEL_LEN / 2 - BRKT_LEN / 2))]:

        # Vertical part: flush with side wall
        brkt_vert = box(f"BracketVert_{side_label}_{end_label}",
                        wx, by,
                        TOTAL_H + BRKT_HEIGHT / 2,
                        WALL_T, BRKT_LEN, BRKT_HEIGHT)

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

        brkt_horiz = box(f"BracketHoriz_{side_label}_{end_label}",
                         horiz_cx, by,
                         TOTAL_H + BRKT_HEIGHT - WALL_T / 2,
                         BRKT_HORIZ_EXT, BRKT_LEN, WALL_T)

        # Union vertical and horizontal parts into L-shape
        bool_union(brkt_vert, brkt_horiz)
        brkt = brkt_vert
        brkt.name = f"Bracket_{side_label}_{end_label}"
        link_to(col, brkt)

        # BRKT_SCREW_N countersunk holes along Y on the bottom face of horizontal part
        horiz_bottom_z = TOTAL_H + BRKT_HEIGHT - WALL_T
        for hi in range(BRKT_SCREW_N):
            hy = by - BRKT_LEN / 2 + (hi + 1) * BRKT_LEN / (BRKT_SCREW_N + 1)
            cut_csunk_up(brkt, f"BrktHole_{side_label}_{end_label}_{hi}",
                         horiz_cx, hy, horiz_bottom_z, WALL_T,
                         BRKT_SHANK_D, BRKT_CSK_D, BRKT_CSK_DEPTH)


# ════════════════════════════════════════════════════════════════
#  EXPORT EACH PART AS STL
# ════════════════════════════════════════════════════════════════

script_dir = os.path.dirname(os.path.abspath(__file__))
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
print(f"  Tunnel length         : {TUNNEL_LEN:.1f} mm  ({TUNNEL_LEN/IN:.2f}\")")
print(f"  Tunnel width          : {TUNNEL_W:.1f} mm  ({TUNNEL_W/IN:.2f}\")")
print(f"  Interior clear height : {SIDE_H:.1f} mm  ({SIDE_H/IN:.2f}\")")
print(f"  Total exterior height : {TOTAL_H:.1f} mm  ({TOTAL_H/IN:.2f}\")")
print(f"  Portal height         : {PORTAL_H:.1f} mm  ({PORTAL_H/IN:.2f}\")")
print(f"  Train arch            : {ARCH_W:.1f} mm wide × {ARCH_SPRING_H + ARCH_R:.1f} mm tall")
print(f"  Floor screw holes     : Ø{FLOOR_SHANK_D:.2f} mm shank / "
      f"CSK Ø{FLOOR_CSK_D:.2f} mm × {len(FLOOR_SCREW_POS)}")
print(f"  L-bracket dimensions  : {BRKT_HEIGHT:.1f} mm high × {BRKT_HORIZ_EXT:.1f} mm extension  "
      f"({BRKT_HEIGHT/IN:.2f}\" × {BRKT_HORIZ_EXT/IN:.2f}\")")
print(f"  Bracket screw holes   : Ø{BRKT_SHANK_D:.2f} mm × {BRKT_SCREW_N} per bracket × 4 brackets")
print(f"  Output dir            : {output_dir}")
print("=" * 62)
