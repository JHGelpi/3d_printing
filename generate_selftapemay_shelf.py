"""
Self Tape May Custom Desk Shelf — bpy Generator
------------------------------------------------
A custom branded desk organizer/shelf for Self Tape May with theatrical theme.

Design inspired by www.selftapemay.com branding:
  • Theater/Broadway marquee aesthetic
  • Orange banner with brand name
  • Yellow and purple marquee arrows with light bulbs
  • Microphone and spotlight imagery
  • Deep blue theatrical background

Features:
  • Main shelf compartment for storage
  • Decorative front panel with embossed "Self Tape May" text
  • Marquee-style side panels with light bulb details
  • Optional pen/microphone holder
  • Spotlight-inspired design elements

All parts designed to fit Bambu P2S build plate (256×256mm)

Coordinate system (all mm):
  X  =  width (left-right)
  Y  =  depth (front-back)
  Z  =  height (vertical)
"""

import os
import math
import bmesh
import bpy

# ════════════════════════════════════════════════════════════════
#  PARAMETERS  —  edit these; all dimensions in mm
# ════════════════════════════════════════════════════════════════

IN = 25.4  # mm per inch

# ── Main shelf dimensions ──────────────────────────────────────────
SHELF_WIDTH = 8.0 * IN      # 203.2 mm — interior width
SHELF_DEPTH = 4.0 * IN      # 101.6 mm — interior depth
SHELF_HEIGHT = 3.0 * IN     # 76.2 mm — interior height
WALL_T = 0.125 * IN         # 3.175 mm — wall thickness

# ── Branding front panel ───────────────────────────────────────────
FRONT_PANEL_HEIGHT = 1.5 * IN  # 38.1 mm — decorative panel above shelf
TEXT_DEPTH = 1.5               # mm — embossed text depth
BANNER_STYLE = True            # True = orange banner ribbon shape

# ── Marquee elements ───────────────────────────────────────────────
MARQUEE_BULBS = True           # Add decorative light bulb pattern
BULB_DIAMETER = 0.15 * IN      # 3.81 mm — marquee bulb size
BULB_SPACING = 0.4 * IN        # 10.16 mm — spacing between bulbs

# ── Arrow side panels ──────────────────────────────────────────────
SIDE_ARROWS = True             # Add marquee arrow design to sides
ARROW_DEPTH = 2.0              # mm — arrow relief depth

# ── Pen/Microphone holder ──────────────────────────────────────────
PEN_HOLDER = True              # Add pen holder compartment
PEN_DIAMETER = 0.5 * IN        # 12.7 mm — pen hole diameter
PEN_COUNT = 3                  # Number of pen holes

# ── Base and feet ──────────────────────────────────────────────────
FOOT_HEIGHT = 0.125 * IN       # 3.175 mm — foot height
FOOT_DIAMETER = 0.4 * IN       # 10.16 mm — foot diameter

# ── Derived constants ──────────────────────────────────────────────
OUTER_WIDTH = SHELF_WIDTH + 2 * WALL_T
OUTER_DEPTH = SHELF_DEPTH + 2 * WALL_T
TOTAL_HEIGHT = WALL_T + SHELF_HEIGHT + FRONT_PANEL_HEIGHT


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


def sphere(name, cx, cy, cz, radius):
    """Sphere at (cx, cy, cz)."""
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius,
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


def add_text_emboss(target, text, location, size, depth, rotation=(0, 0, 0)):
    """Add embossed text to target object."""
    # Create text curve
    bpy.ops.object.text_add(location=location, rotation=rotation)
    text_obj = bpy.context.active_object
    text_obj.data.body = text
    text_obj.data.size = size
    text_obj.data.align_x = 'CENTER'
    text_obj.data.align_y = 'CENTER'
    text_obj.data.extrude = depth

    # Convert to mesh
    bpy.context.view_layer.objects.active = text_obj
    bpy.ops.object.convert(target='MESH')

    # Union with target
    bool_union(target, text_obj)


# ════════════════════════════════════════════════════════════════
#  BUILD
# ════════════════════════════════════════════════════════════════

clear_scene()
col = bpy.data.collections.new("SelfTapeMayShelf")
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
# Base with feet

bottom = box(
    "BottomPanel",
    0, 0, WALL_T / 2,
    OUTER_WIDTH, OUTER_DEPTH, WALL_T
)
link_to(bottom)

# Add 4 corner feet
foot_inset = 0.5 * IN
for fx, fy in [
    (-SHELF_WIDTH/2 + foot_inset, -SHELF_DEPTH/2 + foot_inset),
    (SHELF_WIDTH/2 - foot_inset, -SHELF_DEPTH/2 + foot_inset),
    (SHELF_WIDTH/2 - foot_inset, SHELF_DEPTH/2 - foot_inset),
    (-SHELF_WIDTH/2 + foot_inset, SHELF_DEPTH/2 - foot_inset),
]:
    foot = cylinder(
        "Foot_temp",
        fx, fy, -FOOT_HEIGHT / 2,
        FOOT_DIAMETER / 2,
        FOOT_HEIGHT
    )
    bool_union(bottom, foot)


# ── 2. SIDE WALLS ──────────────────────────────────────────────────
# Left and right walls - can add arrow designs

for side_label, sx in [("Left", -OUTER_WIDTH / 2 + WALL_T / 2),
                        ("Right", OUTER_WIDTH / 2 - WALL_T / 2)]:
    wall = box(
        f"SideWall_{side_label}",
        sx, 0, WALL_T + SHELF_HEIGHT / 2,
        WALL_T, OUTER_DEPTH, SHELF_HEIGHT
    )
    link_to(wall)

    # Add marquee bulbs along the edge if enabled
    if MARQUEE_BULBS:
        bulb_count = int(SHELF_HEIGHT / BULB_SPACING)
        for i in range(bulb_count):
            bz = WALL_T + BULB_SPACING * (i + 0.5)
            bulb = sphere(
                "Bulb_temp",
                sx, SHELF_DEPTH / 2 + WALL_T / 2, bz,
                BULB_DIAMETER / 2
            )
            bool_union(wall, bulb)


# ── 3. BACK WALL ───────────────────────────────────────────────────

back = box(
    "BackWall",
    0, -OUTER_DEPTH / 2 + WALL_T / 2, WALL_T + SHELF_HEIGHT / 2,
    SHELF_WIDTH, WALL_T, SHELF_HEIGHT
)
link_to(back)


# ── 4. FRONT DECORATIVE PANEL ──────────────────────────────────────
# Tall panel with "Self Tape May" branding

front_panel_z = WALL_T + SHELF_HEIGHT + FRONT_PANEL_HEIGHT / 2

if BANNER_STYLE:
    # Create banner ribbon shape (wider in middle)
    panel = box(
        "FrontPanel",
        0, OUTER_DEPTH / 2 - WALL_T / 2, front_panel_z,
        OUTER_WIDTH * 0.9, WALL_T, FRONT_PANEL_HEIGHT
    )
else:
    # Simple rectangular panel
    panel = box(
        "FrontPanel",
        0, OUTER_DEPTH / 2 - WALL_T / 2, front_panel_z,
        OUTER_WIDTH, WALL_T, FRONT_PANEL_HEIGHT
    )

link_to(panel)

# Add embossed "Self Tape May" text
# Note: Text will be added as raised relief
text_z = front_panel_z
text_y = OUTER_DEPTH / 2
add_text_emboss(
    panel,
    "Self Tape May",
    (0, text_y, text_z),
    size=8.0,  # mm
    depth=TEXT_DEPTH,
    rotation=(math.pi/2, 0, 0)  # Rotate to face forward
)

# Add marquee bulbs along top and bottom edges
if MARQUEE_BULBS:
    bulb_count = int(OUTER_WIDTH / BULB_SPACING)
    for i in range(bulb_count):
        bx = -OUTER_WIDTH / 2 + BULB_SPACING * (i + 0.5)
        # Top bulbs
        bulb_top = sphere(
            "BulbTop_temp",
            bx, text_y, front_panel_z + FRONT_PANEL_HEIGHT / 2,
            BULB_DIAMETER / 2
        )
        bool_union(panel, bulb_top)
        # Bottom bulbs
        bulb_bot = sphere(
            "BulbBot_temp",
            bx, text_y, front_panel_z - FRONT_PANEL_HEIGHT / 2,
            BULB_DIAMETER / 2
        )
        bool_union(panel, bulb_bot)


# ── 5. PEN/MICROPHONE HOLDER (optional) ────────────────────────────

if PEN_HOLDER and PEN_COUNT > 0:
    # Create a raised section at the back for pen holders
    pen_block = box(
        "PenBlock",
        0, -SHELF_DEPTH / 2 + WALL_T, WALL_T + PEN_DIAMETER,
        SHELF_WIDTH * 0.8, WALL_T * 3, PEN_DIAMETER * 2
    )
    link_to(pen_block)

    # Drill pen holes
    spacing = (SHELF_WIDTH * 0.8) / (PEN_COUNT + 1)
    for i in range(PEN_COUNT):
        px = -SHELF_WIDTH * 0.4 + (i + 1) * spacing
        pen_hole = cylinder(
            "PenHole_temp",
            px, -SHELF_DEPTH / 2 + WALL_T, WALL_T + PEN_DIAMETER,
            PEN_DIAMETER / 2,
            PEN_DIAMETER * 3
        )
        bool_diff(pen_block, pen_hole)


# ════════════════════════════════════════════════════════════════
#  EXPORT EACH PART AS STL
# ════════════════════════════════════════════════════════════════

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir.endswith('.blend'):
    script_dir = os.path.dirname(script_dir)
output_dir = os.path.join(script_dir, "output")
os.makedirs(output_dir, exist_ok=True)

bpy.ops.object.select_all(action='DESELECT')
for obj in col.objects:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    out_path = os.path.join(output_dir, f"SelfTapeMay_{obj.name}.stl")
    bpy.ops.wm.stl_export(filepath=out_path, export_selected_objects=True)
    obj.select_set(False)

print("=" * 70)
print("  Self Tape May Custom Desk Shelf — build complete")
print("=" * 70)
print(f'  Shelf dimensions      : {SHELF_WIDTH:.1f} × {SHELF_DEPTH:.1f} × {SHELF_HEIGHT:.1f} mm')
print(f'                         ({SHELF_WIDTH/IN:.2f}" × {SHELF_DEPTH/IN:.2f}" × {SHELF_HEIGHT/IN:.2f}")')
print(f'  Total height          : {TOTAL_HEIGHT:.1f} mm  ({TOTAL_HEIGHT/IN:.2f}")')
print(f'  Front panel           : {"Orange banner style" if BANNER_STYLE else "Standard"}')
print(f'  Marquee bulbs         : {"Yes" if MARQUEE_BULBS else "No"}')
print(f'  Pen holders           : {PEN_COUNT if PEN_HOLDER else 0}')
print(f'  Output directory      : {output_dir}')
print("=" * 70)
print("\nPrinting tips:")
print("  • Print in orange/red filament for theater theme")
print("  • Paint marquee bulbs in yellow/white for contrast")
print("  • Consider multi-color print for brand accuracy")
print("=" * 70)
