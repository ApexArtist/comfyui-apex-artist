#!/usr/bin/env python3
"""
Apex Sharpen Node - Professional image sharpening with multiple algorithms
Features unsharp mask, structure-aware sharpening, and edge enhancement
"""
import torch
import torch.nn.functional as F
from .apex_utils import gaussian_blur, validate_image_tensor, validate_radius, apply_mask as utils_apply_mask

class ApexSharpen:
    """
    Professional image sharpening node with multiple algorithms
    Includes unsharp mask, edge enhancement, and structure-aware sharpening
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "algorithm": ([
                    "Unsharp Mask",
                    "High Pass Filter", 
                    "Edge Enhancement",
                    "Structure Aware",
                    "Laplacian Sharpen",
                    "Multi-Scale Sharpen",
                    "Luminance Sharpen",
                    "Detail Enhancement"
                ], {"default": "Unsharp Mask"}),
                "strength": ("FLOAT", {
                    "default": 1.0, 
                    "min": 0.0, 
                    "max": 5.0, 
                    "step": 0.1
                }),
            },
            "optional": {
                "radius": ("FLOAT", {
                    "default": 1.0, 
                    "min": 0.1, 
                    "max": 10.0, 
                    "step": 0.1
                }),
                "threshold": ("FLOAT", {
                    "default": 0.0, 
                    "min": 0.0, 
                    "max": 1.0, 
                    "step": 0.01
                }),
                "preserve_highlights": ("BOOLEAN", {"default": True}),
                "preserve_shadows": ("BOOLEAN", {"default": True}),
                "edge_protection": ("FLOAT", {
                    "default": 0.0,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.1
                }),
                "fine_detail": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 3.0,
                    "step": 0.1
                }),
                "mask": ("MASK",),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("sharpened_image", "sharpen_info")
    FUNCTION = "apply_sharpening"
    CATEGORY = "Apex Artist/Image/Filters"
    
    def apply_sharpening(self, image, algorithm="Unsharp Mask", strength=1.0, radius=1.0, 
                        threshold=0.0, preserve_highlights=True, preserve_shadows=True,
                        edge_protection=0.0, fine_detail=1.0, mask=None):
        
        # Validate inputs
        validate_image_tensor(image, "image")
        radius = validate_radius(radius, min_val=0.1, max_val=10.0)
        
        device = image.device
        batch_size = image.shape[0]
        
        # Apply selected sharpening algorithm
        if algorithm == "Unsharp Mask":
            result = self._unsharp_mask(image, strength, radius, threshold)
        elif algorithm == "High Pass Filter":
            result = self._high_pass_filter(image, strength, radius)
        elif algorithm == "Edge Enhancement":
            result = self._edge_enhancement(image, strength, radius)
        elif algorithm == "Structure Aware":
            result = self._structure_aware_sharpen(image, strength, radius, edge_protection)
        elif algorithm == "Laplacian Sharpen":
            result = self._laplacian_sharpen(image, strength, fine_detail)
        elif algorithm == "Multi-Scale Sharpen":
            result = self._multi_scale_sharpen(image, strength, fine_detail)
        elif algorithm == "Luminance Sharpen":
            result = self._luminance_sharpen(image, strength, radius)
        elif algorithm == "Detail Enhancement":
            result = self._detail_enhancement(image, strength, radius, fine_detail)
        else:
            result = image
        
        # Apply tone protection
        if preserve_highlights or preserve_shadows:
            result = self._apply_tone_protection(image, result, preserve_highlights, preserve_shadows)
        
        # Apply mask if provided
        if mask is not None:
            result = utils_apply_mask(image, result, mask)
        
        # Generate info
        info = f"{algorithm} | Strength: {strength:.1f} | Radius: {radius:.1f}"
        if threshold > 0:
            info += f" | Threshold: {threshold:.2f}"
        
        return (torch.clamp(result, 0, 1), info)
    
    def _unsharp_mask(self, image, strength, radius, threshold):
        """Classic unsharp mask sharpening"""
        device = image.device
        batch, height, width, channels = image.shape
        
        # Create Gaussian blur for the mask using shared utility
        blurred = gaussian_blur(image, radius)
        
        # Create unsharp mask
        mask = image - blurred
        
        # Apply threshold (only sharpen areas with sufficient contrast)
        if threshold > 0:
            mask_magnitude = torch.sqrt(torch.sum(mask**2, dim=-1, keepdim=True))
            threshold_mask = torch.where(mask_magnitude > threshold, 1.0, 0.0)
            mask = mask * threshold_mask
        
        # Apply sharpening
        result = image + mask * strength
        
        return result
    
    def _high_pass_filter(self, image, strength, radius):
        """High-pass filter sharpening"""
        # Create high-pass filter by subtracting low-pass (blur) using shared utility
        blurred = gaussian_blur(image, radius)
        high_pass = image - blurred
        
        # Apply with overlay blend mode for natural look
        result = image + high_pass * strength * 0.5
        
        return result
    
    def _edge_enhancement(self, image, strength, radius):
        """Edge-based sharpening using Sobel operators"""
        device = image.device
        
        # Convert to grayscale for edge detection
        gray = 0.299 * image[..., 0:1] + 0.587 * image[..., 1:2] + 0.114 * image[..., 2:3]
        
        # Sobel edge detection
        sobel_x = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], 
                              device=device, dtype=torch.float32).unsqueeze(0).unsqueeze(0) / 8.0
        sobel_y = torch.tensor([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], 
                              device=device, dtype=torch.float32).unsqueeze(0).unsqueeze(0) / 8.0
        
        gray_reshaped = gray.permute(0, 3, 1, 2)
        edges_x = F.conv2d(gray_reshaped, sobel_x, padding=1)
        edges_y = F.conv2d(gray_reshaped, sobel_y, padding=1)
        
        # Calculate edge magnitude
        edge_magnitude = torch.sqrt(edges_x**2 + edges_y**2)
        edge_magnitude = edge_magnitude.permute(0, 2, 3, 1)
        
        # Apply edge-based sharpening
        # Create sharpening kernel
        sharpen_kernel = torch.tensor([
            [0, -1, 0], 
            [-1, 5, -1], 
            [0, -1, 0]
        ], device=device, dtype=torch.float32).unsqueeze(0).unsqueeze(0)
        
        batch, height, width, channels = image.shape
        img_reshaped = image.permute(0, 3, 1, 2).reshape(-1, 1, height, width)
        
        sharpened = F.conv2d(img_reshaped, sharpen_kernel, padding=1)
        sharpened = sharpened.reshape(batch, channels, height, width).permute(0, 2, 3, 1)
        
        # Blend based on edge strength
        edge_mask = edge_magnitude * radius
        result = image * (1 - edge_mask * strength) + sharpened * (edge_mask * strength)
        
        return result
    
    def _structure_aware_sharpen(self, image, strength, radius, edge_protection):
        """Structure-aware sharpening that protects smooth areas"""
        device = image.device
        
        # Calculate local variance to identify texture vs smooth areas
        kernel_size = max(3, int(radius * 2) + 1)
        kernel = torch.ones(1, 1, kernel_size, kernel_size, device=device) / (kernel_size**2)
        
        # Convert to grayscale for structure analysis
        gray = 0.299 * image[..., 0:1] + 0.587 * image[..., 1:2] + 0.114 * image[..., 2:3]
        gray_reshaped = gray.permute(0, 3, 1, 2)
        
        # Calculate local mean and variance
        local_mean = F.conv2d(gray_reshaped, kernel, padding=kernel_size//2)
        local_var = F.conv2d(gray_reshaped**2, kernel, padding=kernel_size//2) - local_mean**2
        
        # Create structure mask (high variance = texture, low variance = smooth)
        structure_mask = torch.sigmoid((local_var - 0.01) * 50)  # Adjust sensitivity
        structure_mask = structure_mask.permute(0, 2, 3, 1)
        
        # Apply edge protection
        if edge_protection > 0:
            structure_mask = structure_mask * (1 - edge_protection) + edge_protection
        
        # Apply unsharp mask only in textured areas using shared utility
        blurred = gaussian_blur(image, radius)
        mask = image - blurred
        result = image + mask * strength * structure_mask
        
        return result
    
    def _laplacian_sharpen(self, image, strength, fine_detail):
        """Laplacian-based sharpening for fine detail enhancement"""
        device = image.device
        
        # Laplacian kernel for edge detection
        laplacian_kernel = torch.tensor([
            [0, -1, 0], 
            [-1, 4, -1], 
            [0, -1, 0]
        ], device=device, dtype=torch.float32).unsqueeze(0).unsqueeze(0) * fine_detail
        
        batch, height, width, channels = image.shape
        img_reshaped = image.permute(0, 3, 1, 2).reshape(-1, 1, height, width)
        
        laplacian = F.conv2d(img_reshaped, laplacian_kernel, padding=1)
        laplacian = laplacian.reshape(batch, channels, height, width).permute(0, 2, 3, 1)
        
        # Apply sharpening
        result = image + laplacian * strength * 0.1
        
        return result
    
    def _multi_scale_sharpen(self, image, strength, fine_detail):
        """Multi-scale sharpening for different detail levels"""
        # Create multiple scales
        scale1 = self._unsharp_mask(image, strength * 0.4, 0.5, 0.0)  # Fine details
        scale2 = self._unsharp_mask(image, strength * 0.4, 1.5, 0.0)  # Medium details
        scale3 = self._unsharp_mask(image, strength * 0.2, 3.0, 0.0)  # Large details
        
        # Combine scales with fine detail control
        result = image * 0.4 + scale1 * 0.3 * fine_detail + scale2 * 0.2 + scale3 * 0.1
        
        return result
    
    def _luminance_sharpen(self, image, strength, radius):
        """Sharpen only the luminance channel to preserve color"""
        device = image.device
        
        # Convert to YUV color space
        y = 0.299 * image[..., 0:1] + 0.587 * image[..., 1:2] + 0.114 * image[..., 2:3]
        u = -0.14713 * image[..., 0:1] - 0.28886 * image[..., 1:2] + 0.436 * image[..., 2:3]
        v = 0.615 * image[..., 0:1] - 0.51499 * image[..., 1:2] - 0.10001 * image[..., 2:3]
        
        # Sharpen only luminance
        y_sharpened = self._unsharp_mask(y, strength, radius, 0.0)
        
        # Convert back to RGB
        r = y_sharpened + 1.13983 * v
        g = y_sharpened - 0.39465 * u - 0.58060 * v
        b = y_sharpened + 2.03211 * u
        
        result = torch.cat([r, g, b], dim=-1)
        
        return result
    
    def _detail_enhancement(self, image, strength, radius, fine_detail):
        """Advanced detail enhancement with frequency separation"""
        # Create different frequency layers using shared utility
        blur_low = gaussian_blur(image, radius * 2)      # Low frequency
        blur_mid = gaussian_blur(image, radius)          # Mid frequency
        
        # Extract frequency bands
        high_freq = image - blur_mid                           # High frequency details
        mid_freq = blur_mid - blur_low                         # Mid frequency details
        
        # Enhance different frequencies
        enhanced_high = high_freq * (1 + strength * fine_detail)
        enhanced_mid = mid_freq * (1 + strength * 0.5)
        
        # Recombine
        result = blur_low + enhanced_mid + enhanced_high
        
        return result
    
    
    def _apply_tone_protection(self, original, sharpened, preserve_highlights, preserve_shadows):
        """Protect highlights and/or shadows from over-sharpening"""
        if not preserve_highlights and not preserve_shadows:
            return sharpened
        
        # Calculate luminance
        luminance = 0.299 * original[..., 0:1] + 0.587 * original[..., 1:2] + 0.114 * original[..., 2:3]
        
        # Create protection masks
        result = sharpened
        
        if preserve_highlights:
            # Protect bright areas
            highlight_mask = torch.sigmoid((luminance - 0.8) * 10)
            result = result * (1 - highlight_mask) + original * highlight_mask
        
        if preserve_shadows:
            # Protect dark areas
            shadow_mask = torch.sigmoid((0.2 - luminance) * 10)
            result = result * (1 - shadow_mask) + original * shadow_mask

        return result
    
