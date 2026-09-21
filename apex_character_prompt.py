"""
Apex Character Prompt Node - Character prompt generator with preset categories.

This module provides:
- 12 character preset categories (gender, age, ethnicity, face, eye color, skin tone,
  hair, headwear, top, bottom, shoes, hand accessory)
- Facial feature presets focused on structure/shape; eye color and skin tone are
  separate independent categories so they can vary freely
- Weighted, seed-deterministic random selection per category
- One STRING output per category plus a combined character prompt prefixed by your own input text
- Preset storage in character_presets.json, managed by apex_character_prompt_api.py
  and the character preset API
"""

import json
import os
import hashlib
import random
import threading
from typing import Any, Dict, List

from .apex_prompt import ApexPromptPreset


class ApexCharacterPrompt:
    """
    Character prompt generator with independent preset storage.

    Reuses only stateless text helpers from ApexPromptPreset. Character storage and
    selection stay independent of the environment/lighting/style user library.
    """

    CATEGORY_GENDER = "Apex Character Gender"
    CATEGORY_AGE = "Apex Character Age"
    CATEGORY_ETHNICITY = "Apex Character Ethnicity"
    CATEGORY_FACE = "Apex Character Face"
    CATEGORY_EYE_COLOR = "Apex Character Eye Color"
    CATEGORY_SKIN_TONE = "Apex Character Skin Tone"
    CATEGORY_HAIR = "Apex Character Hair"
    CATEGORY_HEADWEAR = "Apex Character Headwear"
    CATEGORY_TOP = "Apex Character Top"
    CATEGORY_BOTTOM = "Apex Character Bottom"
    CATEGORY_SHOES = "Apex Character Shoes"
    CATEGORY_HAND = "Apex Character Hand Accessory"

    CHARACTER_CATEGORIES = (
        CATEGORY_GENDER,
        CATEGORY_AGE,
        CATEGORY_ETHNICITY,
        CATEGORY_FACE,
        CATEGORY_EYE_COLOR,
        CATEGORY_SKIN_TONE,
        CATEGORY_HAIR,
        CATEGORY_HEADWEAR,
        CATEGORY_TOP,
        CATEGORY_BOTTOM,
        CATEGORY_SHOES,
        CATEGORY_HAND,
    )


    PRESET_FILE_NAME = "character_presets.json"

    # mtime-keyed cache of the on-disk store (used to populate the dropdowns)
    _store_cache = {"mtime": None, "data": {}}
    _store_cache_lock = threading.Lock()

    def __init__(self):
        self.presets_file = os.path.join(os.path.dirname(__file__), self.PRESET_FILE_NAME)
        self.presets = self.load_presets()

    process_random_brackets = ApexPromptPreset.process_random_brackets
    clean_prompt = ApexPromptPreset.clean_prompt

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        path = os.path.join(os.path.dirname(__file__), cls.PRESET_FILE_NAME)
        try:
            with open(path, "rb") as stream:
                return hashlib.sha256(stream.read()).hexdigest()
        except FileNotFoundError:
            return "character-defaults"

    def get_preset_data(self, category, preset_name):
        return self.presets.get(category, {}).get(preset_name)

    def get_random_preset(self, category, seed):
        presets = self.presets.get(category, {})
        if not presets:
            return (None, None)
        names = list(presets)
        weights = [presets[name].get("weight", 1.0) for name in names]
        name = random.Random(seed).choices(names, weights=weights, k=1)[0]
        return (name, presets[name].get("prompt", ""))

    def _get_preset_text(self, category, preset_name, seed_offset):
        if preset_name == "Random":
            return self.get_random_preset(category, seed_offset)
        if preset_name in ("Disabled", "None"):
            return (preset_name, "")
        return (preset_name, (self.get_preset_data(category, preset_name) or {}).get("prompt", ""))

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "gender_preset": (cls._combo_options(cls.CATEGORY_GENDER), {"default": "Random"}),
                "age_preset": (cls._combo_options(cls.CATEGORY_AGE), {"default": "Random"}),
                "ethnicity_preset": (cls._combo_options(cls.CATEGORY_ETHNICITY), {"default": "Random"}),
                "face_preset": (cls._combo_options(cls.CATEGORY_FACE), {"default": "Random"}),
                "eye_color_preset": (cls._combo_options(cls.CATEGORY_EYE_COLOR), {"default": "Random"}),
                "skin_tone_preset": (cls._combo_options(cls.CATEGORY_SKIN_TONE), {"default": "Random"}),
                "hair_preset": (cls._combo_options(cls.CATEGORY_HAIR), {"default": "Random"}),
                "headwear_preset": (cls._combo_options(cls.CATEGORY_HEADWEAR), {"default": "Random"}),
                "top_preset": (cls._combo_options(cls.CATEGORY_TOP), {"default": "Random"}),
                "bottom_preset": (cls._combo_options(cls.CATEGORY_BOTTOM), {"default": "Random"}),
                "shoes_preset": (cls._combo_options(cls.CATEGORY_SHOES), {"default": "Random"}),
                "hand_accessory_preset": (cls._combo_options(cls.CATEGORY_HAND), {"default": "Random"}),
                # Free-text box for your own prompt (same idea as the Apex Prompt input box).
                # Appended last so existing workflows keep their positional widget values.
                "input_text": ("STRING", {"multiline": True, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING",) * 13
    RETURN_NAMES = (
        "combined_prompt",
        "gender",
        "age",
        "ethnic",
        "face",
        "eye_color",
        "skin_tone",
        "hair",
        "headwear",
        "top",
        "bottom",
        "shoes",
        "hand_accessory",
    )
    FUNCTION = "combine_prompts"
    CATEGORY = "Apex Artist/Text"
    DESCRIPTION = ("Character prompt generator: gender, age, ethnicity, facial features, eye color, "
                   "skin tone, hair, headwear, tops, bottoms, shoes, and hand accessories from preset categories, "
                   "with an optional free-text input box leading the combined prompt.")

    @classmethod
    def _combo_options(cls, category: str) -> List[str]:
        """Dropdown options for a category: Disabled, Random, then every preset name."""
        return ["Disabled", "Random"] + cls.get_all_presets_in_category(category)

    @classmethod
    def _store_data(cls) -> Dict[str, Any]:
        """Read character_presets.json, cached until the file changes."""
        path = os.path.join(os.path.dirname(__file__), cls.PRESET_FILE_NAME)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            return {}

        with cls._store_cache_lock:
            if mtime == cls._store_cache["mtime"]:
                return cls._store_cache["data"]

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            print(f"[Apex Character Prompt] Error loading {cls.PRESET_FILE_NAME}: {e}")
            return {}

        if not isinstance(data, dict):
            return {}

        with cls._store_cache_lock:
            cls._store_cache["mtime"] = mtime
            cls._store_cache["data"] = data
        return data

    @classmethod
    def get_all_presets_in_category(cls, category: str) -> List[str]:
        """Preset names for a category dropdown.

        The on-disk store is authoritative when it defines a non-empty category, so presets
        added, renamed, or deleted in the manager UI appear immediately. The built-in library
        is the fallback before character_presets.json exists.
        """
        store = cls._store_data()
        stored_category = store.get(category)
        if isinstance(stored_category, dict) and stored_category:
            return list(stored_category.keys())
        return list(cls.get_default_presets().get(category, {}).keys())

    def load_presets(self) -> Dict[str, Any]:
        """Load the character store, filling any missing category from the built-in library.

        An unreadable or malformed store degrades to the built-in library with a warning
        instead of raising, so a damaged JSON file cannot stop the node from loading. The
        damaged file is left untouched on disk for the user to repair.
        """
        try:
            with open(self.presets_file, "r", encoding="utf-8") as stream:
                presets = json.load(stream)
        except FileNotFoundError:
            presets = {}
        except (OSError, ValueError) as exc:
            print(f"[Apex Character Prompt] Cannot read {self.PRESET_FILE_NAME} ({exc}); "
                  f"using the built-in library. The file was left unchanged.")
            presets = {}
        merged: Dict[str, Any] = dict(presets) if isinstance(presets, dict) else {}
        for category, data in self.get_default_presets().items():
            if not isinstance(merged.get(category), dict) or not merged[category]:
                merged[category] = data
        return merged

    @staticmethod
    def get_default_presets() -> Dict[str, Any]:
        """Built-in character preset library (fallback data and store seed)."""
        return {
            ApexCharacterPrompt.CATEGORY_GENDER: _GENDER_PRESETS,
            ApexCharacterPrompt.CATEGORY_AGE: _AGE_PRESETS,
            ApexCharacterPrompt.CATEGORY_ETHNICITY: _ETHNICITY_PRESETS,
            ApexCharacterPrompt.CATEGORY_FACE: _FACE_PRESETS,
            ApexCharacterPrompt.CATEGORY_EYE_COLOR: _EYE_COLOR_PRESETS,
            ApexCharacterPrompt.CATEGORY_SKIN_TONE: _SKIN_TONE_PRESETS,
            ApexCharacterPrompt.CATEGORY_HAIR: _HAIR_PRESETS,
            ApexCharacterPrompt.CATEGORY_HEADWEAR: _HEADWEAR_PRESETS,
            ApexCharacterPrompt.CATEGORY_TOP: _TOP_PRESETS,
            ApexCharacterPrompt.CATEGORY_BOTTOM: _BOTTOM_PRESETS,
            ApexCharacterPrompt.CATEGORY_SHOES: _SHOES_PRESETS,
            ApexCharacterPrompt.CATEGORY_HAND: _HAND_ACCESSORY_PRESETS,
        }

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        """Accept any preset name.

        Presets can be added, renamed, or deleted through the character preset manager while a
        workflow is loaded, so validating against the static dropdown list would incorrectly
        reject those values when the prompt is queued.
        """
        return True

    def combine_prompts(self, input_text: str = "", seed: int = 0, gender_preset: str = "Random",
                        age_preset: str = "Random",
                        ethnicity_preset: str = "Random", face_preset: str = "Random",
                        eye_color_preset: str = "Random", skin_tone_preset: str = "Random",
                        hair_preset: str = "Random", headwear_preset: str = "Random",
                        top_preset: str = "Random", bottom_preset: str = "Random",
                        shoes_preset: str = "Random", hand_accessory_preset: str = "Random") -> tuple:
        """Combine the optional free-text input with every preset category.

        Category order: gender, age, ethnicity, face, eye color, skin tone, hair, headwear,
        top, bottom, shoes, hand accessory. Each category is resolved with its own seed
        offset, so the same seed always produces the same character while a different seed
        produces a different look. The input box leads the combined prompt, supports its own
        [option a, option b] brackets, and never appears in the per-category outputs.
        """
        seed = seed if seed is not None else 0

        # The input box keeps its own [option a, option b] bracket support, seeded with the plain
        # seed so it stays independent of the preset seed offsets (1-12) used below.
        user_text = input_text.strip() if isinstance(input_text, str) else ""
        if "[" in user_text:
            user_text = self.process_random_brackets(user_text, seed).strip()
        self.presets = self.load_presets()

        selections = (
            (self.CATEGORY_GENDER, gender_preset, 1),
            (self.CATEGORY_AGE, age_preset, 2),
            (self.CATEGORY_ETHNICITY, ethnicity_preset, 3),
            (self.CATEGORY_FACE, face_preset, 4),
            (self.CATEGORY_EYE_COLOR, eye_color_preset, 5),
            (self.CATEGORY_SKIN_TONE, skin_tone_preset, 6),
            (self.CATEGORY_HAIR, hair_preset, 7),
            (self.CATEGORY_HEADWEAR, headwear_preset, 8),
            (self.CATEGORY_TOP, top_preset, 9),
            (self.CATEGORY_BOTTOM, bottom_preset, 10),
            (self.CATEGORY_SHOES, shoes_preset, 11),
            (self.CATEGORY_HAND, hand_accessory_preset, 12),
        )

        texts: List[str] = []
        for category, preset_name, offset in selections:
            _selected_name, text = self._get_preset_text(category, preset_name, seed + offset)
            text = (text or "").strip()
            # Support [option a, option b] variants inside a preset for extra variety
            if "[" in text:
                text = self.process_random_brackets(text, seed + offset).strip()
            texts.append(text)

        # Trim trailing periods (and repeats) so segments join cleanly for the combined prompt.
        # The input box leads the prompt; it is never part of the per-category outputs.
        parts = [user_text] + [t.rstrip(". ") for t in texts if t]
        combined = self.clean_prompt(", ".join([part.rstrip(". ") for part in parts if part]))
        return (combined, *texts)


# Node registration
NODE_CLASS_MAPPINGS = {
    "ApexCharacterPrompt": ApexCharacterPrompt
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ApexCharacterPrompt": "Apex Character Prompt"
}


# --------------------------------------------------------------------------------------
# Built-in character preset library
# Each preset stores: prompt, description, tags, weight (1.0 - 1.3 for random variety).
# prompts are written as positive fragments so they concatenate cleanly into a positive
# prompt slot. Run scripts/generate_character_presets.py to refresh character_presets.json.
# --------------------------------------------------------------------------------------

_GENDER_PRESETS = {
    "Female": {
        "prompt": "female",
        "description": "Female character",
        "tags": ["female", "woman"],
        "weight": 1.2
    },
    "Male": {
        "prompt": "male",
        "description": "Male character",
        "tags": ["male", "man"],
        "weight": 1.2
    },
    "Androgynous": {
        "prompt": "androgynous",
        "description": "Androgynous character",
        "tags": ["androgynous", "gender neutral"],
        "weight": 1.0
    },
    "Non-Binary": {
        "prompt": "non-binary",
        "description": "Non-binary character",
        "tags": ["non-binary", "neutral"],
        "weight": 0.9
    },
    "Soft Feminine Male": {
        "prompt": "soft feminine male",
        "description": "Male with soft feminine features",
        "tags": ["male", "soft", "delicate"],
        "weight": 0.9
    },
    "Tomboyish Female": {
        "prompt": "tomboyish female",
        "description": "Tomboyish female",
        "tags": ["female", "tomboy"],
        "weight": 0.9
    },
    "Trans Feminine": {
        "prompt": "trans feminine",
        "description": "Trans feminine character",
        "tags": ["trans feminine"],
        "weight": 0.8
    },
    "Trans Masculine": {
        "prompt": "trans masculine",
        "description": "Trans masculine character",
        "tags": ["trans masculine"],
        "weight": 0.8
    }
}

_AGE_PRESETS = {
    "Teens 13-17": {
        "prompt": "13-17 years old",
        "description": "Teenage youth",
        "tags": ["teen", "13-17"],
        "weight": 1.0
    },
    "Young Adult 18-21": {
        "prompt": "18-21 years old",
        "description": "Young adult",
        "tags": ["young adult", "18-21"],
        "weight": 1.1
    },
    "Early Twenties 22-25": {
        "prompt": "22-25 years old",
        "description": "Early twenties",
        "tags": ["early twenties", "22-25"],
        "weight": 1.2
    },
    "Mid Twenties 26-29": {
        "prompt": "26-29 years old",
        "description": "Mid twenties",
        "tags": ["mid twenties", "26-29"],
        "weight": 1.2
    },
    "Early Thirties 30-35": {
        "prompt": "30-35 years old",
        "description": "Early thirties",
        "tags": ["thirties", "30-35"],
        "weight": 1.1
    },
    "Late Thirties 36-39": {
        "prompt": "36-39 years old",
        "description": "Late thirties",
        "tags": ["late thirties", "36-39"],
        "weight": 1.0
    },
    "Forties 40-49": {
        "prompt": "40-49 years old",
        "description": "Forties",
        "tags": ["forties", "40-49"],
        "weight": 1.0
    },
    "Fifties 50-59": {
        "prompt": "50-59 years old",
        "description": "Fifties",
        "tags": ["fifties", "50-59"],
        "weight": 0.9
    },
    "Sixties 60-69": {
        "prompt": "60-69 years old",
        "description": "Sixties",
        "tags": ["sixties", "60-69"],
        "weight": 0.9
    },
    "Seventy Plus": {
        "prompt": "70+ years old",
        "description": "Elderly senior",
        "tags": ["elderly", "70+"],
        "weight": 0.8
    },
    "Ageless Timeless": {
        "prompt": "ageless",
        "description": "Ageless character",
        "tags": ["ageless", "timeless"],
        "weight": 0.9
    }
}

_ETHNICITY_PRESETS = {
    "European Caucasian": {
        "prompt": "European Caucasian heritage, fair to lightly tanned skin with natural texture, softly structured European facial features, Western European appearance",
        "description": "European Caucasian heritage",
        "tags": ["european", "caucasian", "western", "fair skin"],
        "weight": 1.2
    },
    "Nordic Scandinavian": {
        "prompt": "Nordic Scandinavian heritage, fair cool-toned skin, light blonde hair tones, pale blue or grey eyes, northern European facial structure",
        "description": "Nordic Scandinavian heritage",
        "tags": ["nordic", "scandinavian", "fair skin", "blonde", "pale eyes"],
        "weight": 1.1
    },
    "Mediterranean Southern European": {
        "prompt": "Mediterranean southern European heritage, warm olive-toned skin, dark hair with deep-set dark eyes, southern European facial structure",
        "description": "Mediterranean southern European heritage",
        "tags": ["mediterranean", "olive skin", "southern european", "dark hair"],
        "weight": 1.1
    },
    "Slavic Eastern European": {
        "prompt": "Slavic eastern European heritage, fair skin with cool undertones, softly defined cheekbones, light brown to dark hair, eastern European facial structure",
        "description": "Slavic eastern European heritage",
        "tags": ["slavic", "eastern european", "fair skin", "cheekbones"],
        "weight": 1.0
    },
    "British Isles": {
        "prompt": "British Isles heritage, fair skin with rosy undertones, light brown or auburn hair, softly freckled complexion, northwestern European facial features",
        "description": "British Isles heritage",
        "tags": ["british", "irish", "fair skin", "rosy", "freckles"],
        "weight": 1.0
    },
    "East Asian": {
        "prompt": "East Asian heritage, fair porcelain-toned skin, softly almond-shaped dark eyes, straight glossy dark hair, refined East Asian facial structure",
        "description": "East Asian heritage",
        "tags": ["east asian", "porcelain", "almond eyes", "dark hair"],
        "weight": 1.2
    },
    "Southeast Asian": {
        "prompt": "Southeast Asian heritage, warm golden-toned skin, softly rounded facial features, dark almond eyes, glossy dark hair, Southeast Asian appearance",
        "description": "Southeast Asian heritage",
        "tags": ["southeast asian", "golden skin", "warm", "dark hair"],
        "weight": 1.1
    },
    "South Asian": {
        "prompt": "South Asian heritage, warm bronze skin, large expressive dark eyes with long lashes, strong dark brows, glossy dark hair, South Asian facial structure",
        "description": "South Asian heritage",
        "tags": ["south asian", "bronze skin", "expressive eyes", "dark hair"],
        "weight": 1.1
    }
}

_ETHNICITY_PRESETS.update({
    "Central Asian": {
        "prompt": "Central Asian heritage, warm light-tan skin, softly almond-shaped dark eyes, high gentle cheekbones, dark hair, Central Asian facial structure",
        "description": "Central Asian heritage",
        "tags": ["central asian", "tan skin", "almond eyes", "cheekbones"],
        "weight": 1.0
    },
    "Middle Eastern": {
        "prompt": "Middle Eastern heritage, warm olive-to-bronze skin, large dark expressive eyes with thick lashes, strong well-defined brows, dark hair, Middle Eastern facial structure",
        "description": "Middle Eastern heritage",
        "tags": ["middle eastern", "olive skin", "dark eyes", "strong brows"],
        "weight": 1.1
    },
    "Black African": {
        "prompt": "Black African heritage, rich deep skin tones with a luminous natural sheen, full softly arched lips, high elegant cheekbones, tightly coiled dark hair, West African facial structure",
        "description": "Black African heritage",
        "tags": ["black african", "deep skin", "full lips", "cheekbones"],
        "weight": 1.1
    },
    "Afro-Caribbean": {
        "prompt": "Afro-Caribbean heritage, warm deep brown skin with golden undertones, bright expressive dark eyes, softly rounded facial features, natural coiled hair, Caribbean facial structure",
        "description": "Afro-Caribbean heritage",
        "tags": ["afro-caribbean", "deep skin", "golden undertones", "expressive"],
        "weight": 1.0
    },
    "North African": {
        "prompt": "North African heritage, warm olive-bronze skin, deep-set dark eyes, softly defined cheekbones, glossy dark curly hair, North African facial structure",
        "description": "North African heritage",
        "tags": ["north african", "olive skin", "dark eyes", "curly hair"],
        "weight": 1.0
    },
    "Latin American Hispanic": {
        "prompt": "Latin American Hispanic heritage, warm sun-kissed tan skin, expressive dark brown eyes, softly arched brows, full lips, glossy dark hair, Latin American facial structure",
        "description": "Latin American Hispanic heritage",
        "tags": ["latin american", "hispanic", "tan skin", "full lips"],
        "weight": 1.1
    },
    "Indigenous American": {
        "prompt": "Indigenous American heritage, warm copper-toned skin, high defined cheekbones, dark almond eyes, long straight dark hair, Indigenous American facial structure",
        "description": "Indigenous American heritage",
        "tags": ["indigenous american", "copper skin", "cheekbones", "dark hair"],
        "weight": 1.0
    },
    "Pacific Islander": {
        "prompt": "Pacific Islander heritage, warm golden-brown skin, softly rounded facial features, bright dark eyes, thick dark wavy hair, Polynesian facial structure",
        "description": "Pacific Islander heritage",
        "tags": ["pacific islander", "golden skin", "wavy hair", "warm"],
        "weight": 1.0
    },
    "Mixed Heritage": {
        "prompt": "Mixed heritage appearance, blended warm skin tones, harmonized facial features drawn from multiple ethnicities, naturally balanced structure, effortlessly international beauty",
        "description": "Mixed heritage character with blended features",
        "tags": ["mixed heritage", "blended", "international", "balanced"],
        "weight": 1.1
    }
})

_FACE_PRESETS = {
    "Universal Beauty": {
        "prompt": "Delicate youthful feminine face with a soft oval-to-tapered shape, gently rounded cheeks, softly defined high cheekbones, noticeably slim lower face, smooth narrow jawline curving inward gradually toward a small softly rounded chin, compact balanced mid-face proportions, large almond-shaped eyes with gently lifted outer corners and a large eye-to-face ratio, softly arched natural eyebrows, small delicate straight nose with a narrow bridge and softly rounded petite tip, softly full lips with a naturally defined Cupid's bow and slightly fuller lower lip, smooth rounded facial contours, delicate feminine bone structure, harmonious proportions, fair porcelain skin with a faint natural flush across the cheeks, realistic skin texture with visible pores and natural detail, naturally youthful appearance, serene gentle expression.",
        "description": "Universal delicate beauty - merged Pale Porcelain structure with Micro Drama naturalism",
        "tags": ["universal", "delicate", "porcelain", "oval face", "almond eyes", "natural", "youthful", "refined"],
        "weight": 1.3
    },
    "American Beauty": {
        "prompt": "Small compact oval-to-heart-shaped face with distinctly youthful late-teen proportions, softly rounded upper cheeks, gentle natural cheek fullness, short soft midface, narrow lower face, clean delicately tapered jawline ending in a small refined chin, natural Caucasian-American facial characteristics with balanced understated proportions, large expressive almond-shaped to softly rounded eyes with youthful openness, naturally defined upper lashes, softly straight medium-dark eyebrows with a gentle low arch and naturally tapered ends, small refined Caucasian nose with a narrow-to-medium straight bridge, neat nostrils, softly defined nasal tip and natural subtle projection, naturally full rose-colored lips with a clearly defined Cupid's bow, slightly fuller lower lip, soft relaxed mouth, balanced near-symmetrical facial proportions, delicate features, gentle transitions between forehead, cheeks, nose, jaw and chin, youthful naturally realistic facial structure with understated realistic beauty, Euro-American Western facial structure, moderately narrow face width, soft rounded cheek volume, subtle softly blending cheekbones, softly curved facial contours, compact short face length, small narrow moderately projecting nose, rounded soft chin, proportionally natural eye size, clean bare-faced natural look, subtle natural facial modeling, realistic skin texture with visible fine pores and natural detail.",
        "description": "American beauty - youthful classic Western look, delicate balanced proportions",
        "tags": ["american", "western", "youthful", "classic beauty", "caucasian"],
        "weight": 1.3
    },
    "K-Idol Soft": {
        "prompt": "Korean idol beauty, soft rounded cheeks, softly straight dark brows, gentle monolid or softly creased eyes, gradient soft pink lips, delicate small nose, glass skin finish with subtle dewy highlighter, clean youthful features, elegant natural minimal makeup.",
        "description": "K-idol look with porcelain glass skin and gradient lips",
        "tags": ["k-beauty", "idol", "porcelain", "glass skin", "soft"],
        "weight": 1.2
    },
    "Editorial High Fashion": {
        "prompt": "High fashion editorial face, striking sculpted cheekbones, defined angular jawline, bold groomed eyebrows, deep-set dramatic eyes, matte flawless complexion, sharp elegant features, couture runway beauty, confident closed-lip expression, refined editorial makeup.",
        "description": "Runway editorial beauty with sculpted features",
        "tags": ["editorial", "fashion", "sculpted", "runway", "bold"],
        "weight": 1.1
    }
}

_FACE_PRESETS.update({
    "Girl Next Door": {
        "prompt": "Fresh natural girl next door beauty, light freckles across the nose, rosy cheeks, soft natural brows, subtle glossy pink lips, minimal clean makeup, approachable friendly expression, healthy realistic skin texture.",
        "description": "Fresh approachable beauty with light freckles",
        "tags": ["natural", "freckles", "fresh", "girl next door", "approachable"],
        "weight": 1.2
    },
    "Hollywood Classic": {
        "prompt": "Classic Hollywood cinematic beauty, elegantly arched defined eyebrows, deep expressive eyes with soft lashes, sculpted cheekbones, glossy deep red lips, smooth luminous complexion, glamorous timeless features, polished silver-screen elegance, refined vintage glamour.",
        "description": "Timeless silver-screen glamour with red lips",
        "tags": ["hollywood", "classic", "glamour", "red lips", "cinematic"],
        "weight": 1.1
    },
    "Ethereal Elf": {
        "prompt": "Ethereal elven beauty, subtly pointed graceful ears, large luminous eyes, softly feathered brows, delicate slender nose, soft petal lips, otherworldly serene expression, gentle fairy-like glow with faint luminous shimmer.",
        "description": "Otherworldly elven beauty with luminous glow",
        "tags": ["ethereal", "elf", "fantasy", "luminous", "delicate"],
        "weight": 1.0
    },
    "Nordic Cool": {
        "prompt": "Nordic Scandinavian beauty, high soft cheekbones, light ash-blonde eyebrows, narrow straight nose, subtle natural rose lips, calm cool expression, fresh clean minimal makeup, wintery pale elegance.",
        "description": "Nordic cool beauty with delicate pale features",
        "tags": ["nordic", "cool", "scandinavian", "pale", "elegant"],
        "weight": 1.1
    },
    "Mediterranean Warm": {
        "prompt": "Mediterranean beauty, deep-set expressive eyes, strong dark well-defined eyebrows, straight sculpted nose, full glossy lips with warm rose tone, softly defined cheekbones, lively warm expression.",
        "description": "Sun-kissed Mediterranean warmth with deep expressive eyes",
        "tags": ["mediterranean", "warm", "expressive", "full lips", "european"],
        "weight": 1.1
    },
    "East Asian Delicate": {
        "prompt": "Refined East Asian beauty, delicate oval face, softly almond-shaped eyes with subtle eyeliner, gently arched thin brows, small refined nose, softly tinted lips, smooth radiant complexion, elegant minimal makeup, graceful delicate features.",
        "description": "Refined East Asian beauty with delicate graceful features",
        "tags": ["east asian", "porcelain", "delicate", "refined", "elegant"],
        "weight": 1.2
    },
    "Afrocentric Radiance": {
        "prompt": "Radiant Afrocentric beauty, striking wide-set expressive eyes, full softly arched eyebrows, high elegant cheekbones, beautifully full lips, defined nose with soft rounded tip, vibrant confident features, healthy glowing skin with natural texture.",
        "description": "Radiant beauty with full lips and strong cheekbones",
        "tags": ["afrocentric", "radiant", "full lips", "glowing", "confident"],
        "weight": 1.1
    },
    "South Asian Grace": {
        "prompt": "Graceful South Asian beauty, large expressive almond eyes with long lashes, strong sculpted eyebrows, softly defined cheekbones, elegant straight nose, full natural lips with warm rose tone, refined classic features, elegant graceful expression.",
        "description": "Graceful beauty with expressive almond eyes and full lips",
        "tags": ["south asian", "expressive", "graceful", "elegant", "full lips"],
        "weight": 1.1
    },
    "Latina Spark": {
        "prompt": "Vibrant Latina beauty, large expressive eyes, softly arched defined brows, prominent natural cheekbones, full glossy lips, softly rounded nose, lively confident expression, energetic warm beauty.",
        "description": "Vibrant beauty with full lips and strong cheekbones",
        "tags": ["latina", "vivacious", "full lips", "cheekbones", "confident"],
        "weight": 1.1
    },
    "Gothic Porcelain": {
        "prompt": "Gothic porcelain beauty, sharp expressive eyes with heavy natural lashes, dark arched brows, delicate straight nose, deep plum or black lips, soft contrasting pale features, moody elegant alternative beauty.",
        "description": "Gothic beauty with dark lips and sharp expressive eyes",
        "tags": ["gothic", "pale", "porcelain", "dark lips", "alternative"],
        "weight": 1.0
    },
    "Freckled Fresh": {
        "prompt": "Fresh freckled beauty, a warm scattering of freckles across the nose and cheeks, soft light brows, natural pink lips, healthy outdoor glow, natural bare skin texture, youthful lively expression.",
        "description": "Sun-kissed freckled look with a healthy outdoor glow",
        "tags": ["freckles", "fresh", "sun-kissed", "natural", "youthful"],
        "weight": 1.1
    },
    "Mature Elegance": {
        "prompt": "Timeless mature elegance, refined gently matured features, softly defined cheekbones, poised groomed brows, calm knowing expressive eyes with subtle fine lines, elegant natural lips, smooth dignified complexion, graceful self-assured expression, sophisticated beauty with character.",
        "description": "Refined mature beauty with poised elegant features",
        "tags": ["mature", "elegant", "refined", "timeless", "sophisticated"],
        "weight": 1.0
    },
    "Athlete Sun-Kissed": {
        "prompt": "Athletic sun-kissed beauty, healthy natural texture, bright clear eyes, straight clean eyebrows, defined jaw, softly balanced features, small natural athletic nose, neutral relaxed mouth, clean fresh-faced look, energetic healthy appearance.",
        "description": "Healthy athletic look with clean energetic features",
        "tags": ["athletic", "sun-kissed", "healthy", "clean", "fresh-faced"],
        "weight": 1.0
    },
    "Square Eyes": {
        "prompt": "Soft oval face shape with naturally balanced proportions, gently rounded cheeks, a smooth softly curved jawline tapering into a subtly rounded chin, moderate cheekbone definition with soft transitions, a relatively short balanced mid-face, distinctive horizontally elongated rectangular-shaped eyes with relatively straight upper and lower eyelid contours and softly rounded inner and outer corners, medium-to-large eye openings with a naturally horizontal appearance rather than an almond shape, pale blue-grey irises, naturally defined upper lashes, dark medium-thick eyebrows with a softly straight shape and gentle low arch, a delicate straight nose with a narrow-to-medium bridge and softly rounded natural tip, naturally proportioned nose projection, subtly full lips with a clearly defined Cupid's bow and slightly fuller lower lip, balanced mouth width, soft natural lip contours, harmonious facial feature spacing, gentle transitions between the forehead, eyes, cheeks, nose, lips, jaw, and chin, realistic natural facial asymmetry and refined human facial proportions.",
        "description": "Soft oval face with distinctive horizontally elongated rectangular-shaped eyes",
        "tags": ["square eyes", "horizontal eyes", "oval face", "soft", "balanced"],
        "weight": 1.2
    }
})

_EYE_COLOR_PRESETS = {
    "Dark Brown": {
        "prompt": "dark brown eyes, deep rich brown irises with warm depth, natural dark lashes",
        "description": "Deep warm dark brown eyes",
        "tags": ["dark brown", "deep", "warm", "natural"],
        "weight": 1.3
    },
    "Medium Brown": {
        "prompt": "medium brown eyes, warm mid-tone brown irises with subtle golden flecks, soft natural lashes",
        "description": "Warm medium brown eyes with golden flecks",
        "tags": ["medium brown", "warm", "golden flecks", "natural"],
        "weight": 1.2
    },
    "Hazel": {
        "prompt": "hazel eyes, shifting blend of green and brown tones in the iris, soft warm mixed hue, natural lashes",
        "description": "Warm hazel eyes with green-brown tones",
        "tags": ["hazel", "green-brown", "warm", "mixed"],
        "weight": 1.2
    },
    "Amber": {
        "prompt": "amber eyes, warm golden-yellow to light brown irises with a glowing honey tone, striking natural lashes",
        "description": "Striking warm amber honey-toned eyes",
        "tags": ["amber", "honey", "golden", "warm"],
        "weight": 1.1
    },
    "Green": {
        "prompt": "green eyes, vivid natural green irises with subtle variation in depth, bright expressive lashes",
        "description": "Vivid natural green eyes",
        "tags": ["green", "vivid", "natural", "expressive"],
        "weight": 1.1
    },
    "Blue-Green": {
        "prompt": "blue-green eyes, shifting teal to seafoam irises with cool-warm variation, expressive bright lashes",
        "description": "Shifting teal blue-green eyes",
        "tags": ["blue-green", "teal", "seafoam", "shifting"],
        "weight": 1.1
    },
    "Light Blue": {
        "prompt": "light blue eyes, pale cool blue irises with a soft clear clarity, delicate natural lashes",
        "description": "Pale soft light blue eyes",
        "tags": ["light blue", "pale", "cool", "clear"],
        "weight": 1.2
    },
    "Deep Blue": {
        "prompt": "deep blue eyes, intense dark blue irises with rich ocean-like depth, defined natural lashes",
        "description": "Intense deep blue eyes with ocean depth",
        "tags": ["deep blue", "intense", "ocean", "dark"],
        "weight": 1.1
    },
    "Gray": {
        "prompt": "gray eyes, cool neutral gray irises with subtle silver undertones, soft pale natural lashes",
        "description": "Cool silver-gray eyes",
        "tags": ["gray", "silver", "cool", "neutral"],
        "weight": 1.0
    },
    "Gray-Blue": {
        "prompt": "gray-blue eyes, soft silvery-blue irises with a gentle cool mist tone, delicate natural lashes",
        "description": "Soft mist-toned gray-blue eyes",
        "tags": ["gray-blue", "silver", "mist", "cool"],
        "weight": 1.1
    },
    "Black": {
        "prompt": "black eyes, very dark near-black irises with deep glossy depth, strong natural lashes",
        "description": "Very dark near-black deep eyes",
        "tags": ["black", "very dark", "deep", "glossy"],
        "weight": 1.1
    },
    "Violet": {
        "prompt": "violet eyes, rare soft purple-toned irises with a luminous ethereal quality, delicate expressive lashes",
        "description": "Rare luminous violet purple eyes",
        "tags": ["violet", "purple", "rare", "ethereal", "luminous"],
        "weight": 0.8
    },
    "Heterochromia": {
        "prompt": "heterochromia, one eye a different color from the other, each iris distinctly colored, striking rare eye feature",
        "description": "Striking heterochromia with differently colored eyes",
        "tags": ["heterochromia", "two-colored", "rare", "striking"],
        "weight": 0.7
    },
    "Pale Icy Blue": {
        "prompt": "pale icy blue eyes, very light almost white-blue irises with a cool crystalline clarity, striking pale lashes",
        "description": "Pale icy crystalline blue eyes",
        "tags": ["icy blue", "pale", "crystalline", "nordic", "cool"],
        "weight": 1.0
    }
}

_SKIN_TONE_PRESETS = {
    "Porcelain": {
        "prompt": "porcelain skin, very fair cool-toned complexion with delicate translucency, smooth refined texture",
        "description": "Very fair cool porcelain skin",
        "tags": ["porcelain", "very fair", "cool", "translucent", "pale"],
        "weight": 1.2
    },
    "Fair Cool": {
        "prompt": "fair cool-toned skin, light complexion with cool pink undertone, soft even texture, natural healthy pallor",
        "description": "Fair skin with cool pink undertones",
        "tags": ["fair", "cool", "pink undertone", "light"],
        "weight": 1.2
    },
    "Fair Warm": {
        "prompt": "fair warm-toned skin, light complexion with subtle warm peachy-yellow undertone, soft natural even texture",
        "description": "Fair skin with warm peachy undertones",
        "tags": ["fair", "warm", "peachy", "light", "natural"],
        "weight": 1.2
    },
    "Light Ivory": {
        "prompt": "light ivory skin, softly neutral to warm ivory complexion, smooth even natural texture, healthy gentle glow",
        "description": "Soft natural ivory skin",
        "tags": ["ivory", "light", "neutral", "soft", "natural"],
        "weight": 1.1
    },
    "Olive": {
        "prompt": "olive skin, warm medium-toned complexion with a natural olive-green undertone, smooth even texture",
        "description": "Warm medium olive-toned skin",
        "tags": ["olive", "warm", "medium", "mediterranean", "natural"],
        "weight": 1.2
    },
    "Light Tan": {
        "prompt": "light tan skin, warm lightly sun-kissed complexion with a golden peachy undertone, soft healthy natural texture",
        "description": "Lightly sun-kissed warm tan skin",
        "tags": ["light tan", "sun-kissed", "warm", "golden", "peachy"],
        "weight": 1.1
    },
    "Golden Tan": {
        "prompt": "golden tan skin, warm medium golden-brown complexion with a rich sun-warmed undertone, smooth luminous texture",
        "description": "Rich warm golden-tan skin",
        "tags": ["golden tan", "warm", "golden", "luminous", "sun-warmed"],
        "weight": 1.1
    },
    "Bronze": {
        "prompt": "bronze skin, medium-deep warm bronze-toned complexion with a rich golden-copper undertone, smooth healthy glow",
        "description": "Warm medium-deep bronze skin",
        "tags": ["bronze", "warm", "medium-deep", "copper", "rich"],
        "weight": 1.1
    },
    "Caramel": {
        "prompt": "caramel skin, warm medium-brown complexion with a smooth caramel tone and subtle golden warmth, soft even texture",
        "description": "Smooth warm caramel-toned skin",
        "tags": ["caramel", "warm", "medium brown", "golden", "smooth"],
        "weight": 1.1
    },
    "Warm Brown": {
        "prompt": "warm brown skin, rich medium-to-deep warm brown complexion with golden undertones, smooth healthy luminous texture",
        "description": "Rich warm brown skin with golden undertones",
        "tags": ["warm brown", "rich", "golden", "luminous", "deep"],
        "weight": 1.1
    },
    "Deep Brown": {
        "prompt": "deep brown skin, rich deep warm-toned brown complexion with a natural lustrous sheen, smooth healthy skin texture",
        "description": "Rich deep warm-toned brown skin",
        "tags": ["deep brown", "rich", "warm", "lustrous", "deep"],
        "weight": 1.1
    },
    "Ebony": {
        "prompt": "ebony skin, very deep rich dark complexion with a luminous natural sheen and blue-black depth, smooth radiant texture",
        "description": "Deep luminous ebony skin with natural radiance",
        "tags": ["ebony", "very deep", "luminous", "radiant", "rich"],
        "weight": 1.1
    },
    "Warm Rosy": {
        "prompt": "warm rosy skin, fair to medium complexion with a natural rosy-pink flush, soft warm undertones, healthy bloom",
        "description": "Fair skin with a warm natural rosy flush",
        "tags": ["rosy", "warm", "fair", "pink flush", "natural bloom"],
        "weight": 1.0
    },
    "Cool Beige": {
        "prompt": "cool beige skin, light to medium complexion with cool neutral-beige undertones, smooth even texture, refined finish",
        "description": "Cool neutral beige skin",
        "tags": ["beige", "cool", "neutral", "light", "refined"],
        "weight": 1.0
    }
}



_HAIR_PRESETS = {
    "Long Wavy Brunette": {
        "prompt": "Long wavy brunette hair flowing past the shoulders, loose natural waves with soft volume, subtle warm highlights through the lengths, healthy glossy shine, softly layered movement",
        "description": "Long loose waves with warm brunette highlights",
        "tags": ["long", "wavy", "brunette", "layers", "flowing"],
        "weight": 1.2
    },
    "Silky Straight Black": {
        "prompt": "Silky straight jet-black hair, smooth glass-like shine, precise even lengths falling past the shoulders, sleek healthy texture, softly rounded ends",
        "description": "Sleek silky straight black hair",
        "tags": ["straight", "black", "silky", "sleek", "long"],
        "weight": 1.2
    },
    "Blunt Bob": {
        "prompt": "Classic blunt-cut bob at jaw length, sharp even hemline, smooth glossy finish, softly curved under at the ends, chin-framing silhouette",
        "description": "Sharp chin-length blunt bob",
        "tags": ["bob", "blunt", "short", "sleek", "classic"],
        "weight": 1.1
    },
    "Collarbone Lob": {
        "prompt": "Collarbone-length lob, soft inward curve at the ends, lightweight face-framing layers, natural airy volume, smooth healthy texture",
        "description": "Soft collarbone-length lob with face framing",
        "tags": ["lob", "collarbone", "medium", "soft", "layered"],
        "weight": 1.1
    },
    "Pixie Cut": {
        "prompt": "Short textured pixie cut, softly shaped crown with piecey definition, tapered nape and sides, minimal styling, confident modern silhouette",
        "description": "Short textured pixie with tapered sides",
        "tags": ["pixie", "short", "textured", "modern", "androgynous"],
        "weight": 1.0
    },
    "Sleek High Ponytail": {
        "prompt": "Sleek high ponytail pulled taut from the crown, perfectly smooth glossy crown, long straight lengths swinging behind, sharp polished styling",
        "description": "Polished sleek high ponytail",
        "tags": ["ponytail", "high", "sleek", "polished", "long"],
        "weight": 1.1
    },
    "Low Ponytail": {
        "prompt": "Low ponytail gathered at the nape, softly smoothed crown, relaxed lengths resting over one shoulder, elegant understated everyday styling",
        "description": "Elegant relaxed low ponytail",
        "tags": ["ponytail", "low", "relaxed", "elegant", "nape"],
        "weight": 1.1
    },
    "Twin Tails": {
        "prompt": "Twin tails tied high on each side, softly swinging pigtails with even symmetrical volume, lightly waved lengths, playful youthful styling",
        "description": "Playful high twin tails",
        "tags": ["twintails", "pigtails", "playful", "youthful", "symmetrical"],
        "weight": 1.1
    },
    "Space Buns": {
        "prompt": "Two round space buns on top of the head, neatly wrapped with softly wispy front strands, smooth tightened base, cute symmetrical styling",
        "description": "Cute symmetrical space buns",
        "tags": ["space buns", "buns", "cute", "updo", "symmetrical"],
        "weight": 1.0
    },
    "Braided Crown": {
        "prompt": "Braided crown wrapping around the head, neat tightly woven plaits, softly draped loose strands at the temples, elegant romantic styling",
        "description": "Romantic woven braided crown updo",
        "tags": ["braid", "crown", "updo", "romantic", "woven"],
        "weight": 1.1
    }
}

_HAIR_PRESETS.update({
    "Fishtail Side Braid": {
        "prompt": "Long fishtail braid draped over one shoulder, finely interwoven strands, softly loosened crown for volume, delicate face-framing wisps, bohemian romantic styling",
        "description": "Bohemian fishtail braid over one shoulder",
        "tags": ["braid", "fishtail", "bohemian", "side", "romantic"],
        "weight": 1.0
    },
    "Cornrow Braids": {
        "prompt": "Neat cornrow braids running back over the scalp in clean parallel rows, precise even partings, visible scalp pattern, long braided tails falling behind, protective styling with sharp definition",
        "description": "Clean parallel cornrows with braided tails",
        "tags": ["cornrows", "braids", "protective", "defined", "rows"],
        "weight": 1.0
    },
    "Natural Afro": {
        "prompt": "Round natural afro with dense springy coils, even rounded silhouette, soft natural sheen, beautifully defined curl texture, healthy hydrated ends",
        "description": "Rounded natural afro with springy coils",
        "tags": ["afro", "natural", "coils", "round", "healthy"],
        "weight": 1.1
    },
    "Voluminous Curls": {
        "prompt": "Voluminous bouncy curls with defined spiral ringlets, plenty of body and lift at the roots, glossy hydrated texture, soft romantic movement",
        "description": "Bouncy defined spiral curls with volume",
        "tags": ["curls", "volume", "spiral", "bouncy", "glossy"],
        "weight": 1.1
    },
    "Shag with Curtain Bangs": {
        "prompt": "Textured shag cut with curtain bangs parted in the middle, choppy layered lengths, soft feathered ends, easygoing rock-inspired styling",
        "description": "Textured shag with middle-parted curtain bangs",
        "tags": ["shag", "curtain bangs", "layers", "textured", "rock"],
        "weight": 1.0
    },
    "Mohawk Fade": {
        "prompt": "Bold mohawk with a raised spiked crest, tightly faded sides, sharply defined edges, confident punk-inspired silhouette, clean structured styling",
        "description": "Bold spiked mohawk with faded sides",
        "tags": ["mohawk", "fade", "punk", "spiked", "bold"],
        "weight": 1.0
    },
    "Buzz Cut": {
        "prompt": "Clean uniform buzz cut, very short cropped hair with a soft even shadow, sharp hairline, minimal styling, strong no-nonsense silhouette",
        "description": "Short uniform buzz cut",
        "tags": ["buzz cut", "short", "clean", "minimal", "sharp"],
        "weight": 0.9
    },
    "Undercut Slick Back": {
        "prompt": "Undercut with shaved sides and long slicked-back top, sharply defined part, glossy combed texture with visible lines, modern tailored styling",
        "description": "Undercut with glossy slicked-back top",
        "tags": ["undercut", "slick back", "glossy", "modern", "tailored"],
        "weight": 1.0
    },
    "Man Bun": {
        "prompt": "Tied-back man bun at the crown, smoothly gathered sides with a few loose strands, natural healthy texture, relaxed contemporary styling",
        "description": "Relaxed tied-back man bun",
        "tags": ["man bun", "tied back", "relaxed", "contemporary", "natural"],
        "weight": 0.9
    },
    "Middle Part Loose Waves": {
        "prompt": "Hair parted cleanly in the middle with soft loose waves falling to both sides, natural volume and gentle movement, glossy healthy lengths, symmetric elegant framing",
        "description": "Middle-parted loose waves with natural volume",
        "tags": ["middle part", "waves", "loose", "symmetric", "elegant"],
        "weight": 1.1
    }
})

_HAIR_PRESETS.update({
    "Platinum Blonde Long": {
        "prompt": "Long platinum blonde hair with pale icy tones, softly waved lengths, subtle root shadow for depth, visible healthy shine, glamorous high-contrast styling",
        "description": "Icy platinum blonde with soft waves",
        "tags": ["platinum", "blonde", "long", "icy", "glamorous"],
        "weight": 1.1
    },
    "Copper Red Waves": {
        "prompt": "Rich copper red hair with warm auburn depth, loose brushed-out waves, glossy iridescent sheen catching the light, softly layered lengths, vivid natural warmth",
        "description": "Warm copper red waves with glossy sheen",
        "tags": ["red hair", "copper", "auburn", "waves", "vivid"],
        "weight": 1.1
    },
    "Blue-Black Hime Cut": {
        "prompt": "Blue-black hime cut with blunt straight sidelocks framing the face, long straight back lengths, glassy dark shine, precise even edges, traditional Japanese styling",
        "description": "Traditional hime cut with blunt sidelocks",
        "tags": ["hime cut", "blue black", "blunt", "japanese", "straight"],
        "weight": 1.0
    },
    "Ash Blonde Wolf Cut": {
        "prompt": "Ash blonde wolf cut with heavy layered volume, softly flipped mullet-inspired ends, wispy curtain fringe, cool-toned highlights, edgy modern texture",
        "description": "Cool ash blonde wolf cut with layered volume",
        "tags": ["wolf cut", "ash blonde", "layered", "edgy", "fringe"],
        "weight": 1.0
    },
    "Messy Bedhead Bun": {
        "prompt": "Loose messy bun with deliberately undone texture, soft escaping strands around the face, casual gathered crown, effortless relaxed everyday styling",
        "description": "Effortless messy bedhead bun",
        "tags": ["messy bun", "undone", "casual", "relaxed", "everyday"],
        "weight": 1.1
    },
    "Half-Up Top Knot": {
        "prompt": "Half-up top knot with the front section gathered into a small knot, long loose lengths falling below, softly textured crown, easy elegant everyday styling",
        "description": "Elegant half-up top knot with loose lengths",
        "tags": ["half up", "top knot", "elegant", "everyday", "loose"],
        "weight": 1.1
    },
    "Vintage Finger Waves": {
        "prompt": "Sculpted vintage finger waves with glossy set ridges, precise S-shaped ripples close to the head, polished 1920s styling, soft sheen under studio light",
        "description": "Glossy sculpted 1920s finger waves",
        "tags": ["finger waves", "vintage", "1920s", "sculpted", "glossy"],
        "weight": 0.9
    },
    "Box Braids": {
        "prompt": "Long box braids with neat square partings, consistent even thickness, softly swaying lengths, glossy ends, elegant protective styling with beautiful definition",
        "description": "Neat long box braids with square partings",
        "tags": ["box braids", "protective", "neat", "long", "defined"],
        "weight": 1.0
    },
    "Long Silver Blonde Wispy Bangs": {
        "prompt": "Long soft silver-blonde hair falling past the shoulders, gentle natural movement with softly layered lengths, wispy feathered bangs sweeping across the forehead, cool silvery tones with a healthy diffused shine, airy relaxed styling",
        "description": "Long silver-blonde hair with wispy feathered bangs",
        "tags": ["silver blonde", "long", "wispy bangs", "soft", "cool toned"],
        "weight": 1.1
    }
})

_HEADWEAR_PRESETS = {
    "Classic Baseball Cap": {
        "prompt": "Classic baseball cap worn forward with a curved brim, structured six-panel crown, subtle stitching detail, casual sporty styling",
        "description": "Everyday forward-facing baseball cap",
        "tags": ["baseball cap", "cap", "casual", "sporty", "brim"],
        "weight": 1.2
    },
    "Backwards Snapback": {
        "prompt": "Snapback cap worn backwards with a flat brim, adjustable plastic snap closure, clean streetwear styling, relaxed urban attitude",
        "description": "Streetwear snapback worn backwards",
        "tags": ["snapback", "backwards", "streetwear", "urban", "flat brim"],
        "weight": 1.0
    },
    "Ribbed Beanie": {
        "prompt": "Ribbed knit beanie pulled low over the forehead, soft folded cuff, cozy winter texture, snug casual fit",
        "description": "Cozy ribbed knit beanie",
        "tags": ["beanie", "knit", "winter", "cozy", "cuffed"],
        "weight": 1.2
    },
    "Fisherman Beanie": {
        "prompt": "Short fisherman beanie sitting high on the crown, minimal folded edge, clean cropped silhouette, modern minimalist knit styling",
        "description": "Minimal high-sitting fisherman beanie",
        "tags": ["fisherman beanie", "short", "minimal", "modern", "knit"],
        "weight": 1.0
    },
    "Bucket Hat": {
        "prompt": "Soft bucket hat with a gently downturned brim, relaxed cotton texture, casual festival styling, easy unpretentious 90s attitude",
        "description": "Relaxed cotton bucket hat",
        "tags": ["bucket hat", "casual", "90s", "cotton", "downturned"],
        "weight": 1.1
    },
    "Wide-Brim Fedora": {
        "prompt": "Classic wide-brim fedora with a pinched crown and grosgrain band, elegant structured felt, confident vintage-inspired styling",
        "description": "Structured felt fedora with pinched crown",
        "tags": ["fedora", "wide brim", "vintage", "felt", "elegant"],
        "weight": 1.0
    },
    "French Beret": {
        "prompt": "Soft French beret tilted to one side, fine wool texture, subtle slouchy volume, effortlessly artistic Parisian styling",
        "description": "Artistic Parisian wool beret",
        "tags": ["beret", "french", "wool", "artistic", "parisian"],
        "weight": 1.1
    },
    "Straw Sun Hat": {
        "prompt": "Wide woven straw sun hat with a softly floppy brim, delicate ribbon band, warm summer sunlight styling, natural breezy texture",
        "description": "Wide woven straw sun hat",
        "tags": ["straw hat", "sun hat", "summer", "woven", "wide brim"],
        "weight": 1.1
    },
    "Hood Up": {
        "prompt": "Hood pulled up over the head, soft fabric framing the face in gentle shadow, casual streetwear styling, subtle mysterious mood",
        "description": "Hood up with soft fabric framing the face",
        "tags": ["hood", "hoodie", "streetwear", "casual", "shadowed"],
        "weight": 1.1
    },
    "Sport Headband": {
        "prompt": "Athletic sweatband worn across the forehead, stretchy ribbed fabric, clean sporty detail, energetic workout styling",
        "description": "Athletic ribbed sport headband",
        "tags": ["headband", "sport", "athletic", "sweatband", "energetic"],
        "weight": 0.9
    }
}

_HEADWEAR_PRESETS.update({
    "Bandana Head Wrap": {
        "prompt": "Bandana tied around the head with a knot at the front, softly folded fabric band, casual retro styling, relaxed rebellious attitude",
        "description": "Retro knotted bandana head wrap",
        "tags": ["bandana", "head wrap", "retro", "casual", "knot"],
        "weight": 0.9
    },
    "Beanie with Headphones": {
        "prompt": "Slouchy knit beanie worn with over-ear headphones on top, cozy winter layers, soft pooling fabric at the crown, casual music-lover styling",
        "description": "Slouchy beanie worn with over-ear headphones",
        "tags": ["beanie", "headphones", "winter", "music", "cozy"],
        "weight": 0.9
    },
    "Delicate Tiara": {
        "prompt": "Delicate crystal tiara resting on the crown, fine intricate metalwork, sparkling subtle gemstones, elegant regal styling, refined fairy-tale mood",
        "description": "Delicate crystal tiara with elegant metalwork",
        "tags": ["tiara", "crystal", "regal", "elegant", "fairy tale"],
        "weight": 0.8
    },
    "Cowboy Hat": {
        "prompt": "Classic cowboy hat with a pinched crown and gently curved brim, weathered leather band, dusty western styling, confident frontier attitude",
        "description": "Classic curved-brim cowboy hat",
        "tags": ["cowboy hat", "western", "leather", "frontier", "classic"],
        "weight": 0.9
    },
    "Silk Headscarf": {
        "prompt": "Silk headscarf wrapped over the hair with soft elegant folds, glossy patterned fabric, chic retro styling, sophisticated polished finish",
        "description": "Glossy silk headscarf with elegant folds",
        "tags": ["headscarf", "silk", "chic", "retro", "elegant"],
        "weight": 1.0
    },
    "Cat-Ear Hood": {
        "prompt": "Hood with softly sculpted cat ears on top, plush cozy fabric, playful character styling, cute fantasy-inspired mood",
        "description": "Playful hood with sculpted cat ears",
        "tags": ["cat ears", "hood", "playful", "cute", "fantasy"],
        "weight": 0.8
    },
    "White Wireless Headphones": {
        "prompt": "Oversized white wireless over-ear headphones worn over the hair, softly rounded padded ear cups and a smooth cushioned headband, subtle glowing blue accent lighting along the edges, modern futuristic music styling",
        "description": "Oversized white wireless headphones with glowing blue accents",
        "tags": ["headphones", "white", "wireless", "neon", "futuristic"],
        "weight": 1.0
    }
})

_TOP_PRESETS = {
    "Oversized Cream Knit Hoodie": {
        "prompt": "Oversized cream knit hoodie, soft fleece texture, dropped shoulders, ribbed cuffs and hem, relaxed streetwear styling",
        "description": "Cozy oversized cream knit hoodie",
        "tags": ["hoodie", "knit", "oversized", "casual", "streetwear"],
        "weight": 1.2
    },
    "Cropped Graphic Tee": {
        "prompt": "Cropped graphic tee with a faded printed design, soft cotton jersey, raw hem, casual fitted silhouette, easy summer styling",
        "description": "Faded cropped graphic tee",
        "tags": ["tee", "cropped", "graphic", "cotton", "casual"],
        "weight": 1.1
    },
    "Fitted Ribbed Tank Top": {
        "prompt": "Fitted ribbed tank top, soft stretchy knit with visible vertical ribbing, scooped neckline, clean minimal styling",
        "description": "Stretchy fitted ribbed tank top",
        "tags": ["tank top", "ribbed", "fitted", "minimal", "summer"],
        "weight": 1.1
    },
    "Silky Slip Blouse": {
        "prompt": "Silky slip blouse with a liquid satin drape, modest neckline, soft sheen catching the light, elegant evening styling",
        "description": "Liquid satin slip blouse with modest neckline",
        "tags": ["blouse", "silk", "satin", "elegant", "evening"],
        "weight": 1.1
    },
    "Structured Blazer": {
        "prompt": "Structured tailored blazer with sharp padded shoulders, crisp lapels, precise buttoned front over a fitted blouse, confident professional styling",
        "description": "Sharp tailored structured blazer with blouse",
        "tags": ["blazer", "tailored", "structured", "professional", "sharp"],
        "weight": 1.1
    },
    "Black Leather Jacket": {
        "prompt": "Black leather biker jacket with asymmetric zip, silver hardware, worn-in supple leather texture, rebel edge styling",
        "description": "Classic black leather biker jacket",
        "tags": ["leather jacket", "biker", "black", "edgy", "zip"],
        "weight": 1.2
    },
    "Oversized Denim Jacket": {
        "prompt": "Oversized denim jacket with a faded wash, dropped shoulders and rolled sleeves, vintage trucker details, casual layered styling",
        "description": "Vintage-wash oversized denim jacket",
        "tags": ["denim jacket", "oversized", "vintage", "casual", "layered"],
        "weight": 1.1
    },
    "Bomber Jacket": {
        "prompt": "Classic bomber jacket with ribbed collar and cuffs, glossy nylon shell, utility sleeve pocket, sporty street styling",
        "description": "Glossy nylon bomber jacket",
        "tags": ["bomber", "nylon", "sporty", "street", "jacket"],
        "weight": 1.1
    },
    "Trench Coat": {
        "prompt": "Classic belted trench coat with double-breasted buttons, wide lapels and storm flap, elegant flowing drape, sophisticated urban styling",
        "description": "Belted double-breasted trench coat",
        "tags": ["trench coat", "belted", "elegant", "urban", "classic"],
        "weight": 1.1
    },
    "Kimono Wrap Top": {
        "prompt": "Kimono wrap top with a wide patterned sash, softly draped sleeves, flowing lightweight fabric, artistic bohemian styling",
        "description": "Flowing kimono wrap top with sash",
        "tags": ["kimono", "wrap", "sash", "bohemian", "flowing"],
        "weight": 1.0
    }
}

_TOP_PRESETS.update({
    "Corset Top": {
        "prompt": "Structured corset top with visible boning, satin panels and delicate lacing, high neckline, cinched waist silhouette, dramatic statement styling",
        "description": "Structured corset top with high neckline",
        "tags": ["corset", "boned", "satin", "statement", "cinched"],
        "weight": 1.0
    },
    "Chunky Knit Sweater": {
        "prompt": "Chunky cable-knit sweater with thick wool texture, oversized relaxed fit, visible braided cables, cozy winter warmth, soft natural tones",
        "description": "Cozy chunky cable-knit sweater",
        "tags": ["sweater", "chunky", "cable knit", "cozy", "wool"],
        "weight": 1.2
    },
    "Sports Jersey": {
        "prompt": "Sports jersey with bold printed numbers and team lettering, breathable mesh fabric, athletic loose fit, energetic stadium styling",
        "description": "Bold printed athletic sports jersey",
        "tags": ["jersey", "sports", "mesh", "athletic", "printed"],
        "weight": 1.0
    },
    "Crisp White Dress Shirt": {
        "prompt": "Crisp white dress shirt with a precise tailored collar, subtle cotton sheen, neatly buttoned front, clean professional styling",
        "description": "Crisp tailored white dress shirt",
        "tags": ["dress shirt", "white", "crisp", "professional", "tailored"],
        "weight": 1.2
    },
    "Puffer Jacket": {
        "prompt": "Quilted puffer jacket with deep padded channels, glossy technical shell, high collar, warm winter volume, modern outdoor styling",
        "description": "Quilted glossy puffer jacket",
        "tags": ["puffer", "quilted", "winter", "glossy", "padded"],
        "weight": 1.1
    },
    "Longline Cardigan": {
        "prompt": "Longline open cardigan falling past the hips, soft brushed knit, draped relaxed front panels, effortless layered styling",
        "description": "Long draped open cardigan",
        "tags": ["cardigan", "longline", "knit", "layered", "relaxed"],
        "weight": 1.1
    },
    "Poncho Cape": {
        "prompt": "Flowing poncho cape with a softly fringed hem, warm woven texture, dramatic draped silhouette, bohemian autumnal styling",
        "description": "Flowing fringed poncho cape",
        "tags": ["poncho", "cape", "fringe", "bohemian", "draped"],
        "weight": 0.9
    },
    "Sleeveless Turtleneck": {
        "prompt": "Sleeveless turtleneck top with a soft rolled collar, smooth stretchy knit, sleek close fit, minimalist modern styling",
        "description": "Sleek sleeveless turtleneck top",
        "tags": ["turtleneck", "sleeveless", "sleek", "minimal", "knit"],
        "weight": 1.0
    },
    "Varsity Jacket": {
        "prompt": "Varsity letterman jacket with contrasting leather sleeves, ribbed collar and cuffs, bold chenille patch detail, classic collegiate styling",
        "description": "Collegiate varsity letterman jacket",
        "tags": ["varsity", "letterman", "collegiate", "patch", "classic"],
        "weight": 1.0
    },
    "Flannel Overshirt": {
        "prompt": "Brushed flannel overshirt in a classic checked pattern, soft cotton texture, worn open over a tee, relaxed outdoorsy styling",
        "description": "Classic checked flannel overshirt",
        "tags": ["flannel", "plaid", "overshirt", "casual", "outdoorsy"],
        "weight": 1.1
    }
})

_TOP_PRESETS.update({
    "Lace Camisole": {
        "prompt": "Delicate lace camisole with fine floral lace trim, opaque lined fabric, adjustable straps, romantic feminine styling",
        "description": "Romantic lace camisole with opaque lining",
        "tags": ["camisole", "lace", "delicate", "romantic", "straps"],
        "weight": 1.0
    },
    "Off-Shoulder Knit Top": {
        "prompt": "Off-shoulder knit top with wide boat neckline, soft ribbed cotton, fitted comfortable drape, relaxed feminine styling",
        "description": "Soft off-shoulder ribbed knit top",
        "tags": ["off shoulder", "knit", "ribbed", "feminine", "relaxed"],
        "weight": 1.0
    },
    "Utility Vest": {
        "prompt": "Technical utility vest with multiple flap pockets, sturdy canvas weave, adjustable straps, functional tactical streetwear styling",
        "description": "Pocketed technical utility vest",
        "tags": ["vest", "utility", "tactical", "pockets", "streetwear"],
        "weight": 0.9
    },
    "Wool Peacoat": {
        "prompt": "Double-breasted wool peacoat with wide notched lapels, dense warm melton texture, oversized horn buttons, elegant cold-weather styling",
        "description": "Double-breasted wool peacoat",
        "tags": ["peacoat", "wool", "double breasted", "winter", "elegant"],
        "weight": 1.0
    },
    "Cropped Puffer Vest": {
        "prompt": "Cropped puffer vest with glossy quilted channels, high padded collar, sleeveless sporty volume, modern streetwear layering",
        "description": "Glossy cropped quilted puffer vest",
        "tags": ["puffer vest", "cropped", "quilted", "sporty", "layering"],
        "weight": 1.0
    },
    "Ruched Mesh Top": {
        "prompt": "Ruched mesh top with fine stretch mesh overlay and gathered side seams, fully lined opaque underlayer, trendy evening styling",
        "description": "Trendy ruched mesh top with opaque lining",
        "tags": ["mesh", "ruched", "trendy", "evening", "layered"],
        "weight": 0.9
    },
    "Vintage Band Tee": {
        "prompt": "Vintage band tee with a faded distressed print, soft washed cotton jersey, relaxed unisex fit, worn retro rock styling",
        "description": "Faded vintage band tee",
        "tags": ["band tee", "vintage", "distressed", "rock", "retro"],
        "weight": 1.1
    },
    "Classic Polo Shirt": {
        "prompt": "Classic polo shirt with a crisp folded collar and buttoned placket, breathable pique cotton, neat preppy styling, clean smart-casual look",
        "description": "Neat preppy pique polo shirt",
        "tags": ["polo", "preppy", "pique", "smart casual", "classic"],
        "weight": 1.1
    },
    "Tuxedo Jacket": {
        "prompt": "Sharp tuxedo jacket with satin-faced shawl lapels, precise tailored fit, elegant evening formality, black-tie glamour styling",
        "description": "Tailored satin-lapel tuxedo jacket",
        "tags": ["tuxedo", "formal", "satin", "black tie", "elegant"],
        "weight": 0.9
    },
    "Tied Crop Shirt": {
        "prompt": "Button-up shirt tied into a crop knot at the waist, lightweight cotton with rolled sleeves, casual breezy summer styling",
        "description": "Casual button-up shirt tied at the waist",
        "tags": ["shirt", "knotted", "crop", "summer", "casual"],
        "weight": 1.0
    },
    "Oversized Pale Blue Hoodie": {
        "prompt": "Oversized pale blue hoodie with soft brushed fabric, dropped shoulders and slouchy relaxed volume, roomy hood with ribbed cuffs and hem, casual comfortable streetwear styling",
        "description": "Oversized pale blue hoodie with soft slouchy volume",
        "tags": ["hoodie", "pale blue", "oversized", "soft", "streetwear"],
        "weight": 1.1
    }
})

_BOTTOM_PRESETS = {
    "High-Waisted Skinny Jeans": {
        "prompt": "High-waisted skinny jeans with a figure-hugging stretch fit, neat ankle crop, classic five-pocket detail, everyday denim styling",
        "description": "Figure-hugging high-waisted skinny jeans",
        "tags": ["jeans", "skinny", "high waisted", "denim", "everyday"],
        "weight": 1.2
    },
    "Ripped Straight Jeans": {
        "prompt": "Straight-leg jeans with distressed rips at the knees, faded vintage wash, raw frayed hems, casual street styling",
        "description": "Distressed straight-leg jeans with knee rips",
        "tags": ["jeans", "ripped", "straight leg", "distressed", "street"],
        "weight": 1.1
    },
    "Cargo Pants": {
        "prompt": "Utility cargo pants with large side flap pockets, sturdy cotton twill, adjustable ankle cuffs, functional tactical streetwear styling",
        "description": "Utility cargo pants with large pockets",
        "tags": ["cargo", "utility", "pockets", "tactical", "streetwear"],
        "weight": 1.2
    },
    "Tapered Chinos": {
        "prompt": "Tapered chino trousers in soft cotton twill, clean pressed front crease, neat rolled ankles, smart-casual styling",
        "description": "Smart-casual tapered chino trousers",
        "tags": ["chinos", "tapered", "smart casual", "cotton", "neat"],
        "weight": 1.1
    },
    "Fleece Joggers": {
        "prompt": "Fleece jogger pants with a soft brushed interior, elastic drawstring waist, tapered cuffs, cozy off-duty styling",
        "description": "Cozy fleece joggers with tapered cuffs",
        "tags": ["joggers", "fleece", "cozy", "athleisure", "casual"],
        "weight": 1.1
    },
    "Tailored Trousers": {
        "prompt": "Sharply tailored trousers with a precise front crease, crisp wool weave, high clean waistband, elegant professional styling",
        "description": "Sharply tailored wool trousers",
        "tags": ["trousers", "tailored", "professional", "wool", "elegant"],
        "weight": 1.1
    },
    "Wide-Leg Pants": {
        "prompt": "Flowing wide-leg pants with a high waist and fluid drape, soft pleated folds down the leg, elegant modern styling",
        "description": "Flowing high-waist wide-leg pants",
        "tags": ["wide leg", "flowing", "high waist", "modern", "draped"],
        "weight": 1.1
    },
    "Pleated Mini Skirt": {
        "prompt": "Short pleated mini skirt with crisp knife pleats, lightweight fabric that moves with every step, playful preppy styling",
        "description": "Crisp pleated preppy mini skirt",
        "tags": ["skirt", "pleated", "mini", "preppy", "playful"],
        "weight": 1.2
    },
    "Pencil Midi Skirt": {
        "prompt": "Fitted pencil midi skirt falling below the knee, smooth structured fabric, subtle back slit, elegant office-chic styling",
        "description": "Fitted pencil midi skirt with back slit",
        "tags": ["skirt", "pencil", "midi", "elegant", "office"],
        "weight": 1.1
    }
}

_BOTTOM_PRESETS.update({
    "Denim Skirt": {
        "prompt": "Classic denim mini skirt with a buttoned front, sturdy cotton denim, softly frayed hem, casual everyday styling",
        "description": "Classic button-front denim mini skirt",
        "tags": ["denim skirt", "mini", "buttoned", "casual", "frayed"],
        "weight": 1.1
    },
    "A-Line Skirt": {
        "prompt": "Flared A-line skirt with a gently swinging hem, smooth structured fabric, comfortable knee-length cut, timeless feminine styling",
        "description": "Timeless flared knee-length A-line skirt",
        "tags": ["skirt", "a-line", "flared", "timeless", "knee length"],
        "weight": 1.1
    },
    "Maxi Flowy Skirt": {
        "prompt": "Long flowing maxi skirt reaching the ankles, soft lightweight fabric catching the breeze, graceful draping folds, bohemian summer styling",
        "description": "Long flowing bohemian maxi skirt",
        "tags": ["maxi skirt", "flowy", "long", "bohemian", "summer"],
        "weight": 1.1
    },
    "Leather Pants": {
        "prompt": "Fitted leather pants with a high glossy sheen, subtle stretch panels, sharply tailored legs, bold edgy styling",
        "description": "Glossy fitted leather pants",
        "tags": ["leather", "pants", "glossy", "edgy", "fitted"],
        "weight": 1.0
    },
    "Bike Shorts": {
        "prompt": "Compression bike shorts ending mid thigh, smooth stretchy athletic fabric, high supportive waistband, sporty fitted styling",
        "description": "Sporty high-waist compression bike shorts",
        "tags": ["bike shorts", "compression", "sporty", "athletic", "fitted"],
        "weight": 1.0
    },
    "Leggings": {
        "prompt": "Smooth high-waisted leggings in matte stretch fabric, seamless fitted silhouette, subtle contour seaming, athleisure styling",
        "description": "Matte seamless high-waisted leggings",
        "tags": ["leggings", "athleisure", "seamless", "matte", "fitted"],
        "weight": 1.1
    },
    "Hakama Pants": {
        "prompt": "Wide traditional hakama pants with deep structured pleats, generously flowing legs, tied waist, elegant Japanese-inspired styling",
        "description": "Pleated wide traditional hakama pants",
        "tags": ["hakama", "pleated", "traditional", "japanese", "wide"],
        "weight": 0.9
    },
    "Parachute Pants": {
        "prompt": "Baggy parachute pants in lightweight nylon, adjustable bungee cuffs and waist, utility straps and pockets, Y2K street styling",
        "description": "Baggy nylon parachute pants with bungee cuffs",
        "tags": ["parachute pants", "baggy", "nylon", "y2k", "street"],
        "weight": 1.0
    },
    "Corduroy Pants": {
        "prompt": "Soft corduroy pants with fine wale ridges, warm earthy tone, comfortable straight leg, retro autumnal styling",
        "description": "Soft retro corduroy pants",
        "tags": ["corduroy", "pants", "retro", "autumn", "straight leg"],
        "weight": 1.0
    }
})

_BOTTOM_PRESETS.update({
    "Cargo Shorts": {
        "prompt": "Cargo shorts ending above the knee with utility flap pockets, durable cotton twill, relaxed summer outdoor styling",
        "description": "Utility cargo shorts with flap pockets",
        "tags": ["cargo shorts", "utility", "summer", "outdoor", "pockets"],
        "weight": 0.9
    },
    "Ruffle Tiered Skirt": {
        "prompt": "Tiered ruffle skirt with layered flounced tiers, soft lightweight fabric, playful cascading movement, romantic feminine styling",
        "description": "Layered romantic tiered ruffle skirt",
        "tags": ["skirt", "ruffle", "tiered", "romantic", "feminine"],
        "weight": 1.0
    },
    "Plaid Pleated Skirt": {
        "prompt": "Plaid pleated skirt with a classic tartan check, sharp knife pleats, buttoned waistband, school-uniform inspired styling",
        "description": "Classic tartan plaid pleated skirt",
        "tags": ["plaid", "tartan", "pleated", "skirt", "school"],
        "weight": 1.1
    },
    "Linen Wide Trousers": {
        "prompt": "Wide-leg linen trousers with a relaxed breathable weave, softly wrinkled natural texture, drawstring waist, easy summer styling",
        "description": "Breathable wide-leg linen trousers",
        "tags": ["linen", "wide leg", "trousers", "summer", "relaxed"],
        "weight": 1.1
    },
    "Belted Paperbag Shorts": {
        "prompt": "High-waisted paperbag shorts with gathered pleats at the waist and a tied fabric belt, lightweight woven fabric, chic summer styling",
        "description": "Chic belted high-waist paperbag shorts",
        "tags": ["shorts", "paperbag", "belted", "high waisted", "chic"],
        "weight": 1.0
    },
    "Slit Long Skirt": {
        "prompt": "Long skirt with a dramatic thigh-high side slit, smooth fluid fabric, elegant sleek drape, sophisticated evening styling",
        "description": "Elegant long skirt with a high side slit",
        "tags": ["skirt", "slit", "long", "elegant", "evening"],
        "weight": 1.0
    },
    "Denim Overalls": {
        "prompt": "Classic denim overalls with adjustable bib straps, roomy front pocket, sturdy cotton denim, casual workwear styling",
        "description": "Classic strapped denim overalls",
        "tags": ["overalls", "denim", "workwear", "casual", "straps"],
        "weight": 0.9
    },
    "Palazzo Pants": {
        "prompt": "Flowing palazzo pants with an extremely wide elegant leg, soft high-waisted drape, luxurious fluid movement, sophisticated resort styling",
        "description": "Extra-wide flowing palazzo pants",
        "tags": ["palazzo", "wide leg", "flowing", "elegant", "resort"],
        "weight": 1.0
    }
})

_SHOES_PRESETS = {
    "White Sneakers": {
        "prompt": "Clean white low-top sneakers with crisp leather uppers, minimal branding, thick rubber soles, everyday casual styling",
        "description": "Clean minimalist white low-top sneakers",
        "tags": ["sneakers", "white", "clean", "casual", "minimal"],
        "weight": 1.2
    },
    "High-Top Canvas Sneakers": {
        "prompt": "High-top canvas sneakers with laced ankle support, worn-in rubber toe caps, casual skate styling, relaxed street attitude",
        "description": "Classic high-top canvas sneakers",
        "tags": ["sneakers", "high top", "canvas", "skate", "street"],
        "weight": 1.1
    },
    "Chunky Platform Sneakers": {
        "prompt": "Chunky platform sneakers with a thick sculpted sole, layered panel uppers, bold statement volume, modern streetwear styling",
        "description": "Bold chunky platform sneakers",
        "tags": ["sneakers", "platform", "chunky", "streetwear", "statement"],
        "weight": 1.0
    },
    "Combat Boots": {
        "prompt": "Black leather combat boots with tall laced shafts, heavy lugged soles, sturdy eyelets, tough utilitarian styling",
        "description": "Heavy lace-up black combat boots",
        "tags": ["boots", "combat", "leather", "laced", "utilitarian"],
        "weight": 1.2
    },
    "Chelsea Boots": {
        "prompt": "Sleek Chelsea boots with elastic side panels and a pull tab, polished leather finish, refined ankle-height silhouette, smart modern styling",
        "description": "Polished leather Chelsea boots",
        "tags": ["boots", "chelsea", "leather", "smart", "sleek"],
        "weight": 1.1
    },
    "Stiletto Heels": {
        "prompt": "Elegant stiletto heels with a slender pointed toe, glossy patent finish, tall thin heel, confident evening glamour styling",
        "description": "Glossy patent stiletto heels",
        "tags": ["heels", "stiletto", "glamour", "evening", "elegant"],
        "weight": 1.0
    },
    "Platform Boots": {
        "prompt": "Chunky platform boots with a thick block sole, glossy leather shafts, heavy hardware buckles, bold alternative styling",
        "description": "Chunky buckled platform boots",
        "tags": ["boots", "platform", "chunky", "alternative", "buckle"],
        "weight": 1.0
    },
    "Leather Loafers": {
        "prompt": "Classic leather loafers with a soft penny strap, polished smooth finish, low stacked heel, timeless preppy styling",
        "description": "Timeless polished leather loafers",
        "tags": ["loafers", "leather", "preppy", "classic", "polished"],
        "weight": 1.1
    },
    "Mary Janes": {
        "prompt": "Mary Jane shoes with a rounded toe and delicate ankle strap, soft leather uppers, dainty vintage styling, sweet nostalgia mood",
        "description": "Dainty vintage Mary Jane shoes",
        "tags": ["mary janes", "strap", "vintage", "dainty", "sweet"],
        "weight": 1.0
    },
    "Ballet Flats": {
        "prompt": "Soft ballet flats with a smoothly rounded toe, supple leather finish, slim flexible sole, graceful minimal styling",
        "description": "Soft graceful ballet flats",
        "tags": ["flats", "ballet", "soft", "graceful", "minimal"],
        "weight": 1.0
    }
}

_SHOES_PRESETS.update({
    "Strappy Sandals": {
        "prompt": "Delicate strappy sandals with fine leather bands crossing the foot, slim buckle closure, barefoot summer elegance, refined holiday styling",
        "description": "Delicate leather strappy sandals",
        "tags": ["sandals", "strappy", "summer", "elegant", "leather"],
        "weight": 1.0
    },
    "Cowboy Boots": {
        "prompt": "Western cowboy boots with pointed toes, stacked leather heels, decorative stitched shafts, authentic ranch styling",
        "description": "Authentic stitched western cowboy boots",
        "tags": ["cowboy boots", "western", "leather", "stitched", "ranch"],
        "weight": 1.0
    },
    "Japanese Geta": {
        "prompt": "Traditional Japanese geta sandals with raised wooden blocks and a thong strap, polished dark wood, elegant summer festival styling",
        "description": "Traditional wooden geta sandals",
        "tags": ["geta", "japanese", "wooden", "traditional", "summer"],
        "weight": 0.8
    },
    "Hiking Boots": {
        "prompt": "Rugged hiking boots with aggressive lugged tread, reinforced leather and mesh uppers, padded ankle collar, dependable outdoor styling",
        "description": "Rugged reinforced hiking boots",
        "tags": ["hiking boots", "outdoor", "rugged", "tread", "practical"],
        "weight": 0.9
    },
    "Running Shoes": {
        "prompt": "Lightweight running shoes with breathable knit uppers and cushioned foam midsoles, streamlined athletic silhouette, sporty energetic styling",
        "description": "Lightweight cushioned running shoes",
        "tags": ["running shoes", "athletic", "knit", "cushioned", "sporty"],
        "weight": 1.0
    },
    "Ankle Boots": {
        "prompt": "Sleek ankle boots with a modest block heel, smooth leather finish, understated zip detail, versatile everyday styling",
        "description": "Sleek block-heel ankle boots",
        "tags": ["boots", "ankle", "leather", "versatile", "everyday"],
        "weight": 1.1
    },
    "Knee-High Boots": {
        "prompt": "Knee-high boots with a fitted calf and softly stacked heel, supple leather shafts, confident dramatic styling",
        "description": "Fitted knee-high leather boots",
        "tags": ["boots", "knee high", "leather", "dramatic", "fitted"],
        "weight": 1.0
    },
    "Espadrilles": {
        "prompt": "Woven espadrille shoes with traditional jute rope soles, canvas or suede uppers, relaxed Mediterranean summer styling",
        "description": "Jute-soled woven espadrilles",
        "tags": ["espadrilles", "jute", "summer", "mediterranean", "woven"],
        "weight": 0.9
    },
    "Oxford Shoes": {
        "prompt": "Classic leather oxford shoes with closed lacing, finely burnished finish, elegant slim silhouette, polished formal styling",
        "description": "Polished classic leather oxfords",
        "tags": ["oxfords", "formal", "leather", "polished", "classic"],
        "weight": 1.0
    },
    "Slide Sandals": {
        "prompt": "Easy slide sandals with a wide single band across the foot, soft molded footbed, casual poolside styling, relaxed summer comfort",
        "description": "Easy casual slide sandals",
        "tags": ["sandals", "slides", "casual", "summer", "comfort"],
        "weight": 0.9
    }
})

_HAND_ACCESSORY_PRESETS = {
    "Chronograph Wristwatch": {
        "prompt": "Stainless steel chronograph wristwatch with a polished link bracelet, deep blue dial and three subdials, precise luxury detail, refined classic styling",
        "description": "Steel chronograph watch with blue dial",
        "tags": ["watch", "chronograph", "steel", "luxury", "classic"],
        "weight": 1.2
    },
    "Smartwatch": {
        "prompt": "Modern smartwatch with a slim rectangular display, soft silicone sport band, glowing fitness interface, sleek contemporary styling",
        "description": "Slim smartwatch with sport band",
        "tags": ["smartwatch", "digital", "sport", "modern", "fitness"],
        "weight": 1.1
    },
    "Stacked Gold Bangles": {
        "prompt": "Stacked thin gold bangles jingling on the wrist, warm polished metal with subtle engraved patterns, layered luxurious styling",
        "description": "Stacked thin gold bangles",
        "tags": ["bangles", "gold", "stacked", "layered", "luxury"],
        "weight": 1.1
    },
    "Silver Signet Ring": {
        "prompt": "Chunky silver signet ring worn on the hand, brushed metal surface with a softly engraved crest, bold understated statement styling",
        "description": "Chunky engraved silver signet ring",
        "tags": ["ring", "signet", "silver", "statement", "engraved"],
        "weight": 1.0
    },
    "Fingerless Gloves": {
        "prompt": "Black fingerless gloves with exposed fingertips, soft worn leather or knit texture, practical street styling, subtle rebellious edge",
        "description": "Black fingerless gloves",
        "tags": ["gloves", "fingerless", "black", "street", "edgy"],
        "weight": 1.0
    },
    "Leather Gloves": {
        "prompt": "Fine leather gloves with delicate stitching across the knuckles, supple matte finish, elegant tailored styling",
        "description": "Fine elegantly stitched leather gloves",
        "tags": ["gloves", "leather", "elegant", "tailored", "stitched"],
        "weight": 1.1
    },
    "Armored Gauntlets": {
        "prompt": "Plated armored gauntlets with articulated finger segments, brushed metal plates and dark leather straps, fantasy warrior styling",
        "description": "Articulated armored fantasy gauntlets",
        "tags": ["gauntlets", "armor", "fantasy", "metal", "warrior"],
        "weight": 0.8
    },
    "Painted Nail Art": {
        "prompt": "Carefully painted nail art with glossy lacquer, fine detail accents and a subtle shimmer topcoat, neatly manicured hands, refined beauty styling",
        "description": "Glossy detailed painted nail art",
        "tags": ["nails", "manicure", "glossy", "beauty", "detail"],
        "weight": 1.0
    },
    "Boxing Hand Wraps": {
        "prompt": "Boxing hand wraps securely bandaged around the knuckles and wrists, worn cotton texture, athletic combat styling",
        "description": "Worn cotton boxing hand wraps",
        "tags": ["wraps", "boxing", "athletic", "cotton", "combat"],
        "weight": 0.8
    },
    "Silicone Wristband": {
        "prompt": "Simple silicone wristband worn on the wrist, matte rubber finish with a subtle embossed logo, casual sporty detail",
        "description": "Casual matte silicone wristband",
        "tags": ["wristband", "silicone", "casual", "sporty", "simple"],
        "weight": 0.9
    }
}

_HAND_ACCESSORY_PRESETS.update({
    "Charm Bracelet": {
        "prompt": "Delicate charm bracelet with small dangling silver charms, fine link chain, personal keepsake styling, softly sparkling detail",
        "description": "Fine silver charm bracelet",
        "tags": ["bracelet", "charms", "silver", "delicate", "keepsake"],
        "weight": 1.0
    },
    "Pearl Bracelet": {
        "prompt": "Elegant single-strand pearl bracelet, lustrous evenly matched pearls with a fine gold clasp, classic refined styling",
        "description": "Classic single-strand pearl bracelet",
        "tags": ["bracelet", "pearl", "elegant", "classic", "gold clasp"],
        "weight": 1.0
    },
    "Chunky Chain Bracelet": {
        "prompt": "Bold chunky chain bracelet in polished metal, heavy interlocking links, statement street-luxury styling",
        "description": "Bold polished chunky chain bracelet",
        "tags": ["bracelet", "chain", "chunky", "bold", "statement"],
        "weight": 0.9
    },
    "Knit Mittens": {
        "prompt": "Cozy knit mittens with a soft wool texture and folded cuffs, warm winter styling, charming handmade feel",
        "description": "Cozy folded-cuff knit mittens",
        "tags": ["mittens", "knit", "cozy", "winter", "handmade"],
        "weight": 0.9
    },
    "Woven Leather Cuff": {
        "prompt": "Woven leather cuff bracelet with interlaced straps and a metal buckle, rustic artisan texture, bohemian styling",
        "description": "Rustic woven leather cuff",
        "tags": ["cuff", "leather", "woven", "bohemian", "artisan"],
        "weight": 0.9
    },
    "Jade Beaded Bracelet": {
        "prompt": "Jade beaded bracelet with polished green stones, smooth rounded beads, subtle traditional elegance, calm refined styling",
        "description": "Polished green jade beaded bracelet",
        "tags": ["bracelet", "jade", "beaded", "traditional", "elegant"],
        "weight": 0.9
    }
})
