"""
L-Bracket Generator for Blender 5.0
=====================================
Bracket specs:
  - 4 inches (101.6 mm) on each side
  - 90-degree bend in the middle
  - Two M4 screw holes (one per arm)
  - 30 mm wide, 5 mm thick

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
  L           - arm length in mm  (default: 101.6 = 4 inches)
  W           - bracket width in mm (default: 30.0)
  T           - wall thickness in mm (default: 5.0)
  HOLE_D      - screw hole diameter in mm (default: 4.2 = M4)
  HOLE_OFFSET - distance from arm tip to hole center in mm (default: 20.0)
"""

import bpy
import bmesh
import math

# ── PARAMETERS ──────────────────────────────────────────────────────────────
L             = 101.6   # arm length  (4 inches)
W             = 30.0    # bracket width
T             = 5.0     # wall thickness
HOLE_D        = 4.2     # screw hole diameter (M4 = 4.2 mm)
HOLE_OFFSET   = 20.0    # distance from arm tip to hole center
GUSSET_REACH  = 50.0    # how far the diagonal gusset extends along each arm
                         # from the inner corner (mm); must be <= L - T
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


def build_bracket_mesh(name="LBracket") -> bpy.types.Object:
    """
    Build the L-bracket body using bmesh.

    Cross-section profile (XZ plane, viewed from +Y):

        z=T+L ┌──┐
              │  │   ← vertical arm
         z=T  │  └───────────────┐
              │                  │  ← horizontal arm
         z=0  └──────────────────┘
              x=0  x=T          x=L

    The profile is extruded W mm in the +Y direction.
    """
    mesh = bpy.data.meshes.new(name + "Mesh")
    obj  = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    bm = bmesh.new()

    # L-profile vertices (x, z) — listed counter-clockwise for correct normals
    profile = [
        (0.0, 0.0),       # bottom-left
        (L,   0.0),       # bottom-right
        (L,   T),         # top of horizontal arm, far end
        (T,   T),         # inner corner
        (T,   T + L),     # top of vertical arm, far end
        (0.0, T + L),     # top-left
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


def build_gusset_mesh(name="Gusset") -> bpy.types.Object:
    """
    Build a triangular diagonal gusset that bisects the inner corner of the L.

    The gusset profile (XZ plane) is a right triangle with:
      - Right-angle vertex at the inner corner (T, T)
      - Base vertex on the horizontal arm at (T + GUSSET_REACH, T)
      - Apex vertex on the vertical arm  at (T, T + GUSSET_REACH)

    The hypotenuse runs at 45° and bisects the 90° angle of the bracket.
    The profile is extruded W mm in +Y to match the bracket width.
    """
    mesh = bpy.data.meshes.new(name + "Mesh")
    obj  = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    bm = bmesh.new()

    profile = [
        (T,               T),                # inner corner (right angle)
        (T + GUSSET_REACH, T),               # along horizontal arm
        (T,               T + GUSSET_REACH), # along vertical arm
    ]

    front = [bm.verts.new((x, 0.0, z)) for x, z in profile]
    bm.faces.new(front)

    ret = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    new_verts = [e for e in ret['geom'] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=new_verts, vec=(0.0, W, 0.0))

    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    return obj


def union_objects(base: bpy.types.Object, addition: bpy.types.Object) -> None:
    """Boolean-union `addition` into `base`, then remove `addition`."""
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = base
    base.select_set(True)

    mod = base.modifiers.new(name="GussetUnion", type='BOOLEAN')
    mod.operation = 'UNION'
    mod.object    = addition
    mod.solver    = 'EXACT'

    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(addition, do_unlink=True)


def add_screw_hole(target: bpy.types.Object,
                   location: tuple,
                   axis: str = 'Z') -> None:
    """
    Drill a cylindrical hole in `target` at `location` along `axis`.
    Uses a Boolean DIFFERENCE modifier.
    """
    depth = max(T, W) + 4.0   # ensure cutter passes fully through

    bpy.ops.mesh.primitive_cylinder_add(
        radius=HOLE_R,
        depth=depth,
        location=location
    )
    cutter = bpy.context.active_object
    cutter.name = "HoleCutter"

    # Rotate cutter to align with the desired axis
    if axis == 'X':
        cutter.rotation_euler = (0.0, math.radians(90), 0.0)
    elif axis == 'Y':
        cutter.rotation_euler = (math.radians(90), 0.0, 0.0)
    # axis == 'Z' needs no rotation

    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

    # Apply boolean modifier to the bracket
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = target
    target.select_set(True)

    mod = target.modifiers.new(name="HoleBool", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object    = cutter
    mod.solver    = 'EXACT'

    bpy.ops.object.modifier_apply(modifier=mod.name)

    # Remove the cutter object
    bpy.data.objects.remove(cutter, do_unlink=True)


def main():
    clear_scene()
    set_units_mm()

    # ── 1. Build the L-bracket body ─────────────────────────────────────────
    bracket = build_bracket_mesh("LBracket")

    # ── 2. Diagonal gusset support ──────────────────────────────────────────
    gusset = build_gusset_mesh("Gusset")
    union_objects(bracket, gusset)

    # ── 3. Screw hole in the HORIZONTAL arm ─────────────────────────────────
    #   Near the far (right) end of the bottom arm, through the thickness (Z).
    hole1_x = L - HOLE_OFFSET
    hole1_y = W / 2
    hole1_z = T / 2   # midpoint through the T-thick floor
    add_screw_hole(bracket, (hole1_x, hole1_y, hole1_z), axis='Z')
    
    hole1a_x = L - (HOLE_OFFSET + 40)
    hole1a_y = W / 2
    hole1a_z = T / 4   # midpoint through the T-thick floor
    add_screw_hole(bracket, (hole1a_x, hole1a_y, hole1a_z), axis='Z')

    # ── 4. Screw hole in the VERTICAL arm ───────────────────────────────────
    #   Near the far (top) end of the vertical arm, through the thickness (X).
    hole2_x = T / 2   # midpoint through the T-thick wall
    hole2_y = W / 2
    hole2_z = T + L - HOLE_OFFSET
    add_screw_hole(bracket, (hole2_x, hole2_y, hole2_z), axis='X')

    hole3_x = T / 4
    hole3_y = W / 2
    hole3_z = T + L - (HOLE_OFFSET + 40)
    add_screw_hole(bracket, (hole3_x, hole3_y, hole3_z), axis='X')

    # ── 5. Clean up ─────────────────────────────────────────────────────────
    bpy.ops.object.select_all(action='DESELECT')
    bracket.select_set(True)
    bpy.context.view_layer.objects.active = bracket

    # Centre origin on geometry
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

    # Zoom viewport to fit
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            with bpy.context.temp_override(area=area):
                bpy.ops.view3d.view_all()
            break

    print("=" * 50)
    print("  L-Bracket created successfully!")
    print(f"  Arms  : {L:.1f} mm × {L:.1f} mm  ({L/25.4:.2f}\")")
    print(f"  Width : {W:.1f} mm")
    print(f"  Thick : {T:.1f} mm")
    print(f"  Holes : Ø{HOLE_D:.1f} mm (M4), {HOLE_OFFSET:.0f} mm from tips")
    print(f"  Gusset: {GUSSET_REACH:.1f} mm reach along each arm (45° bisector)")
    print("=" * 50)
    print("  Next steps:")
    print("  • Edit mesh in Edit Mode as needed")
    print("  • File > Export > STL  (or 3MF)")
    print("  • Open in Bambu Studio and slice!")
    print("=" * 50)


main()
