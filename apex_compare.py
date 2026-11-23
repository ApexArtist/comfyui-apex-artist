"""Interactive A/B wipe preview. Original image tensors pass through unchanged."""
import torch
import torch.nn.functional as F


def preview_frame(images, frame, max_edge=2048):
    if not isinstance(images, torch.Tensor) or images.ndim != 4 or min(images.shape[:3]) < 1 or images.shape[-1] not in (1,3,4):
        raise ValueError("Apex Compare: each input must be a nonempty BHWC IMAGE tensor with 1, 3 or 4 channels.")
    selected = min(max(int(frame),0), images.shape[0]-1)
    # Only the chosen frame moves to CPU; never retain/copy a video batch for UI.
    image = images[selected:selected+1].detach().to(device="cpu",dtype=torch.float32)
    if image.shape[-1] == 1:
        image = image.repeat(1,1,1,3)
    h,w = image.shape[1:3]
    if max(h,w) > max_edge:
        scale = max_edge/max(h,w)
        image = F.interpolate(image.movedim(-1,1),size=(max(1,round(h*scale)),max(1,round(w*scale))),mode="bilinear",align_corners=False,antialias=True).movedim(1,-1)
    return torch.nan_to_num(image,nan=0.0,posinf=1.0,neginf=0.0).clamp(0,1), selected


class ApexCompare:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"A": ("IMAGE",), "B": ("IMAGE",)},
                "optional": {
                    "label_a": ("STRING", {"default":"Original", "tooltip":"Overlay on the left: A + this label."}),
                    "label_b": ("STRING", {"default":"Result", "tooltip":"Overlay on the right: B + this label."}),
                    "frame": ("INT", {"default":0,"min":0,"max":2**31-1,"tooltip":"Zero-based preview frame. Each input clamps to its own batch length; outputs remain the full original batches."})}}

    RETURN_TYPES = ("IMAGE","IMAGE")
    RETURN_NAMES = ("A","B")
    FUNCTION = "compare"
    OUTPUT_NODE = True
    CATEGORY = "Apex Artist/Image"
    DESCRIPTION = "Drag a vertical wipe to compare A (left) and B (right), with always-visible labels. Preview only: no labels, resizing or wipe are applied to outputs."

    def __init__(self):
        from nodes import PreviewImage
        self._preview = PreviewImage()

    def compare(self,A,B,label_a="Original",label_b="Result",frame=0):
        a,af = preview_frame(A,frame)
        b,bf = preview_frame(B,frame)
        # Use ComfyUI's temporary preview handling, never a custom HTTP route.
        a_file = self._preview.save_images(a,filename_prefix="apex_compare_A")["ui"]["images"][0]
        b_file = self._preview.save_images(b,filename_prefix="apex_compare_B")["ui"]["images"][0]
        info = {"a":a_file,"b":b_file,"label_a":str(label_a)[:120],"label_b":str(label_b)[:120],
                "size_a":[A.shape[2],A.shape[1]],"size_b":[B.shape[2],B.shape[1]],"frame_a":af,"frame_b":bf}
        return {"ui":{"apex_compare":[info]},"result":(A,B)}
