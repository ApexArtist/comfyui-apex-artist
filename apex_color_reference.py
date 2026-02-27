#!/usr/bin/env python3
"""
Apex Color Reference Node - Automatic color matching and curve generation
based on reference images
"""
import torch
import torch.nn.functional as F
import numpy as np

class ApexColorReference:
    """
    Analyzes reference images and generates matching curves for color grading
    Features:
    - Color histogram matching
    - Tone curve extraction
    - Channel-specific adjustments
    - Multiple matching methods
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "target_image": ("IMAGE",),
                "reference_image": ("IMAGE",),
                "matching_method": ([
                    "histogram_matching",    # Direct histogram matching
                    "curve_extraction",      # Extract curves from reference
                    "statistical",           # Match statistical properties
                    "zone_based",           # Match by luminance zones
                    "selective"             # Match specific tonal ranges
                ], {"default": "histogram_matching"}),
                "strength": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01
                }),
                "preserve_luminance": ("BOOLEAN", {
                    "default": True,
                    "label": "Preserve Luminance"
                }),
                "match_zones": ([
                    "all",
                    "shadows_only",
                    "midtones_only",
                    "highlights_only",
                    "shadows_midtones",
                    "midtones_highlights"
                ], {"default": "all"})
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("matched_image", "match_info")
    FUNCTION = "match_colors"
    CATEGORY = "ApexArtist/Color"

    def match_colors(self, target_image, reference_image, matching_method="histogram_matching",
                    strength=1.0, preserve_luminance=True, match_zones="all"):
        try:
            # Ensure images are in correct format
            if len(target_image.shape) == 3:
                target_image = target_image.unsqueeze(0)
            if len(reference_image.shape) == 3:
                reference_image = reference_image.unsqueeze(0)
            
            # Get histograms and curves based on method
            if matching_method == "histogram_matching":
                matched_image = self._histogram_matching(target_image, reference_image, strength)
            elif matching_method == "curve_extraction":
                matched_image = self._extract_curves(target_image, reference_image, strength)
            elif matching_method == "statistical":
                matched_image = self._statistical_matching(target_image, reference_image, strength)
            elif matching_method == "zone_based":
                matched_image = self._zone_based_matching(target_image, reference_image, match_zones, strength)
            else:  # selective
                matched_image = self._selective_matching(target_image, reference_image, match_zones, strength)
            
            # Apply preserve luminance if requested
            if preserve_luminance:
                matched_image = self._preserve_luminance(target_image, matched_image)
            
            # Generate match info
            match_info = self._generate_match_info(matching_method, strength, preserve_luminance, match_zones)
            
            return (matched_image, match_info)
            
        except Exception as e:
            print(f"Color matching error: {str(e)}")
            return (target_image, f"Error: {str(e)}")

    def _histogram_matching(self, target, reference, strength):
        """Fixed histogram matching with proper algorithm"""
        device = target.device
        result = target.clone()
        
        # Process each channel (keeping the working algorithm)
        for c in range(3):
            # Get channel data
            target_channel = target[0, :, :, c].flatten()
            ref_channel = reference[0, :, :, c].flatten()
            
            # Sort both channels (this is the correct approach)
            target_sorted, target_indices = torch.sort(target_channel)
            ref_sorted, _ = torch.sort(ref_channel)
            
            # Match distributions by mapping sorted values
            n_target = target_sorted.shape[0]
            n_ref = ref_sorted.shape[0]
            
            # Create index mapping for reference values
            ref_indices = torch.linspace(0, n_ref - 1, n_target, device=device)
            ref_indices = torch.clamp(ref_indices, 0, n_ref - 1).long()
            
            # Map target values to reference distribution
            mapped_values = ref_sorted[ref_indices]
            
            # Apply strength blending
            blended_values = target_sorted + strength * (mapped_values - target_sorted)
            
            # Put values back in original positions
            result_channel = torch.zeros_like(target_channel)
            result_channel[target_indices] = blended_values
            
            # Reshape back to image
            result[0, :, :, c] = result_channel.view(target.shape[1], target.shape[2])
        
        return torch.clamp(result, 0, 1)

    def _extract_curves(self, target, reference, strength):
        """Fixed curve extraction using reliable percentile mapping"""
        result = target.clone()
        
        # Use key percentiles for curve points
        percentiles = [0, 0.05, 0.25, 0.5, 0.75, 0.95, 1.0]
        
        # Process each channel
        for c in range(3):
            target_channel = target[0, :, :, c]
            ref_channel = reference[0, :, :, c]
            
            # Calculate percentiles for both images
            target_points = []
            ref_points = []
            
            for p in percentiles:
                target_points.append(torch.quantile(target_channel, p))
                ref_points.append(torch.quantile(ref_channel, p))
            
            target_points = torch.stack(target_points)
            ref_points = torch.stack(ref_points)
            
            # Create smooth mapping using linear interpolation
            flat_channel = target_channel.flatten()
            mapped_values = torch.zeros_like(flat_channel)
            
            # Map each pixel value using the curve points
            for i in range(len(percentiles) - 1):
                # Find pixels in this range
                mask = (flat_channel >= target_points[i]) & (flat_channel <= target_points[i + 1])
                
                if mask.any():
                    # Linear interpolation between curve points
                    t = (flat_channel[mask] - target_points[i]) / (target_points[i + 1] - target_points[i] + 1e-8)
                    mapped_values[mask] = ref_points[i] + t * (ref_points[i + 1] - ref_points[i])
            
            # Apply strength blending
            adjusted_channel = flat_channel + strength * (mapped_values - flat_channel)
            result[0, :, :, c] = adjusted_channel.view_as(target_channel)
        
        return torch.clamp(result, 0, 1)

    def _statistical_matching(self, target, reference, strength):
        """Match statistical properties between images"""
        result = target.clone()
        
        # Process each channel
        for c in range(3):
            target_channel = target[0,:,:,c]
            ref_channel = reference[0,:,:,c]
            
            # Calculate statistics
            t_mean = torch.mean(target_channel)
            t_std = torch.std(target_channel)
            r_mean = torch.mean(ref_channel)
            r_std = torch.std(ref_channel)
            
            # Apply statistical transformation
            normalized = (target_channel - t_mean) / (t_std + 1e-8)
            adjusted = normalized * r_std + r_mean
            
            # Blend with original based on strength
            result[0,:,:,c] = target_channel + strength * (adjusted - target_channel)
        
        return torch.clamp(result, 0, 1)

    def _zone_based_matching(self, target, reference, zones, strength):
        """Fixed zone-based matching with reliable algorithm"""
        result = target.clone()
        
        # Calculate luminance (standard rec709 weights)
        target_luma = 0.2989 * target[0, :, :, 0] + 0.5870 * target[0, :, :, 1] + 0.1140 * target[0, :, :, 2]
        ref_luma = 0.2989 * reference[0, :, :, 0] + 0.5870 * reference[0, :, :, 1] + 0.1140 * reference[0, :, :, 2]
        
        # Define zone boundaries
        zone_bounds = {
            "shadows": (0.0, 0.3),
            "midtones": (0.3, 0.7), 
            "highlights": (0.7, 1.0)
        }
        
        # Select active zones
        if zones == "all":
            active_zones = list(zone_bounds.keys())
        elif zones == "shadows_midtones":
            active_zones = ["shadows", "midtones"]
        elif zones == "midtones_highlights":
            active_zones = ["midtones", "highlights"]
        else:
            active_zones = [zones.replace("_only", "")]
        
        # Apply zone-based matching
        for zone in active_zones:
            low, high = zone_bounds[zone]
            
            # Create masks for the zone
            target_mask = (target_luma >= low) & (target_luma <= high)
            ref_mask = (ref_luma >= low) & (ref_luma <= high)
            
            if target_mask.any() and ref_mask.any():
                # Process each color channel
                for c in range(3):
                    # Get pixels in this zone
                    target_zone_pixels = target[0, :, :, c][target_mask]
                    ref_zone_pixels = reference[0, :, :, c][ref_mask]
                    
                    # Calculate zone statistics
                    target_mean = torch.mean(target_zone_pixels)
                    target_std = torch.std(target_zone_pixels)
                    ref_mean = torch.mean(ref_zone_pixels)
                    ref_std = torch.std(ref_zone_pixels)
                    
                    # Apply statistical matching within the zone
                    normalized = (target_zone_pixels - target_mean) / (target_std + 1e-8)
                    adjusted = normalized * ref_std + ref_mean
                    
                    # Blend with original based on strength
                    blended = target_zone_pixels + strength * (adjusted - target_zone_pixels)
                    
                    # Apply back to result
                    result[0, :, :, c][target_mask] = torch.clamp(blended, 0, 1)
        
        return result

    def _selective_matching(self, target, reference, zones, strength):
        """Selective color matching based on specified zones"""
        return self._zone_based_matching(target, reference, zones, strength)

    def _preserve_luminance(self, original, adjusted):
        """Preserve original luminance while keeping color changes"""
        # Calculate original luminance
        orig_luma = 0.2989 * original[0, :, :, 0] + 0.5870 * original[0, :, :, 1] + 0.1140 * original[0, :, :, 2]
        
        # Calculate adjusted luminance  
        adj_luma = 0.2989 * adjusted[0, :, :, 0] + 0.5870 * adjusted[0, :, :, 1] + 0.1140 * adjusted[0, :, :, 2]
        
        # Calculate ratio to preserve luminance
        ratio = torch.where(adj_luma > 1e-6, orig_luma / adj_luma, torch.ones_like(orig_luma))
        
        # Apply ratio to all channels
        result = adjusted.clone()
        for c in range(3):
            result[0, :, :, c] = adjusted[0, :, :, c] * ratio
        
        return torch.clamp(result, 0, 1)

    def _generate_match_info(self, method, strength, preserve_luminance, zones):
        """Generate information about the color matching"""
        info = [
            f"Color Match Method: {method}",
            f"Strength: {strength:.2f}",
            f"Preserve Luminance: {preserve_luminance}",
            f"Target Zones: {zones}"
        ]
        
        return " | ".join(info)