import os
import hashlib
import numpy as np
import torch
from PIL import Image, ImageOps, ImageSequence
import folder_paths
import node_helpers
import json

class ApexLoadImage:
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        files = folder_paths.filter_files_content_types(files, ["image"])
        return {
            "required": {
                "image": (sorted(files), {"image_upload": True}),
                "batch_mode": (["single", "increment", "folder_sequence", "custom_list"], {"default": "single"}),
                "max_size": (["None", "256", "512", "768", "1024", "1280", "1344", "1536", "1920", "2048", "2560", "3072", "3840", "4096"], {"default": "None"}),
            },
            "optional": {
                "folder_filter": ("STRING", {"default": "", "placeholder": "e.g., portrait_, img_001"}),
                "custom_image_list": ("STRING", {"multiline": True, "default": "", "placeholder": "Enter image filenames, one per line"}),
                "batch_index": ("INT", {"default": 0, "min": 0, "max": 9999}),
            }
        }

    CATEGORY = "Apex Artist/Image"
    RETURN_TYPES = ("IMAGE", "MASK", "INT", "INT", "STRING")
    RETURN_NAMES = ("image", "mask", "width", "height", "filename")
    FUNCTION = "load_image"

    def __init__(self):
        self.counter_file = os.path.join(folder_paths.get_temp_directory(), "apex_load_image_counter.json")
        self.load_counter()

    def load_counter(self):
        """Load the counter from file or initialize to 0"""
        try:
            if os.path.exists(self.counter_file):
                with open(self.counter_file, 'r') as f:
                    data = json.load(f)
                    self.counter = data.get('counter', 0)
            else:
                self.counter = 0
        except:
            self.counter = 0

    def save_counter(self):
        """Save the counter to file"""
        try:
            with open(self.counter_file, 'w') as f:
                json.dump({'counter': self.counter}, f)
        except:
            pass

    def get_filtered_files(self, folder_filter=""):
        """Get filtered list of image files"""
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        files = folder_paths.filter_files_content_types(files, ["image"])
        
        if folder_filter.strip():
            # Filter files that contain any of the filter terms
            filter_terms = [term.strip() for term in folder_filter.split(",") if term.strip()]
            filtered_files = []
            for file in files:
                if any(term.lower() in file.lower() for term in filter_terms):
                    filtered_files.append(file)
            files = filtered_files
        
        return sorted(files)

    def get_custom_list(self, custom_image_list):
        """Parse custom image list from text input"""
        if not custom_image_list.strip():
            return []
        
        # Parse lines and validate files exist
        input_dir = folder_paths.get_input_directory()
        lines = [line.strip() for line in custom_image_list.split('\n') if line.strip()]
        valid_files = []
        
        for filename in lines:
            if os.path.isfile(os.path.join(input_dir, filename)):
                valid_files.append(filename)
        
        return valid_files

    def get_next_image(self, image, batch_mode, batch_index, folder_filter="", custom_image_list=""):
        """Get the next image filename based on batch mode"""
        if batch_mode == "single":
            return image
        
        # Determine which file list to use
        if batch_mode == "folder_sequence":
            files = self.get_filtered_files(folder_filter)
        elif batch_mode == "custom_list":
            files = self.get_custom_list(custom_image_list)
        else:  # increment mode (all files)
            input_dir = folder_paths.get_input_directory()
            files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
            files = folder_paths.filter_files_content_types(files, ["image"])
            files = sorted(files)
        
        if not files:
            return image
        
        if batch_index > 0:
            # Manual batch index override
            index = batch_index % len(files)
            return files[index]
        else:
            # Auto increment mode
            index = self.counter % len(files)
            selected_image = files[index]
            self.counter += 1
            self.save_counter()
            return selected_image

    def load_image(self, image, batch_mode="single", max_size="None", folder_filter="", custom_image_list="", batch_index=0):
        # Get the actual image to load based on batch mode
        actual_image = self.get_next_image(image, batch_mode, batch_index, folder_filter, custom_image_list)
        image_path = folder_paths.get_annotated_filepath(actual_image)
        
        # Safe open: catch errors from PIL and return empty tensors instead of raising
        try:
            img = node_helpers.pillow(Image.open, image_path)
        except Exception as e:
            print(f"[Apex Load Image] Failed to open image {image_path}: {e}")
            # Return an empty placeholder image/mask to avoid crashing downstream
            empty_image = torch.zeros((1, 1, 1, 3), dtype=torch.float32)
            empty_mask = torch.zeros((1, 1, 1), dtype=torch.float32)
            return (empty_image, empty_mask, 0, 0, actual_image)
        
        output_images = []
        output_masks = []
        w, h = None, None
        
        excluded_formats = ['MPO']
        
        for i in ImageSequence.Iterator(img):
            i = node_helpers.pillow(ImageOps.exif_transpose, i)
            
            if i.mode == 'I':
                i = i.point(lambda i: i * (1 / 255))
            image_pil = i.convert("RGB")
            
            # Apply max_size if specified (maintain aspect ratio)
            if max_size != "None":
                max_dimension = int(max_size)
                original_w, original_h = image_pil.size
                
                # Calculate new dimensions maintaining aspect ratio
                if original_w > original_h:
                    # Landscape: limit width
                    if original_w > max_dimension:
                        new_w = max_dimension
                        new_h = int((original_h * max_dimension) / original_w)
                    else:
                        new_w, new_h = original_w, original_h
                else:
                    # Portrait or square: limit height
                    if original_h > max_dimension:
                        new_h = max_dimension
                        new_w = int((original_w * max_dimension) / original_h)
                    else:
                        new_w, new_h = original_w, original_h
                
                # Automatically make smaller dimension divisible by 32
                divisor = 32
                smaller_dim = min(new_w, new_h)
                if smaller_dim > divisor:
                    if new_w < new_h:
                        # Width is smaller, make it divisible by 32
                        new_w = (new_w // divisor) * divisor
                    else:
                        # Height is smaller, make it divisible by 32
                        new_h = (new_h // divisor) * divisor
                
                # Only resize if dimensions changed
                if (new_w, new_h) != (original_w, original_h):
                    # Use Lanczos for high quality resizing. Older Pillow versions may not have Image.Resampling
                    try:
                        resample = Image.Resampling.LANCZOS
                    except Exception:
                        resample = Image.LANCZOS
                    image_pil = image_pil.resize((new_w, new_h), resample)
            
            if len(output_images) == 0:
                w = image_pil.size[0]
                h = image_pil.size[1]
            
            if image_pil.size[0] != w or image_pil.size[1] != h:
                continue
            
            image_np = np.array(image_pil).astype(np.float32) / 255.0
            image_tensor = torch.from_numpy(image_np)[None,]
            
            if 'A' in i.getbands():
                mask_np = np.array(i.getchannel('A')).astype(np.float32) / 255.0
                mask = torch.from_numpy(mask_np).to(dtype=torch.float32, device='cpu')
                mask = 1.0 - mask
            elif i.mode == 'P' and 'transparency' in i.info:
                mask_np = np.array(i.convert('RGBA').getchannel('A')).astype(np.float32) / 255.0
                mask = torch.from_numpy(mask_np).to(dtype=torch.float32, device='cpu')
                mask = 1.0 - mask
            else:
                mask = torch.zeros((h, w), dtype=torch.float32, device="cpu")
            
            output_images.append(image_tensor)
            output_masks.append(mask.unsqueeze(0))
        
        if len(output_images) > 1 and img.format not in excluded_formats:
            output_image = torch.cat(output_images, dim=0)
            output_mask = torch.cat(output_masks, dim=0)
        else:
            # Guard: if no frames were collected (corrupt image), return empty placeholders
            if not output_images:
                empty_image = torch.zeros((1, 1, 1, 3), dtype=torch.float32)
                empty_mask = torch.zeros((1, 1, 1), dtype=torch.float32)
                return (empty_image, empty_mask, 0, 0, actual_image)
            output_image = output_images[0]
            output_mask = output_masks[0]
        
        return (output_image, output_mask, w, h, actual_image)

    @classmethod
    def IS_CHANGED(s, image, batch_mode="single", max_size="None", folder_filter="", custom_image_list="", batch_index=0):
        # For increment modes, always trigger change to load next image
        if batch_mode in ["increment", "folder_sequence", "custom_list"]:
            import time
            return str(time.time())
        
        image_path = folder_paths.get_annotated_filepath(image)
        m = hashlib.sha256()
        with open(image_path, 'rb') as f:
            m.update(f.read())
        # Include resize parameters in hash
        m.update(f"{max_size}_{batch_mode}_{folder_filter}_{custom_image_list}_{batch_index}".encode())
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(s, image, **kwargs):
        if not folder_paths.exists_annotated_filepath(image):
            return "Invalid image file: {}".format(image)
        return True

# Node registration
NODE_CLASS_MAPPINGS = {
    "ApexLoadImage": ApexLoadImage
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ApexLoadImage": "Apex Load Image"
}