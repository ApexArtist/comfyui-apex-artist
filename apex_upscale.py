"""
Apex Upscale By Node
Upscales images by a float factor with 3-decimal slider precision (e.g. 1.000).
"""

import torch
import torch.nn.functional as F

class ApexUpscaleBy:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "upscale_method": (["lanczos", "bicubic", "bilinear", "nearest"], {"default": "lanczos"}),
                "scale_by": ("FLOAT", {"default": 1.875, "min": 0.01, "max": 16.0, "step": 0.001, "slider": True, "precision": 3, "format": "{:.3f}"}),
                "antialias": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "info")
    FUNCTION = "upscale"
    CATEGORY = "Apex Artist/Image"

    def upscale(self, image, upscale_method="lanczos", scale_by=1.0, antialias=True):
        """
        Upscale `image` by a float factor `scale_by`.
        - `image`: torch tensor in shape (N, H, W, C), float [0..1]
        - `upscale_method`: one of 'lanczos', 'bicubic', 'bilinear', 'nearest'
        - `scale_by`: float factor (slider precision 0.001, default 1.000)
        - `antialias`: whether to use antialiasing when available
        Returns (upscaled_image,)
        """
        try:
            # quick no-op (return info as well)
            if scale_by is None or float(scale_by) == 1.0:
                N_in = image.shape[0] if image.ndim == 4 else 1
                H_in = image.shape[1] if image.ndim == 4 else image.shape[0]
                W_in = image.shape[2] if image.ndim == 4 else image.shape[1]
                C_in = image.shape[3] if image.ndim == 4 else image.shape[2]
                info = f"scale={float(scale_by or 1.0):.3f} in=({N_in},{H_in},{W_in},{C_in}) out=(no-change)"
                return (image, info)

            img = image
            # ensure float and device
            img = img.to(dtype=torch.float32)
            device = img.device

            # Accept both (N,H,W,C) and single (H,W,C) and (N,C,H,W)
            added_batch = False
            if img.ndim == 3 and img.shape[2] in (1, 3, 4):
                # single image H,W,C -> add batch
                img = img.unsqueeze(0)
                added_batch = True

            if img.ndim == 4 and img.shape[-1] in (1, 3, 4):
                N, H, W, C = img.shape
            elif img.ndim == 4 and img.shape[1] in (1, 3, 4):
                # N,C,H,W -> convert to N,H,W,C
                img = img.permute(0, 2, 3, 1)
                N, H, W, C = img.shape
            else:
                raise ValueError("Unsupported image shape. Expected (N,H,W,C) or (H,W,C) with C=1,3,4.")
            new_h = max(1, int(round(H * float(scale_by))))
            new_w = max(1, int(round(W * float(scale_by))))

            # Convert to N,C,H,W for interpolate
            t = img.permute(0, 3, 1, 2)

            # Robust interpolation: try requested mode, then fall back to bicubic/bilinear/nearest
            requested_mode = upscale_method
            supported_modes = {"lanczos", "bicubic", "bilinear", "nearest"}
            if requested_mode not in supported_modes:
                requested_mode = "bicubic"

            out = None
            try_modes = [requested_mode, "bicubic", "bilinear", "nearest"]
            for m in try_modes:
                try:
                    if hasattr(F, "interpolate"):
                        if m in ("lanczos", "bicubic", "bilinear"):
                            try:
                                out = F.interpolate(t, size=(new_h, new_w), mode=m, antialias=antialias)
                            except TypeError:
                                out = F.interpolate(t, size=(new_h, new_w), mode=m)
                        else:
                            out = F.interpolate(t, size=(new_h, new_w), mode=m)
                    else:
                        out = F.interpolate(t, size=(new_h, new_w), mode=m)
                except Exception:
                    out = None
                if out is not None:
                    break

            if out is None:
                # All attempts failed — return original image with info
                print(f"ApexUpscaleBy: interpolation failed for modes {try_modes}")
                info = f"scale={float(scale_by):.3f} interpolation_failed"
                return (image, info)

            out = out.permute(0, 2, 3, 1)
            out = out.clamp(0.0, 1.0)

            # If we added a batch dimension earlier, squeeze it back
            if added_batch:
                out = out.squeeze(0)

            info = f"scale={float(scale_by):.3f} in=({N},{H},{W},{C}) out=({N if not added_batch else 1},{new_h},{new_w},{C})"
            return (out, info)

        except Exception as e:
            # On error, return the original image and message in STRING slot if caller expects it.
            print(f"ApexUpscaleBy error: {e}")
            return (image, f"error: {e}")
