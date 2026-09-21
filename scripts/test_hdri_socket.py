"""Socket HDRI backend regressions; no running server or user files needed."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image
import torch

ROOT = Path(__file__).resolve().parents[1]
folder_paths = types.ModuleType("folder_paths")
comfy = types.ModuleType("comfy")
management = types.ModuleType("comfy.model_management")
comfy.model_management = management
spec = importlib.util.spec_from_file_location("hdri_under_test", ROOT / "apex_hdri_viewer.py")
hdri = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"folder_paths": folder_paths, "comfy": comfy,
                            "comfy.model_management": management,
                            "node_helpers": types.ModuleType("node_helpers")}):
    spec.loader.exec_module(hdri)


class HDRISocketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        folder_paths.get_temp_directory = lambda: self.temp.name
        self.viewer = hdri.ApexHDRIViewer()
        self.source = torch.linspace(0, 1, 129).view(1, 1, 129, 1).expand(2, 65, 129, 3).clone()

    def render(self, **kwargs):
        args = dict(image_input=self.source, yaw=30, pitch=10, roll=5,
                    fov=90, back_fov=120, lens_type="rectilinear",
                    output_width=64, output_height=64, exposure=0)
        args.update(kwargs)
        return self.viewer.render(**args)

    def test_back_direction_and_batch(self):
        result = self.render()
        front, back = result["result"]
        self.assertEqual(front.shape, (2, 64, 64, 3))
        expected = hdri.equirect_to_camera_view(self.source, -150, 10, 5, 120, 64, 64)
        torch.testing.assert_close(back, expected)
        self.assertFalse(torch.allclose(front, back))

    def test_unique_previews_and_original_source(self):
        first, second = self.render(), self.render()
        items = [item for result in (first, second)
                 for key in ("images", "hdri_source") for item in result["ui"][key]]
        self.assertEqual(len({i["filename"] for i in items}), 10)
        self.assertTrue(all(i["type"] == "temp" for i in items))
        for item in items:
            self.assertTrue((Path(self.temp.name) / item["filename"]).is_file())
        with Image.open(Path(self.temp.name) / first["ui"]["hdri_source"][0]["filename"]) as image:
            self.assertEqual(image.size, (129, 65))
            np.testing.assert_allclose(np.asarray(image) / 255, self.source[0].numpy(), atol=1 / 255)

    def test_exposure_hdr_and_grad_tensors(self):
        source = (self.source * 4).requires_grad_()
        result = self.render(image_input=source, exposure=-1)
        self.assertEqual(result["ui"]["hdri_source_scale"], [4.0])
        expected = hdri.equirect_to_camera_view(source * 0.5, 30, 10, 5, 90, 64, 64)
        torch.testing.assert_close(result["result"][0], expected)
        self.assertGreater(float(result["result"][0].detach().max()), 1)

    def test_bounded_source_and_fisheye(self):
        result = self.render(image_input=torch.ones(1, 64, 4096, 3), lens_type="fisheye")
        with Image.open(Path(self.temp.name) / result["ui"]["hdri_source"][0]["filename"]) as image:
            self.assertEqual(image.size, (2048, 32))
        self.assertTrue(torch.isfinite(result["result"][0]).all())

    def test_invalid_input_raises_instead_of_silent_black_output(self):
        with self.assertRaises(ValueError):
            self.render(image_input=torch.zeros(1, 10, 10, 1))

    def test_native_cache_and_widget_order(self):
        self.assertFalse(hasattr(self.viewer, "IS_CHANGED"))
        self.assertEqual(list(self.viewer.INPUT_TYPES()["required"]), [
            "image_input", "yaw", "pitch", "roll", "fov", "back_fov", "lens_type",
            "output_width", "output_height", "exposure"])


if __name__ == "__main__":
    unittest.main()