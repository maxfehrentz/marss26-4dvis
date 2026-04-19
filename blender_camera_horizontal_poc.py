"""
Proof-of-concept for marss26.blend: logic-driven camera + mirror during the same
time range as the existing camera animation.

Usage (recommended — loads your scene file, runs, saves a NEW .blend):
  blender --background /path/to/marss26.blend --python blender_camera_horizontal_poc.py

Or open marss26.blend in Blender, then Run Script (uses the open file; still
saves to OUTPUT_BLEND only).

The original marss26.blend on disk is never overwritten; output is written to
marss26_mirror_logic.blend next to this script.
"""

from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Euler, Vector

# Same directory as this script (place marss26.blend here, or pass it on CLI).
_BLEND_DIR = Path(__file__).resolve().parent
INPUT_BLEND = _BLEND_DIR / "marss26.blend"
OUTPUT_BLEND = _BLEND_DIR / "marss26_mirror_logic.blend"

# --- tweak ---
CAMERA_NAME: str | None = None  # None = scene camera
MIRROR_OBJECT_NAME: str | None = None  # Optional: use as mirror group root (includes children)
MIRROR_NAME_TOKEN = "mirror"  # Used when MIRROR_OBJECT_NAME is None
CAMERA_AMPLITUDE = 20  # meters, world +X wiggle on camera position
MIRROR_ROT_DEG = 45  # peak extra tilt on mirror (degrees), added to evaluated rotation
USE_SINE = True
# -------------


def _ensure_marss_scene_loaded() -> None:
    """Load marss26.blend if the script was run without a file (empty startup)."""
    current = bpy.data.filepath
    if current and Path(current).resolve() == INPUT_BLEND.resolve():
        return
    if current:
        # User opened a different blend; respect it.
        print(f"Using already open file: {current}")
        return
    if not INPUT_BLEND.is_file():
        raise FileNotFoundError(
            f"Expected {INPUT_BLEND} — put marss26.blend next to this script, "
            "or open it in Blender before running."
        )
    bpy.ops.wm.open_mainfile(filepath=str(INPUT_BLEND))
    print(f"Loaded {INPUT_BLEND}")


def _resolve_camera() -> bpy.types.Object:
    if CAMERA_NAME:
        obj = bpy.data.objects.get(CAMERA_NAME)
        if obj and obj.type == "CAMERA":
            return obj
        raise RuntimeError(f"No camera object named {CAMERA_NAME!r}")
    cam = bpy.context.scene.camera
    if cam:
        return cam
    for obj in bpy.data.objects:
        if obj.type == "CAMERA":
            return obj
    raise RuntimeError("No camera found (set scene camera or CAMERA_NAME).")


def _collect_children_recursive(root: bpy.types.Object) -> list[bpy.types.Object]:
    out: list[bpy.types.Object] = []
    stack = [root]
    seen = set()
    while stack:
        obj = stack.pop()
        if obj.name in seen:
            continue
        seen.add(obj.name)
        out.append(obj)
        for child in obj.children:
            stack.append(child)
    out.sort(key=lambda o: o.name)
    return out


def _resolve_mirror_group() -> list[bpy.types.Object]:
    """
    Resolve all mirror objects that should move together as one block.
    - If MIRROR_OBJECT_NAME is set: use it as group root and include children.
    - Otherwise: include all objects whose name contains MIRROR_NAME_TOKEN.
    """
    if MIRROR_OBJECT_NAME:
        root = bpy.data.objects.get(MIRROR_OBJECT_NAME)
        if not root:
            raise RuntimeError(f"No object named {MIRROR_OBJECT_NAME!r}")
        group = _collect_children_recursive(root)
        print(f"Mirror group from root {root.name!r}: {[o.name for o in group]}")
        return group

    token = MIRROR_NAME_TOKEN.lower()
    matches = [o for o in bpy.data.objects if token in o.name.lower()]
    if not matches:
        raise RuntimeError(
            f'No objects with "{MIRROR_NAME_TOKEN}" in their name — set MIRROR_OBJECT_NAME.'
        )
    matches.sort(key=lambda o: o.name)
    print(f"Mirror group by token {MIRROR_NAME_TOKEN!r}: {[o.name for o in matches]}")
    return matches


def _keyframes_frame_span(obj: bpy.types.Object) -> tuple[float, float] | None:
    ad = obj.animation_data
    if not ad or not ad.action:
        return None
    frames: list[float] = []
    for fc in ad.action.fcurves:
        for kp in fc.keyframe_points:
            frames.append(kp.co.x)
    if not frames:
        return None
    return min(frames), max(frames)


def _phase_offset(
    frame: float, frame_start: float, frame_end: float, amplitude: float
) -> float:
    span = max(frame_end - frame_start, 1e-6)
    t = (frame - frame_start) / span
    if USE_SINE:
        return amplitude * math.sin(t * math.pi)
    return amplitude * (t * 2.0 - 1.0)


def _sample_camera_translations(
    cam: bpy.types.Object,
    scene: bpy.types.Scene,
    depsgraph: bpy.types.Depsgraph,
    start_i: int,
    end_i: int,
) -> dict[int, Vector]:
    out: dict[int, Vector] = {}
    for f in range(start_i, end_i + 1):
        scene.frame_set(f)
        depsgraph.update()
        ev = cam.evaluated_get(depsgraph)
        out[f] = ev.matrix_world.translation.copy()
    return out


def _sample_mirror_rotation_eulers(
    mirrors: list[bpy.types.Object],
    scene: bpy.types.Scene,
    depsgraph: bpy.types.Depsgraph,
    start_i: int,
    end_i: int,
) -> dict[str, dict[int, Euler]]:
    """Local rotation_euler after animation (matches keyframe_insert rotation_euler)."""
    out: dict[str, dict[int, Euler]] = {m.name: {} for m in mirrors}
    for f in range(start_i, end_i + 1):
        scene.frame_set(f)
        depsgraph.update()
        for mirror in mirrors:
            ev = mirror.evaluated_get(depsgraph)
            out[mirror.name][f] = ev.rotation_euler.copy()
    return out


def _apply_camera_offset(
    cam: bpy.types.Object,
    scene: bpy.types.Scene,
    samples_t: dict[int, Vector],
    frame_start: float,
    frame_end: float,
    start_i: int,
    end_i: int,
) -> None:
    for f in range(start_i, end_i + 1):
        scene.frame_set(f)
        base = samples_t[f]
        dx = _phase_offset(float(f), frame_start, frame_end, CAMERA_AMPLITUDE)
        new_world = base + Vector((dx, 0.0, 0.0))
        mat = cam.matrix_world.copy()
        mat.translation = new_world
        cam.matrix_world = mat
        cam.keyframe_insert(data_path="location", frame=f)


def _apply_mirror_rotation_delta(
    mirrors: list[bpy.types.Object],
    scene: bpy.types.Scene,
    samples_r: dict[str, dict[int, Euler]],
    frame_start: float,
    frame_end: float,
    start_i: int,
    end_i: int,
) -> None:
    peak_rad = math.radians(MIRROR_ROT_DEG)
    for f in range(start_i, end_i + 1):
        scene.frame_set(f)
        dz = _phase_offset(float(f), frame_start, frame_end, peak_rad)
        for mirror in mirrors:
            base = samples_r[mirror.name][f]
            e = Euler((base.x, base.y, base.z + dz), base.order)
            mirror.rotation_euler = e
            mirror.keyframe_insert(data_path="rotation_euler", frame=f)


def main() -> None:
    _ensure_marss_scene_loaded()

    cam = _resolve_camera()
    mirrors = _resolve_mirror_group()

    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()

    span = _keyframes_frame_span(cam)
    if span:
        frame_start, frame_end = span
        print(f"Camera keyframe span (drives mirror too): {frame_start:.0f} – {frame_end:.0f}")
    else:
        frame_start = float(scene.frame_start)
        frame_end = float(scene.frame_end)
        print(
            "No keyframes on camera; using scene frame range "
            f"{frame_start:.0f} – {frame_end:.0f}"
        )

    start_i = int(round(frame_start))
    end_i = int(round(frame_end))

    cam_t = _sample_camera_translations(cam, scene, depsgraph, start_i, end_i)
    mir_r = _sample_mirror_rotation_eulers(mirrors, scene, depsgraph, start_i, end_i)

    _apply_camera_offset(cam, scene, cam_t, frame_start, frame_end, start_i, end_i)
    _apply_mirror_rotation_delta(
        mirrors, scene, mir_r, frame_start, frame_end, start_i, end_i
    )

    scene.frame_set(start_i)

    out_path = OUTPUT_BLEND.resolve()
    bpy.ops.wm.save_as_mainfile(filepath=str(out_path), check_existing=False)
    print(f"Saved (original {INPUT_BLEND.name} on disk was not overwritten): {out_path}")


if __name__ == "__main__":
    main()
