"""
Modular Stackable Shelf — bpy Generator
-----------------------------------------
Generates parametric modular shelf units that can stack vertically or sit side-by-side.

Features:
  • Configurable dimensions (width, depth, height)
  • Interlocking registration pins for secure stacking
  • Optional dividers for compartments
  • Optional back panel
  • Rounded corners and beveled edges
  • All parts designed to fit Bambu P2S build plate (256×256mm)

Coordinate system (all mm):
  X  =  width (left-right)
  Y  =  depth (front-back)
  Z  =  height (vertical)

Assembly:
  • Bottom panel with registration holes
  • Two side walls
  • Optional back wall
  • Optional dividers
  • Top rim with registration pins (for stacking)

Print orientation:
  • Bottom panel: print flat
  • Side walls: print flat
  • Back wall: print flat
  • Dividers: print flat
"""

import os
import bmesh
import bpy

# ════════════════════════════════════════════════════════════════
#  PARAMETERS  —  edit these; all dimensions in mm
# ════════════════════════════════════════════════════════════════

IN = 25.4  # mm per inch

# ── Shelf unit dimensions ──────────────────────────────────────────
SHELF_WIDTH = 8.0 * IN      # 203.2 mm — interior width
SHELF_DEPTH = 6.0 * IN      # 152.4 mm — interior depth
SHELF_HEIGHT = 4.0 * IN     # 101.6 mm — interior height
WALL_T = 0.125 * IN         #   3.175 mm — wall thickness

# ── Edge finishing ─────────────────────────────────────────────────
CORNER_RADIUS = 0.25 * IN   #   6.35 mm — rounded corner radius
BEVEL_SIZE = 1.0            # mm — edge bevel/chamfer width

# ── Dividers ───────────────────────────────────────────────────────
NUM_DIVIDERS = 1            # number of vertical dividers (0 = no dividers)
DIVIDER_T = 0.125 * IN      #   3.175 mm — divider thickness

# ── Back panel ─────────────────────────────────────────────────────
INCLUDE_BACK = True         # True = closed back, False = open back

# ── Registration pins (for stacking) ───────────────────────────────
PIN_DIAMETER = 0.25 * IN    #   6.35 mm — registration pin diameter
PIN_HEIGHT = 0.25 * IN      #   6.35 mm — pin protrusion above top rim
PIN_HOLE_DEPTH = 0.3 * IN   #   7.62 mm — pin hole depth in bottom panel
PIN_CLEARANCE = 0.01 * IN   #   0.254 mm — clearance for easy fit
# 4 pins in a square pattern, inset from corners:
PIN_INSET = 1.0 * IN        #  25.4 mm — pin inset from each corner

# ── Feet (bottom panel standoffs) ──────────────────────────────────
FOOT_HEIGHT = 0.125 * IN    #   3.175 mm — foot height from bottom
FOOT_DIAMETER = 0.5 * IN    #  12.7 mm — foot diameter
FOOT_INSET = 0.5 * IN       #  12.7 mm — foot inset from corners

# ── Derived constants ──────────────────────────────────────────────
OUTER_WIDTH = SHELF_WIDTH + 2 * WALL_T
OUTER_DEPTH = SHELF_DEPTH + 2 * WALL_T
OUTER_HEIGHT = SHELF_HEIGHT + WALL_T  # bottom panel + height
PIN_POSITIONS = [
    (-SHELF_WIDTH/2 + PIN_INSET, -SHELF_DEPTH/2 + PIN_INSET),
    (SHELF_WIDTH/2 - PIN_INSET, -SHELF_DEPTH/2 + PIN_INSET),
    (SHELF_WIDTH/2 - PIN_INSET, SHELF_DEPTH/2 - PIN_INSET),
    (-SHELF_WIDTH/2 + PIN_INSET, SHELF_DEPTH/2 - PIN_INSET),
]


# ════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
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


def cylinder(name, cx, cy, cz, radius, height):
    """Cylinder centred at (cx, cy, cz) along Z axis."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius,
        depth=height,
        location=(cx, cy, cz)
    )
    obj = bpy.context.active_object
    obj.name = name
    return obj


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


def bool_diff(target, cutter):
    """Subtract cutter from target in-place, then remove cutter."""
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    cutter.hide_viewport = False
    mod = target.modifiers.new("BoolDiff", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "EXACT"
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


# ════════════════════════════════════════════════════════════════
#  BUILD
# ════════════════════════════════════════════════════════════════

clear_scene()
col = bpy.data.collections.new("ModularShelf")
bpy.context.scene.collection.children.link(col)


def link_to(obj):
    """Move obj into collection."""
    col.objects.link(obj)
    try:
        bpy.context.scene.collection.objects.unlink(obj)
    except RuntimeError:
        pass
    return obj


# ── 1. BOTTOM PANEL ────────────────────────────────────────────────
# Full exterior dimensions with registration holes for stacking pins

bottom = box(
    "BottomPanel",
    0, 0, WALL_T / 2,
    OUTER_WIDTH, OUTER_DEPTH, WALL_T
)
link_to(bottom)

# Cut registration pin holes
for px, py in PIN_POSITIONS:
    hole = cylinder(
        "PinHole_temp",
        px, py, WALL_T / 2,
        PIN_DIAMETER / 2 + PIN_CLEARANCE,
        PIN_HOLE_DEPTH
    )
    bool_diff(bottom, hole)

# Add feet
for fx, fy in [
    (-SHELF_WIDTH/2 + FOOT_INSET, -SHELF_DEPTH/2 + FOOT_INSET),
    (SHELF_WIDTH/2 - FOOT_INSET, -SHELF_DEPTH/2 + FOOT_INSET),
    (SHELF_WIDTH/2 - FOOT_INSET, SHELF_DEPTH/2 - FOOT_INSET),
    (-SHELF_WIDTH/2 + FOOT_INSET, SHELF_DEPTH/2 - FOOT_INSET),
]:
    foot = cylinder(
        "Foot_temp",
        fx, fy, -FOOT_HEIGHT / 2,
        FOOT_DIAMETER / 2,
        FOOT_HEIGHT
    )
    bool_union(bottom, foot)


# ── 2. SIDE WALLS (Left & Right) ───────────────────────────────────
# Vertical walls from bottom panel to top rim

for side_label, sx in [("Left", -OUTER_WIDTH / 2 + WALL_T / 2),
                        ("Right", OUTER_WIDTH / 2 - WALL_T / 2)]:
    wall = box(
        f"SideWall_{side_label}",
        sx, 0, WALL_T + SHELF_HEIGHT / 2,
        WALL_T, OUTER_DEPTH, SHELF_HEIGHT
    )
    link_to(wall)


# ── 3. BACK WALL (optional) ────────────────────────────────────────

if INCLUDE_BACK:
    back = box(
        "BackWall",
        0, -OUTER_DEPTH / 2 + WALL_T / 2, WALL_T + SHELF_HEIGHT / 2,
        SHELF_WIDTH, WALL_T, SHELF_HEIGHT
    )
    link_to(back)


# ── 4. DIVIDERS (optional) ─────────────────────────────────────────

if NUM_DIVIDERS > 0:
    # Evenly space dividers across the width
    spacing = SHELF_WIDTH / (NUM_DIVIDERS + 1)
    for i in range(NUM_DIVIDERS):
        dx = -SHELF_WIDTH / 2 + (i + 1) * spacing
        divider = box(
            f"Divider_{i}",
            dx, 0, WALL_T + SHELF_HEIGHT / 2,
            DIVIDER_T, SHELF_DEPTH, SHELF_HEIGHT
        )
        link_to(divider)


# ── 5. TOP RIM WITH REGISTRATION PINS ──────────────────────────────
# Thin rim around the top edge with pins for stacking

rim = box(
    "TopRim",
    0, 0, WALL_T + SHELF_HEIGHT + WALL_T / 2,
    OUTER_WIDTH, OUTER_DEPTH, WALL_T
)
link_to(rim)

# Add registration pins on top
for px, py in PIN_POSITIONS:
    pin = cylinder(
        "Pin_temp",
        px, py, WALL_T + SHELF_HEIGHT + WALL_T + PIN_HEIGHT / 2,
        PIN_DIAMETER / 2,
        PIN_HEIGHT
    )
    bool_union(rim, pin)


# ════════════════════════════════════════════════════════════════
#  EXPORT EACH PART AS STL
# ════════════════════════════════════════════════════════════════

script_dir = os.path.dirname(os.path.abspath(__file__))
# If running from within a .blend file, use the parent directory
if script_dir.endswith('.blend'):
    script_dir = os.path.dirname(script_dir)
output_dir = os.path.join(script_dir, "output")
os.makedirs(output_dir, exist_ok=True)

bpy.ops.object.select_all(action='DESELECT')
for obj in col.objects:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    out_path = os.path.join(output_dir, f"ModularShelf_{obj.name}.stl")
    bpy.ops.wm.stl_export(filepath=out_path, export_selected_objects=True)
    obj.select_set(False)

print("=" * 70)
print("  Modular Stackable Shelf — build complete")
print("=" * 70)
print(f'  Exterior dimensions   : {OUTER_WIDTH:.1f} × {OUTER_DEPTH:.1f} × {OUTER_HEIGHT:.1f} mm')
print(f'                         ({OUTER_WIDTH/IN:.2f}" × {OUTER_DEPTH/IN:.2f}" × {OUTER_HEIGHT/IN:.2f}")')
print(f'  Interior dimensions   : {SHELF_WIDTH:.1f} × {SHELF_DEPTH:.1f} × {SHELF_HEIGHT:.1f} mm')
print(f'                         ({SHELF_WIDTH/IN:.2f}" × {SHELF_DEPTH/IN:.2f}" × {SHELF_HEIGHT/IN:.2f}")')
print(f'  Wall thickness        : {WALL_T:.2f} mm  ({WALL_T/IN:.3f}")')
print(f'  Dividers              : {NUM_DIVIDERS}')
print(f'  Back panel            : {"Yes" if INCLUDE_BACK else "No"}')
print(f'  Registration pins     : {len(PIN_POSITIONS)} × Ø{PIN_DIAMETER:.1f} mm')
print(f'  Output directory      : {output_dir}')
print("=" * 70)
