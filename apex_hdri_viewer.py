#!/usr/bin/env python3
"""
Apex HDRI Viewer Node - Equirectangular panorama camera renderer

Loads an equirectangular 360 panorama/HDRI IMAGE tensor and outputs a rendered
camera view using yaw, pitch, roll, FOV, lens type, and output resolution
controls. Final reprojection is performed in Python/PyTorch at full output
resolution; the optional JS frontend only drives widget values for aiming.
"""

import math
import os
import hashlib

import numpy as np
from PIL import Image, ImageOps, ImageSequence

import torch
import torch.nn.functional as F
import folder_paths
import comfy.model_management
import node_helpers

try:
    import cv2
except ImportError:  # pragma: no cover - dependency installed via requirements
    cv2 = None


def _rotation_matrix(yaw_deg, pitch_deg, roll_deg, device, dtype):
    """Camera-to-world rotation, yaw around Y, pitch around X, roll around Z.

    Order: roll -> pitch -> yaw (applied right to left: R = Ry @ Rx @ Rz).
    """
    yaw = torch.deg2rad(torch.as_tensor(float(yaw_deg), device=device, dtype=dtype))
    pitch = torch.deg2rad(torch.as_tensor(float(pitch_deg), device=device, dtype=dtype))
    roll = torch.deg2rad(torch.as_tensor(float(roll_deg), device=device, dtype=dtype))

    cy, sy = torch.cos(yaw), torch.sin(yaw)
    cx, sx = torch.cos(pitch), torch.sin(pitch)
    cz, sz = torch.cos(roll), torch.sin(roll)

    zero = torch.zeros((), device=device, dtype=dtype)
    one = torch.ones((), device=device, dtype=dtype)

    ry = torch.stack([
        torch.stack([cy, zero, sy]),
        torch.stack([zero, one, zero]),
        torch.stack([-sy, zero, cy]),
    ])
    rx = torch.stack([
        torch.stack([one, zero, zero]),
        torch.stack([zero, cx, -sx]),
        torch.stack([zero, sx, cx]),
    ])
    rz = torch.stack([
        torch.stack([cz, -sz, zero]),
        torch.stack([sz, cz, zero]),
        torch.stack([zero, zero, one]),
    ])

    return ry @ rx @ rz


def _camera_ray_grid(out_w, out_h, fov_deg, lens_type, device, dtype):
    """Build an (H, W, 3) unit direction grid in camera space.

    Camera looks down -Z, +X points right, +Y points up. Supports rectilinear
    pinhole projection and equidistant fisheye projection.
    """
    fov = math.radians(float(fov_deg))
    xs = torch.linspace(-1.0, 1.0, int(out_w), device=device, dtype=dtype)
    ys = torch.linspace(1.0, -1.0, int(out_h), device=device, dtype=dtype)
    grid_y, grid_x = torch.meshgrid(ys, xs, indexing="ij")

    if lens_type == "rectilinear":
        aspect = float(out_h) / float(out_w)
        tan_half_fov = math.tan(fov / 2.0)
        px = grid_x * tan_half_fov
        py = grid_y * tan_half_fov * aspect
        pz = -torch.ones_like(px)
        dirs = torch.stack((px, py, pz), dim=-1)
    elif lens_type == "fisheye":
        radius = torch.sqrt(grid_x.square() + grid_y.square()).clamp(0.0, 1.0)
        theta = radius * (fov / 2.0)
        phi = torch.atan2(grid_y, grid_x)
        dx = torch.sin(theta) * torch.cos(phi)
        dy = torch.sin(theta) * torch.sin(phi)
        dz = -torch.cos(theta)
        dirs = torch.stack((dx, dy, dz), dim=-1)
    else:
        raise ValueError(f"Unknown lens_type: {lens_type}")

    return F.normalize(dirs, dim=-1)


def equirect_to_camera_view(equirect, yaw_deg, pitch_deg, roll_deg, fov_deg,
                            out_w, out_h, lens_type="rectilinear"):
    """Render an equirectangular IMAGE tensor batch to camera-view images.

    Args:
        equirect: Tensor shaped [B,H,W,C], float32-like in ComfyUI IMAGE format.

    Returns:
        Tensor shaped [B,out_h,out_w,C], preserving float dynamic range.
    """
    if equirect.ndim == 3:
        equirect = equirect.unsqueeze(0)
    if equirect.ndim != 4 or equirect.shape[-1] < 3:
        raise ValueError("hdri_image must be a ComfyUI IMAGE tensor shaped [B,H,W,C]")

    device = equirect.device
    sample_dtype = torch.float32
    source = equirect.to(dtype=sample_dtype)
    batch, _, _, channels = source.shape

    dirs_cam = _camera_ray_grid(out_w, out_h, fov_deg, lens_type, device, sample_dtype)
    rotation = _rotation_matrix(yaw_deg, pitch_deg, roll_deg, device, sample_dtype)
    dirs_world = dirs_cam @ rotation.T

    dx = dirs_world[..., 0]
    dy = dirs_world[..., 1].clamp(-1.0, 1.0)
    dz = dirs_world[..., 2]

    lon = torch.atan2(dx, -dz)
    lat = torch.asin(dy)

    # grid_sample expects normalized coordinates in [-1, 1]. align_corners=True
    # gives direct pixel-center-compatible mapping at the equirectangular bounds.
    grid_x = lon / math.pi
    grid_y = -2.0 * lat / math.pi
    grid = torch.stack((grid_x, grid_y), dim=-1).unsqueeze(0).repeat(batch, 1, 1, 1)

    # Horizontal longitude must wrap across the 360 seam. Padding with one
    # repeated column on each side lets grid_sample interpolate cleanly there.
    source_nchw = source.permute(0, 3, 1, 2)
    source_wrapped = torch.cat((source_nchw[..., -1:], source_nchw, source_nchw[..., :1]), dim=-1)
    padded_width = source_wrapped.shape[-1]
    grid = grid.clone()
    grid[..., 0] = ((grid[..., 0] + 1.0) * 0.5 * (source.shape[2] - 1.0) + 1.0) / (padded_width - 1.0) * 2.0 - 1.0

    rendered = F.grid_sample(
        source_wrapped,
        grid,
        mode="bilinear",
        padding_mode="border",
        align_corners=True,
    )
    return rendered.permute(0, 2, 3, 1)[..., :channels]


class ApexHDRIViewer:
    """Load an HDRI/equirect panorama file and output a captured camera view."""

    SUPPORTED_EXTENSIONS = {
        ".exr", ".hdr", ".pic",
        ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp",
    }

    @classmethod
    def _list_hdri_files(cls):
        input_dir = folder_paths.get_input_directory()
        files = []
        if not os.path.isdir(input_dir):
            return files
        for root, _, filenames in os.walk(input_dir):
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in cls.SUPPORTED_EXTENSIONS:
                    continue
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, input_dir).replace(os.sep, "/")
                files.append(rel_path)
        return sorted(files)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "hdri_image": (cls._list_hdri_files(), {"image_upload": True}),
                "yaw": ("FLOAT", {"default": 0.0, "min": -360.0, "max": 360.0, "step": 0.5}),
                "pitch": ("FLOAT", {"default": 0.0, "min": -89.0, "max": 89.0, "step": 0.5}),
                "roll": ("FLOAT", {"default": 0.0, "min": -180.0, "max": 180.0, "step": 0.5}),
                "fov": ("FLOAT", {"default": 90.0, "min": 10.0, "max": 179.0, "step": 1.0}),
                "lens_type": (["rectilinear", "fisheye"], {"default": "rectilinear"}),
                "output_width": ("INT", {"default": 1024, "min": 64, "max": 8192, "step": 8}),
                "output_height": ("INT", {"default": 1024, "min": 64, "max": 8192, "step": 8}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("camera_view",)
    FUNCTION = "render"
    CATEGORY = "Apex Artist/Image"
    SEARCH_ALIASES = ["hdri loader", "panorama viewer", "environment map", "360 image", "equirectangular camera"]

    @staticmethod
    def _pil_to_tensor_batch(image_path):
        dtype = comfy.model_management.intermediate_dtype()
        device = comfy.model_management.intermediate_device()
        img = node_helpers.pillow(Image.open, image_path)

        output_images = []
        width, height = None, None
        for frame in ImageSequence.Iterator(img):
            frame = node_helpers.pillow(ImageOps.exif_transpose, frame)

            if frame.mode in ("I;16", "I", "F"):
                arr = np.array(frame).astype(np.float32)
                max_value = float(np.nanmax(arr)) if arr.size else 1.0
                if max_value > 1.0:
                    arr = arr / max_value
                arr = np.stack([arr, arr, arr], axis=-1)
            else:
                rgb = frame.convert("RGB")
                arr = np.array(rgb).astype(np.float32) / 255.0

            if width is None:
                height, width = arr.shape[:2]
            if arr.shape[1] != width or arr.shape[0] != height:
                continue
            output_images.append(torch.from_numpy(arr)[None,].to(dtype=dtype))

        if not output_images:
            raise ValueError(f"No readable image frames found in {image_path}")
        return torch.cat(output_images, dim=0).to(device=device, dtype=dtype)

    @staticmethod
    def _load_hdri_tensor(image_path):
        ext = os.path.splitext(image_path)[1].lower()
        if ext in {".hdr", ".pic", ".exr"}:
            if cv2 is None:
                raise ImportError(
                    "Apex HDRI Viewer needs opencv-python to load .hdr/.exr files. "
                    "Install this node's requirements.txt, or use PNG/TIFF/JPEG panoramas."
                )

            dtype = comfy.model_management.intermediate_dtype()
            device = comfy.model_management.intermediate_device()
            image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED | cv2.IMREAD_ANYDEPTH | cv2.IMREAD_ANYCOLOR)
            if image is None:
                raise ValueError(f"OpenCV could not read HDRI file: {image_path}")
            if image.ndim == 2:
                image = np.stack([image, image, image], axis=-1)
            if image.shape[-1] >= 3:
                image = image[..., :3]
                image = image[..., ::-1]  # BGR -> RGB
            image = np.ascontiguousarray(image.astype(np.float32))
            # Replace NaN/Inf with 0 (common in broken EXR tiles)
            image = np.nan_to_num(image, nan=0.0, posinf=0.0, neginf=0.0)
            max_val = float(image.max()) if image.size else 1.0
            if max_val > 1.0:
                # HDR data: apply Reinhard tone-mapping to compress dynamic range
                # into [0, 1] while preserving relative brightness
                image = image / (1.0 + image)
            return torch.from_numpy(image)[None,].to(device=device, dtype=dtype)

        return ApexHDRIViewer._pil_to_tensor_batch(image_path)

    def render(self, hdri_image, yaw, pitch, roll, fov, lens_type,
               output_width, output_height):
        try:
            output_width = int(output_width)
            output_height = int(output_height)
            image_path = folder_paths.get_annotated_filepath(hdri_image)
            source = self._load_hdri_tensor(image_path)
            print(
                f"Apex HDRI Viewer: {lens_type}, yaw={yaw}, pitch={pitch}, "
                f"roll={roll}, fov={fov}, size={output_width}x{output_height}, file={hdri_image}"
            )
            rendered = equirect_to_camera_view(
                source,
                yaw,
                pitch,
                roll,
                fov,
                output_width,
                output_height,
                lens_type,
            )
            return (rendered.clamp(0.0, 1.0).cpu(),)
        except Exception as exc:
            print(f"[Apex HDRI Viewer] Error: {exc}")
            return (torch.zeros((1, 1, 1, 3), dtype=torch.float32),)

    @classmethod
    def IS_CHANGED(cls, hdri_image, yaw, pitch, roll, fov, lens_type,
                   output_width, output_height):
        image_path = folder_paths.get_annotated_filepath(hdri_image)
        digest = hashlib.sha256()
        with open(image_path, "rb") as file:
            digest.update(file.read())
        digest.update(str((yaw, pitch, roll, fov, lens_type, output_width, output_height)).encode("utf-8"))
        return digest.hexdigest()

    @classmethod
    def VALIDATE_INPUTS(cls, hdri_image, **kwargs):
        if not folder_paths.exists_annotated_filepath(hdri_image):
            return f"Invalid HDRI/panorama image file: {hdri_image}"
        ext = os.path.splitext(hdri_image.split("[")[0])[1].lower()
        if ext not in cls.SUPPORTED_EXTENSIONS:
            return f"Unsupported HDRI/panorama file extension: {ext}"
        return True


NODE_CLASS_MAPPINGS = {
    "ApexHDRIViewer": ApexHDRIViewer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ApexHDRIViewer": "Apex HDRI Viewer",
}
