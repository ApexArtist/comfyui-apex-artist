"""Run with the ComfyUI Python environment: python -m unittest discover -s tests."""

import importlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest

import torch


package = types.ModuleType("apex_regression")
package.__path__ = [str(Path(__file__).resolve().parents[1])]
sys.modules[package.__name__] = package
blur = importlib.import_module("apex_regression.apex_blur").ApexBlur
sharpen = importlib.import_module("apex_regression.apex_sharpen").ApexSharpen
blend = importlib.import_module("apex_regression.apex_layer_blend").ApexLayerBlend
normal = importlib.import_module("apex_regression.apex_depth_to_normal").ApexDepthToNormal
storage = importlib.import_module("apex_regression.apex_prompt_store")


class ImageRegressions(unittest.TestCase):
    def setUp(self):
        self.image = torch.linspace(0, 1, 16 * 16 * 3).reshape(1, 16, 16, 3)

    def test_depth_blur_covers_all_pixels(self):
        depth = torch.linspace(0, 1, 256).reshape(1, 16, 16)
        for radius in (0.5, 3, 10):
            with self.subTest(radius=radius):
                result, _ = blur().apply_blur(torch.ones_like(self.image), "depth", radius, depth=depth)
                self.assertTrue((result > 0).all())

    def test_fractional_radius_preserves_dimensions(self):
        for radius in (0.5, 1.5, 2.5, 10.5):
            with self.subTest(radius=radius):
                result, _ = blur().apply_blur(self.image, "motion", radius)
                self.assertEqual(result.shape, self.image.shape)
        result, _ = sharpen().apply_sharpening(self.image, "Structure Aware", radius=1.5)
        self.assertEqual(result.shape, self.image.shape)

    def test_half_precision_filters(self):
        image = self.image.half()
        for kind in ("gaussian", "box", "motion", "radial", "lens", "spin", "zoom", "depth"):
            with self.subTest(kind=kind):
                result, _ = blur().apply_blur(image, kind, radius=2, depth=torch.zeros(1, 16, 16))
                self.assertEqual(result.dtype, torch.float16)
                self.assertTrue(torch.isfinite(result).all())
        for kind in ("Edge Enhancement", "Structure Aware", "Laplacian Sharpen"):
            with self.subTest(kind=kind):
                result, _ = sharpen().apply_sharpening(image, kind)
                self.assertEqual(result.dtype, image.dtype)
                self.assertTrue(torch.isfinite(result).all())

    def test_zero_strength_does_not_change_brightness(self):
        result, _ = sharpen().apply_sharpening(self.image, "Multi-Scale Sharpen", strength=0, fine_detail=2)
        torch.testing.assert_close(result, self.image)

    def test_dissolve_endpoints_and_pixel_channels(self):
        base, overlay = torch.zeros_like(self.image), torch.ones_like(self.image)
        for opacity, expected in ((0, base), (1, overlay)):
            result, _ = blend().blend_layers(base, overlay, "dissolve", opacity)
            self.assertTrue(torch.equal(result, expected))
        result, _ = blend().blend_layers(base, overlay, "dissolve", .5)
        self.assertTrue(torch.equal(result[..., 0], result[..., 1]))

    def test_normal_map_is_rgb_for_rgba_depth(self):
        result, _ = normal().depth_to_normal(torch.cat([self.image, torch.ones(1, 16, 16, 1)], -1).half())
        self.assertEqual(result.shape, self.image.shape)
        self.assertTrue(torch.isfinite(result).all())

    def test_processing_errors_are_not_hidden(self):
        with self.assertRaises(RuntimeError):
            blur().apply_blur(None)
        with self.assertRaises(RuntimeError):
            blend().blend_layers(self.image, torch.ones(2, 16, 16, 2), "multiply")


class PresetStorageRegressions(unittest.TestCase):
    def test_character_replacement_validation_and_revisions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            factory = root / "factory.json"
            factory.write_text(json.dumps({"Top": {"Coat": {"prompt": "black coat"}}}))
            store = storage.PromptPresetStore(factory, root / "user.json", lambda: {}, categories=("Top",), complete_library=True)
            original = store.snapshot()
            changed = {"Top": {"Jacket": {"prompt": "blue jacket"}}}
            saved = store.mutate("replace", {"revision": original["revision"], "presets": changed})
            self.assertNotIn("Coat", saved["presets"]["Top"])
            with self.assertRaises(storage.PresetConflict):
                store.mutate("replace", {"revision": original["revision"], "presets": changed})
            before = store.user_path.read_bytes()
            with self.assertRaises(storage.PresetError):
                store.mutate("replace", {"revision": saved["revision"], "presets": {"Top": {"Bad": "not an object"}}})
            self.assertEqual(store.user_path.read_bytes(), before)
            self.assertIn("Coat", json.loads(factory.read_text())["Top"])


if __name__ == "__main__":
    unittest.main()
