# Modular Picture Frame Generator

## Overview

This Blender script generates a modular, low-profile picture frame designed to fit your 22.3" x 34" poster. The frame is split into printable segments that fit on the Bambu P2S print bed (256mm x 256mm).

## Features

- **Low profile design**: 10mm depth, 12.7mm (0.5") face width
- **Rabbet joint**: Inner lip holds poster securely without glass
- **Modular segments**: Each side split into printable pieces with tongue-and-groove joints
- **Wall mounting**: Keyhole slots on top segments for easy hanging
- **45-degree mitered corners**: Professional appearance

## Frame Specifications

### Dimensions
- Poster size: 22.3" x 34" (566.42mm x 863.6mm)
- Frame face width: 0.5" (12.7mm)
- Frame depth: 10mm
- Rabbet depth: 5mm (poster retention)
- Rabbet width: 4mm

### Segmentation
- **Horizontal (top/bottom)**: 4 segments (~216mm each)
- **Vertical (left/right)**: 3 segments (~189mm each)
- **Total pieces**: 14 segments

### Interlocking Joints
- Tongue length: 15mm
- Tongue height: 3mm
- Joint tolerance: 0.2mm (clearance fit)

### Keyhole Mounting
- Large hole diameter: 8mm (screw head)
- Small slot diameter: 4mm (screw shaft)
- Slot length: 10mm
- Location: Two keyholes on top rail near ends

## Running the Script

### Prerequisites
- Blender 3.0 or later installed
- Command line access

### Generate Frame Segments

```bash
# Run the script in Blender (headless mode)
blender --background --python modular_picture_frame.py

# Or run with a .blend file
blender --background LidStorageTray.blend --python modular_picture_frame.py
```

### Output
All STL files will be exported to: `output/picture_frame/`

Files generated:
- `Frame_horizontal_top_0.stl` through `Frame_horizontal_top_3.stl` (4 pieces)
- `Frame_horizontal_bottom_0.stl` through `Frame_horizontal_bottom_3.stl` (4 pieces)
- `Frame_vertical_left_0.stl` through `Frame_vertical_left_2.stl` (3 pieces)
- `Frame_vertical_right_0.stl` through `Frame_vertical_right_2.stl` (3 pieces)

## Printing Instructions

### Print Settings (Recommended)
- **Layer height**: 0.2mm
- **Wall thickness**: 3-4 perimeters (1.2-1.6mm)
- **Infill**: 15-20%
- **Supports**: None required
- **Orientation**: Print flat (rabbet side down works best)
- **Material**: PLA, PETG, or ABS

### Print Order
1. Print all pieces with the same settings for consistency
2. Check fit of tongue-and-groove joints with a test piece first
3. If joints are too tight, adjust `TONGUE_TOLERANCE` parameter in script and regenerate

## Assembly Instructions

### Tools Needed
- Wood glue or cyanoacrylate (CA) glue
- Masking tape or rubber bands
- Sandpaper (220 grit) for cleaning up joints
- 2x wall anchors and screws (for keyhole mounting)

### Assembly Steps

1. **Prepare segments**
   - Lightly sand any rough edges
   - Test-fit tongue-and-groove joints
   - Do NOT glue yet

2. **Assemble each side**
   - For top rail: Connect horizontal_top_0 through horizontal_top_3 using tongue-and-groove
   - Apply small amount of glue to each joint
   - Let dry flat for 30 minutes
   - Repeat for bottom, left, and right rails

3. **Create corner miters**
   - Lay out all four sides to form rectangle
   - Check that miters align properly at corners
   - Adjust with sandpaper if needed

4. **Final assembly**
   - Apply glue to mitered corners
   - Use masking tape or rubber bands to hold corners together
   - Ensure frame is square (measure diagonals - should be equal)
   - Let cure for 24 hours

5. **Install poster**
   - Place poster face-down on clean surface
   - Lower frame onto poster (rabbet faces poster)
   - Poster edges should rest in the rabbet
   - Optional: Use small pieces of tape to secure poster to rabbet

6. **Wall mounting**
   - Install two screws/anchors on wall 863mm apart (horizontal spacing)
   - Screws should protrude 3-4mm from wall
   - Hang frame using keyhole slots on top rail

## Customization

### Adjustable Parameters (in script)

Edit these constants at the top of `modular_picture_frame.py`:

```python
# Poster dimensions
POSTER_WIDTH = 566.42  # Change for different poster size
POSTER_HEIGHT = 863.6

# Frame profile
FRAME_FACE_WIDTH = 12.7  # Visible frame width
FRAME_DEPTH = 10.0  # Adjust for deeper/shallower frame

# Rabbet
RABBET_DEPTH = 5.0  # How deep poster sits
RABBET_WIDTH = 4.0  # Overlap on poster edge

# Joint fit
TONGUE_TOLERANCE = 0.2  # Increase if joints too tight, decrease if too loose

# Keyhole size (adjust for your screws)
KEYHOLE_LARGE_DIA = 8.0
KEYHOLE_SMALL_DIA = 4.0
```

After changing parameters, re-run the script to regenerate STL files.

## Troubleshooting

### Joints too tight
- Increase `TONGUE_TOLERANCE` by 0.1mm increments
- Check printer calibration (especially XY dimensional accuracy)

### Joints too loose
- Decrease `TONGUE_TOLERANCE`
- Consider using thicker glue or adding small shims

### Corners don't align
- Check that all pieces are from the same generation (don't mix old/new STLs)
- Verify printer isn't warping pieces - try lowering bed temperature
- Sand miter cuts to adjust fit

### Frame warping
- Increase infill to 20-25%
- Add more perimeters (4-5)
- Print with slower cooling to reduce internal stress
- Consider printing in ABS with an enclosure

## Design Notes

### Why modular?
Your poster is 863mm (34") wide, but the Bambu P2S bed is only 256mm. By splitting into segments with interlocking joints, each piece fits comfortably on the print bed while maintaining strength when assembled.

### Profile cross-section
```
Front view:              Side view of rabbet:
┌─────────┐             ┌──────────┐
│ (face)  │             │  Poster  │
│  12.7mm │             │  sits    │
│         │  10mm       │  here    │
└─────────┘             └──┐     ┌─┘
                           │ 5mm │
                        Rabbet  └─────┘
```

### Corner joints
The 45-degree miters provide a clean, professional appearance. Apply glue carefully to avoid squeeze-out on visible surfaces.

### Wall mounting
The keyhole slots accept standard screws. For best results:
- Use #8 wood screws (4.2mm shaft)
- Wall anchors rated for 10+ lbs each
- Space screws to match keyhole positions on your specific frame segments

## License

This script is part of the 3D printing project. See main LICENSE file.
