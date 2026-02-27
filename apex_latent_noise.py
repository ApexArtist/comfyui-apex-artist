import torch
import random
from typing import Tuple

class ApexLatentNoise:
    """Inject Gaussian noise into a LATENT tensor.

    Useful as a small helper node to perturb latents before a second ksampler pass.
    Supports reproducible seeding and two modes: 'add' (noisy = latent + noise)
    and 'replace' (noisy = noise).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent": ("LATENT",),
            },
            "optional": {
                "strength": ("FLOAT", {"default": 0.08, "min": 0.0, "max": 2.0, "step": 0.01}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffff}),
                "mode": (("add", "replace"), {"default": "add"}),
                "per_batch": ("BOOLEAN", {"default": True}),
                "clamp": ("BOOLEAN", {"default": False}),
                "preset": (("low", "mid", "high", "custom"), {"default": "mid"}),
            }
        }

    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("noisy_latent",)
    FUNCTION = "inject_noise"
    CATEGORY = "Apex Artist/Latent"

    def inject_noise(self, latent, strength: float = 0.08, preset: str = "mid", seed: int = 0, mode: str = "add", per_batch: bool = True, clamp: bool = False) -> Tuple[object]:
        """latent: LATENT tensor (PyTorch)
        Adds Gaussian noise with standard deviation `strength` (friendly name).
        A `preset` dropdown (low/mid/high/custom) is available. If preset is not 'custom', it
        overrides `strength` with conservative defaults: low=0.02, mid=0.08, high=0.20.
        Returns a LATENT tensor (same shape) with noise injected.
        """
        if latent is None:
            return (None,)

        # Ensure torch tensor
        try:
            import torch as _torch
        except Exception:
            raise RuntimeError("PyTorch is required for ApexLatentNoise")

        # Normalize seed for reproducibility
        if seed is None:
            seed = 0
        random.seed(seed)
        _torch.manual_seed(int(seed))
        if _torch.cuda.is_available():
            _torch.cuda.manual_seed_all(int(seed))

        x = latent

        # Some LATENTs may be provided as nested tuples; handle common case of tensor
        if isinstance(x, tuple) or isinstance(x, list):
            # operate on first tensor element (common pattern)
            t = x[0]
            is_container = True
        else:
            t = x
            is_container = False

        if not isinstance(t, _torch.Tensor):
            # If it's not a tensor, return original
            return (latent,)

        # Generate noise of same shape
        if per_batch and t.ndim >= 1:
            noise = _torch.randn_like(t)
        else:
            # If not per-batch, create noise per-sample shape excluding batch dim
            if t.ndim >= 1:
                shape = (1,) + tuple(t.shape[1:])
            else:
                shape = t.shape
            noise = _torch.randn(shape, device=t.device, dtype=t.dtype)

        # Apply preset mapping unless user selected 'custom'
        final_strength = float(strength)
        if isinstance(preset, str) and preset in ("low", "mid", "high"):
            mapping = {"low": 0.02, "mid": 0.08, "high": 0.20}
            final_strength = float(mapping[preset])

        noise = noise * final_strength

        if mode == "replace":
            out = noise
        else:
            out = t + noise

        if clamp:
            out = _torch.clamp(out, -1.0, 1.0)

        # Preserve container structure when appropriate
        if is_container:
            new_container = list(x)
            new_container[0] = out
            return (tuple(new_container),)

        return (out,)


NODE_CLASS_MAPPINGS = {
    "ApexLatentNoise": ApexLatentNoise
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ApexLatentNoise": "Apex Latent Noise"
}
