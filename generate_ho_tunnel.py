"""
HO Scale Ceiling Tunnel — bpy Generator
----------------------------------------
Generates a decorative tunnel for an HO scale model railroad.

Assembly overview:
  • The 1×6 board (0.75" × 5.5" actual) is the tunnel floor, hung from the ceiling.
  • The tunnel body wraps around the board and track — open at the bottom and both ends.
  • Four screw holes in the top panel bolt the tunnel down onto the 1×6 board.
  • Decorative end portals are taller than the side walls (7" vs 3").
  • Each end portal has an arched train opening and a smaller decorative arch window.
  • Three rectangular windows per side wall.
  • L-shaped mounting brackets (with screw holes) clip each end to the board sides.

Coordinate system (all mm, origin at tunnel floor centre):
  Y  =  along track  (tunnel length)
  X  =  across track (tunnel width)
  Z  =  vertical     (Z = 0 at floor / top of 1×6 board)

Print notes (Bambu P2S, 256 × 256 × 256 mm):
  Top panel   : 241 × 152 mm — print flat      ✓
  Side walls  : 242 × 76 mm  — print flat      ✓
  End portals : 152 × 178 mm — print flat      ✓
  Brackets    : small, print upright            ✓
  (All components fit individually; full assembled size exceeds bed.)
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
TUNNEL_LEN     = 9.5  * IN   # 241.3 mm — outer length along Y (track axis)
TUNNEL_W       = 6.0  * IN   # 152.4 mm — outer width along X
WALL_T         = 0.5  * IN   #  12.7 mm — all wall / panel thickness
SIDE_H         = 3.0  * IN   #  76.2 mm — side wall interior height (Z)

# ── End portals ───────────────────────────────────────────────────
PORTAL_H       = 7.0  * IN   # 177.8 mm — end portal total height

# ── Train arch opening (bottom of each end portal) ───────────────
#    Must clear HO trains — typical max ~40 mm wide × 50 mm tall
ARCH_W         = 3.5  * IN   #  88.9 mm — opening width
ARCH_SPRING_H  = 2.5  * IN   #  63.5 mm — rectangular height below spring line
ARCH_R         = ARCH_W / 2  #  44.45 mm — semicircle radius

# ── Decorative arch window (upper portal section) ─────────────────
DECO_W         = 2.5  * IN   #  63.5 mm — window width
DECO_SPRING_H  = 0.5  * IN   #  12.7 mm — rect height below spring line
DECO_R         = DECO_W / 2  #  31.75 mm — semicircle radius
DECO_Z_BASE    = SIDE_H + WALL_T + 0.75 * IN  # bottom of deco window

# ── Decorative side wall windows (3 per side: 2" / 1.5" / 2") ────
SIDE_WIN_WIDTHS = [2.0 * IN, 1.5 * IN, 2.0 * IN]
SIDE_WIN_H      = 1.0 * IN   #  25.4 mm — window height
SIDE_WIN_Z_BOT  = 0.5 * IN   #  12.7 mm — window bottom above floor

# ── Top panel screw holes (bolt tunnel down onto 1×6 board) ───────
SCREW_D        = 0.75 * IN   #  19.05 mm — hole diameter
SCREW_Y_OFF    = 3.5  * IN   #  from Y = 0 (near each end)
SCREW_X_OFF    = 1.5  * IN   #  from X = 0 (near each side wall)

# ── Mounting brackets (2" wide, clip over board edge) ─────────────
BRKT_LEN       = 2.0  * IN   #  50.8 mm — bracket length (along Y)
BRKT_H         = 0.75 * IN   #  19.05 mm — wraps over 1×6 board edge
BRKT_HOLE_D    = 0.18 * IN   #   4.57 mm — pilot screw holes in bracket

# ── Mesh quality ──────────────────────────────────────────────────
ARCH_SEGS      = 32


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


def cylinder_z(name, cx, cy, cz, r, depth, segs=32):
    """Vertical cylinder centred at (cx, cy, cz)."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=r, depth=depth, vertices=segs, location=(cx, cy, cz)
    )
    obj = bpy.context.active_object
    obj.name = name
    return obj


def cylinder_x(name, cx, cy, cz, r, depth, segs=32):
    """Horizontal cylinder along X, centred at (cx, cy, cz)."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=r, depth=depth, vertices=segs, location=(cx, cy, cz)
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = (0, math.pi / 2, 0)
    bpy.ops.object.transform_apply(rotation=True)
    return obj


def bool_diff(target, cutter):
    """Subtract cutter from target in-place, then delete cutter."""
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    cutter.hide_viewport = False
    mod = target.modifiers.new("Bool", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "EXACT"
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def make_arch_cutter(name, w, spring_h, r, depth, segs=ARCH_SEGS):
    """
    Solid arch cutter: rectangle [w × spring_h] topped with a semicircle
    of radius r.  Extruded along Y by depth, base at Z = 0.
    """
    bm = bmesh.new()

    # 2D profile in XZ:  bottom-left → bottom-right → right post top →
    #                    arch segments → left post top
    pts = []
    pts.append((-w / 2, 0.0))
    pts.append(( w / 2, 0.0))
    pts.append(( w / 2, spring_h))
    for i in range(1, segs):
        a = math.pi * i / segs            # sweeps 0 → π
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


def link_to(col, obj):
    """Move obj into collection col (unlink from scene root if needed)."""
    col.objects.link(obj)
    try:
        bpy.context.scene.collection.objects.unlink(obj)
    except RuntimeError:
        pass
    return obj


# ════════════════════════════════════════════════════════════════
#  BUILD
# ════════════════════════════════════════════════════════════════

clear_scene()

col = bpy.data.collections.new("HO_Tunnel")
bpy.context.scene.collection.children.link(col)

# Convenience: inner dimensions
INNER_LEN = TUNNEL_LEN - 2 * WALL_T   # Y span between portal inner faces
INNER_W   = TUNNEL_W   - 2 * WALL_T   # X interior clear width
TOP_Z     = SIDE_H + WALL_T            # Z centre of top panel
TOP_CZ    = SIDE_H + WALL_T / 2        # Z centre of top panel slab

# ── 1. TOP PANEL ─────────────────────────────────────────────────
#    Flat slab at Z = SIDE_H → SIDE_H + WALL_T.
#    Four screw holes (0.75" dia.) to bolt onto the 1×6 board.

top = box("TopPanel", 0, 0, TOP_CZ, TUNNEL_W, TUNNEL_LEN, WALL_T)
link_to(col, top)

screw_positions = [
    (-SCREW_X_OFF, -SCREW_Y_OFF),
    ( SCREW_X_OFF, -SCREW_Y_OFF),
    (-SCREW_X_OFF,  SCREW_Y_OFF),
    ( SCREW_X_OFF,  SCREW_Y_OFF),
]
for i, (sx, sy) in enumerate(screw_positions):
    hole = cylinder_z(f"ScrewHole_Top_{i}", sx, sy, TOP_CZ, SCREW_D / 2, WALL_T * 3)
    bool_diff(top, hole)


# ── 2. SIDE WALLS (Left & Right) ─────────────────────────────────
#    Run along Y (full outer tunnel length).
#    Height: SIDE_H, sitting on Z = 0 (floor).
#    Three rectangular windows per wall.

# Evenly space three windows across the inner wall length with 4 equal gaps.
total_win_w = sum(SIDE_WIN_WIDTHS)
inner_span  = INNER_LEN           # usable Y span between portal walls
gap         = (inner_span - total_win_w) / 4.0   # equal gaps: edges & between

for label, wx in [("Left", -(TUNNEL_W / 2 - WALL_T / 2)),
                  ("Right", TUNNEL_W / 2 - WALL_T / 2)]:
    wall = box(f"SideWall_{label}", wx, 0, SIDE_H / 2, WALL_T, TUNNEL_LEN, SIDE_H)
    link_to(col, wall)

    # Cut rectangular windows
    y_cursor = -INNER_LEN / 2 + gap
    for wi, ww in enumerate(SIDE_WIN_WIDTHS):
        win_cy = y_cursor + ww / 2
        win_cz = SIDE_WIN_Z_BOT + SIDE_WIN_H / 2
        cutter = box(
            f"Win_{label}_{wi}",
            wx, win_cy, win_cz,
            WALL_T * 3, ww, SIDE_WIN_H,
        )
        bool_diff(wall, cutter)
        y_cursor += ww + gap


# ── 3. END PORTALS (Front & Back) ────────────────────────────────
#    Decorative facades at each end, 7" tall.
#    Each has:
#      a) An arched train opening centred at Z = 0 (floor level)
#      b) A smaller decorative arch window above the tunnel body

for label, py in [("Front",  TUNNEL_LEN / 2 - WALL_T / 2),
                  ("Back",  -(TUNNEL_LEN / 2 - WALL_T / 2))]:
    portal = box(
        f"Portal_{label}",
        0, py, PORTAL_H / 2,
        TUNNEL_W, WALL_T, PORTAL_H,
    )
    link_to(col, portal)

    # a) Train arch opening (base at Z = 0, centred in X)
    train_arch = make_arch_cutter(
        f"TrainArch_{label}",
        ARCH_W, ARCH_SPRING_H, ARCH_R,
        WALL_T * 3,
    )
    train_arch.location = (0, py, 0)
    bool_diff(portal, train_arch)

    # b) Decorative arch window (higher up in facade)
    deco_arch = make_arch_cutter(
        f"DecoArch_{label}",
        DECO_W, DECO_SPRING_H, DECO_R,
        WALL_T * 3,
    )
    deco_arch.location = (0, py, DECO_Z_BASE)
    bool_diff(portal, deco_arch)


# ── 4. MOUNTING BRACKETS ──────────────────────────────────────────
#    L-shaped clips at each of the 4 corners.
#    The vertical tab presses against the outer face of the 1×6 board.
#    Three pilot holes per bracket.
#
#    1×6 board: 0.75" × 5.5" actual  →  19.05 mm × 139.7 mm
BOARD_W_ACTUAL = 5.5  * IN   # 139.7 mm
BOARD_T_ACTUAL = 0.75 * IN   #  19.05 mm

# Bracket sits at the outer face of the board (X = ±BOARD_W_ACTUAL/2)
for b_label, bx_sign in [("L", -1), ("R", 1)]:
    for e_label, by_sign in [("Front", 1), ("Back", -1)]:
        # Vertical tab (presses against board edge, at X face)
        tab_cx = bx_sign * (BOARD_W_ACTUAL / 2 + WALL_T / 2)
        tab_cy = by_sign * (TUNNEL_LEN / 2 - BRKT_LEN / 2)
        tab_cz = SIDE_H - BRKT_H / 2

        tab = box(
            f"BracketTab_{b_label}_{e_label}",
            tab_cx, tab_cy, tab_cz,
            WALL_T, BRKT_LEN, BRKT_H,
        )
        link_to(col, tab)

        # Horizontal flange (sits on top of board edge)
        flange_cx = bx_sign * (BOARD_W_ACTUAL / 2 + WALL_T / 2 + WALL_T / 2)
        flange = box(
            f"BracketFlange_{b_label}_{e_label}",
            flange_cx, tab_cy, SIDE_H + WALL_T / 2,
            WALL_T * 2, BRKT_LEN, WALL_T,
        )
        link_to(col, flange)

        # 3 pilot holes through tab (horizontal, along X)
        for hi in range(3):
            hz = tab_cz - BRKT_H / 2 + (hi + 0.5) * (BRKT_H / 3)
            pilot = cylinder_x(
                f"BrktHole_{b_label}_{e_label}_{hi}",
                tab_cx, tab_cy, hz,
                BRKT_HOLE_D / 2, WALL_T * 4,
            )
            bool_diff(tab, pilot)


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

print("=" * 60)
print("  HO Tunnel — build complete")
print("=" * 60)
print(f"  Tunnel length  : {TUNNEL_LEN:.1f} mm  ({TUNNEL_LEN / IN:.2f}\")")
print(f"  Tunnel width   : {TUNNEL_W:.1f} mm  ({TUNNEL_W / IN:.2f}\")")
print(f"  Side wall height: {SIDE_H:.1f} mm  ({SIDE_H / IN:.2f}\")")
print(f"  Portal height  : {PORTAL_H:.1f} mm  ({PORTAL_H / IN:.2f}\")")
print(f"  Train arch     : {ARCH_W:.1f} mm wide  ×  {ARCH_SPRING_H + ARCH_R:.1f} mm tall")
print(f"  Screw holes    : Ø{SCREW_D:.1f} mm  ×  4")
print(f"  Output dir     : {output_dir}")
print("=" * 60)
