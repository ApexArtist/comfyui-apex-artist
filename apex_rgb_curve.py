"""
Apex RGB Curve Node - Professional RGB curve adjustment for ComfyUI
Photoshop-style RGB curves with interactive web GUI
"""

import torch
import torch.nn.functional as F
import numpy as np
import json

class ApexRGBCurve:
    """RGB curve adjustment node with Photoshop-style interface"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            },
            "optional": {
                "curve_data": ("STRING", {
                    "default": "", 
                    "multiline": False
                }),
                "preserve_luminosity": ("BOOLEAN", {"default": True}),
                "gamma_correction": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.1,
                    "max": 3.0,
                    "step": 0.1
                }),
                "processing_space": (["linear", "srgb"], {"default": "linear"}),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "IMAGE", "STRING")
    RETURN_NAMES = ("processed_image", "histogram_image", "histogram_data")
    FUNCTION = "apply_rgb_curves"
    CATEGORY = "Apex Artist/Color"
    
    def apply_rgb_curves(self, image, curve_data="", preserve_luminosity=True, gamma_correction=1.0, processing_space="linear"):
        """
        Optimized: Apply RGB curves to a batch of images using vectorized torch operations (GPU-friendly).
        """
        try:
            curves = self._parse_curves(curve_data)
            lut_res = 4096
            device = image.device
            # Create LUTs as torch tensors on the same device as image
            rgb_lut = torch.from_numpy(self._create_lut_highres(curves["rgb"], lut_res)).to(device)
            red_lut = torch.from_numpy(self._create_lut_highres(curves["red"], lut_res)).to(device)
            green_lut = torch.from_numpy(self._create_lut_highres(curves["green"], lut_res)).to(device)
            blue_lut = torch.from_numpy(self._create_lut_highres(curves["blue"], lut_res)).to(device)

            img = image
            if processing_space == "srgb":
                img = torch.where(img <= 0.04045, img / 12.92, ((img + 0.055) / 1.055) ** 2.4)

            # Store original luminosity if preserving
            if preserve_luminosity:
                original_lum = 0.299 * img[...,0] + 0.587 * img[...,1] + 0.114 * img[...,2]

            # Vectorized LUT application for all images in batch
            # Apply RGB curve to all channels
            indices = (img * (lut_res-1)).clamp(0, lut_res-1).long()
            img = torch.stack([rgb_lut[indices[...,c]] for c in range(3)], dim=-1)
            # Apply individual channel curves
            img = torch.stack([
                red_lut[ (img[...,0] * (lut_res-1)).clamp(0, lut_res-1).long() ],
                green_lut[ (img[...,1] * (lut_res-1)).clamp(0, lut_res-1).long() ],
                blue_lut[ (img[...,2] * (lut_res-1)).clamp(0, lut_res-1).long() ]
            ], dim=-1)

            # Apply gamma correction
            if gamma_correction != 1.0:
                img = torch.pow(img.clamp(0, 1), 1.0 / gamma_correction)

            # Restore luminosity if preserving
            if preserve_luminosity:
                new_lum = 0.299 * img[...,0] + 0.587 * img[...,1] + 0.114 * img[...,2]
                ratio = torch.ones_like(new_lum)
                mask = new_lum != 0
                ratio[mask] = original_lum[mask] / new_lum[mask]
                img = img * ratio.unsqueeze(-1)

            img = img.clamp(0, 1)

            # Optionally convert back to sRGB
            if processing_space == "srgb":
                img = torch.where(img <= 0.0031308, img * 12.92, 1.055 * (img ** (1/2.4)) - 0.055)

            # Generate histogram from the first processed image
            histogram_image, histogram_data = self._generate_histogram(img[0])
            return (img, histogram_image, histogram_data)
        except Exception as e:
            print(f"ApexRGBCurve error: {e}")
            return (image, image, f"Error: {e}")

    def srgb_to_linear(self, img):
        return torch.where(
            img <= 0.04045,
            img / 12.92,
            ((img + 0.055) / 1.055) ** 2.4
        )

    def linear_to_srgb(self, img):
        return torch.where(
            img <= 0.0031308,
            img * 12.92,
            1.055 * torch.pow(img, 1/2.4) - 0.055
        )

    # _apply_curves_highbit is now replaced by vectorized torch logic in apply_rgb_curves

    def _create_lut_highres(self, points, lut_res=4096):
        """Create high-res LUT for float32 processing"""
        lut = np.zeros(lut_res, dtype=np.float32)
        if len(points) < 2:
            return np.linspace(0, 1, lut_res, dtype=np.float32)
        points = sorted(points, key=lambda p: p[0])
        for i in range(lut_res):
            x = float(i) / (lut_res-1) * 255.0
            # Find surrounding points
            left, right = points[0], points[-1]
            for j in range(len(points) - 1):
                if points[j][0] <= x <= points[j + 1][0]:
                    left, right = points[j], points[j + 1]
                    break
            # Linear interpolation
            if left[0] == right[0]:
                lut[i] = left[1] / 255.0
            else:
                t = (x - left[0]) / (right[0] - left[0])
                lut[i] = (left[1] + t * (right[1] - left[1])) / 255.0
        return lut
    
    def _parse_curves(self, curve_data):
        """Parse curve data from GUI"""
        default = {
            "rgb": [[0, 0], [255, 255]],
            "red": [[0, 0], [255, 255]],
            "green": [[0, 0], [255, 255]],
            "blue": [[0, 0], [255, 255]]
        }
        
        if not curve_data:
            return default
            
        try:
            parsed = json.loads(curve_data)
            # Handle both uppercase and lowercase keys from GUI
            result = default.copy()
            
            # Map GUI keys (uppercase) to processing keys (lowercase)
            key_mapping = {
                "RGB": "rgb",
                "Red": "red", 
                "Green": "green",
                "Blue": "blue"
            }
            
            for gui_key, process_key in key_mapping.items():
                if gui_key in parsed:
                    result[process_key] = parsed[gui_key]
                elif process_key in parsed:
                    result[process_key] = parsed[process_key]
                    
            return result
            
        except:
            return default
    
    def _generate_histogram(self, image_tensor):
        """Generate histogram visualization and data from image tensor"""
        # Convert tensor to numpy for histogram calculation
        img_np = (image_tensor.detach().cpu().numpy() * 255).astype(np.uint8)
        height, width, channels = img_np.shape
        
        # Calculate histograms for each channel
        hist_red = np.histogram(img_np[:, :, 0], bins=256, range=(0, 256))[0]
        hist_green = np.histogram(img_np[:, :, 1], bins=256, range=(0, 256))[0]
        hist_blue = np.histogram(img_np[:, :, 2], bins=256, range=(0, 256))[0]
        
        # Calculate luminance histogram
        luminance = 0.299 * img_np[:, :, 0] + 0.587 * img_np[:, :, 1] + 0.114 * img_np[:, :, 2]
        hist_luma = np.histogram(luminance, bins=256, range=(0, 256))[0]
        
        # Create histogram visualization
        hist_image = self._create_histogram_image(hist_red, hist_green, hist_blue, hist_luma)
        
        # Create histogram data
        histogram_data = {
            "red": hist_red.tolist(),
            "green": hist_green.tolist(), 
            "blue": hist_blue.tolist(),
            "luminance": hist_luma.tolist(),
            "statistics": {
                "red": self._calculate_channel_stats(hist_red),
                "green": self._calculate_channel_stats(hist_green),
                "blue": self._calculate_channel_stats(hist_blue),
                "luminance": self._calculate_channel_stats(hist_luma)
            },
            "image_info": {
                "width": width,
                "height": height,
                "total_pixels": width * height
            }
        }
        
        return hist_image, json.dumps(histogram_data, indent=2)
    
    def _create_histogram_image(self, hist_red, hist_green, hist_blue, hist_luma):
        """Create a visual histogram image"""
        # Create histogram visualization (512x256 image)
        hist_width = 512
        hist_height = 256
        
        # Create canvas
        hist_img = np.zeros((hist_height, hist_width, 3), dtype=np.float32)
        
        # Normalize histograms
        max_val = max(np.max(hist_red), np.max(hist_green), np.max(hist_blue), np.max(hist_luma))
        if max_val == 0:
            max_val = 1
        
        # Draw background grid
        for i in range(0, hist_width, hist_width // 8):
            hist_img[:, i:i+1, :] = 0.1
        for i in range(0, hist_height, hist_height // 4):
            hist_img[i:i+1, :, :] = 0.1
        
        # Draw histograms
        bin_width = hist_width / 256
        
        for i in range(256):
            x_start = int(i * bin_width)
            x_end = int((i + 1) * bin_width)
            
            # Red channel
            red_height = int((hist_red[i] / max_val) * (hist_height - 10))
            if red_height > 0:
                hist_img[hist_height-red_height:hist_height, x_start:x_end, 0] = 0.8
            
            # Green channel
            green_height = int((hist_green[i] / max_val) * (hist_height - 10))
            if green_height > 0:
                hist_img[hist_height-green_height:hist_height, x_start:x_end, 1] = 0.8
            
            # Blue channel
            blue_height = int((hist_blue[i] / max_val) * (hist_height - 10))
            if blue_height > 0:
                hist_img[hist_height-blue_height:hist_height, x_start:x_end, 2] = 0.8
            
            # Luminance (white overlay)
            luma_height = int((hist_luma[i] / max_val) * (hist_height - 10))
            if luma_height > 0:
                y_start = hist_height - luma_height
                y_end = hist_height
                # Add white luminance histogram with transparency
                hist_img[y_start:y_end, x_start:x_end, :] += 0.3
                hist_img[y_start:y_end, x_start:x_end, :] = np.clip(hist_img[y_start:y_end, x_start:x_end, :], 0, 1)
        
        # Convert to tensor and add batch dimension
        hist_tensor = torch.from_numpy(hist_img).unsqueeze(0)
        
        return hist_tensor
    
    def _calculate_channel_stats(self, histogram):
        """Calculate statistics for a histogram channel"""
        total_pixels = np.sum(histogram)
        if total_pixels == 0:
            return {
                "mean": 0.0,
                "median": 0,
                "mode": 0,
                "std": 0.0,
                "min": 0,
                "max": 255,
                "percentile_25": 0,
                "percentile_75": 255
            }
        
        # Calculate mean
        weighted_sum = np.sum(np.arange(256) * histogram)
        mean = weighted_sum / total_pixels
        
        # Calculate median and percentiles
        cumsum = np.cumsum(histogram)
        median = np.argmax(cumsum >= total_pixels / 2)
        percentile_25 = np.argmax(cumsum >= total_pixels * 0.25)
        percentile_75 = np.argmax(cumsum >= total_pixels * 0.75)
        
        # Calculate mode
        mode = np.argmax(histogram)
        
        # Calculate standard deviation
        variance = np.sum(((np.arange(256) - mean) ** 2) * histogram) / total_pixels
        std = np.sqrt(variance)
        
        # Find actual min and max values
        min_val = np.argmax(histogram > 0)
        max_val = 255 - np.argmax(histogram[::-1] > 0)
        
        return {
            "mean": float(mean),
            "median": int(median),
            "mode": int(mode),
            "std": float(std),
            "min": int(min_val),
            "max": int(max_val),
            "percentile_25": int(percentile_25),
            "percentile_75": int(percentile_75)
        }
    
    # _apply_curves (legacy, not used)
    
    def _create_lut(self, points):
        """Create 256-element lookup table from curve points"""
        lut = np.zeros(256, dtype=np.float32)
        
        if len(points) < 2:
            return np.arange(256, dtype=np.float32)
        
        # Sort points by x coordinate
        points = sorted(points, key=lambda p: p[0])
        
        for i in range(256):
            x = float(i)
            
            # Find surrounding points
            left, right = points[0], points[-1]
            for j in range(len(points) - 1):
                if points[j][0] <= x <= points[j + 1][0]:
                    left, right = points[j], points[j + 1]
                    break
            
            # Linear interpolation
            if left[0] == right[0]:
                lut[i] = left[1]
            else:
                t = (x - left[0]) / (right[0] - left[0])
                lut[i] = left[1] + t * (right[1] - left[1])
        
        return lut
