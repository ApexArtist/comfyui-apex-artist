"""
Apex Prompt Preset Selector Node
Professional prompt preset system with hierarchical categories, search, and dynamic management.
"""

import os
import json
import torch
import random
import re
from typing import Dict, List, Optional, Any

class ApexPromptPreset:
    """
    Advanced prompt preset selector with categorization, search, and management features.
    """
    
    def __init__(self):
        self.presets_file = os.path.join(os.path.dirname(__file__), "prompt_presets.json")
        self.presets = self.load_presets()
    
    @classmethod
    def INPUT_TYPES(cls):
        environment_presets = [
            "None", "Urban Racing Street"
        ]
        
        lighting_presets = [
            "None", "Apex Studio", "Professional Portrait", "Outdoor Afternoon", "Night Urban"
        ]
        
        return {
            "required": {
                "input_text": ("STRING", {"multiline": True, "default": ""}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "environment_preset": (environment_presets, {"default": "None"}),
                "lighting_preset": (lighting_presets, {"default": "None"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("combined_prompt", "environment_text", "lighting_text")
    FUNCTION = "combine_prompts"
    CATEGORY = "Apex Artist/Text"

    def load_presets(self) -> Dict[str, Any]:
        """Load presets from JSON file, create default if not exists."""
        if os.path.exists(self.presets_file):
            try:
                with open(self.presets_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading presets: {e}")
                return self.get_default_presets()
        else:
            presets = self.get_default_presets()
            self.save_presets(presets)
            return presets

    def save_presets(self, presets: Dict[str, Any]) -> None:
        """Save presets to JSON file."""
        try:
            with open(self.presets_file, 'w', encoding='utf-8') as f:
                json.dump(presets, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving presets: {e}")

    def get_default_presets(self) -> Dict[str, Any]:
        """Get comprehensive default preset collection."""
        return {
            "Apex Lighting": {
                "Apex Studio": {
                    "prompt": "A professional photography studio with clean white backdrop and walls. The subject is illuminated by carefully positioned studio lights creating even lighting across their face and body, with subtle rim lighting highlighting their edges and creating depth. The lighting setup produces soft, flattering illumination without harsh shadows.",
                    "description": "Professional studio lighting setup with even illumination and rim lighting",
                    "tags": ["studio", "professional", "clean", "even lighting"],
                    "weight": 1.3
                },
                "Professional Portrait": {
                    "prompt": "A high-contrast portrait photograph taken with professional studio lighting. The subject's skin tone appears natural and well-balanced under neutral daylight color temperature. The lighting creates a cinematic quality with soft, controlled shadows that add dimension without being harsh. The image shows true-to-life colors with natural skin texture where you can see fine details and pores. Clear highlights define facial features without overexposure, and there are no unwanted color casts or pink tints. The photograph has studio-grade exposure with sharp focus throughout.",
                    "description": "Professional high-contrast portrait with balanced skin tones and cinematic quality",
                    "tags": ["professional", "portrait", "high-contrast", "balanced", "cinematic"],
                    "weight": 1.3
                },
                "Outdoor Afternoon": {
                    "prompt": "Natural outdoor afternoon lighting with soft, warm daylight. The lighting is gentle and flattering, creating subtle shadows that add dimension to facial features without being harsh. The natural light has a warm, golden quality typical of afternoon sun, with soft highlights on the skin and hair.",
                    "description": "Natural outdoor afternoon lighting with warm, gentle daylight",
                    "tags": ["outdoor", "afternoon", "natural", "warm", "daylight"],
                    "weight": 1.2
                },
                "Night Urban": {
                    "prompt": "Clean, well-balanced white lighting that illuminates the subject with perfect color temperature and even coverage. The light is bright and pure white, creating crisp details and natural skin tones with excellent color accuracy. The lighting has a professional quality with no color cast, producing sharp, clean highlights and well-defined features with beautiful contrast.",
                    "description": "Clean, balanced white lighting perfect for nighttime urban photography",
                    "tags": ["night", "urban", "clean", "white", "balanced"],
                    "weight": 1.3
                }
            },
            "Apex Environment": {
                "Urban Racing Street": {
                    "prompt": "A nighttime urban street scene with sleek sports cars positioned on wet asphalt. The environment features glowing neon signs, colorful city lights reflecting on the street surface, and tall buildings creating an urban canyon. The atmosphere is moody and cinematic with a mix of warm and cool colored lights creating depth and visual interest.",
                    "description": "Nighttime urban street with racing cars and neon lights",
                    "tags": ["urban", "racing", "street", "neon", "cars"],
                    "weight": 1.3
                }
            }
        }


    def get_categories(self) -> List[str]:
        """Get list of all categories."""
        return list(self.presets.keys())

    def get_presets_in_category(self, category: str) -> List[str]:
        """Get preset names in a specific category."""
        if category in self.presets:
            return list(self.presets[category].keys())
        return []

    def get_all_preset_names(self) -> List[str]:
        """Get all preset names with category prefixes."""
        all_presets = []
        for category, presets in self.presets.items():
            for preset_name in presets.keys():
                all_presets.append(f"{category}/{preset_name}")
        return all_presets if all_presets else ["None"]

    def parse_preset_name(self, preset_name: str) -> tuple:
        """Parse category/preset format."""
        if "/" in preset_name:
            category, name = preset_name.split("/", 1)
            return category, name
        return "General", preset_name

    def get_preset_data(self, category: str, preset_name: str) -> Optional[Dict[str, Any]]:
        """Get specific preset data."""
        if category in self.presets and preset_name in self.presets[category]:
            return self.presets[category][preset_name]
        return None

    def apply_weight_multiplier(self, prompt: str, multiplier: float) -> str:
        """Apply weight multiplier to prompt elements."""
        if multiplier == 1.0:
            return prompt
        
        # Simple weight adjustment - wrap in parentheses with multiplier
        if multiplier > 1.0:
            return f"({prompt}:{multiplier:.1f})"
        else:
            return f"[{prompt}:{multiplier:.1f}]"

    def process_random_brackets(self, text: str, seed: int) -> str:
        """
        Process brackets with random selection.
        Example: "woman in a [flower field, alien landscape, new york street]"
        Will randomly pick one option from the bracketed list.
        """
        import random
        
        # Set random seed for reproducibility
        random.seed(seed)
        
        # Pattern to match [option1, option2, option3]
        pattern = r'\[([^\]]+)\]'
        
        def replace_bracket(match):
            # Get options from bracket content
            content = match.group(1)
            options = [opt.strip() for opt in content.split(',') if opt.strip()]
            
            if not options:
                return ""
            
            # Pick a random option based on the seed
            return random.choice(options)
        
        # Replace all brackets with random selections
        return re.sub(pattern, replace_bracket, text)

    def combine_prompts(self, input_text: str, seed: int = 0, environment_preset: str = "None", 
                       lighting_preset: str = "None") -> tuple:
        """Combine input text with environment and lighting prompts."""
        # Fallback if seed is None
        if seed is None:
            seed = 0
        
        # Process random brackets in input text first
        if input_text.strip():
            input_text = self.process_random_brackets(input_text, seed)
        
        # Get actual prompt text from presets if selected
        env_text = ""
        if environment_preset != "None":
            env_data = self.get_preset_data("Apex Environment", environment_preset)
            if env_data:
                env_text = env_data.get("prompt", "")
        
        light_text = ""
        if lighting_preset != "None":
            light_data = self.get_preset_data("Apex Lighting", lighting_preset)
            if light_data:
                light_text = light_data.get("prompt", "")
        
        # Combine all parts
        parts = []
        
        if input_text.strip():
            parts.append(input_text.strip())
            
        if env_text:
            parts.append(env_text)
            
        if light_text:
            parts.append(light_text)
        
        # Join with commas and clean up
        combined = ", ".join(parts)
        combined = self.clean_prompt(combined)
        
        return (combined, env_text, light_text)

    def clean_prompt(self, prompt: str) -> str:
        """Clean and format the final prompt."""
        # Remove extra commas and spaces
        prompt = ", ".join([part.strip() for part in prompt.split(",") if part.strip()])
        return prompt

# Node registration
NODE_CLASS_MAPPINGS = {
    "ApexPromptPreset": ApexPromptPreset
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ApexPromptPreset": "Apex Random Prompt"
}