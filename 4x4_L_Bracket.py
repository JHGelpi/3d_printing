"""
Custom Window Bracket Generator for Blender 5.0
================================================
Transom-following bracket with diagonal transition section.

Design based on sketch:
  - Vertical section: 10cm
  - Diagonal transition: 6cm horizontal gap
  - Horizontal sections: 2cm + 10cm
  - Width: 30mm, Thickness: 5mm

HOW TO USE IN BLENDER:
  1. Open Blender 5.0
  2. Switch to the "Scripting" workspace (top tab bar)
  3. Click "New" to create a new script
  4. Paste or open this file
  5. Click "Run Script" (the ▶ button)
  6. The bracket will appear in your 3D viewport
  7. Switch back to the "Layout" workspace to inspect it
  8. Export via File > Export > STL (or 3MF) for Bambu Studio

CUSTOMIZATION (edit values below before running):
  VERT_LENGTH    - vertical section length (mm)
  DIAG_H_GAP     - horizontal gap bridged by diagonal (mm)
  DIAG_V_DROP    - vertical drop of diagonal section (mm)
  HORIZ_SHORT    - short horizontal section near diagonal (mm)
  HORIZ_LONG     - long horizontal section (mm)
  W              - bracket width (mm)
  T              - wall thickness (mm)
"""

import bpy
import bmesh
import math

# ── PARAMETERS ──────────────────────────────────────────────────────────────
# Bracket path dimensions (following the transom)
VERT_LENGTH   = 100.0   # vertical section length (10cm from sketch)
DIAG_H_GAP    = 60.0    # horizontal gap bridged by diagonal (6cm from sketch)
DIAG_V_DROP   = 20.0    # vertical drop of diagonal section (adjustable)
HORIZ_SHORT   = 20.0    # short horizontal section near diagonal (2cm from sketch)
HORIZ_LONG    = 100.0   # long horizontal section (10cm from sketch)

# Cross-section dimensions
W             = 30.0    # bracket width (depth into page)
T             = 5.0     # wall thickness

# Screw holes
HOLE_D        = 4.2     # screw hole diameter (M4 = 4.2 mm)
NUM_HOLES     = 4       # total number of screw holes
# ────────────────────────────────────────────────────────────────────────────

HOLE_R = HOLE_D / 2


def clear_scene():
    """Remove all mesh objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    # Clean up orphaned data
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)


def set_units_mm():
    """Set scene units to millimetres."""
    scene = bpy.context.scene
    scene.unit_settings.system       = 'METRIC'
    scene.unit_settings.scale_length = 0.001   # 1 Blender unit = 1 mm
    scene.unit_settings.length_unit  = 'MILLIMETERS'


def build_bracket_mesh(name="CustomBracket") -> bpy.types.Object:
    """
    Build the transom-following bracket using bmesh.

    Profile follows the path (XZ plane, viewed from +Y):
    - Vertical section from bottom
    - Diagonal transition bridging the gap
    - Horizontal section at top

    The profile is T mm thick and extruded W mm in the +Y direction.
    """
    mesh = bpy.data.meshes.new(name + "Mesh")
    obj  = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    bm = bmesh.new()

    # Calculate key points along the centerline path
    # Point 1: Bottom of vertical section
    p1_x, p1_z = 0.0, 0.0

    # Point 2: Top of vertical section (start of diagonal)
    p2_x, p2_z = 0.0, VERT_LENGTH

    # Point 3: End of diagonal (start of horizontal)
    p3_x, p3_z = DIAG_H_GAP, VERT_LENGTH + DIAG_V_DROP

    # Point 4: End of short horizontal section
    p4_x, p4_z = DIAG_H_GAP + HORIZ_SHORT, VERT_LENGTH + DIAG_V_DROP

    # Point 5: End of long horizontal section
    p5_x, p5_z = DIAG_H_GAP + HORIZ_SHORT + HORIZ_LONG, VERT_LENGTH + DIAG_V_DROP

    # Create profile outline with thickness T
    # The profile is a closed shape representing the bracket's cross-section
    # We'll offset perpendicular to each segment to create thickness

    # For vertical section: thickness in +X direction
    # For horizontal section: thickness in +Z direction
    # For diagonal: thickness perpendicular to diagonal angle

    # Calculate diagonal angle
    diag_dx = p3_x - p2_x
    diag_dz = p3_z - p2_z
    diag_angle = math.atan2(diag_dz, diag_dx)

    # Perpendicular offset for diagonal (rotated 90°)
    diag_offset_x = -T * math.sin(diag_angle)
    diag_offset_z = T * math.cos(diag_angle)

    # Build the profile as a closed loop (counter-clockwise for correct normals)
    # The profile traces the outer edge, then returns along the inner edge
    profile = [
        # Outer edge (left/bottom side)
        (0.0, 0.0),                                      # 0: bottom-left corner
        (0.0, VERT_LENGTH),                              # 1: top of vertical (outer edge)
        (DIAG_H_GAP, VERT_LENGTH + DIAG_V_DROP),         # 2: end of diagonal (outer edge)
        (p5_x, VERT_LENGTH + DIAG_V_DROP),               # 3: far end of horizontal (outer edge)

        # Far end (thickness transition)
        (p5_x, VERT_LENGTH + DIAG_V_DROP + T),           # 4: far end (inner edge)

        # Inner edge (right/top side, returning)
        (DIAG_H_GAP, VERT_LENGTH + DIAG_V_DROP + T),    # 5: diagonal end (inner edge)
        (p2_x + diag_offset_x, p2_z + diag_offset_z),    # 6: top of vertical (inner edge, offset for diagonal)
        (T, VERT_LENGTH),                                # 7: top of vertical (inner edge)
        (T, 0.0),                                        # 8: bottom (inner edge)
    ]

    # Create front-face vertices at y = 0
    front = [bm.verts.new((x, 0.0, z)) for x, z in profile]
    bm.faces.new(front)

    # Extrude the face by W in +Y
    ret = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    new_geom = ret['geom']
    new_verts = [e for e in new_geom if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=new_verts, vec=(0.0, W, 0.0))

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    return obj


def add_screw_hole(target: bpy.types.Object,
                   location: tuple,
                   axis: str = 'Z',
                   hole_name: str = "Hole") -> None:
    """
    Drill a cylindrical hole in `target` at `location` along `axis`.
    Uses a Boolean DIFFERENCE modifier.
    """
    # Make depth much longer to ensure it passes fully through
    depth = 50.0  # Fixed large depth to ensure complete penetration

    # Ensure we're in object mode
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.mesh.primitive_cylinder_add(
        radius=HOLE_R,
        depth=depth,
        location=location
    )
    cutter = bpy.context.active_object
    cutter.name = f"Cutter_{hole_name}"

    # Ensure cutter is in the same collection as target
    if cutter.name not in bpy.context.collection.objects:
        bpy.context.collection.objects.link(cutter)
    cutter.hide_viewport = False
    cutter.hide_render = False

    # Rotate cutter to align with the desired axis
    if axis == 'X':
        cutter.rotation_euler = (0.0, math.radians(90), 0.0)
    elif axis == 'Y':
        cutter.rotation_euler = (math.radians(90), 0.0, 0.0)
    # axis == 'Z' needs no rotation (default orientation)

    # Apply the rotation transform to make it permanent
    bpy.ops.object.select_all(action='DESELECT')
    cutter.select_set(True)
    bpy.context.view_layer.objects.active = cutter
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

    # Apply boolean modifier to the bracket
    bpy.ops.object.select_all(action='DESELECT')
    target.select_set(True)
    bpy.context.view_layer.objects.active = target

    mod = target.modifiers.new(name=f"Bool_{hole_name}", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = cutter
    mod.solver = 'EXACT'

    # Apply the modifier
    try:
        bpy.ops.object.modifier_apply(modifier=mod.name)
        print(f"  ✓ {hole_name} cut successfully at {location}")
    except Exception as e:
        print(f"  ✗ {hole_name} FAILED: {e}")
        # Try to remove the failed modifier
        if mod.name in target.modifiers:
            target.modifiers.remove(mod)

    # Remove the cutter object - ensure it's properly unlinked first
    if cutter:
        # Unlink from all collections
        for collection in cutter.users_collection:
            collection.objects.unlink(cutter)
        # Remove the data
        bpy.data.objects.remove(cutter, do_unlink=True)


def main():
    clear_scene()
    set_units_mm()

    # ── 1. Build the transom-following bracket ──────────────────────────────
    bracket = build_bracket_mesh("CustomBracket")

    # ── 2. Add screw holes ──────────────────────────────────────────────────
    # Place holes evenly distributed across the bracket sections
    print("\n  Adding screw holes...")

    # Hole 1: Bottom of vertical section (through X axis)
    hole1_x = T / 2
    hole1_y = W / 2
    hole1_z = 20.0  # 20mm from bottom
    add_screw_hole(bracket, (hole1_x, hole1_y, hole1_z), axis='X', hole_name="Vertical_Bottom")

    # Hole 2: Top of vertical section (through X axis)
    hole2_x = T / 2
    hole2_y = W / 2
    hole2_z = VERT_LENGTH - 20.0  # 20mm from top of vertical
    add_screw_hole(bracket, (hole2_x, hole2_y, hole2_z), axis='X', hole_name="Vertical_Top")

    # Hole 3: First horizontal section (through Z axis)
    hole3_x = DIAG_H_GAP + HORIZ_SHORT / 2
    hole3_y = W / 2
    hole3_z = VERT_LENGTH + DIAG_V_DROP + T / 2
    add_screw_hole(bracket, (hole3_x, hole3_y, hole3_z), axis='Z', hole_name="Horizontal_Short")

    # Hole 4: Second horizontal section (through Z axis)
    hole4_x = DIAG_H_GAP + HORIZ_SHORT + HORIZ_LONG / 2
    hole4_y = W / 2
    hole4_z = VERT_LENGTH + DIAG_V_DROP + T / 2
    add_screw_hole(bracket, (hole4_x, hole4_y, hole4_z), axis='Z', hole_name="Horizontal_Long")

    # ── 3. Clean up ─────────────────────────────────────────────────────────
    # Remove any remaining cutter objects (safety cleanup)
    print("\n  Cleaning up...")
    cutters_removed = 0
    for obj in list(bpy.data.objects):
        if obj.name.startswith("Cutter_") or obj.name == "HoleCutter":
            bpy.data.objects.remove(obj, do_unlink=True)
            cutters_removed += 1
    if cutters_removed > 0:
        print(f"  ⚠ Removed {cutters_removed} orphaned cutter objects!")

    bpy.ops.object.select_all(action='DESELECT')
    bracket.select_set(True)
    bpy.context.view_layer.objects.active = bracket

    # Centre origin on geometry
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

    # Zoom viewport to fit
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            region = next((r for r in area.regions if r.type == 'WINDOW'), None)
            if region:
                with bpy.context.temp_override(area=area, region=region):
                    bpy.ops.view3d.view_all()
            break

    print("=" * 68)
    print("  Custom Window Bracket created successfully!")
    print("=" * 68)
    print(f"  Vertical section  : {VERT_LENGTH:.1f} mm ({VERT_LENGTH/10:.1f} cm)")
    print(f"  Diagonal gap      : {DIAG_H_GAP:.1f} mm ({DIAG_H_GAP/10:.1f} cm)")
    print(f"  Diagonal drop     : {DIAG_V_DROP:.1f} mm ({DIAG_V_DROP/10:.1f} cm)")
    print(f"  Horizontal short  : {HORIZ_SHORT:.1f} mm ({HORIZ_SHORT/10:.1f} cm)")
    print(f"  Horizontal long   : {HORIZ_LONG:.1f} mm ({HORIZ_LONG/10:.1f} cm)")
    print(f"  Width             : {W:.1f} mm")
    print(f"  Thickness         : {T:.1f} mm")
    print(f"  Screw holes       : {NUM_HOLES} × Ø{HOLE_D:.1f} mm (M4)")
    print("=" * 68)
    print("  Next steps:")
    print("  • Verify dimensions match your transom requirements")
    print("  • Edit mesh in Edit Mode as needed")
    print("  • File > Export > STL  (or 3MF)")
    print("  • Open in Bambu Studio and slice!")
    print("=" * 68)


main()
