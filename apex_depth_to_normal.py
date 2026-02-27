#!/usr/bin/env python3
"""
Apex Depth to Normal Node - Professional depth map to normal map conversion
Specialized for converting depth maps (DepthAnything, MiDaS, etc.) to high-quality normal maps
"""

import torch
import torch.nn.functional as F
import numpy as np

class ApexDepthToNormal:
    """
    Professional depth map to normal map converter
    
    Optimized specifically for depth maps from:
    - DepthAnything v2
    - MiDaS
    - Other depth estimation models
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "depth_map": ("IMAGE",),
                "strength": ("FLOAT", {
                    "default": 12.0, 
                    "min": 0.1, 
                    "max": 30.0, 
                    "step": 0.1
                }),
            },
            "optional": {
                "invert": ("BOOLEAN", {"default": False}),
                "auto_invert_depth": ("BOOLEAN", {"default": False}),
                "blur": ("FLOAT", {
                    "default": 0.0, 
                    "min": 0.0, 
                    "max": 3.0, 
                    "step": 0.1
                }),
                "enhance_details": ("FLOAT", {
                    "default": 0.0,
                    "min": 0.0,
                    "max": 3.0,
                    "step": 0.1
                }),
            }
        } 
    
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("normal_map", "info")
    FUNCTION = "depth_to_normal"
    CATEGORY = "Apex Artist/Compositing"
    
    def depth_to_normal(self, depth_map, strength=12.0, invert=False, auto_invert_depth=False, blur=0.0, enhance_details=0.0):
        print("ApexDepthToNormal: Processing depth map")
        
        # Convert to grayscale if RGB
        if depth_map.shape[-1] == 3:
            # Use luminance formula
            gray = 0.299 * depth_map[..., 0:1] + 0.587 * depth_map[..., 1:2] + 0.114 * depth_map[..., 2:3]
        else:
            gray = depth_map
        
        # Smart depth map inversion detection
        should_invert = invert
        if auto_invert_depth and not invert:
            # Check if this looks like an inverted depth map
            h, w = gray.shape[1], gray.shape[2]
            center_region = gray[:, h//4:3*h//4, w//4:3*w//4, :]
            
            # Sample edge regions
            edge_samples = []
            edge_samples.append(gray[:, :h//8, :, :])  # top edge
            edge_samples.append(gray[:, -h//8:, :, :])  # bottom edge
            edge_samples.append(gray[:, :, :w//8, :])  # left edge
            edge_samples.append(gray[:, :, -w//8:, :])  # right edge
            
            center_mean = torch.mean(center_region)
            edge_mean = torch.mean(torch.stack([torch.mean(edge) for edge in edge_samples]))
            
            # If center is significantly darker than edges, likely inverted depth
            if center_mean < edge_mean - 0.2:
                should_invert = True
                print("ApexDepthToNormal: Auto-detected inverted depth map, applying inversion")
        
        # Invert if requested or auto-detected
        if should_invert:
            gray = 1.0 - gray
        
        # Apply depth-specific preprocessing
        gray = self._preprocess_depth(gray, enhance_details)
        
        # Apply blur if requested
        if blur > 0.0:
            gray = self._apply_blur(gray, blur)
        
        # Calculate gradients optimized for depth maps
        dx, dy = self._calculate_gradients(gray, strength)
        
        # Create normal map
        normal_map = self._create_normal_map(dx, dy)
        
        # Generate info about processing
        invert_status = ""
        if should_invert and auto_invert_depth and not invert:
            invert_status = " | Auto-Inverted"
        elif should_invert:
            invert_status = " | Inverted"
            
        info = f"Depth to Normal | Strength: {strength:.1f} | Details: {enhance_details:.1f}{invert_status}"
        
        return (normal_map, info)
    
    def _preprocess_depth(self, gray, enhance_details):
        """Specialized preprocessing for depth maps"""
        # Histogram stretching for better dynamic range
        min_val = torch.min(gray)
        max_val = torch.max(gray)
        range_val = max_val - min_val + 1e-8
        stretched = (gray - min_val) / range_val
        
        # Apply adaptive histogram equalization if details enhancement is requested
        if enhance_details > 0:
            kernel_size = 15
            kernel = torch.ones(1, 1, kernel_size, kernel_size, device=gray.device) / (kernel_size**2)
            
            padded_input = stretched.permute(0, 3, 1, 2)
            local_mean = F.conv2d(padded_input, kernel, padding=kernel_size//2)
            local_mean = local_mean.permute(0, 2, 3, 1)
            
            # Enhance details relative to local mean
            enhanced = stretched + enhance_details * 0.3 * (stretched - local_mean)
            enhanced = torch.clamp(enhanced, 0, 1)
        else:
            enhanced = stretched
        
        return enhanced
    
    def _apply_blur(self, image, blur_amount):
        """Apply Gaussian blur"""
        device = image.device
        batch, height, width, channels = image.shape
        
        # Create Gaussian kernel
        kernel_size = int(blur_amount * 4) * 2 + 1
        sigma = blur_amount
        
        x = torch.arange(kernel_size, device=device, dtype=torch.float32) - kernel_size // 2
        kernel = torch.exp(-(x**2) / (2 * sigma**2))
        kernel = kernel / kernel.sum()
        
        # Create 2D kernels for separable convolution
        kernel_h = kernel.view(1, 1, 1, kernel_size)  # Horizontal kernel
        kernel_v = kernel.view(1, 1, kernel_size, 1)  # Vertical kernel
        
        # Reshape for convolution
        img_reshaped = image.permute(0, 3, 1, 2).reshape(-1, 1, height, width)
        
        # Apply separable convolution (horizontal then vertical)
        padding = kernel_size // 2
        blurred = F.conv2d(img_reshaped, kernel_h, padding=(0, padding))
        blurred = F.conv2d(blurred, kernel_v, padding=(padding, 0))
        
        return blurred.reshape(batch, channels, height, width).permute(0, 2, 3, 1)
    
    def _calculate_gradients(self, image, strength):
        """Calculate gradients optimized for depth maps"""
        device = image.device
        
        # Enhanced 3x3 Sobel for depth maps
        sobel_x = torch.tensor([
            [-1, 0, 1],
            [-2, 0, 2],
            [-1, 0, 1]
        ], device=device, dtype=torch.float32).unsqueeze(0).unsqueeze(0) / 4.0
        
        sobel_y = torch.tensor([
            [-1, -2, -1],
            [0, 0, 0],
            [1, 2, 1]
        ], device=device, dtype=torch.float32).unsqueeze(0).unsqueeze(0) / 4.0
        
        padding = 1
        strength_multiplier = 3.0  # Higher strength for depth maps
        
        # Reshape for convolution
        batch, height, width, channels = image.shape
        img_reshaped = image.permute(0, 3, 1, 2).reshape(-1, 1, height, width)
        
        # Calculate gradients with enhanced strength
        dx = F.conv2d(img_reshaped, sobel_x, padding=padding) * strength * strength_multiplier
        dy = F.conv2d(img_reshaped, sobel_y, padding=padding) * strength * strength_multiplier
        
        # Enhance gradients with adaptive scaling
        gradient_magnitude = torch.sqrt(dx**2 + dy**2)
        max_gradient = torch.max(gradient_magnitude) + 1e-8
        
        # Enhance weaker gradients more to reveal subtle surface details
        enhancement_factor = 1.0 + (1.0 - gradient_magnitude / max_gradient) * 0.5
        dx = dx * enhancement_factor
        dy = dy * enhancement_factor
        
        # Reshape back
        dx = dx.reshape(batch, channels, height, width).permute(0, 2, 3, 1)
        dy = dy.reshape(batch, channels, height, width).permute(0, 2, 3, 1)
        
        return dx, dy
    
    def _create_normal_map(self, dx, dy):
        """Create RGB normal map from gradients"""
        # Calculate Z component with proper scaling for surface detail
        z_base = 0.3  # Lower base Z for better surface definition
        
        # Calculate gradient magnitude for adaptive Z scaling
        gradient_magnitude = torch.sqrt(dx**2 + dy**2)
        max_gradient = torch.max(gradient_magnitude) + 1e-8
        normalized_gradient = gradient_magnitude / max_gradient
        
        # Inverse relationship: stronger gradients = lower Z
        adaptive_z = z_base * (2.0 - normalized_gradient)
        
        # Normalize the normal vectors
        length = torch.sqrt(dx**2 + dy**2 + adaptive_z**2 + 1e-8)
        nx = -dx / length  # Flip X for correct surface orientation
        ny = dy / length   # Y gradient (no flip needed)
        nz = adaptive_z / length
        
        # Map to RGB with proper normalization
        r = nx * 0.5 + 0.5  # X gradient -> Red
        g = ny * 0.5 + 0.5  # Y gradient -> Green 
        b = nz * 0.5 + 0.5  # Z component -> Blue
        
        # Apply clamping
        r = torch.clamp(r, 0, 1)
        g = torch.clamp(g, 0, 1)
        b = torch.clamp(b, 0, 1)
        
        # Combine into RGB normal map
        normal_map = torch.cat([r, g, b], dim=-1)
        
        return normal_map