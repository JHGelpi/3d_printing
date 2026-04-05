"""
Modular Picture Frame Generator for Blender
Generates a low-profile picture frame with interlocking segments
Designed for: 22.3" x 34" poster, Bambu P2S printer (256mm bed)
"""

import bpy
import bmesh
from mathutils import Vector, Matrix
import math
import os

# ========== DESIGN PARAMETERS ==========

# Poster dimensions (in mm)
POSTER_WIDTH = 566.42  # 22.3 inches
POSTER_HEIGHT = 863.6  # 34 inches

# Frame profile dimensions
FRAME_FACE_WIDTH = 12.7  # 0.5 inches - visible frame width
FRAME_DEPTH = 10.0  # front-to-back depth
FRAME_THICKNESS = 3.0  # minimum wall thickness

# Rabbet (inner lip) for poster retention
RABBET_DEPTH = 5.0  # how deep the poster sits
RABBET_WIDTH = 4.0  # overlap on poster edge

# Interlocking joint parameters
TONGUE_LENGTH = 15.0  # length of tongue/groove joint
TONGUE_HEIGHT = 3.0  # height of tongue
TONGUE_TOLERANCE = 0.2  # clearance for fit

# Keyhole mounting
KEYHOLE_LARGE_DIA = 8.0  # large hole for screw head
KEYHOLE_SMALL_DIA = 4.0  # small slot for screw shaft
KEYHOLE_SLOT_LENGTH = 10.0  # length of keyhole slot

# Segmentation (to fit print bed)
MAX_SEGMENT_LENGTH = 215.0  # slightly under 256mm bed size

# Corner miter angle
MITER_ANGLE = 45.0  # degrees

# Export settings
OUTPUT_DIR = "output/picture_frame"
EXPORT_FORMAT = "STL"

# ========== HELPER FUNCTIONS ==========

def clear_scene():
    """Remove all objects from the scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def create_frame_profile():
    """
    Create the cross-section profile for the frame
    Returns a bmesh with the 2D profile
    """
    bm = bmesh.new()

    # Define profile vertices (starting from front-top-outer corner, going clockwise)
    # Front face is at z=0, back is at z=FRAME_DEPTH

    # Outer edge
    v1 = bm.verts.new((0, 0, 0))  # front-top-outer
    v2 = bm.verts.new((0, -FRAME_FACE_WIDTH, 0))  # front-bottom-outer
    v3 = bm.verts.new((0, -FRAME_FACE_WIDTH, FRAME_DEPTH))  # back-bottom-outer

    # Rabbet cut (creates the inner lip)
    v4 = bm.verts.new((0, -FRAME_FACE_WIDTH, FRAME_DEPTH - RABBET_DEPTH))  # rabbet corner outer
    v5 = bm.verts.new((0, -FRAME_FACE_WIDTH + RABBET_WIDTH, FRAME_DEPTH - RABBET_DEPTH))  # rabbet corner inner
    v6 = bm.verts.new((0, -FRAME_FACE_WIDTH + RABBET_WIDTH, FRAME_DEPTH))  # back-bottom-inner

    # Inner edge
    v7 = bm.verts.new((0, -FRAME_THICKNESS, FRAME_DEPTH))  # back-top-inner
    v8 = bm.verts.new((0, -FRAME_THICKNESS, 0))  # front-top-inner

    bm.verts.ensure_lookup_table()

    # Create face from vertices
    face = bm.faces.new([v1, v2, v3, v4, v5, v6, v7, v8])

    return bm

def extrude_profile(bm, length):
    """
    Extrude a 2D profile along the X axis
    """
    # Select all faces
    for face in bm.faces:
        face.select = True

    # Extrude along X axis
    result = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    verts_extruded = [v for v in result['geom'] if isinstance(v, bmesh.types.BMVert)]

    # Move extruded vertices
    for v in verts_extruded:
        v.co.x += length

    return bm

def add_tongue_end(obj):
    """
    Add a tongue to the end of a frame segment (male connector)
    """
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Get the max X position (end of segment)
    bbox = obj.bound_box
    max_x = max([v[0] for v in bbox])

    # Create tongue protrusion
    tongue_width = FRAME_FACE_WIDTH - 2 * TONGUE_TOLERANCE
    tongue_depth = FRAME_DEPTH - TONGUE_TOLERANCE

    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=(max_x + TONGUE_LENGTH / 2, -tongue_width / 2 - FRAME_THICKNESS / 2, tongue_depth / 2)
    )
    tongue = bpy.context.active_object
    tongue.scale = (TONGUE_LENGTH / 2, tongue_width / 2, TONGUE_HEIGHT / 2)
    bpy.ops.object.transform_apply(scale=True)

    # Join tongue to segment
    obj.select_set(True)
    tongue.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()

def add_groove_end(obj):
    """
    Add a groove to the end of a frame segment (female connector)
    """
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Get the min X position (start of segment)
    bbox = obj.bound_box
    min_x = min([v[0] for v in bbox])

    # Create groove cutout
    groove_width = FRAME_FACE_WIDTH
    groove_depth = FRAME_DEPTH

    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=(min_x - TONGUE_LENGTH / 2, -groove_width / 2 - FRAME_THICKNESS / 2, groove_depth / 2)
    )
    groove = bpy.context.active_object
    groove.scale = (TONGUE_LENGTH / 2, groove_width / 2, TONGUE_HEIGHT / 2)
    bpy.ops.object.transform_apply(scale=True)

    # Boolean subtract groove from segment
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    mod = obj.modifiers.new(name="Groove", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = groove

    bpy.ops.object.modifier_apply(modifier="Groove")

    # Delete groove cutter
    bpy.data.objects.remove(groove, do_unlink=True)

def create_segment(length, segment_type, segment_index):
    """
    Create a single frame segment
    segment_type: 'horizontal' or 'vertical'
    segment_index: which segment in the sequence (0, 1, 2...)
    """
    # Create profile
    bm = create_frame_profile()

    # Extrude to create the segment
    bm = extrude_profile(bm, length)

    # Create mesh and object
    mesh = bpy.data.meshes.new(f"Frame_{segment_type}_{segment_index}")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(f"Frame_{segment_type}_{segment_index}", mesh)
    bpy.context.collection.objects.link(obj)

    return obj

def add_miter_cut(obj, angle, cut_position, is_start=True):
    """
    Add a 45-degree miter cut to the end of a frame piece
    """
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Add a plane as a cutting object
    if is_start:
        loc_x = 0
        rot_z = math.radians(angle)
    else:
        # Get object length
        bbox = obj.bound_box
        max_x = max([v[0] for v in bbox])
        loc_x = max_x
        rot_z = math.radians(-angle)

    # Use boolean modifier for the cut
    bpy.ops.mesh.primitive_cube_add(
        size=100,
        location=(loc_x, 0, 0),
        rotation=(0, 0, rot_z)
    )
    cutter = bpy.context.active_object

    # Apply boolean difference
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    mod = obj.modifiers.new(name="Miter", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = cutter

    bpy.ops.object.modifier_apply(modifier="Miter")

    # Delete cutter
    bpy.data.objects.remove(cutter, do_unlink=True)

def add_keyhole_slot(obj, position):
    """
    Add a keyhole mounting slot to the back of a frame piece
    position: (x, y, z) location for the keyhole
    """
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Create keyhole geometry (cylinder for large hole + slot for shaft)
    # Large hole
    bpy.ops.mesh.primitive_cylinder_add(
        radius=KEYHOLE_LARGE_DIA / 2,
        depth=5.0,
        location=position,
        rotation=(math.radians(90), 0, 0)
    )
    large_hole = bpy.context.active_object

    # Small slot
    bpy.ops.mesh.primitive_cylinder_add(
        radius=KEYHOLE_SMALL_DIA / 2,
        depth=5.0,
        location=(position[0], position[1], position[2] - KEYHOLE_SLOT_LENGTH),
        rotation=(math.radians(90), 0, 0)
    )
    small_slot = bpy.context.active_object

    # Join them
    large_hole.select_set(True)
    small_slot.select_set(True)
    bpy.context.view_layer.objects.active = large_hole
    bpy.ops.object.join()
    keyhole = bpy.context.active_object

    # Boolean subtract from frame
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    mod = obj.modifiers.new(name="Keyhole", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = keyhole

    bpy.ops.object.modifier_apply(modifier="Keyhole")

    # Delete keyhole
    bpy.data.objects.remove(keyhole, do_unlink=True)

def calculate_segments(total_length, max_length):
    """
    Calculate how many segments needed and their lengths
    Returns: [(length1, has_start_joint, has_end_joint), ...]
    """
    num_segments = math.ceil(total_length / max_length)
    segment_length = total_length / num_segments

    segments = []
    for i in range(num_segments):
        has_start_joint = (i > 0)  # All but first have start joint
        has_end_joint = (i < num_segments - 1)  # All but last have end joint
        segments.append((segment_length, has_start_joint, has_end_joint))

    return segments

def generate_frame():
    """
    Main function to generate the complete modular frame
    """
    clear_scene()

    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Calculate segment requirements
    horizontal_segments = calculate_segments(POSTER_WIDTH + 2 * FRAME_FACE_WIDTH, MAX_SEGMENT_LENGTH)
    vertical_segments = calculate_segments(POSTER_HEIGHT + 2 * FRAME_FACE_WIDTH, MAX_SEGMENT_LENGTH)

    print(f"Generating frame with:")
    print(f"  Horizontal segments: {len(horizontal_segments)}")
    print(f"  Vertical segments: {len(vertical_segments)}")

    all_objects = []

    # Generate horizontal segments (top and bottom)
    for i, (length, has_start, has_end) in enumerate(horizontal_segments):
        # Top segment
        obj_top = create_segment(length, "horizontal_top", i)

        # Add tongue/groove joints for multi-segment sides
        if has_start:
            add_groove_end(obj_top)  # Groove at start (female)
        if has_end:
            add_tongue_end(obj_top)  # Tongue at end (male)

        # Add miter cuts at ends if it's first or last segment
        if i == 0:
            add_miter_cut(obj_top, MITER_ANGLE, 0, is_start=True)
        if i == len(horizontal_segments) - 1:
            add_miter_cut(obj_top, MITER_ANGLE, length, is_start=False)

        # Add keyholes to top segments (for wall mounting)
        # Place them near the ends for better support
        if i == 0:
            keyhole_pos = (length * 0.75, -FRAME_FACE_WIDTH / 2, FRAME_DEPTH - 2)
            add_keyhole_slot(obj_top, keyhole_pos)
        if i == len(horizontal_segments) - 1:
            keyhole_pos = (length * 0.25, -FRAME_FACE_WIDTH / 2, FRAME_DEPTH - 2)
            add_keyhole_slot(obj_top, keyhole_pos)

        all_objects.append(obj_top)

        # Bottom segment (mirror of top)
        obj_bottom = create_segment(length, "horizontal_bottom", i)

        # Add tongue/groove joints
        if has_start:
            add_groove_end(obj_bottom)
        if has_end:
            add_tongue_end(obj_bottom)

        # Add miter cuts
        if i == 0:
            add_miter_cut(obj_bottom, MITER_ANGLE, 0, is_start=True)
        if i == len(horizontal_segments) - 1:
            add_miter_cut(obj_bottom, MITER_ANGLE, length, is_start=False)

        all_objects.append(obj_bottom)

    # Generate vertical segments (left and right)
    for i, (length, has_start, has_end) in enumerate(vertical_segments):
        # Left segment
        obj_left = create_segment(length, "vertical_left", i)

        # Add tongue/groove joints
        if has_start:
            add_groove_end(obj_left)
        if has_end:
            add_tongue_end(obj_left)

        # Add miter cuts at corners
        if i == 0:
            add_miter_cut(obj_left, MITER_ANGLE, 0, is_start=True)
        if i == len(vertical_segments) - 1:
            add_miter_cut(obj_left, MITER_ANGLE, length, is_start=False)

        all_objects.append(obj_left)

        # Right segment (mirror of left)
        obj_right = create_segment(length, "vertical_right", i)

        # Add tongue/groove joints
        if has_start:
            add_groove_end(obj_right)
        if has_end:
            add_tongue_end(obj_right)

        # Add miter cuts at corners
        if i == 0:
            add_miter_cut(obj_right, MITER_ANGLE, 0, is_start=True)
        if i == len(vertical_segments) - 1:
            add_miter_cut(obj_right, MITER_ANGLE, length, is_start=False)

        all_objects.append(obj_right)

    # Export each object
    for obj in all_objects:
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        # Apply all transforms
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        # Export
        filepath = os.path.join(OUTPUT_DIR, f"{obj.name}.stl")
        bpy.ops.wm.stl_export(
            filepath=filepath,
            check_existing=False,
            export_selected_objects=True
        )

        obj.select_set(False)
        print(f"Exported: {filepath}")

    print(f"\nFrame generation complete!")
    print(f"Total pieces: {len(all_objects)}")
    print(f"Output directory: {OUTPUT_DIR}")

# ========== MAIN EXECUTION ==========

if __name__ == "__main__":
    generate_frame()
