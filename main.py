import json
import open3d as o3d
import numpy as np


# STEP 1: LOAD ITEMS
ITEMS_FILE = "data/Item List.json"

with open(ITEMS_FILE, "r") as f:
    items = json.load(f)

print(f"Total items loaded: {len(items)}")

# Print first 5 items as sanity check
print("\nFirst 5 items (L, W, H):")
for i, item in enumerate(items[:5]):
    print(f"Item {i+1}: {item}")


# STEP 2: DEFINE CONTAINER & DATA STRUCTURES
# Master box dimensions (X, Y, Z)
CONTAINER_SIZE = (100, 100, 100)

# Convert items into a clean internal format
boxes = []
for item in items:
    l, w, h = item["dims"]
    boxes.append({
        "id": item["id"],
        "type": item["type"],
        "l": l,
        "w": w,
        "h": h,
        "volume": l * w * h
    })

print("\nContainer size:", CONTAINER_SIZE)
print("Prepared boxes (first 5):")
for b in boxes[:5]:
    print(b)

# Placement state (initially empty)
placed_boxes = []

# Valid Z-levels (gravity support)
z_levels = {0}

print("\nInitial Z-levels:", z_levels)
print("Placed boxes:", placed_boxes)



# STEP 3: SORT BOXES (LARGEST FIRST)
# Sort boxes by height + volume (descending order)
boxes.sort(
    key=lambda b: (b["h"], b["volume"]),
    reverse=True
)


print("\nBoxes sorted by volume (descending):")
for b in boxes:
    print(f"ID {b['id']} | type={b['type']} | dims=({b['l']},{b['w']},{b['h']}) | volume={b['volume']}")



# STEP 4: COLLISION CHECK (AABB OVERLAP)
def boxes_overlap(box_a, box_b):
    """
    Check if two axis-aligned boxes overlap in 3D.
    box format:
    {
        'x', 'y', 'z',
        'l', 'w', 'h'
    }
    """

    overlap_x = (
        box_a["x"] < box_b["x"] + box_b["l"] and
        box_a["x"] + box_a["l"] > box_b["x"]
    )

    overlap_y = (
        box_a["y"] < box_b["y"] + box_b["w"] and
        box_a["y"] + box_a["w"] > box_b["y"]
    )

    overlap_z = (
        box_a["z"] < box_b["z"] + box_b["h"] and
        box_a["z"] + box_a["h"] > box_b["z"]
    )

    return overlap_x and overlap_y and overlap_z


# STEP 5: SUPPORT / GRAVITY CHECK
def is_supported(candidate_box, placed_boxes):
    """
    Check if a box is supported by the floor or another box.
    candidate_box format:
    {
        'x', 'y', 'z',
        'l', 'w', 'h'
    }
    """

    # Case 1: On the floor
    if candidate_box["z"] == 0:
        return True

    # Case 2: Supported by another box
    for box in placed_boxes:
        # Check if box top is exactly at candidate bottom
        if box["z"] + box["h"] == candidate_box["z"]:

            # Check X-Y overlap (support area)
            overlap_x = (
                candidate_box["x"] < box["x"] + box["l"] and
                candidate_box["x"] + candidate_box["l"] > box["x"]
            )

            overlap_y = (
                candidate_box["y"] < box["y"] + box["w"] and
                candidate_box["y"] + candidate_box["w"] > box["y"]
            )

            if overlap_x and overlap_y:
                return True

    # No support found
    return False

# STEP 6: PLACEMENT LOOP
placements = []

for box in boxes:
    placed = False
    l, w, h = box["l"], box["w"], box["h"]

    # Try all valid Z-levels (gravity levels)
    for z in sorted(z_levels):
        if z + h > CONTAINER_SIZE[2]:
            continue

        # Scan X-Y plane
        x = 0
        while x + l <= CONTAINER_SIZE[0]:
            y = 0
            while y + w <= CONTAINER_SIZE[1]:

                candidate = {
                    "id": box["id"],
                    "type": box["type"],
                    "x": x,
                    "y": y,
                    "z": z,
                    "l": l,
                    "w": w,
                    "h": h
                }

                # 1. Collision check
                collision = False
                for placed_box in placed_boxes:
                    if boxes_overlap(candidate, placed_box):
                        collision = True
                        break

                # 2. Support check
                if not collision and is_supported(candidate, placed_boxes):
                    # Place the box
                    placed_boxes.append(candidate)
                    placements.append(candidate)
                    z_levels.add(z + h)

                    placed = True
                    break

                y += 1
            if placed:
                break
            x += 1

        if placed:
            break

    if not placed:
        print(f"❌ Could not place box ID {box['id']} ({box['type']})")
    else:
        print(f"✅ Placed box ID {box['id']} at ({candidate['x']}, {candidate['y']}, {candidate['z']})")


# STEP 7: FINAL VALIDATION & SUMMARY
print("\n========== FINAL SUMMARY ==========")

print(f"Total boxes expected : {len(boxes)}")
print(f"Total boxes placed   : {len(placed_boxes)}")

# Compute max height used
max_height = 0
for box in placed_boxes:
    top_z = box["z"] + box["h"]
    if top_z > max_height:
        max_height = top_z

print(f"Maximum height used  : {max_height} / {CONTAINER_SIZE[2]}")

# Sanity: ensure all boxes are inside container
for box in placed_boxes:
    assert box["x"] + box["l"] <= CONTAINER_SIZE[0]
    assert box["y"] + box["w"] <= CONTAINER_SIZE[1]
    assert box["z"] + box["h"] <= CONTAINER_SIZE[2]

print("✔ All boxes are inside the container")
print("✔ Packing validation successful")



# FINAL VISUALIZATION
geometries = []

# 1️⃣ BIG CONTAINER (WIRE FRAME)
container = o3d.geometry.AxisAlignedBoundingBox(
    min_bound=(0, 0, 0),
    max_bound=CONTAINER_SIZE
)
container.color = (0, 0, 0)  # black
geometries.append(container)

# SMALL BOXES INSIDE CONTAINER
np.random.seed(42)  # fixed colors (professional)

for box in placed_boxes:
    l, w, h = box["l"], box["w"], box["h"]

    cube = o3d.geometry.TriangleMesh.create_box(l, w, h)
    cube.translate((box["x"], box["y"], box["z"]))
    cube.compute_vertex_normals()

    # Random but soft color
    color = np.random.rand(3) * 0.8 + 0.2
    cube.paint_uniform_color(color)

    geometries.append(cube)

# SHOW 3D SCENE
o3d.visualization.draw_geometries(
    geometries,
    window_name="3D Bin Packing – Small Boxes inside Big Box",
    width=1200,
    height=800
)
