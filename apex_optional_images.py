from comfy_api.latest import io
from comfy_extras.nodes_post_processing import batch_images


class ApexOptionalImages(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="ApexOptionalImages",
            display_name="Apex Optional Images",
            category="Apex Artist/Image",
            description="Connect optional reference images. Inputs grow as images are connected. An empty set returns count 0 so its video track can be skipped.",
            inputs=[io.Autogrow.Input(
                "images", optional=True,
                template=io.Autogrow.TemplatePrefix(
                    input=io.Image.Input("image"), prefix="image_", min=0, max=100),
            )],
            outputs=[io.Image.Output("images"), io.Int.Output("count")],
        )

    @classmethod
    def execute(cls, images=None):
        batch = batch_images([image for image in (images or {}).values() if image is not None])
        count = 0 if batch is None else batch.shape[0]
        return io.NodeOutput(batch, count)
