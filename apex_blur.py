#!/usr/bin/env python3
"""
Apex Blur Node - Professional blur effects with multiple algorithms
Supports various blur types for different artistic and technical needs
"""
import torch
import torch.nn.functional as F
import numpy as np
import math
from functools import lru_cache
from .apex_utils import gaussian_blur, validate_image_tensor, validate_radius, apply_mask as utils_apply_mask, calculate_luminance, create_gaussian_kernel_1d


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
                    "zoom",
                    "depth"
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
                "depth": ("MASK",),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("blurred_image", "blur_info")
    FUNCTION = "apply_blur"
    CATEGORY = "Apex Artist/Image/Filters"

    def apply_blur(self, image, blur_type="gaussian", radius=5.0, strength=1.0, 
                   angle=0.0, center_x=0.5, center_y=0.5, edge_threshold=0.1, mask=None, depth=None):
        try:
            # Validate inputs using apex_utils
            validate_image_tensor(image, "image")
            radius = validate_radius(radius, min_val=0.5, max_val=100.0)
            
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
            elif blur_type == "depth":
                blurred = self._depth_blur(image, radius, depth)
            else:
                blurred = self._gaussian_blur(image, radius)
            
            # Apply strength blending
            if strength < 1.0:
                blurred = image + strength * (blurred - image)
            
            # Apply mask if provided
            if mask is not None:
                blurred = utils_apply_mask(image, blurred, mask)
            
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

    @staticmethod
    @lru_cache(maxsize=32)
    def _get_2d_kernel(kernel_size: int, sigma: float, device_str: str = "cpu"):
        """Cached 2D Gaussian kernel creation to avoid recomputation"""
        device = torch.device(device_str)
        x = torch.arange(kernel_size, device=device, dtype=torch.float32) - kernel_size // 2
        y = torch.arange(kernel_size, device=device, dtype=torch.float32) - kernel_size // 2
        xx, yy = torch.meshgrid(x, y, indexing='ij')
        kernel_2d = torch.exp(-(xx**2 + yy**2) / (2 * sigma**2))
        kernel_2d = kernel_2d / kernel_2d.sum()
        return kernel_2d.unsqueeze(0).unsqueeze(0)

    @staticmethod
    def _apply_conv2d_per_channel(image: torch.Tensor, kernel: torch.Tensor, padding: int):
        """Apply 2D convolution per channel using grouped convolution for efficiency"""
        batch, height, width, channels = image.shape
        # Reshape to [B*C, 1, H, W] for grouped convolution
        img_reshaped = image.permute(0, 3, 1, 2).reshape(-1, 1, height, width)
        # Apply grouped conv2d (groups=channels means each channel gets its own kernel)
        result = F.conv2d(img_reshaped, kernel, padding=padding, groups=1)
        # Reshape back to [B, C, H, W] then [B, H, W, C]
        result = result.reshape(batch, channels, height, width).permute(0, 2, 3, 1)
        return result

    def _gaussian_blur(self, image, radius):
        """Simple and reliable Gaussian blur - now uses shared apex_utils implementation"""
        return gaussian_blur(image, radius, sigma_multiplier=0.5)

    def _strong_gaussian_blur(self, image, radius):
        """Strong Gaussian blur with enhanced sigma - now uses shared apex_utils implementation"""
        return gaussian_blur(image, radius, sigma_multiplier=0.8)

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
        
        # Apply using grouped convolution for efficiency
        blurred = self._apply_conv2d_per_channel(image, kernel_2d, padding)
        
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
        
        # Apply convolution using grouped approach
        blurred = self._apply_conv2d_per_channel(image, kernel, padding)
        
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
        
        # Pre-permute image once
        img_for_sampling = image.permute(0, 3, 1, 2)
        
        for scale in scales:
            # Create sampling grid
            grid_x = xx / scale + center_x_adj
            grid_y = yy / scale + center_y_adj
            
            grid = torch.stack([grid_x, grid_y], dim=-1).unsqueeze(0)
            grid = grid.expand(batch_size, -1, -1, -1)
            
            # Sample image (GPU operation)
            sampled = F.grid_sample(img_for_sampling, grid, mode='bilinear', 
                                  padding_mode='border', align_corners=False)
            sampled = sampled.permute(0, 2, 3, 1)
            
            result += sampled
        
        return result / samples

    def _depth_blur(self, image, radius, depth):
        """
        Depth-based blur using depth map (e.g., from Depth Anything V3)
        
        Args:
            image: Input image tensor [B, H, W, C]
            radius: Maximum blur radius
            depth: Depth map as MASK tensor [B, H, W] or [B, H, W, 1]
            
        Returns:
            Depth-blurred image tensor
        """
        if depth is None:
            print("Depth blur: No depth map provided, falling back to Gaussian blur")
            return self._gaussian_blur(image, radius)
        
        device = image.device
        batch_size, height, width, channels = image.shape
        
        # Ensure depth has correct shape [B, H, W, 1]
        if len(depth.shape) == 3:
            depth = depth.unsqueeze(-1)
        elif len(depth.shape) == 2:
            depth = depth.unsqueeze(0).unsqueeze(-1)
        
        # Resize depth to match image if needed
        if depth.shape[1:3] != (height, width):
            depth = F.interpolate(
                depth.permute(0, 3, 1, 2),
                size=(height, width),
                mode='bilinear',
                align_corners=False
            ).permute(0, 2, 3, 1)
        
        # Normalize depth to [0, 1]
        depth_min = depth.amin(dim=(1, 2), keepdim=True)
        depth_max = depth.amax(dim=(1, 2), keepdim=True)
        depth_normalized = (depth - depth_min) / (depth_max - depth_min + 1e-8)
        
        # Depth map typically has: near=white (1), far=black (0) or vice versa
        # We'll invert so that near objects get less blur, far objects get more blur
        blur_amount = 1.0 - depth_normalized  # Far objects get more blur
        
        # Scale by max radius
        blur_amount = blur_amount * radius
        
        # For efficiency, we'll quantize depth into bins and apply different blur levels
        num_bins = 8  # Number of depth bins for multi-layer blur
        result = torch.zeros_like(image)
        
        # Pre-permute image once for grouped convolution
        img_permuted = image.permute(0, 3, 1, 2)
        
        for i in range(num_bins):
            bin_min = i / num_bins
            bin_max = (i + 1) / num_bins
            
            # Create mask for this depth bin
            bin_mask = ((blur_amount >= bin_min) & (blur_amount < bin_max)).float()
            
            # For the last bin, include the max value
            if i == num_bins - 1:
                bin_mask = ((blur_amount >= bin_min) & (blur_amount <= bin_max)).float()
            
            # Check if any pixels fall in this bin
            if bin_mask.sum() > 0:
                # Calculate average blur radius for this bin
                bin_center = (bin_min + bin_max) / 2
                bin_radius = bin_center * radius
                
                if bin_radius < 0.5:
                    # No blur needed for this bin
                    blurred_bin = image
                else:
                    # Calculate kernel parameters
                    sigma = max(bin_radius * 0.5, 0.5)
                    kernel_size = int(2 * math.ceil(2 * sigma) + 1)
                    kernel_size = max(kernel_size, 3)
                    kernel_size = min(kernel_size, 101)
                    if kernel_size % 2 == 0:
                        kernel_size += 1
                    
                    # Get or create cached kernel
                    kernel_2d = self._get_2d_kernel(kernel_size, sigma, str(device))
                    padding = kernel_size // 2
                    
                    # Apply blur using grouped convolution
                    blurred_channels = []
                    for c in range(channels):
                        channel = img_permuted[:, c:c+1, :, :]
                        blurred_channel = F.conv2d(channel, kernel_2d, padding=padding)
                        blurred_channels.append(blurred_channel)
                    blurred_bin = torch.cat(blurred_channels, dim=1).permute(0, 2, 3, 1)
                
                # Blend this bin into result
                bin_mask_expanded = bin_mask.expand(-1, -1, -1, channels)
                result += blurred_bin * bin_mask_expanded
        
        # Handle any remaining pixels (should be minimal)
        remaining_mask = 1.0 - (blur_amount >= 0).float().sum(dim=0, keepdim=True).clamp(0, 1)
        if remaining_mask.sum() > 0:
            result += image * remaining_mask.unsqueeze(-1).expand(-1, -1, -1, channels)
        
        print(f"Depth Blur: radius={radius}, depth_bins={num_bins}, depth_range=[{depth_normalized.min():.3f}, {depth_normalized.max():.3f}]")
        
        return torch.clamp(result, 0, 1)

    def _surface_blur(self, image, radius, edge_threshold):
        """Edge-preserving surface blur"""
        # Apply Gaussian blur
        blurred = self._gaussian_blur(image, radius)
        
        # Calculate edge weights based on luminance difference
        original_luma = calculate_luminance(image)
        blurred_luma = calculate_luminance(blurred)
        
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
        
        # Get or create cached kernel
        kernel_2d = self._get_2d_kernel(blur_kernel_size, blur_sigma, str(device))
        padding = blur_kernel_size // 2
        
        # Apply blur using grouped convolution
        blurred_image = self._apply_conv2d_per_channel(image, kernel_2d, padding)
        
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
        
        # Pre-permute image once
        img_for_sampling = image.permute(0, 3, 1, 2)
        
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
        
        # Pre-permute image once
        img_for_sampling = image.permute(0, 3, 1, 2)
        
        for zoom_factor in zoom_factors:
            # Calculate zoom transform
            scale = 1.0 / zoom_factor
            
            # Apply zoom from center
            xx_zoom = (xx - center_x_adj) * scale + center_x_adj
            yy_zoom = (yy - center_y_adj) * scale + center_y_adj
            
            grid = torch.stack([xx_zoom, yy_zoom], dim=-1).unsqueeze(0)
            grid = grid.expand(batch_size, -1, -1, -1)
            
            # Sample image
            sampled = F.grid_sample(img_for_sampling, grid, mode='bilinear',
                                  padding_mode='border', align_corners=False)
            sampled = sampled.permute(0, 2, 3, 1)
            
            result += sampled
        
        return result / samples