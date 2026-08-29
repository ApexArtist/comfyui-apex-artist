"""
Apex HDRI Preview API
Serves a browser-displayable PNG preview of the camera view rendered from an
HDRI/equirectangular panorama. Rendering happens server-side so .hdr/.exr files
(which browsers cannot decode) are supported too.
"""
import io
import os

import numpy as np
from PIL import Image
from aiohttp import web
from server import PromptServer
import folder_paths

from .apex_hdri_viewer import ApexHDRIViewer, equirect_to_camera_view


class ApexHDRIAPI:
    def __init__(self):
        self.setup_routes()

    def _tensor_to_png_bytes(self, tensor):
        """Convert a [1,H,W,3] float tensor (0..1) to PNG bytes."""
        arr = (
            tensor[0]
            .clamp(0.0, 1.0)
            .mul(255.0)
            .round()
            .byte()
            .cpu()
            .numpy()
        )
        img = Image.fromarray(np.ascontiguousarray(arr), "RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def setup_routes(self):
        """Setup API routes for HDRI camera-view preview serving."""

        @PromptServer.instance.routes.get("/apex/hdri_preview")
        async def get_hdri_preview(request):
            """Render a small camera view from the panorama and return it as a PNG."""
            try:
                filename = request.query.get("filename", "")
                if not filename:
                    return web.Response(status=400, text="No filename provided")

                yaw = float(request.query.get("yaw", 0))
                pitch = float(request.query.get("pitch", 0))
                roll = float(request.query.get("roll", 0))
                fov = float(request.query.get("fov", 90))
                lens = request.query.get("lens", "rectilinear")
                if lens not in ("rectilinear", "fisheye"):
                    lens = "rectilinear"

                filepath = folder_paths.get_annotated_filepath(filename)
                if not os.path.exists(filepath):
                    return web.Response(status=404, text="File not found")

                source = ApexHDRIViewer._load_hdri_tensor(filepath)

                # Render size can be requested by the client to match the
                # widget shape; clamped for performance.
                try:
                    out_w = int(float(request.query.get("width", 512)))
                    out_h = int(float(request.query.get("height", 288)))
                except (TypeError, ValueError):
                    out_w, out_h = 512, 288
                out_w = max(64, min(out_w, 1024))
                out_h = max(64, min(out_h, 1024))

                rendered = equirect_to_camera_view(
                    source, yaw, pitch, roll, fov, out_w, out_h, lens
                )
                png = self._tensor_to_png_bytes(rendered)
                return web.Response(
                    body=png,
                    content_type="image/png",
                    headers={"Cache-Control": "no-cache"},
                )
            except Exception as exc:  # pragma: no cover - defensive
                print(f"[Apex HDRI Preview] Error: {exc}")
                return web.Response(status=500, text=str(exc))


# Initialize the API
api_instance = ApexHDRIAPI()