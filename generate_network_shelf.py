"""
Network Gear Two-Level Shelf
-----------------------------
Top shelf:    Asus ZenWifi router
Bottom shelf: Firewalla Gold SE firewall

All dimensions in mm internally; inch constants converted at the top.
"""

import bpy
import bmesh
import os

# ============================================================
# PARAMETERS (edit these)
# ============================================================
SHELF_WIDTH      = 6    * 25.4   # 152.4 mm — max width (hard limit)
SHELF_DEPTH      = 10   * 25.4   # 254.0 mm — front-to-back depth
TOTAL_HEIGHT_MAX = 7    * 25.4   # 177.8 mm — maximum overall height
SHELF_GAP        = 1.25 * 25.4   #  31.75 mm — clear vertical space between shelves

SHELF_THICKNESS  = 4.0           # mm — each shelf board
WALL_THICKNESS   = 4.0           # mm — side walls and back panel
FOOT_CLEARANCE   = 15.0          # mm — air gap below bottom shelf (ventilation + cable routing)

# Ventilation slots cut into side walls
VENT_SLOT_W      = 6.0           # mm — slot width
VENT_SLOT_H      = 20.0          # mm — slot height
VENT_SLOT_COUNT  = 4             # slots per side per tier

# ============================================================
# Derived dimensions
# ============================================================
BOTTOM_SHELF_BOT = FOOT_CLEARANCE                          # Z of bottom face of lower shelf
BOTTOM_SHELF_TOP = BOTTOM_SHELF_BOT + SHELF_THICKNESS
TOP_SHELF_BOT    = BOTTOM_SHELF_TOP + SHELF_GAP            # clear gap then upper shelf
TOP_SHELF_TOP    = TOP_SHELF_BOT + SHELF_THICKNESS
TOTAL_STRUCT     = TOP_SHELF_TOP                           # full structure height

assert TOTAL_STRUCT <= TOTAL_HEIGHT_MAX, (
    f"Structure {TOTAL_STRUCT:.1f} mm exceeds max {TOTAL_HEIGHT_MAX:.1f} mm"
)

print("=" * 55)
print("  Network Gear Shelf — Dimensions Summary")
print("=" * 55)
print(f"  Width:              {SHELF_WIDTH:.1f} mm  ({SHELF_WIDTH/25.4:.2f} in)")
print(f"  Depth:              {SHELF_DEPTH:.1f} mm  ({SHELF_DEPTH/25.4:.2f} in)")
print(f"  Structure height:   {TOTAL_STRUCT:.1f} mm  ({TOTAL_STRUCT/25.4:.2f} in)")
print(f"  Max allowed height: {TOTAL_HEIGHT_MAX:.1f} mm  ({TOTAL_HEIGHT_MAX/25.4:.2f} in)")
print(f"  Foot clearance:     {FOOT_CLEARANCE:.1f} mm")
print(f"  Shelf gap (clear):  {SHELF_GAP:.1f} mm  ({SHELF_GAP/25.4:.2f} in)")
# NOTE: Depth (254 mm) is very close to Bambu P2S bed limit (256 mm).
# Orient with the depth axis along X or Y but confirm slicer clearance before printing.
print("  ** Depth is 254 mm — verify printer bed clearance before slicing **")
print("=" * 55)

# ============================================================
# Scene helpers
# ============================================================
def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def add_box(name, cx, cy, cz, sx, sy, sz):
    """Create a box centred at (cx, cy, cz) with full dimensions (sx, sy, sz)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    return obj


def boolean_cut(target, cutter, op='DIFFERENCE'):
    """Apply a boolean modifier and remove the cutter object."""
    mod = target.modifiers.new(name="Bool", type='BOOLEAN')
    mod.operation = op
    mod.object = cutter
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


# ============================================================
# Build the shelf
# ============================================================
clear_scene()

# Shelf is centred on X=0, front face at Y=0, back at Y=SHELF_DEPTH.
HW  = SHELF_WIDTH / 2
MID_Y = SHELF_DEPTH / 2

# --- Solid side walls (full height of structure) ---
for label, x_centre in [("Left",  -(HW - WALL_THICKNESS / 2)),
                          ("Right",  (HW - WALL_THICKNESS / 2))]:
    wall = add_box(
        f"SideWall_{label}",
        cx=x_centre, cy=MID_Y, cz=TOTAL_STRUCT / 2,
        sx=WALL_THICKNESS, sy=SHELF_DEPTH, sz=TOTAL_STRUCT,
    )

    # Cut ventilation slots into each tier
    for tier_bot, tier_top in [
        (FOOT_CLEARANCE, BOTTOM_SHELF_BOT),          # below bottom shelf (foot zone)
        (BOTTOM_SHELF_TOP, TOP_SHELF_BOT),            # between shelves
    ]:
        tier_h = tier_top - tier_bot
        if tier_h < VENT_SLOT_H + 4:
            continue  # not enough room for slots in this tier
        slot_z_centre = tier_bot + tier_h / 2
        usable_depth  = SHELF_DEPTH - 2 * 20          # leave 20 mm margins front/back
        spacing       = usable_depth / VENT_SLOT_COUNT
        for i in range(VENT_SLOT_COUNT):
            slot_y = 20 + spacing * (i + 0.5)         # evenly spaced
            cutter = add_box(
                f"VentCut_{label}_tier{tier_bot:.0f}_{i}",
                cx=x_centre, cy=slot_y, cz=slot_z_centre,
                sx=WALL_THICKNESS + 2,                 # +2 so it punches through cleanly
                sy=VENT_SLOT_W, sz=VENT_SLOT_H,
            )
            boolean_cut(wall, cutter)

# --- Back panel (full height, full width) ---
back = add_box(
    "BackPanel",
    cx=0, cy=SHELF_DEPTH - WALL_THICKNESS / 2, cz=TOTAL_STRUCT / 2,
    sx=SHELF_WIDTH, sy=WALL_THICKNESS, sz=TOTAL_STRUCT,
)
# Large cable pass-through cutout in the back panel centre
cable_cutout = add_box(
    "CableHole",
    cx=0, cy=SHELF_DEPTH - WALL_THICKNESS / 2, cz=TOTAL_STRUCT / 2,
    sx=SHELF_WIDTH * 0.55, sy=WALL_THICKNESS + 2, sz=TOTAL_STRUCT * 0.55,
)
boolean_cut(back, cable_cutout)

# --- Bottom shelf ---
add_box(
    "BottomShelf",
    cx=0, cy=MID_Y,
    cz=BOTTOM_SHELF_BOT + SHELF_THICKNESS / 2,
    sx=SHELF_WIDTH, sy=SHELF_DEPTH, sz=SHELF_THICKNESS,
)

# --- Top shelf ---
add_box(
    "TopShelf",
    cx=0, cy=MID_Y,
    cz=TOP_SHELF_BOT + SHELF_THICKNESS / 2,
    sx=SHELF_WIDTH, sy=SHELF_DEPTH, sz=SHELF_THICKNESS,
)

# ============================================================
# Join everything, apply transforms, export
# ============================================================
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.join()
shelf = bpy.context.active_object
shelf.name = "NetworkGearShelf"
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, "output")
os.makedirs(output_dir, exist_ok=True)
out_path = os.path.join(output_dir, "network_gear_shelf.stl")
bpy.ops.wm.stl_export(filepath=out_path)
print(f"Exported STL → {out_path}")
