import torch

class ApexLastFrame:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "optional": {
                "images": ("IMAGE",),
                "video": ("VIDEO",),
            }
        }

    CATEGORY = "Apex Artist/Image"
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("last_image",)
    FUNCTION = "get_last_frame"

    def get_last_frame(self, images=None, video=None):
        """
        Get the last frame from a batch of video frames/images or video input
        
        Args:
            images: Batch of images tensor [batch, height, width, channels] (optional)
            video: VideoInput from ComfyUI Load Video node (optional)
            
        Returns:
            The last image in the batch or video
        """
        
        # Determine input source
        if video is not None:
            # Handle VideoInput from ComfyUI Load Video node
            # VIDEO type is a VideoInput object with get_components() method
            try:
                # Extract components from video
                components = video.get_components()
                # Get the images tensor from video components
                video_images = components.images
                
                # Get the last frame
                if len(video_images.shape) == 4 and video_images.shape[0] > 0:
                    last_frame = video_images[-1:]
                    return (last_frame,)
                else:
                    # Fallback for unexpected shape
                    return (torch.zeros((1, 64, 64, 3), dtype=torch.float32),)
            except Exception as e:
                print(f"Error extracting last frame from video: {e}")
                return (torch.zeros((1, 64, 64, 3), dtype=torch.float32),)
        
        elif images is not None:
            # Handle image batch input (from VHS or other sources)
            # Handle different input shapes
            if len(images.shape) != 4:
                # Single image, return as-is
                return (images,)
            
            batch_size = images.shape[0]
            
            if batch_size == 0:
                # Empty batch, return zero tensor
                empty_image = torch.zeros((1, 64, 64, 3), dtype=images.dtype, device=images.device)
                return (empty_image,)
            
            # Get the last image in the batch (keep as single image with batch dim=1)
            last_image = images[-1:] 
            
            return (last_image,)
        
        else:
            # No input provided, return default
            return (torch.zeros((1, 64, 64, 3), dtype=torch.float32),)

class ApexGetFrame:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "frame_index": ("INT", {"default": 0, "min": 0, "max": 9999}),
            },
            "optional": {
                "wrap_around": ("BOOLEAN", {"default": True}),
            }
        }

    CATEGORY = "Apex Artist/Image"
    RETURN_TYPES = ("IMAGE", "INT", "INT")
    RETURN_NAMES = ("selected_image", "actual_index", "total_count")
    FUNCTION = "get_frame"

    def get_frame(self, images, frame_index, wrap_around=True):
        """
        Get a specific frame from a batch of images
        
        Args:
            images: Batch of images tensor [batch, height, width, channels]
            frame_index: Index of frame to extract
            wrap_around: If True, wrap index around batch size
            
        Returns:
            Tuple of (selected_image, actual_index, total_count)
        """
        
        # Get batch information
        if len(images.shape) != 4:
            # Single image, return as-is
            return (images, 0, 1)
        
        batch_size = images.shape[0]
        
        if batch_size == 0:
            # Empty batch, return zero tensor
            empty_image = torch.zeros((1, 64, 64, 3), dtype=images.dtype, device=images.device)
            return (empty_image, -1, 0)
        
        # Handle index wrapping or clamping
        if wrap_around:
            actual_index = frame_index % batch_size
        else:
            actual_index = max(0, min(frame_index, batch_size - 1))
        
        # Get the selected image
        selected_image = images[actual_index:actual_index+1]  # Keep batch dimension
        
        return (selected_image, actual_index, batch_size)

class ApexBatchInfo:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
            }
        }

    CATEGORY = "Apex Artist/Image"
    RETURN_TYPES = ("INT", "INT", "INT", "INT")
    RETURN_NAMES = ("batch_size", "height", "width", "channels")
    FUNCTION = "get_batch_info"

    def get_batch_info(self, images):
        """
        Get information about an image batch
        
        Args:
            images: Batch of images tensor [batch, height, width, channels]
            
        Returns:
            Tuple of (batch_size, height, width, channels)
        """
        
        if len(images.shape) == 4:
            batch_size, height, width, channels = images.shape
        elif len(images.shape) == 3:
            # Single image without batch dimension
            height, width, channels = images.shape
            batch_size = 1
        else:
            # Invalid shape
            return (0, 0, 0, 0)
        
        return (batch_size, height, width, channels)

# Node registration
NODE_CLASS_MAPPINGS = {
    "ApexLastFrame": ApexLastFrame,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ApexLastFrame": "Apex Last Frame",
}