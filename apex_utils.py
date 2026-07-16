#!/usr/bin/env python3
"""
Apex Utilities - Shared helper functions for Apex Artist nodes
Centralized implementations to avoid code duplication
"""

import torch
import torch.nn.functional as F
import math
from typing import Tuple, Optional


def validate_image_tensor(image: torch.Tensor, name: str = "image") -> None:
    """
    Validate image tensor format and dimensions
    
    Args:
        image: Tensor to validate (expected format: [B, H, W, C])
        name: Name for error messages
        
    Raises:
        ValueError: If tensor is invalid
    """
    if image is None:
        raise ValueError(f"{name} cannot be None")
    
    if not isinstance(image, torch.Tensor):
        raise ValueError(f"{name} must be a torch.Tensor, got {type(image)}")
    
    if len(image.shape) not in [3, 4]:
        raise ValueError(f"{name} must have 3 or 4 dimensions [B, H, W, C], got shape {image.shape}")
    
    if len(image.shape) == 4:
        batch, height, width, channels = image.shape
        if height < 1 or width < 1:
            raise ValueError(f"{name} dimensions invalid: {height}x{width}")
        if channels not in [1, 3, 4]:
            raise ValueError(f"{name} must have 1, 3, or 4 channels, got {channels}")


def validate_radius(radius: float, min_val: float = 0.1, max_val: float = 100.0) -> float:
    """
    Validate and clamp radius parameter
    
    Args:
        radius: Radius value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Clamped radius value
    """
    if radius < min_val:
        print(f"[Apex Utils] Warning: radius {radius} below minimum {min_val}, clamping")
        return min_val
    if radius > max_val:
        print(f"[Apex Utils] Warning: radius {radius} above maximum {max_val}, clamping")
        return max_val
    return radius


def gaussian_blur(image: torch.Tensor, radius: float, sigma_multiplier: float = 0.5) -> torch.Tensor:
    """
    Apply optimized Gaussian blur to image tensor
    
    Uses 2D Gaussian kernel for reliable results across all blur types.
    
    Args:
        image: Input tensor in [B, H, W, C] format
        radius: Blur radius (controls kernel size)
        sigma_multiplier: Multiplier for sigma calculation (default: 0.5)
        
    Returns:
        Blurred image tensor in [B, H, W, C] format
    """
    if radius <= 0:
        return image
    
    device = image.device
    batch, height, width, channels = image.shape
    
    # Calculate sigma and kernel size
    sigma = max(radius * sigma_multiplier, 0.5)
    kernel_size = int(2 * math.ceil(2 * sigma) + 1)
    kernel_size = max(kernel_size, 3)  # Minimum size
    kernel_size = min(kernel_size, 101)  # Cap at 101 to prevent memory issues
    
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
    
    return blurred


def apply_mask(original: torch.Tensor, processed: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """
    Apply mask to blend original and processed images
    
    Args:
        original: Original image [B, H, W, C]
        processed: Processed image [B, H, W, C]
        mask: Mask tensor (will be resized/reshaped as needed)
        
    Returns:
        Masked blend of original and processed images
    """
    device = original.device
    batch, height, width, channels = original.shape
    
    # Ensure mask has correct dimensions
    if len(mask.shape) == 2:
        mask = mask.unsqueeze(0).unsqueeze(-1)
    elif len(mask.shape) == 3:
        mask = mask.unsqueeze(-1)
    
    # Resize mask if needed
    if mask.shape[1:3] != (height, width):
        mask = F.interpolate(
            mask.permute(0, 3, 1, 2), 
            size=(height, width), 
            mode='bilinear', 
            align_corners=False
        ).permute(0, 2, 3, 1)
    
    # Ensure mask is in range [0, 1]
    mask = torch.clamp(mask, 0, 1)
    
    # Apply mask: masked areas get processed image, unmasked areas keep original
    return original * (1 - mask) + processed * mask


def create_gaussian_kernel_1d(radius: float, device: torch.device) -> torch.Tensor:
    """
    Create optimized 1D Gaussian kernel for separable convolution
    
    Args:
        radius: Blur radius
        device: Target device for tensor
        
    Returns:
        1D Gaussian kernel tensor [1, 1, kernel_size]
    """
    sigma = max(radius * 0.3, 0.5)
    kernel_size = max(int(2 * math.ceil(3 * sigma) + 1), 3)
    kernel_size = min(kernel_size, 101)  # Cap size
    
    # Ensure odd kernel size
    if kernel_size % 2 == 0:
        kernel_size += 1
    
    # Create 1D Gaussian kernel
    x = torch.arange(kernel_size, device=device, dtype=torch.float32) - kernel_size // 2
    kernel_1d = torch.exp(-(x**2) / (2 * sigma**2))
    kernel_1d = kernel_1d / kernel_1d.sum()
    
    return kernel_1d.view(1, 1, kernel_size)


def rgb_to_hsl(rgb: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Convert RGB to HSL color space
    
    Args:
        rgb: RGB tensor [B, H, W, 3] with values in [0, 1]
        
    Returns:
        Tuple of (H, S, L) tensors, each [B, H, W, 1]
    """
    r, g, b = rgb[..., 0:1], rgb[..., 1:2], rgb[..., 2:3]
    
    max_val = torch.max(torch.max(r, g), b)
    min_val = torch.min(torch.min(r, g), b)
    diff = max_val - min_val
    
    # Lightness
    l = (max_val + min_val) / 2.0
    
    # Saturation
    s = torch.where(
        diff == 0,
        torch.zeros_like(diff),
        torch.where(
            l < 0.5,
            diff / (max_val + min_val + 1e-10),
            diff / (2.0 - max_val - min_val + 1e-10)
        )
    )
    
    # Hue
    h = torch.zeros_like(diff)
    
    # Red is max
    mask = (max_val == r) & (diff != 0)
    h = torch.where(mask, ((g - b) / (diff + 1e-10)) % 6.0, h)
    
    # Green is max
    mask = (max_val == g) & (diff != 0)
    h = torch.where(mask, ((b - r) / (diff + 1e-10)) + 2.0, h)
    
    # Blue is max
    mask = (max_val == b) & (diff != 0)
    h = torch.where(mask, ((r - g) / (diff + 1e-10)) + 4.0, h)
    
    h = h / 6.0  # Normalize to [0, 1]
    
    return h, s, l


def hsl_to_rgb(h: torch.Tensor, s: torch.Tensor, l: torch.Tensor) -> torch.Tensor:
    """
    Convert HSL to RGB color space
    
    Args:
        h: Hue tensor [B, H, W, 1] in [0, 1]
        s: Saturation tensor [B, H, W, 1] in [0, 1]
        l: Lightness tensor [B, H, W, 1] in [0, 1]
        
    Returns:
        RGB tensor [B, H, W, 3] with values in [0, 1]
    """
    def hue_to_rgb(p, q, t):
        t = torch.where(t < 0, t + 1, t)
        t = torch.where(t > 1, t - 1, t)
        
        result = torch.where(
            t < 1/6,
            p + (q - p) * 6 * t,
            torch.where(
                t < 1/2,
                q,
                torch.where(
                    t < 2/3,
                    p + (q - p) * (2/3 - t) * 6,
                    p
                )
            )
        )
        return result
    
    # Achromatic (grayscale)
    q = torch.where(
        l < 0.5,
        l * (1 + s),
        l + s - l * s
    )
    p = 2 * l - q
    
    r = hue_to_rgb(p, q, h + 1/3)
    g = hue_to_rgb(p, q, h)
    b = hue_to_rgb(p, q, h - 1/3)
    
    # Handle grayscale case
    is_gray = (s == 0)
    r = torch.where(is_gray, l, r)
    g = torch.where(is_gray, l, g)
    b = torch.where(is_gray, l, b)
    
    return torch.cat([r, g, b], dim=-1)


def calculate_luminance(image: torch.Tensor) -> torch.Tensor:
    """
    Calculate luminance from RGB image using standard weights
    
    Args:
        image: RGB image tensor [B, H, W, C]
        
    Returns:
        Luminance tensor [B, H, W, 1]
    """
    if image.shape[-1] == 1:
        return image
    elif image.shape[-1] >= 3:
        # Standard luminance weights (Rec. 709)
        return (0.299 * image[..., 0:1] + 
                0.587 * image[..., 1:2] + 
                0.114 * image[..., 2:3])
    else:
        # Fallback for unexpected channel count
        return image[..., 0:1]
