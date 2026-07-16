#!/usr/bin/env python3
"""
Apex Layer Blend Node - Photoshop-style layer blending modes
Supports all major blend modes with proper algorithms
"""
import torch
import torch.nn.functional as F
import numpy as np

class ApexLayerBlend:
    """
    Professional layer blending node with Photoshop-compatible blend modes
    
    Features:
    - All major Photoshop blend modes
    - Opacity control
    - Proper color space handling
    - GPU-accelerated operations
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_image": ("IMAGE",),
                "overlay_image": ("IMAGE",),
                "blend_mode": ([
                    # Normal group
                    "normal",
                    "dissolve",
                    
                    # Darken group
                    "darken",
                    "multiply", 
                    "color_burn",
                    "linear_burn",
                    "darker_color",
                    
                    # Lighten group
                    "lighten",
                    "screen",
                    "color_dodge",
                    "linear_dodge",
                    "lighter_color",
                    
                    # Contrast group
                    "overlay",
                    "soft_light",
                    "hard_light",
                    "vivid_light",
                    "linear_light",
                    "pin_light",
                    "hard_mix",
                    
                    # Difference group
                    "difference",
                    "exclusion",
                    "subtract",
                    "divide",
                    
                    # Color group
                    "hue",
                    "saturation", 
                    "color",
                    "luminosity"
                ], {"default": "normal"}),
                "opacity": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01
                }),
            },
            "optional": {
                "mask": ("MASK",),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("blended_image", "blend_info")
    FUNCTION = "blend_layers"
    CATEGORY = "Apex Artist/Image/Composite"

    def blend_layers(self, base_image, overlay_image, blend_mode="normal", opacity=1.0, mask=None):
        try:
            # Ensure images are in correct format [B, H, W, C]
            if len(base_image.shape) == 3:
                base_image = base_image.unsqueeze(0)
            if len(overlay_image.shape) == 3:
                overlay_image = overlay_image.unsqueeze(0)
            
            # Resize overlay to match base if needed
            if base_image.shape != overlay_image.shape:
                overlay_image = self._resize_to_match(overlay_image, base_image)
            
            # Apply blend mode
            blended = self._apply_blend_mode(base_image, overlay_image, blend_mode)
            
            # Apply opacity
            if opacity < 1.0:
                blended = base_image + opacity * (blended - base_image)
            
            # Apply mask if provided
            if mask is not None:
                # ComfyUI masks come as [B, H, W], we need [B, H, W, 1] for blending
                if len(mask.shape) == 2:
                    mask = mask.unsqueeze(0).unsqueeze(-1)  # [H, W] -> [1, H, W, 1]
                elif len(mask.shape) == 3:
                    mask = mask.unsqueeze(-1)  # [B, H, W] -> [B, H, W, 1]
                
                # Resize mask to match base image
                mask = self._resize_to_match(mask, base_image)
                
                # Apply mask (mask values should be 0-1)
                blended = base_image + mask * (blended - base_image)
            
            # Generate blend info
            blend_info = f"Blend Mode: {blend_mode} | Opacity: {opacity:.2f}"
            if mask is not None:
                blend_info += " | Masked"
            
            return (torch.clamp(blended, 0, 1), blend_info)
            
        except Exception as e:
            print(f"Layer blend error: {str(e)}")
            return (base_image, f"Error: {str(e)}")

    def _resize_to_match(self, source, target):
        """Resize source image to match target dimensions"""
        if source.shape[1:3] != target.shape[1:3]:
            # Reshape for F.interpolate: [B, C, H, W]
            source_reshaped = source.permute(0, 3, 1, 2)
            target_size = target.shape[1:3]  # [H, W]
            
            resized = F.interpolate(
                source_reshaped, 
                size=target_size, 
                mode='bilinear', 
                align_corners=False
            )
            
            # Reshape back to [B, H, W, C]
            return resized.permute(0, 2, 3, 1)
        return source

    def _apply_blend_mode(self, base, overlay, mode):
        """Apply the specified blend mode"""
        if mode == "normal":
            return overlay
        elif mode == "dissolve":
            return self._blend_dissolve(base, overlay)
        
        # Darken group
        elif mode == "darken":
            return torch.min(base, overlay)
        elif mode == "multiply":
            return base * overlay
        elif mode == "color_burn":
            return self._blend_color_burn(base, overlay)
        elif mode == "linear_burn":
            return torch.clamp(base + overlay - 1, 0, 1)
        elif mode == "darker_color":
            return self._blend_darker_color(base, overlay)
        
        # Lighten group
        elif mode == "lighten":
            return torch.max(base, overlay)
        elif mode == "screen":
            return 1 - (1 - base) * (1 - overlay)
        elif mode == "color_dodge":
            return self._blend_color_dodge(base, overlay)
        elif mode == "linear_dodge":
            return torch.clamp(base + overlay, 0, 1)
        elif mode == "lighter_color":
            return self._blend_lighter_color(base, overlay)
        
        # Contrast group
        elif mode == "overlay":
            return self._blend_overlay(base, overlay)
        elif mode == "soft_light":
            return self._blend_soft_light(base, overlay)
        elif mode == "hard_light":
            return self._blend_hard_light(base, overlay)
        elif mode == "vivid_light":
            return self._blend_vivid_light(base, overlay)
        elif mode == "linear_light":
            return self._blend_linear_light(base, overlay)
        elif mode == "pin_light":
            return self._blend_pin_light(base, overlay)
        elif mode == "hard_mix":
            return self._blend_hard_mix(base, overlay)
        
        # Difference group
        elif mode == "difference":
            return torch.abs(base - overlay)
        elif mode == "exclusion":
            return base + overlay - 2 * base * overlay
        elif mode == "subtract":
            return torch.clamp(base - overlay, 0, 1)
        elif mode == "divide":
            return self._blend_divide(base, overlay)
        
        # Color group
        elif mode == "hue":
            return self._blend_hue(base, overlay)
        elif mode == "saturation":
            return self._blend_saturation(base, overlay)
        elif mode == "color":
            return self._blend_color(base, overlay)
        elif mode == "luminosity":
            return self._blend_luminosity(base, overlay)
        
        else:
            return overlay  # Default to normal

    # Blend mode implementations
    def _blend_dissolve(self, base, overlay):
        """Dissolve blend mode using noise"""
        noise = torch.rand_like(base)
        mask = noise < 0.5
        return torch.where(mask, overlay, base)

    def _blend_color_burn(self, base, overlay):
        """Color burn blend mode"""
        return torch.where(
            overlay == 0,
            torch.zeros_like(base),
            torch.clamp(1 - (1 - base) / (overlay + 1e-8), 0, 1)
        )

    def _blend_color_dodge(self, base, overlay):
        """Color dodge blend mode"""
        return torch.where(
            overlay >= 1,
            torch.ones_like(base),
            torch.clamp(base / (1 - overlay + 1e-8), 0, 1)
        )

    def _blend_darker_color(self, base, overlay):
        """Darker color blend mode"""
        base_luma = self._rgb_to_luminance(base)
        overlay_luma = self._rgb_to_luminance(overlay)
        return torch.where(base_luma < overlay_luma, base, overlay)

    def _blend_lighter_color(self, base, overlay):
        """Lighter color blend mode"""
        base_luma = self._rgb_to_luminance(base)
        overlay_luma = self._rgb_to_luminance(overlay)
        return torch.where(base_luma > overlay_luma, base, overlay)

    def _blend_overlay(self, base, overlay):
        """Overlay blend mode"""
        return torch.where(
            base < 0.5,
            2 * base * overlay,
            1 - 2 * (1 - base) * (1 - overlay)
        )

    def _blend_soft_light(self, base, overlay):
        """Soft light blend mode (Photoshop algorithm)"""
        return torch.where(
            overlay <= 0.5,
            base - (1 - 2 * overlay) * base * (1 - base),
            base + (2 * overlay - 1) * (self._soft_light_aux(base) - base)
        )

    def _soft_light_aux(self, base):
        """Auxiliary function for soft light"""
        return torch.where(
            base <= 0.25,
            ((16 * base - 12) * base + 4) * base,
            torch.sqrt(base)
        )

    def _blend_hard_light(self, base, overlay):
        """Hard light blend mode"""
        return torch.where(
            overlay < 0.5,
            2 * base * overlay,
            1 - 2 * (1 - base) * (1 - overlay)
        )

    def _blend_vivid_light(self, base, overlay):
        """Vivid light blend mode"""
        return torch.where(
            overlay < 0.5,
            self._blend_color_burn(base, 2 * overlay),
            self._blend_color_dodge(base, 2 * (overlay - 0.5))
        )

    def _blend_linear_light(self, base, overlay):
        """Linear light blend mode"""
        return torch.clamp(base + 2 * overlay - 1, 0, 1)

    def _blend_pin_light(self, base, overlay):
        """Pin light blend mode"""
        return torch.where(
            overlay < 0.5,
            torch.min(base, 2 * overlay),
            torch.max(base, 2 * (overlay - 0.5))
        )

    def _blend_hard_mix(self, base, overlay):
        """Hard mix blend mode"""
        return torch.where(base + overlay < 1, torch.zeros_like(base), torch.ones_like(base))

    def _blend_divide(self, base, overlay):
        """Divide blend mode"""
        return torch.clamp(base / (overlay + 1e-8), 0, 1)

    # Color blend modes (HSL-based)
    def _blend_hue(self, base, overlay):
        """Hue blend mode"""
        base_hsl = self._rgb_to_hsl(base)
        overlay_hsl = self._rgb_to_hsl(overlay)
        result_hsl = torch.stack([
            overlay_hsl[..., 0],  # Use overlay hue
            base_hsl[..., 1],     # Keep base saturation
            base_hsl[..., 2]      # Keep base lightness
        ], dim=-1)
        return self._hsl_to_rgb(result_hsl)

    def _blend_saturation(self, base, overlay):
        """Saturation blend mode"""
        base_hsl = self._rgb_to_hsl(base)
        overlay_hsl = self._rgb_to_hsl(overlay)
        result_hsl = torch.stack([
            base_hsl[..., 0],     # Keep base hue
            overlay_hsl[..., 1],  # Use overlay saturation
            base_hsl[..., 2]      # Keep base lightness
        ], dim=-1)
        return self._hsl_to_rgb(result_hsl)

    def _blend_color(self, base, overlay):
        """Color blend mode"""
        base_hsl = self._rgb_to_hsl(base)
        overlay_hsl = self._rgb_to_hsl(overlay)
        result_hsl = torch.stack([
            overlay_hsl[..., 0],  # Use overlay hue
            overlay_hsl[..., 1],  # Use overlay saturation
            base_hsl[..., 2]      # Keep base lightness
        ], dim=-1)
        return self._hsl_to_rgb(result_hsl)

    def _blend_luminosity(self, base, overlay):
        """Luminosity blend mode"""
        base_hsl = self._rgb_to_hsl(base)
        overlay_hsl = self._rgb_to_hsl(overlay)
        result_hsl = torch.stack([
            base_hsl[..., 0],     # Keep base hue
            base_hsl[..., 1],     # Keep base saturation
            overlay_hsl[..., 2]   # Use overlay lightness
        ], dim=-1)
        return self._hsl_to_rgb(result_hsl)

    # Color space conversion utilities
    def _rgb_to_luminance(self, rgb):
        """Convert RGB to luminance"""
        weights = torch.tensor([0.2989, 0.5870, 0.1140], device=rgb.device)
        return torch.sum(rgb * weights, dim=-1, keepdim=True)

    def _rgb_to_hsl(self, rgb):
        """Convert RGB to HSL color space"""
        max_vals, max_indices = torch.max(rgb, dim=-1, keepdim=True)
        min_vals, _ = torch.min(rgb, dim=-1, keepdim=True)
        
        diff = max_vals - min_vals
        sum_vals = max_vals + min_vals
        
        # Lightness
        lightness = sum_vals / 2
        
        # Saturation
        saturation = torch.where(
            diff == 0,
            torch.zeros_like(diff),
            torch.where(
                lightness < 0.5,
                diff / sum_vals,
                diff / (2 - sum_vals)
            )
        )
        
        # Hue
        hue = torch.zeros_like(max_vals)
        
        # Red is max
        red_max = (max_indices.squeeze(-1) == 0)
        hue[red_max] = ((rgb[red_max, 1] - rgb[red_max, 2]) / diff[red_max].squeeze(-1)) % 6
        
        # Green is max
        green_max = (max_indices.squeeze(-1) == 1)
        hue[green_max] = (rgb[green_max, 2] - rgb[green_max, 0]) / diff[green_max].squeeze(-1) + 2
        
        # Blue is max
        blue_max = (max_indices.squeeze(-1) == 2)
        hue[blue_max] = (rgb[blue_max, 0] - rgb[blue_max, 1]) / diff[blue_max].squeeze(-1) + 4
        
        hue = hue / 6
        hue = hue.unsqueeze(-1)
        
        return torch.cat([hue, saturation, lightness], dim=-1)

    def _hsl_to_rgb(self, hsl):
        """Convert HSL to RGB color space"""
        h, s, l = hsl[..., 0], hsl[..., 1], hsl[..., 2]
        
        c = (1 - torch.abs(2 * l - 1)) * s
        x = c * (1 - torch.abs((h * 6) % 2 - 1))
        m = l - c / 2
        
        h_section = (h * 6).long()
        
        rgb = torch.zeros_like(hsl)
        
        # Section 0: R=c, G=x, B=0
        mask = (h_section == 0)
        rgb[mask] = torch.stack([c[mask], x[mask], torch.zeros_like(c[mask])], dim=-1)
        
        # Section 1: R=x, G=c, B=0
        mask = (h_section == 1)
        rgb[mask] = torch.stack([x[mask], c[mask], torch.zeros_like(c[mask])], dim=-1)
        
        # Section 2: R=0, G=c, B=x
        mask = (h_section == 2)
        rgb[mask] = torch.stack([torch.zeros_like(c[mask]), c[mask], x[mask]], dim=-1)
        
        # Section 3: R=0, G=x, B=c
        mask = (h_section == 3)
        rgb[mask] = torch.stack([torch.zeros_like(c[mask]), x[mask], c[mask]], dim=-1)
        
        # Section 4: R=x, G=0, B=c
        mask = (h_section == 4)
        rgb[mask] = torch.stack([x[mask], torch.zeros_like(c[mask]), c[mask]], dim=-1)
        
        # Section 5: R=c, G=0, B=x
        mask = (h_section == 5)
        rgb[mask] = torch.stack([c[mask], torch.zeros_like(c[mask]), x[mask]], dim=-1)
        
        return rgb + m.unsqueeze(-1)