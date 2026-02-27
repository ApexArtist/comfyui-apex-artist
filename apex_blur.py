#!/usr/bin/env python3
"""
Apex Blur Node - Professional blur effects with multiple algorithms
Supports various blur types for different artistic and technical needs
"""
import torch
import torch.nn.functional as F
import numpy as np
import math

class ApexBlur:
    """
    Professional blur node with multiple blur algorithms
    
    Features:
    - Gaussian blur (smooth, natural)
    - Box blur (fast, uniform)
    - Motion blur (directional)
    - Radial blur (zoom effect)
    - Surface blur (edge-preserving)
    - Lens blur (depth of field)
    - Spin blur (rotational)
    - Variable radius control
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "blur_type": ([
                    "gaussian",
                    "strong_gaussian",
                    "box", 
                    "motion",
                    "radial",
                    "surface",
                    "lens",
                    "spin",
                    "zoom"
                ], {"default": "gaussian"}),
                "radius": ("FLOAT", {
                    "default": 10.0,
                    "min": 0.5,
                    "max": 100.0,
                    "step": 0.1
                }),
                "strength": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01
                }),
            },
            "optional": {
                "angle": ("FLOAT", {
                    "default": 0.0,
                    "min": -180.0,
                    "max": 180.0,
                    "step": 1.0
                }),
                "center_x": ("FLOAT", {
                    "default": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01
                }),
                "center_y": ("FLOAT", {
                    "default": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01
                }),
                "edge_threshold": ("FLOAT", {
                    "default": 0.1,
                    "min": 0.01,
                    "max": 1.0,
                    "step": 0.01
                }),
                "mask": ("MASK",),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("blurred_image", "blur_info")
    FUNCTION = "apply_blur"
    CATEGORY = "Apex Artist/Effects"

    def apply_blur(self, image, blur_type="gaussian", radius=5.0, strength=1.0, 
                   angle=0.0, center_x=0.5, center_y=0.5, edge_threshold=0.1, mask=None):
        try:
            # Validate inputs
            if image is None:
                raise ValueError("Image input is required")
            
            # Set default values for optional parameters
            angle = angle if angle is not None else 0.0
            center_x = center_x if center_x is not None else 0.5
            center_y = center_y if center_y is not None else 0.5
            edge_threshold = edge_threshold if edge_threshold is not None else 0.1
                        
            # Debug info
            print(f"Apex Blur: {blur_type}, radius={radius}, strength={strength}")
            
            # Ensure image is in correct format [B, H, W, C]
            if len(image.shape) == 3:
                image = image.unsqueeze(0)
            
            batch_size = image.shape[0]
            
            # Apply blur based on type
            if blur_type == "gaussian":
                blurred = self._gaussian_blur(image, radius)
            elif blur_type == "strong_gaussian":
                blurred = self._strong_gaussian_blur(image, radius)
            elif blur_type == "box":
                blurred = self._box_blur(image, radius)
            elif blur_type == "motion":
                blurred = self._motion_blur(image, radius, angle)
            elif blur_type == "radial":
                blurred = self._radial_blur(image, radius, center_x, center_y)
            elif blur_type == "surface":
                blurred = self._surface_blur(image, radius, edge_threshold)
            elif blur_type == "lens":
                blurred = self._lens_blur(image, radius, center_x, center_y)
            elif blur_type == "spin":
                blurred = self._spin_blur(image, radius, center_x, center_y)
            elif blur_type == "zoom":
                blurred = self._zoom_blur(image, radius, center_x, center_y)
            else:
                blurred = self._gaussian_blur(image, radius)
            
            # Apply strength blending
            if strength < 1.0:
                blurred = image + strength * (blurred - image)
            
            # Apply mask if provided
            if mask is not None:
                blurred = self._apply_mask(image, blurred, mask)
            
            # Generate blur info
            blur_info = f"Blur: {blur_type} | Radius: {radius:.1f} | Strength: {strength:.2f}"
            if blur_type in ["motion"]:
                blur_info += f" | Angle: {angle:.0f}°"
            elif blur_type in ["radial", "lens", "spin", "zoom"]:
                blur_info += f" | Center: ({center_x:.2f}, {center_y:.2f})"
            
            return (torch.clamp(blurred, 0, 1), blur_info)
            
        except Exception as e:
            print(f"Blur error: {str(e)}")
            return (image, f"Error: {str(e)}")

    def _create_gaussian_kernel(self, radius, device):
        """Create optimized 1D Gaussian kernel for separable convolution"""
        # Use radius directly as sigma for more predictable blur effect
        sigma = max(radius * 0.3, 0.5)  # Ensure minimum sigma
        kernel_size = max(int(2 * math.ceil(3 * sigma) + 1), 3)  # 3-sigma rule
        kernel_size = min(kernel_size, 101)  # Cap kernel size
        
        # Ensure odd kernel size
        if kernel_size % 2 == 0:
            kernel_size += 1
        
        # Create 1D Gaussian kernel
        x = torch.arange(kernel_size, device=device, dtype=torch.float32) - kernel_size // 2
        kernel_1d = torch.exp(-(x**2) / (2 * sigma**2))
        kernel_1d = kernel_1d / kernel_1d.sum()
        
        # Debug output
        print(f"Gaussian kernel: radius={radius}, sigma={sigma:.2f}, kernel_size={kernel_size}")
        
        return kernel_1d.view(1, 1, kernel_size)

    def _gaussian_blur(self, image, radius):
        """Simple and reliable Gaussian blur"""
        device = image.device
        batch_size, height, width, channels = image.shape
        
        # Simple sigma calculation
        sigma = max(radius / 2.0, 0.5)
        kernel_size = int(2 * math.ceil(2 * sigma) + 1)
        kernel_size = max(kernel_size, 3)  # Minimum size
        
        # Ensure odd kernel size
        if kernel_size % 2 == 0:
            kernel_size += 1
        
        # Create simple 2D Gaussian kernel (more straightforward)
        x = torch.arange(kernel_size, device=device, dtype=torch.float32) - kernel_size // 2
        y = torch.arange(kernel_size, device=device, dtype=torch.float32) - kernel_size // 2
        xx, yy = torch.meshgrid(x, y, indexing='ij')
        
        kernel_2d = torch.exp(-(xx**2 + yy**2) / (2 * sigma**2))
        kernel_2d = kernel_2d / kernel_2d.sum()
        kernel_2d = kernel_2d.unsqueeze(0).unsqueeze(0)  # [1, 1, H, W]
        
        padding = kernel_size // 2
        
        # Apply to each channel separately for reliability
        result_channels = []
        for c in range(channels):
            # Extract single channel [B, 1, H, W]
            channel = image[:, :, :, c:c+1].permute(0, 3, 1, 2)
            # Apply blur
            blurred_channel = F.conv2d(channel, kernel_2d, padding=padding)
            result_channels.append(blurred_channel)
        
        # Combine channels back
        blurred = torch.cat(result_channels, dim=1)  # [B, C, H, W]
        blurred = blurred.permute(0, 2, 3, 1)  # [B, H, W, C]
        
        print(f"Simple Gaussian: radius={radius}, sigma={sigma:.2f}, kernel_size={kernel_size}")
        
        return blurred

    def _strong_gaussian_blur(self, image, radius):
        """Strong Gaussian blur with enhanced sigma"""
        device = image.device
        batch_size, height, width, channels = image.shape
        
        # Use much stronger sigma for dramatic effect
        sigma = max(radius * 0.8, 1.0)  # More aggressive than regular gaussian
        kernel_size = int(2 * math.ceil(2 * sigma) + 1)
        kernel_size = max(kernel_size, 7)  # Minimum size for strong blur
        
        # Ensure odd kernel size
        if kernel_size % 2 == 0:
            kernel_size += 1
        
        # Create 2D Gaussian kernel
        x = torch.arange(kernel_size, device=device, dtype=torch.float32) - kernel_size // 2
        y = torch.arange(kernel_size, device=device, dtype=torch.float32) - kernel_size // 2
        xx, yy = torch.meshgrid(x, y, indexing='ij')
        
        kernel_2d = torch.exp(-(xx**2 + yy**2) / (2 * sigma**2))
        kernel_2d = kernel_2d / kernel_2d.sum()
        kernel_2d = kernel_2d.unsqueeze(0).unsqueeze(0)  # [1, 1, H, W]
        
        padding = kernel_size // 2
        
        # Apply to each channel separately
        result_channels = []
        for c in range(channels):
            channel = image[:, :, :, c:c+1].permute(0, 3, 1, 2)
            blurred_channel = F.conv2d(channel, kernel_2d, padding=padding)
            result_channels.append(blurred_channel)
        
        # Combine channels back
        blurred = torch.cat(result_channels, dim=1)
        blurred = blurred.permute(0, 2, 3, 1)
        
        print(f"Strong Gaussian: radius={radius}, sigma={sigma:.2f}, kernel_size={kernel_size}")
        
        return blurred

    def _box_blur(self, image, radius):
        """Simple box blur using 2D uniform kernel"""
        device = image.device
        batch_size, height, width, channels = image.shape
        
        # Create box kernel size
        kernel_size = max(int(2 * radius + 1), 3)
        
        # Ensure odd kernel size
        if kernel_size % 2 == 0:
            kernel_size += 1
        
        # Create uniform 2D box kernel
        kernel_2d = torch.ones(kernel_size, kernel_size, device=device)
        kernel_2d = kernel_2d / kernel_2d.sum()  # Normalize
        kernel_2d = kernel_2d.unsqueeze(0).unsqueeze(0)  # [1, 1, H, W]
        
        padding = kernel_size // 2
        
        # Apply to each channel separately
        result_channels = []
        for c in range(channels):
            channel = image[:, :, :, c:c+1].permute(0, 3, 1, 2)
            blurred_channel = F.conv2d(channel, kernel_2d, padding=padding)
            result_channels.append(blurred_channel)
        
        # Combine channels back
        blurred = torch.cat(result_channels, dim=1)
        blurred = blurred.permute(0, 2, 3, 1)
        
        print(f"Box Blur: radius={radius}, kernel_size={kernel_size}")
        
        return blurred

    def _motion_blur(self, image, radius, angle):
        """Optimized directional motion blur"""
        device = image.device
        batch_size, height, width, channels = image.shape
        
        # Limit radius for performance
        radius = min(radius, 50)
        
        # Convert angle to radians
        angle_rad = math.radians(angle)
        
        # Calculate motion vector
        dx = radius * math.cos(angle_rad)
        dy = radius * math.sin(angle_rad)
        
        # Create motion blur kernel more efficiently
        kernel_size = min(int(2 * radius + 1), 101)  # Cap size
        kernel = torch.zeros(kernel_size, kernel_size, device=device)
        
        center = kernel_size // 2
        steps = min(max(1, int(radius)), 20)  # Limit steps for performance
        
        # Vectorized kernel creation
        for i in range(steps + 1):
            t = i / steps if steps > 0 else 0
            x = int(center + t * dx - dx/2)
            y = int(center + t * dy - dy/2)
            
            if 0 <= x < kernel_size and 0 <= y < kernel_size:
                kernel[y, x] += 1
        
        # Normalize kernel
        kernel = kernel / (kernel.sum() + 1e-8)
        kernel = kernel.unsqueeze(0).unsqueeze(0)
        padding = kernel_size // 2
        
        # Apply convolution
        img_reshaped = image.permute(0, 3, 1, 2).reshape(-1, 1, height, width)
        blurred = F.conv2d(img_reshaped, kernel, padding=padding)
        blurred = blurred.reshape(batch_size, channels, height, width).permute(0, 2, 3, 1)
        
        return blurred

    def _radial_blur(self, image, radius, center_x, center_y):
        """Optimized radial/zoom blur effect"""
        device = image.device
        batch_size, height, width, channels = image.shape
        
        # Limit samples for performance
        samples = min(max(int(radius // 2), 3), 8)  # Adaptive sampling
        
        # Pre-calculate coordinate grids
        y_coords = torch.linspace(-1, 1, height, device=device)
        x_coords = torch.linspace(-1, 1, width, device=device)
        yy, xx = torch.meshgrid(y_coords, x_coords, indexing='ij')
        
        # Adjust center
        center_x_adj = (center_x - 0.5) * 2
        center_y_adj = (center_y - 0.5) * 2
        xx = xx - center_x_adj
        yy = yy - center_y_adj
        
        result = torch.zeros_like(image)
        
        # Batch process multiple scales
        scales = torch.linspace(1.0, 1.0 + radius / 20.0, samples, device=device)
        
        for scale in scales:
            # Create sampling grid
            grid_x = xx / scale + center_x_adj
            grid_y = yy / scale + center_y_adj
            
            grid = torch.stack([grid_x, grid_y], dim=-1).unsqueeze(0)
            grid = grid.expand(batch_size, -1, -1, -1)
            
            # Sample image (GPU operation)
            img_for_sampling = image.permute(0, 3, 1, 2)
            sampled = F.grid_sample(img_for_sampling, grid, mode='bilinear', 
                                  padding_mode='border', align_corners=False)
            sampled = sampled.permute(0, 2, 3, 1)
            
            result += sampled
        
        return result / samples

    def _surface_blur(self, image, radius, edge_threshold):
        """Edge-preserving surface blur"""
        # Apply Gaussian blur
        blurred = self._gaussian_blur(image, radius)
        
        # Calculate edge weights based on luminance difference
        luma_weights = torch.tensor([0.299, 0.587, 0.114], device=image.device)
        original_luma = torch.sum(image * luma_weights, dim=-1, keepdim=True)
        blurred_luma = torch.sum(blurred * luma_weights, dim=-1, keepdim=True)
        
        # Edge detection
        luma_diff = torch.abs(original_luma - blurred_luma)
        edge_weight = torch.exp(-luma_diff / edge_threshold)
        
        # Blend based on edge strength
        result = image + edge_weight * (blurred - image)
        
        return result

    def _lens_blur(self, image, radius, center_x, center_y):
        """Simple lens blur with depth of field simulation"""
        device = image.device
        batch_size, height, width, channels = image.shape
        
        # Create distance map from center
        y_coords = torch.linspace(0, 1, height, device=device)
        x_coords = torch.linspace(0, 1, width, device=device)
        yy, xx = torch.meshgrid(y_coords, x_coords, indexing='ij')
        
        # Calculate distance from focus point
        distance = torch.sqrt((xx - center_x)**2 + (yy - center_y)**2)
        max_distance = torch.sqrt(torch.tensor(2.0, device=device))
        
        # Normalize distance (0 = center, 1 = furthest corner)
        normalized_distance = torch.clamp(distance / max_distance, 0, 1)
        
        # Create simple lens blur by applying uniform blur with distance-based masking
        # Create a moderate blur for the entire image
        blur_sigma = max(radius / 3.0, 1.0)
        blur_kernel_size = max(int(2 * math.ceil(2 * blur_sigma) + 1), 7)
        
        # Ensure odd kernel size
        if blur_kernel_size % 2 == 0:
            blur_kernel_size += 1
        
        # Create 2D Gaussian kernel for lens blur
        x = torch.arange(blur_kernel_size, device=device, dtype=torch.float32) - blur_kernel_size // 2
        y = torch.arange(blur_kernel_size, device=device, dtype=torch.float32) - blur_kernel_size // 2
        xx_k, yy_k = torch.meshgrid(x, y, indexing='ij')
        
        kernel_2d = torch.exp(-(xx_k**2 + yy_k**2) / (2 * blur_sigma**2))
        kernel_2d = kernel_2d / kernel_2d.sum()
        kernel_2d = kernel_2d.unsqueeze(0).unsqueeze(0)
        
        padding = blur_kernel_size // 2
        
        # Apply blur to each channel
        blurred_channels = []
        for c in range(channels):
            channel = image[:, :, :, c:c+1].permute(0, 3, 1, 2)
            blurred_channel = F.conv2d(channel, kernel_2d, padding=padding)
            blurred_channels.append(blurred_channel)
        
        blurred_image = torch.cat(blurred_channels, dim=1).permute(0, 2, 3, 1)
        
        # Blend based on distance (center stays sharp, edges get blurred)
        blend_mask = normalized_distance.unsqueeze(0).unsqueeze(-1)
        result = image * (1 - blend_mask) + blurred_image * blend_mask
        
        print(f"Lens Blur: radius={radius}, center=({center_x:.2f}, {center_y:.2f}), blur_kernel={blur_kernel_size}")
        
        return result

    def _spin_blur(self, image, radius, center_x, center_y):
        """Optimized rotational spin blur"""
        device = image.device
        batch_size, height, width, channels = image.shape
        
        # Limit samples for performance
        samples = min(max(int(radius // 3), 3), 6)
        
        # Pre-calculate coordinate grids
        y_coords = torch.linspace(-1, 1, height, device=device)
        x_coords = torch.linspace(-1, 1, width, device=device)
        yy, xx = torch.meshgrid(y_coords, x_coords, indexing='ij')
        
        # Adjust center
        center_x_adj = (center_x - 0.5) * 2
        center_y_adj = (center_y - 0.5) * 2
        xx = xx - center_x_adj
        yy = yy - center_y_adj
        
        result = torch.zeros_like(image)
        
        # Calculate rotation angles
        max_angle = radius * math.pi / 180  # Convert to radians
        angles = torch.linspace(0, max_angle, samples, device=device)
        
        for angle in angles:
            # Rotation matrix (GPU computation)
            cos_a = torch.cos(angle)
            sin_a = torch.sin(angle)
            
            # Rotate coordinates
            xx_rot = xx * cos_a - yy * sin_a + center_x_adj
            yy_rot = xx * sin_a + yy * cos_a + center_y_adj
            
            grid = torch.stack([xx_rot, yy_rot], dim=-1).unsqueeze(0)
            grid = grid.expand(batch_size, -1, -1, -1)
            
            # Sample image
            img_for_sampling = image.permute(0, 3, 1, 2)
            sampled = F.grid_sample(img_for_sampling, grid, mode='bilinear',
                                  padding_mode='border', align_corners=False)
            sampled = sampled.permute(0, 2, 3, 1)
            
            result += sampled
        
        return result / samples

    def _zoom_blur(self, image, radius, center_x, center_y):
        """Optimized zoom blur effect"""
        device = image.device
        batch_size, height, width, channels = image.shape
        
        # Limit samples for performance
        samples = min(max(int(radius // 3), 3), 6)
        
        result = torch.zeros_like(image)
        
        # Pre-calculate coordinate grids
        y_coords = torch.linspace(-1, 1, height, device=device)
        x_coords = torch.linspace(-1, 1, width, device=device)
        yy, xx = torch.meshgrid(y_coords, x_coords, indexing='ij')
        
        # Adjust center
        center_x_adj = (center_x - 0.5) * 2
        center_y_adj = (center_y - 0.5) * 2
        
        # Calculate zoom factors
        zoom_factors = torch.linspace(1.0, 1.0 + radius / 30.0, samples, device=device)
        
        for zoom_factor in zoom_factors:
            # Calculate zoom transform
            scale = 1.0 / zoom_factor
            
            # Apply zoom from center
            xx_zoom = (xx - center_x_adj) * scale + center_x_adj
            yy_zoom = (yy - center_y_adj) * scale + center_y_adj
            
            grid = torch.stack([xx_zoom, yy_zoom], dim=-1).unsqueeze(0)
            grid = grid.expand(batch_size, -1, -1, -1)
            
            # Sample image
            img_for_sampling = image.permute(0, 3, 1, 2)
            sampled = F.grid_sample(img_for_sampling, grid, mode='bilinear',
                                  padding_mode='border', align_corners=False)
            sampled = sampled.permute(0, 2, 3, 1)
            
            result += sampled
        
        return result / samples
    
    def _apply_mask(self, original, processed, mask):
        """Apply mask to blend original and processed images"""
        device = original.device
        batch, height, width, channels = original.shape
        
        # Ensure mask has correct dimensions
        if len(mask.shape) == 2:
            mask = mask.unsqueeze(0).unsqueeze(-1)
        elif len(mask.shape) == 3:
            mask = mask.unsqueeze(-1)
        
        # Resize mask if needed
        if mask.shape[1:3] != (height, width):
            mask = F.interpolate(mask.permute(0, 3, 1, 2), size=(height, width), 
                               mode='bilinear', align_corners=False).permute(0, 2, 3, 1)
        
        # Ensure mask is in range [0, 1]
        mask = torch.clamp(mask, 0, 1)
        
        # Apply mask: masked areas get processed image, unmasked areas keep original
        return original * (1 - mask) + processed * mask