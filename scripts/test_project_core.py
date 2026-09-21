"""Core regression tests; runs without starting ComfyUI or changing user data."""
import ast
import importlib
import math
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest

import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "apex_core_tests"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = package
utils = importlib.import_module(f"{PACKAGE}.apex_utils")


def reference_blur(image, radius, multiplier=0.5):
    """Original dense kernel implementation, retained as a numerical oracle."""
    sigma = max(radius * multiplier, 0.5)
    size = min(max(2 * math.ceil(2 * sigma) + 1, 3), 101)
    dtype = torch.float64 if image.dtype == torch.float64 else torch.float32
    x = torch.arange(size, device=image.device, dtype=dtype) - size // 2
    xx, yy = torch.meshgrid(x, x, indexing="ij")
    kernel = torch.exp(-(xx.square() + yy.square()) / (2 * sigma**2))
    kernel = (kernel / kernel.sum()).to(image.dtype)
    channels = image.shape[-1]
    return F.conv2d(image.permute(0, 3, 1, 2),
                    kernel.view(1, 1, size, size).repeat(channels, 1, 1, 1),
                    padding=size // 2, groups=channels).permute(0, 2, 3, 1)


class CoreTests(unittest.TestCase):
    def test_gaussian_matches_dense_reference(self):
        torch.manual_seed(42)
        devices = ["cpu"] + (["cuda"] if torch.cuda.is_available() else [])
        for device in devices:
            for channels in (1, 3, 4):
                for radius in (0.5, 3.0, 10.0, 100.0):
                    with self.subTest(device=device, channels=channels, radius=radius):
                        image = torch.rand(2, 13, 17, channels, device=device)
                        for multiplier in (0.5, 0.8):
                            actual = utils.gaussian_blur(image, radius, multiplier)
                            expected = reference_blur(image, radius, multiplier)
                            torch.testing.assert_close(actual, expected, atol=2e-6, rtol=2e-5)

    def test_gaussian_dtype_and_noop(self):
        for dtype in (torch.float32, torch.float64):
            image = torch.rand(1, 9, 11, 3, dtype=dtype)
            self.assertIs(utils.gaussian_blur(image, 0), image)
            result = utils.gaussian_blur(image, 2)
            self.assertEqual(result.dtype, dtype)
            torch.testing.assert_close(result, reference_blur(image, 2))

    def test_mask_resize_broadcast_and_dtype(self):
        original = torch.zeros(2, 8, 10, 3)
        processed = torch.ones_like(original)
        mask = torch.full((4, 5), 0.25, dtype=torch.float64)
        result = utils.apply_mask(original, processed, mask)
        self.assertEqual(result.dtype, original.dtype)
        torch.testing.assert_close(result, torch.full_like(original, 0.25))

    @unittest.skipUnless(torch.cuda.is_available(), "CUDA unavailable")
    def test_cpu_mask_with_cuda_image(self):
        original = torch.zeros(1, 8, 10, 3, device="cuda")
        result = utils.apply_mask(original, torch.ones_like(original), torch.ones(8, 10))
        torch.testing.assert_close(result, torch.ones_like(original))

    def test_all_blur_and_sharpen_modes(self):
        image = torch.rand(2, 16, 20, 3)
        blur = importlib.import_module(f"{PACKAGE}.apex_blur").ApexBlur()
        sharpen = importlib.import_module(f"{PACKAGE}.apex_sharpen").ApexSharpen()
        for mode in blur.INPUT_TYPES()["required"]["blur_type"][0]:
            with self.subTest(blur=mode):
                result, info = blur.apply_blur(image, mode, radius=2, depth=torch.rand(2, 16, 20))
                self.assertNotIn("Error:", info)
                self.assertEqual(result.shape, image.shape)
                self.assertTrue(torch.isfinite(result).all())
        for mode in sharpen.INPUT_TYPES()["required"]["algorithm"][0]:
            with self.subTest(sharpen=mode):
                result, info = sharpen.apply_sharpening(image, mode)
                self.assertEqual(result.shape, image.shape)
                self.assertTrue(torch.isfinite(result).all())

    def test_blends_depth_and_json(self):
        image = torch.rand(2, 16, 20, 3)
        blend = importlib.import_module(f"{PACKAGE}.apex_layer_blend").ApexLayerBlend()
        for mode in blend.INPUT_TYPES()["required"]["blend_mode"][0]:
            with self.subTest(blend=mode):
                result, info = blend.blend_layers(image, image.flip(2), mode)
                self.assertNotIn("Error:", info)
                self.assertEqual(result.shape, image.shape)
                self.assertTrue(torch.isfinite(result).all())
        depth = importlib.import_module(f"{PACKAGE}.apex_depth_to_normal").ApexDepthToNormal()
        result, _ = depth.depth_to_normal(image, blur=1)
        self.assertEqual(result.shape, image.shape)
        self.assertTrue(torch.isfinite(result).all())
        lookup = importlib.import_module(f"{PACKAGE}.apex_json_node").ApexJSON()
        self.assertEqual(lookup.lookup('{"a": ["value"]}', "a.0"), ("value",))

    def test_directory_boundaries(self):
        # Extract the pure helper without registering routes or importing ComfyUI.
        tree = ast.parse((ROOT / "apex_lora_api.py").read_text(encoding="utf-8-sig"))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        helper = next(n for n in cls.body if isinstance(n, ast.FunctionDef)
                      and n.name == "_is_within_directory")
        helper.decorator_list = []
        namespace = {"os": os}
        exec(compile(ast.Module(body=[helper], type_ignores=[]), str(ROOT / "apex_lora_api.py"), "exec"), namespace)
        within = namespace[helper.name]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "loras"
            root.mkdir()
            self.assertTrue(within(root, root))
            self.assertTrue(within(root / "nested" / "file.png", root))
            self.assertFalse(within(Path(temp) / "loras-private", root))
            self.assertFalse(within(root / ".." / "outside", root))
            self.assertFalse(within(None, root))


if __name__ == "__main__":
    torch.set_num_threads(2)
    unittest.main(verbosity=2)