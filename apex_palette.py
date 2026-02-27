#!/usr/bin/env python3
"""
Apex Palette Node - color quantization to retro palettes
Provides several video-game-style palettes (8-bit 3-3-2, NES, GameBoy, C64, CGA)
and optional simple dithering or palette extraction from an input image.
"""
import torch
import torch.nn.functional as F
import numpy as np


class ApexPalette:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "palette": ([
                    "8-bit (3-3-2)",
                    "NES",
                    "SNES",
                    "GameBoy",
                    "Commodore64",
                    "CGA",
                    "CustomFromImage"
                ], {"default": "8-bit (3-3-2)"}),
                "preset": ([
                    "None",
                    "8-bit Retro",
                    "SNES Clean",
                    "NES CRT",
                    "GameBoy Heavy Dither",
                    "C64 Palette",
                    "CGA TV",
                    "Custom Low (8)",
                    "Custom Mid (32)",
                    "Custom High (128)"
                ], {"default": "None"}),
                "dither": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {
                "palette_image": ("IMAGE",),
                "max_colors": ("INT", {"default": 64, "min": 2, "max": 256}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("palette_image", "palette_info")
    FUNCTION = "apply_palette"
    CATEGORY = "Apex Artist/Color"

    def apply_palette(self, image, palette="8-bit (3-3-2)", dither=0.0, strength=1.0, palette_image=None, max_colors=64, preset="None"):
        try:
            if image is None:
                raise ValueError("Image input is required")

            # Apply presets (override individual controls)
            if preset is None:
                preset = "None"
            if preset != "None":
                p = preset
                if p == "8-bit Retro":
                    palette = "8-bit (3-3-2)"
                    dither = 0.05
                    strength = 1.0
                    max_colors = 256
                elif p == "SNES Clean":
                    palette = "SNES"
                    dither = 0.01
                    strength = 1.0
                    max_colors = 256
                elif p == "NES CRT":
                    palette = "NES"
                    dither = 0.08
                    strength = 1.0
                    max_colors = 64
                elif p == "GameBoy Heavy Dither":
                    palette = "GameBoy"
                    dither = 0.25
                    strength = 1.0
                    max_colors = 4
                elif p == "C64 Palette":
                    palette = "Commodore64"
                    dither = 0.06
                    strength = 1.0
                    max_colors = 16
                elif p == "CGA TV":
                    palette = "CGA"
                    dither = 0.10
                    strength = 1.0
                    max_colors = 16
                elif p == "Custom Low (8)":
                    palette = "CustomFromImage"
                    dither = 0.05
                    strength = 1.0
                    max_colors = 8
                elif p == "Custom Mid (32)":
                    palette = "CustomFromImage"
                    dither = 0.03
                    strength = 1.0
                    max_colors = 32
                elif p == "Custom High (128)":
                    palette = "CustomFromImage"
                    dither = 0.01
                    strength = 1.0
                    max_colors = 128

            # Ensure batch dim
            if len(image.shape) == 3:
                image = image.unsqueeze(0)

            batch_size, height, width, channels = image.shape
            if channels < 3:
                raise ValueError("Image must have at least 3 channels (RGB)")

            # Prepare palette
            if palette == "CustomFromImage" and palette_image is not None:
                pal = self._extract_palette_from_image(palette_image, max_colors)
                pal_name = f"CustomFromImage ({pal.shape[0]} colors)"
            else:
                pal = self._get_palette_by_name(palette)
                pal_name = palette

            # Optionally add simple dithering noise
            img = image.clone()
            if dither and dither > 0.0:
                noise = (torch.rand_like(img) - 0.5) * (dither / 255.0)
                img = img + noise

            # Quantize: compute nearest palette color per pixel
            pixels = img.reshape(-1, channels)[:, :3]  # [N,3]
            pal_rgb = pal.to(pixels.device).to(pixels.dtype)

            # Compute distances and choose nearest
            # Use (a-b)^2 summed across channels
            # Expand for vectorized distance computation
            pixels_exp = pixels.unsqueeze(1)  # [N,1,3]
            pal_exp = pal_rgb.unsqueeze(0)    # [1,M,3]
            dists = ((pixels_exp - pal_exp) ** 2).sum(dim=2)  # [N,M]
            idx = torch.argmin(dists, dim=1)

            quant = pal_rgb[idx].view(batch_size, height, width, 3)

            # If input had alpha, preserve it
            if channels == 4:
                alpha = image[:, :, :, 3:4]
                quant = torch.cat([quant, alpha], dim=-1)

            # Blend based on strength
            result = image * (1.0 - strength) + quant * strength
            result = torch.clamp(result, 0.0, 1.0)

            info = f"Palette: {pal_name} | Colors: {pal.shape[0]} | Dither: {dither:.2f} | Strength: {strength:.2f}"
            if preset and preset != "None":
                info = f"Preset: {preset} | " + info
            return (result, info)

        except Exception as e:
            return (image, f"Error: {str(e)}")

    def _get_palette_by_name(self, name):
        name = name.lower()
        if name.startswith("8-bit") or name == "8-bit (3-3-2)":
            return self._make_332_palette()
        if name == "gameboy":
            return self._gameboy_palette()
        if name == "nes":
            return self._nes_palette()
        if name in ("commodore64", "c64"):
            return self._c64_palette()
        if name == "cga":
            return self._cga_palette()
        # default fallback to simple 8-bit
        return self._make_332_palette()

    def _make_332_palette(self):
        # 3 bits R, 3 bits G, 2 bits B -> 256 colors
        colors = []
        for r in range(8):
            for g in range(8):
                for b in range(4):
                    R = int(round((r / 7.0) * 255))
                    G = int(round((g / 7.0) * 255))
                    B = int(round((b / 3.0) * 255))
                    colors.append((R / 255.0, G / 255.0, B / 255.0))
        return torch.tensor(colors, dtype=torch.float32)

    def _gameboy_palette(self):
        # Classic DMG GameBoy greenish 4-shade palette
        hexes = ["#0f380f", "#306230", "#8bac0f", "#9bbc0f"]
        return self._hex_list_to_tensor(hexes)

    def _c64_palette(self):
        # Commodore 64 16-color approximation
        hexes = [
            "#000000","#FFFFFF","#884400","#AAFFEE","#CC44CC","#00CC55",
            "#0000AA","#EEEE77","#DD8855","#664400","#FF7777","#333333",
            "#777777","#AAFF66","#0088FF","#BBBBBB"
        ]
        return self._hex_list_to_tensor(hexes)

    def _cga_palette(self):
        # CGA 16-color approximation (common set)
        hexes = [
            "#000000","#0000AA","#00AA00","#00AAAA","#AA0000","#AA00AA",
            "#AA5500","#AAAAAA","#555555","#5555FF","#55FF55","#55FFFF",
            "#FF5555","#FF55FF","#FFFF55","#FFFFFF"
        ]
        return self._hex_list_to_tensor(hexes)

    def _nes_palette(self):
        # Small subset of the NES palette (representative colors)
        hexes = [
            # A small representative selection (not exhaustive)
            "#7C7C7C","#0000FC","#0000BC","#4428BC","#940084","#A80020",
            "#A81000","#881400","#503000","#007800","#006800","#005800",
            "#004058","#000000","#000000","#000000","#BCBCBC","#0078F8",
            "#0058F8","#6844FC","#D800CC","#E40058","#F83800","#E45C10",
            "#AC7C00","#00B800","#00A800","#00A844","#008888","#000000",
            "#000000","#000000","#F8F8F8","#3CBCFC","#6888FC","#9878F8",
            "#F878F8","#F85898","#F87858","#FCA044","#F8B800","#B8F818",
            "#58D854","#58F898","#00E8D8","#787878","#000000","#000000",
            "#FCFCFC","#A4E4FC","#B8B8F8","#D8B8F8","#F8B8F8","#F8A4C0",
            "#F0D0B0","#FCE0A8","#F8D878","#D8F878","#B8F8B8","#B8F8D8",
            "#00FCFC","#F8D8F8","#000000","#000000"
        ]
        return self._hex_list_to_tensor(hexes)

    def _snes_palette(self):
        # SNES uses 15-bit (5-5-5) color values. Generate full 32x32x32 palette.
        colors = []
        for r in range(32):
            for g in range(32):
                for b in range(32):
                    R = r * 255.0 / 31.0
                    G = g * 255.0 / 31.0
                    B = b * 255.0 / 31.0
                    colors.append((R / 255.0, G / 255.0, B / 255.0))
        return torch.tensor(colors, dtype=torch.float32)

    def _hex_list_to_tensor(self, hexes):
        colors = []
        for h in hexes:
            h = h.lstrip('#')
            r = int(h[0:2], 16) / 255.0
            g = int(h[2:4], 16) / 255.0
            b = int(h[4:6], 16) / 255.0
            colors.append((r, g, b))
        return torch.tensor(colors, dtype=torch.float32)

    def _extract_palette_from_image(self, image, max_colors=64):
        # Simple palette extraction: sample pixels, quantize to 8-bit, return unique colors
        if len(image.shape) == 3:
            image = image.unsqueeze(0)
        img = (image[:, :, :, :3] * 255.0).to(torch.uint8)
        pixels = img.reshape(-1, 3)
        uniq = torch.unique(pixels, dim=0)
        if uniq.shape[0] > max_colors:
            # pick evenly spaced subset
            indices = torch.linspace(0, uniq.shape[0] - 1, steps=max_colors).long()
            uniq = uniq[indices]
        uniq = uniq.float() / 255.0
        return uniq
