"""
Apex Prompt Preset Selector Node - Enhanced
Professional prompt preset system with hierarchical categories for Environment, Lighting, Style,
Camera Lens and Color (colour grade).

This module provides:
- 30+ environment presets (urban, natural, fantasy, sci-fi, etc.)
- 30+ lighting presets (natural, dramatic, cinematic, artistic, etc.)
- 15+ style presets (photorealistic, anime, storybook, editorial, etc.)
- Weighted random selection for variety
- Dynamic preset combination with seed-based deterministic randomization
"""

import random
import re
from typing import Dict, List, Optional, Any
from .apex_prompt_store import get_store

class ApexPromptPreset:
    """
    Advanced prompt preset selector with Environment, Lighting, and Style categories.
    """
    
    def __init__(self):
        self._refresh_presets()

    def _refresh_presets(self):
        snapshot = get_store().snapshot()
        self.presets = snapshot["presets"]
        self._factory_presets = snapshot["factory"]
        self._random_names = snapshot["random_names"]
    
    @classmethod
    def INPUT_TYPES(cls):
        presets = get_store().snapshot()["presets"]
        return {
            "required": {
                "input_text": ("STRING", {"multiline": True, "default": ""}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
            "optional": {
                    "environment_preset": (["Disabled", "Random"] + list(presets["Apex Environment"]), {"default": "Disabled"}),
                    "lighting_preset": (["Disabled", "Random"] + list(presets["Apex Lighting"]), {"default": "Disabled"}),
                    "style_preset": (["Disabled", "Random"] + list(presets["Apex Style"]), {"default": "Disabled"}),
                    "camera_lens_preset": (["Disabled", "Random"] + list(presets["Apex Camera Lens"]), {"default": "Disabled"}),
                    "color_preset": (["Disabled", "Random"] + list(presets["Apex Color"]), {"default": "Disabled"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("combined_prompt", "environment_text", "lighting_text", "style_text", "camera_lens_text", "color_text")
    FUNCTION = "combine_prompts"
    CATEGORY = "Apex Artist/Text"

    def load_presets(self) -> Dict[str, Any]:
        """Read the shared library without modifying factory files."""
        return get_store().snapshot()["presets"]

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return get_store().snapshot()["revision"]

    @staticmethod
    def get_default_presets() -> Dict[str, Any]:
        """Get comprehensive default preset collection with expanded variety."""
        return {
            "Apex Environment": {
                # --- Original ---
                "Modern Subway Train": {
                    "prompt": "Modern subway train interior, stainless steel poles, clean white walls, large windows showing passing city skyline, softly blurred seated passengers in background, realistic subway environment.",
                    "description": "Contemporary subway interior with urban views",
                    "tags": ["subway", "urban", "interior", "modern"],
                    "weight": 1.0
                },
                "Ocean Sunrise": {
                    "prompt": "Endless ocean at sunrise, towering crystal-blue waves, dramatic clouds, soft sea mist, atmospheric haze, teal and turquoise ocean water, subtle warm orange sunrise tones.",
                    "description": "Seascape with dramatic waves and sunrise lighting",
                    "tags": ["ocean", "sunrise", "seascape", "dramatic"],
                    "weight": 1.0
                },
                "Rice Paddy Night": {
                    "prompt": "Lush glowing rice paddies at night, picnic setting beside reflective water canal, distant village with warm yellow lights, colorful green paddy fields stretching into distance, vibrant blue night sky with stars and fluffy cinematic clouds.",
                    "description": "Nighttime rural rice paddy landscape with village",
                    "tags": ["rice field", "rural", "night", "peaceful"],
                    "weight": 1.0
                },
                "Urban Street": {
                    "prompt": "Nighttime urban street scene with sleek sports cars positioned on wet asphalt, glowing neon signs, colorful city lights reflecting on street surface, tall buildings creating an urban canyon, moody cinematic atmosphere.",
                    "description": "Urban night street with neon and city lights",
                    "tags": ["urban", "street", "night", "neon"],
                    "weight": 1.0
                },
                "Studio Collage": {
                    "prompt": "Studio setting with dark charcoal-gray background, soft studio depth, clean premium backdrop, no competing environmental details, controlled space for optimal lighting.",
                    "description": "Clean studio environment with minimal backdrop",
                    "tags": ["studio", "clean", "minimal", "professional"],
                    "weight": 1.0
                },
                "Garage Workshop": {
                    "prompt": "Roadside workshop shelter during heavy rain at night, wet reflective asphalt road, storm clouds, distant car headlights through fog and rain, steaming coffee cups, scattered mechanic tools, telephone poles fading into distance.",
                    "description": "Rainy workshop garage with intimate working space",
                    "tags": ["garage", "workshop", "rain", "industrial"],
                    "weight": 1.0
                },
                "Countryside Village": {
                    "prompt": "Rural countryside landscape with distant village houses, long train moving across horizon, lush vegetation, natural trees, peaceful pastoral setting extending into the distance.",
                    "description": "Peaceful rural village and countryside vista",
                    "tags": ["countryside", "village", "rural", "pastoral"],
                    "weight": 1.0
                },
                # --- New Environments ---
                "Alpine Mountain Vista": {
                    "prompt": "Majestic alpine mountain landscape, snow-capped peaks piercing through clouds, pine forest covering lower slopes, crystal clear alpine lake reflecting the sky, wildflower meadow in foreground, dramatic rocky terrain, fresh mountain atmosphere.",
                    "description": "Dramatic alpine mountain scenery with lake and forest",
                    "tags": ["mountain", "alpine", "snow", "nature", "majestic"],
                    "weight": 1.0
                },
                "Tropical Beach Paradise": {
                    "prompt": "Pristine tropical beach with powdery white sand, crystal clear turquoise water gently lapping shore, swaying palm trees with green fronds, colorful coral reef visible offshore, bright blue sky with puffy white clouds, warm sunny tropical atmosphere.",
                    "description": "Tropical beach paradise with white sand and palm trees",
                    "tags": ["beach", "tropical", "ocean", "paradise", "summer"],
                    "weight": 1.0
                },
                "Desert Oasis": {
                    "prompt": "Vast golden desert landscape with towering sand dunes, a lush green oasis with palm trees surrounding a sparkling water pool, ancient ruins partially buried in sand, dramatic heat haze on horizon, warm golden sand stretching to horizon.",
                    "description": "Golden desert landscape with lush oasis",
                    "tags": ["desert", "oasis", "sand", "arid", "ancient"],
                    "weight": 1.0
                },
                "Misty Forest Path": {
                    "prompt": "Enchanted forest path winding through ancient trees, thick morning mist floating between trunks, soft moss-covered ground, shafts of light penetrating through canopy, ferns and wildflowers lining the path, mysterious ethereal woodland atmosphere.",
                    "description": "Mysterious misty forest with ancient trees",
                    "tags": ["forest", "misty", "enchanted", "nature", "moody"],
                    "weight": 1.0
                },
                "Medieval Castle Interior": {
                    "prompt": "Grand medieval castle interior, towering stone walls adorned with tapestries, massive arched windows casting colored light, iron chandeliers with flickering candles, stone floor polished by centuries of footsteps, heavy wooden doors with iron hinges.",
                    "description": "Grand medieval castle interior with stone architecture",
                    "tags": ["castle", "medieval", "stone", "interior", "historic"],
                    "weight": 1.0
                },
                "Space Station Hub": {
                    "prompt": "Futuristic space station hub with sweeping curved corridors, holographic displays showing star charts, large observation windows revealing earth and stars, floating indicator panels, sleek metallic surfaces with soft blue ambient lighting, zero-gravity environment details.",
                    "description": "Futuristic space station interior with star views",
                    "tags": ["space", "futuristic", "sci-fi", "space station", "interior"],
                    "weight": 1.0
                },
                "Underwater Coral Reef": {
                    "prompt": "Vibrant underwater coral reef ecosystem, colorful coral formations in orange and purple, schools of tropical fish swimming through sun rays piercing the water surface, floating plankton particles catching light, deep blue water fading into darkness below.",
                    "description": "Colorful underwater coral reef with marine life",
                    "tags": ["underwater", "coral", "reef", "ocean", "marine"],
                    "weight": 1.0
                },
                "Rooftop Cityscape": {
                    "prompt": "Urban rooftop overlooking a sprawling cityscape, AC units and water towers nearby, string lights draped across the roof, comfortable seating area with potted plants, panoramic view of skyscrapers and city lights, sunset sky painted in orange and purple hues.",
                    "description": "Rooftop terrace with panoramic city views",
                    "tags": ["rooftop", "cityscape", "urban", "sunset", "panoramic"],
                    "weight": 1.0
                },
                "Snowy Winter Cabin": {
                    "prompt": "Cozy wooden cabin nestled in snowy mountains, snow accumulating on roof and pine trees, warm golden light spilling from windows, chimney smoke rising into crisp winter air, snow-covered pathway leading to the front door, serene winter landscape surrounding the cabin.",
                    "description": "Cozy cabin in snowy winter landscape",
                    "tags": ["cabin", "snow", "winter", "cozy", "mountain"],
                    "weight": 1.0
                },
                "Cyberpunk Alley": {
                    "prompt": "Narrow cyberpunk alley in a rain-soaked megacity, vibrant neon signs in pink and cyan illuminating wet pavement, steam rising from street vents, exposed pipes and cables along building walls, flickering holographic advertisements, distant flying vehicles between towering skyscrapers.",
                    "description": "Rainy cyberpunk alley with neon lights",
                    "tags": ["cyberpunk", "alley", "neon", "rain", "futuristic"],
                    "weight": 1.0
                },
                "Ancient Temple Ruins": {
                    "prompt": "Ancient temple ruins overtaken by jungle vegetation, massive stone columns and crumbling walls covered in moss and vines, intricate carvings partially eroded by time, large stone altar at center, shafts of light breaking through the jungle canopy above.",
                    "description": "Ancient temple ruins reclaimed by jungle",
                    "tags": ["temple", "ruins", "ancient", "jungle", "mysterious"],
                    "weight": 1.0
                },
                "Futuristic Laboratory": {
                    "prompt": "Sleek futuristic laboratory with white glossy surfaces, holographic data displays floating above workstations, rows of glowing cylindrical chambers filled with liquid, advanced scientific equipment with blinking LEDs, clean minimalist design with blue accent lighting.",
                    "description": "Advanced futuristic scientific laboratory",
                    "tags": ["laboratory", "futuristic", "sci-fi", "clean", "minimalist"],
                    "weight": 1.0
                },
                "Cozy Library Interior": {
                    "prompt": "Grand cozy library with floor to ceiling bookshelves filled with leather-bound books, warm reading lamps on oak tables, tall arched windows with stained glass, comfortable armchairs arranged for reading, spiral staircase leading to upper galleries, peaceful studious atmosphere.",
                    "description": "Grand traditional library with warm intimate atmosphere",
                    "tags": ["library", "cozy", "books", "interior", "academic"],
                    "weight": 1.0
                },
                "Rainforest Canopy": {
                    "prompt": "Lush tropical rainforest canopy viewed from above, dense green foliage spreading in all directions, exotic flowers in bright colors dotting the greenery, morning mist rising from the jungle floor, vibrant parrot and butterfly species visible, sunlight filtering through multiple leaf layers.",
                    "description": "Lush tropical rainforest canopy from above",
                    "tags": ["rainforest", "canopy", "jungle", "tropical", "lush"],
                    "weight": 1.0
                },
                "Volcanic Wasteland": {
                    "prompt": "Dark volcanic landscape with jagged black rock formations, active lava flows glowing orange cutting through the terrain, plumes of smoke rising from volcanic vents, ash-covered ground with occasional hardy plants, ominous red glow illuminating the scene from below.",
                    "description": "Dark volcanic landscape with flowing lava",
                    "tags": ["volcano", "lava", "wasteland", "dramatic", "dark"],
                    "weight": 1.0
                },
                "Zen Garden": {
                    "prompt": "Peaceful Japanese zen garden with carefully raked sand patterns, smooth rounded stones of varying sizes, carefully pruned bonsai trees, bamboo water feature trickling into a stone basin, moss-covered stone lantern, cherry blossom petals scattered on the sand.",
                    "description": "Serene Japanese zen garden with raked sand",
                    "tags": ["garden", "zen", "japanese", "peaceful", "minimalist"],
                    "weight": 1.0
                },
                "Steampunk Airship Deck": {
                    "prompt": "Steampunk airship observation deck with brass fittings and copper pipes, large glass panels offering views of clouds below, leather-bound control panels with pressure gauges and steam vents, intricate gear mechanisms visible through glass floor panels, warm orange glow from gas lamps.",
                    "description": "Steampunk airship deck with brass and copper details",
                    "tags": ["steampunk", "airship", "deck", "brass", "vintage"],
                    "weight": 1.0
                },
                "Abandoned Hospital": {
                    "prompt": "Abandoned hospital corridor with peeling paint and cracked tiles, dim fluorescent lights flickering overhead, gurneys overturned and medical equipment scattered, broken windows covered by dusty blinds, strange shadows cast by unknown sources, decaying institutional atmosphere.",
                    "description": "Decaying abandoned hospital corridor",
                    "tags": ["abandoned", "hospital", "horror", "decay", "creepy"],
                    "weight": 1.0
                },
                "Lavender Field Sunset": {
                    "prompt": "Endless lavender fields stretching to the horizon, rows of purple blooms creating sweeping color patterns, warm golden sunset light casting long shadows across the fields, distant farmhouse and cypress trees, bees buzzing among the flowers, peaceful rural evening atmosphere.",
                    "description": "Purple lavender fields at golden sunset",
                    "tags": ["lavender", "field", "sunset", "provence", "nature"],
                    "weight": 1.0
                },
                # --- Storybook Environments (from reference images) ---
                "Wildflower Meadow": {
                    "prompt": "Peaceful wildflower meadow, soft grass, small winding stream, diverse botanical plants and flowers including daisies wildflowers and tall grass, rocks along the water, natural landscape with depth, gentle rolling terrain.",
                    "description": "Serene wildflower meadow with stream and diverse botanicals",
                    "tags": ["meadow", "wildflower", "pastoral", "nature", "peaceful"],
                    "weight": 1.0
                },
                "Pastoral Hillside Stream": {
                    "prompt": "Grassy rolling hill with vibrant green grass, small stream with blue water, tall grass tufts, colorful wildflowers including pink daisies white flowers and yellow blooms, blue sky with soft white clouds, rounded hill landscape stretching into distance.",
                    "description": "Rolling grassy hillside with stream and colorful flowers",
                    "tags": ["hillside", "pastoral", "stream", "flowers", "rolling hills"],
                    "weight": 1.0
                },
                "Enchanted Storybook Garden": {
                    "prompt": "Gentle sloped hillside with vibrant green grass, stream with flowing water ripples, rounded white and gray stones, tall golden grass tufts, colorful flower clusters forming pink clouds yellow blooms and white petals, blue sky background, peaceful pastoral fairy-tale setting.",
                    "description": "Enchanted storybook garden with flower clusters and stream",
                    "tags": ["storybook", "garden", "enchanted", "flowers", "fairy tale"],
                    "weight": 1.0
                },
                "Peaceful Countryside Pasture": {
                    "prompt": "Open wildflower meadow with diverse botanical flowers scattered throughout including orange coral daisies yellow flowers blue flowers and white blooms, natural grass field, light clouds in sky, pastoral landscape stretching into distance, peaceful countryside setting with gentle rolling terrain.",
                    "description": "Peaceful countryside pasture with diverse wildflowers",
                    "tags": ["countryside", "pasture", "wildflowers", "peaceful", "natural"],
                    "weight": 1.0
                },
                # --- Fashion Collage Portrait (from user request) ---
                "Fashion Collage Portrait": {
                    "prompt": "Studio setting, dark charcoal-gray background with soft studio depth, elegant visual separation, moody dark backdrop contrast.",
                    "description": "Studio collage layout with dark backdrop and multi-panel composition",
                    "tags": ["studio", "collage", "multi-panel", "dark"],
                    "weight": 1.0
                },
                # --- Subway Fashion Portrait (from user request) ---
                "Subway Fashion Portrait": {
                    "prompt": "Modern subway train interior, standing beside large window, stainless steel poles, overhead fluorescent lighting, clean white walls, large train windows showing passing city skyline, natural daylight streaming through windows, softly blurred passengers seated in background, realistic subway environment. Fashion editorial photography, Korean street fashion aesthetic, contemporary urban style, candid moment, cinematic atmosphere, soft color grading, natural daylight photograph, real camera photo, masterpiece, best quality, photorealistic, hyperrealistic, 8K, DSLR photography quality. Ultra-detailed clothing textures (realistic leather, ribbed knit fabric, fluffy faux fur, intricate silver accessories), highly detailed facial features, realistic eyes, natural skin pores, subtle skin texture, shallow depth of field, creamy bokeh, ultra sharp focus. Camera specs: Canon EOS R5, 85mm lens, f/1.8, ISO 100.",
                    "description": "Contemporary subway interior with urban views and natural light",
                    "tags": ["subway", "urban", "interior", "contemporary", "transport"],
                    "weight": 1.0
                },
                "Cozy Bedroom Window": {
                    "prompt": "Cozy minimalist bedroom bathed in warm golden morning sunlight streaming through large white-framed window. Soft natural light creates gentle highlights and long window-frame shadows across neatly made white bed with fluffy duvet, cream sherpa blanket, and pale blush pillows. Clear glass vase with pale pink tulips on white windowsill beside ceramic coffee mug and small framed photograph. Outside window, softly blurred urban apartment buildings create subtle depth with creamy bokeh effect. White walls decorated with small aesthetic photo prints and minimal handwritten quote, calm lived-in atmosphere. Clean Scandinavian interior design, neutral beige and white color palette, airy composition, peaceful morning mood.",
                    "description": "Cozy Scandinavian bedroom with morning window light",
                    "tags": ["bedroom", "cozy", "scandinavian", "window", "morning"],
                    "weight": 1.0
                }
            },
            "Apex Lighting": {
                # --- Original ---
                "Natural Daylight Window": {
                    "prompt": "Natural daylight streams through large window, soft diffused key light, gentle shadows, bright and open illumination, soft color grading, high dynamic range appearance, controlled highlights, detail-rich shadows.",
                    "description": "Soft natural window light with diffused illumination",
                    "tags": ["daylight", "natural", "window", "soft"],
                    "weight": 1.2
                },
                "Volumetric Moonlight": {
                    "prompt": "Bright full moon illuminating landscape, moonlight reflecting beautifully on water and wet grass, volumetric moonlight, atmospheric fog, gentle fill light, cool-neutral color temperature, dreamy ethereal quality.",
                    "description": "Dramatic moonlit scene with volumetric effects",
                    "tags": ["moonlight", "night", "volumetric", "dreamy"],
                    "weight": 1.3
                },
                "Golden Cinematic Rays": {
                    "prompt": "Golden rays of light breaking through dramatic clouds, intense golden backlight, heavenly volumetric rays, bright rim light, warm orange glow, cinematic color grading, high dynamic range, unclipped highlights.",
                    "description": "Dramatic golden light with volumetric rays",
                    "tags": ["cinematic", "golden", "dramatic", "rays"],
                    "weight": 1.3
                },
                "Studio Professional": {
                    "prompt": "Professional studio lighting with carefully positioned key light and fill light, even illumination throughout the scene, subtle rim lighting highlighting edges, soft flattering light without harsh shadows, neutral white balance, true-to-life colors, perfect exposure.",
                    "description": "Professional studio setup with even balanced light",
                    "tags": ["studio", "professional", "even", "balanced"],
                    "weight": 1.3
                },
                "Warm Lantern Mix": {
                    "prompt": "Cozy warm lantern glow mixed with cool moonlight, soft ambient fill from interior sources, warm tungsten bulb quality contrasting cool night atmosphere, intimate localized lighting, realistic material reflections.",
                    "description": "Warm intimate light mixed with cool night tones",
                    "tags": ["warm", "lantern", "cozy", "atmospheric"],
                    "weight": 1.2
                },
                "Neon Urban Night": {
                    "prompt": "Neon signs and colorful city lights, teal-blue shadows contrasting warm orange highlights, light reflecting on wet surfaces, bright dynamic color palette, harsh clean urban lighting, high contrast dramatic illumination.",
                    "description": "Vibrant neon urban night lighting",
                    "tags": ["neon", "urban", "night", "colorful"],
                    "weight": 1.3
                },
                "HDR Balanced": {
                    "prompt": "Cinematic color grading, high dynamic range, low-contrast balanced exposure, teal and orange color grading, soft bloom, realistic material rendering, smooth tonal transitions, no blown highlights, preserved shadow detail.",
                    "description": "Modern HDR color grading with balanced exposure",
                    "tags": ["HDR", "cinematic", "balanced", "modern"],
                    "weight": 1.2
                },
                # --- New Lighting ---
                "Moody Rembrandt Lighting": {
                    "prompt": "Rembrandt lighting with strong key light from above and to the side, characteristic triangle of light, deep dramatic shadows, rich chiaroscuro contrast, warm amber tones in highlights, painterly shadow quality.",
                    "description": "Classic Rembrandt lighting with deep shadows",
                    "tags": ["rembrandt", "chiaroscuro", "dramatic", "classic", "painterly"],
                    "weight": 1.3
                },
                "Sunrise Golden Hour": {
                    "prompt": "Early morning golden hour light, warm golden-orange sunlight at low angle, long soft shadows stretching across the scene, gentle warm glow on everything, subtle morning haze, dewdrops catching light, fresh vibrant color temperature.",
                    "description": "Warm golden hour sunrise lighting",
                    "tags": ["sunrise", "golden hour", "warm", "morning", "soft"],
                    "weight": 1.2
                },
                "Sunset Purple Dusk": {
                    "prompt": "Twilight sunset lighting with rich purple and magenta sky tones, warm orange horizon fading to cool purple overhead, soft ambient fill from scattered sky light, silhouettes against the colorful sky, romantic and nostalgic atmosphere.",
                    "description": "Rich purple dusk twilight lighting",
                    "tags": ["sunset", "dusk", "purple", "twilight", "romantic"],
                    "weight": 1.2
                },
                "Bioluminescent Glow": {
                    "prompt": "Ethereal bioluminescent lighting with glowing blue and green particles floating in the air, soft cool-colored illumination from natural sources, magical luminous quality, organic light patterns resembling fireflies or deep-sea creatures, dreamlike atmosphere.",
                    "description": "Ethereal bioluminescent glowing light",
                    "tags": ["bioluminescent", "glowing", "magical", "ethereal", "blue"],
                    "weight": 1.3
                },
                "Candlelit Warmth": {
                    "prompt": "Intimate candlelit scene with warm flickering orange light, soft golden glow throughout the space, deep warm shadows, dramatic contrast between light and dark, cozy romantic atmosphere, subtle smoke trails catching light above flames.",
                    "description": "Warm intimate candlelight illumination",
                    "tags": ["candle", "warm", "intimate", "romantic", "cozy"],
                    "weight": 1.2
                },
                "Overcast Diffuse Skylight": {
                    "prompt": "Soft overcast sky providing even diffuse lighting, no harsh shadows, completely uniform illumination, soft cloud-filtered daylight, muted natural colors, ideal for product photography, smooth gradients across all surfaces, gently wrapped light.",
                    "description": "Soft even overcast skylight with no shadows",
                    "tags": ["overcast", "diffuse", "soft", "even", "cloudy"],
                    "weight": 1.1
                },
                "Midnight Starlight": {
                    "prompt": "Deep midnight scene illuminated only by starlight, very low light levels with subtle blue ambient glow, scattered stars visible in the sky, faint Milky Way band, organic dark shadows, visible constellations, peaceful vastness of the night sky.",
                    "description": "Minimal starlight illumination in deep night",
                    "tags": ["starlight", "midnight", "dark", "stars", "peaceful"],
                    "weight": 1.1
                },
                "Fluorescent Office Cool": {
                    "prompt": "Cool fluorescent overhead lighting, even flat illumination with slight greenish-blue cast, harsh shadows under desks and equipment, clinical institutional feel, bright ceiling panels creating multiple light sources, sterile workplace atmosphere.",
                    "description": "Cool fluorescent office lighting",
                    "tags": ["fluorescent", "office", "cool", "clinical", "industrial"],
                    "weight": 1.0
                },
                "Fireworks Explosive Color": {
                    "prompt": "Dynamic colored light from fireworks and sparklers, explosive bursts of red gold blue and green light, rapidly changing colorful highlights, dramatic contrast between dark sky and brilliant explosions, festive celebratory atmosphere, sparkling particles trailing through air.",
                    "description": "Explosive colorful fireworks illumination",
                    "tags": ["fireworks", "colorful", "explosive", "festive", "dynamic"],
                    "weight": 1.3
                },
                "Lightning Storm Flash": {
                    "prompt": "Brief intense lightning flash illumination, stark white-blue light revealing landscape in sharp detail, deep crushing shadows immediately following the flash, dramatic storm clouds backlit by electrical discharge, high contrast monochromatic moment, rain visible in frozen light.",
                    "description": "Stark lightning flash illumination during storm",
                    "tags": ["lightning", "storm", "flash", "dramatic", "intense"],
                    "weight": 1.3
                },
                "Underwater Caustic Light": {
                    "prompt": "Underwater lighting with dancing caustic light patterns on surfaces, sunlight filtering through water creating moving rippled light, blue-green color cast, soft volumetric water haze, light rays scattering through particles, organic flowing illumination patterns.",
                    "description": "Dancing underwater caustic light patterns",
                    "tags": ["underwater", "caustic", "ripple", "aquatic", "pattern"],
                    "weight": 1.2
                },
                "Dappled Forest Sunlight": {
                    "prompt": "Dappled sunlight filtering through a forest canopy, small bright spots of light scattered across the forest floor, long shafts of light between tree trunks, warm yellow-green color palette, organic light patterns dancing on leaves, magical woodland atmosphere.",
                    "description": "Dappled sunlight through forest canopy",
                    "tags": ["dappled", "forest", "sunlight", "magical", "nature"],
                    "weight": 1.2
                },
                "Silhouette Backlight": {
                    "prompt": "Strong dramatic backlight creating clean silhouettes, bright light source from behind with minimal or no fill light, deep shadow areas retaining rich color, bright colored rim light on edges, high contrast scene, atmospheric haze catching the backlight, moody and cinematic.",
                    "description": "Dramatic backlight creating silhouettes",
                    "tags": ["silhouette", "backlight", "dramatic", "contrast", "rim light"],
                    "weight": 1.3
                },
                "Ring Light Beauty": {
                    "prompt": "Professional ring light lighting, soft even illumination with characteristic circular catchlights, minimal shadows, flattering wraparound light throughout the frame, clean bright photography look, natural true-to-life skin tones.",
                    "description": "Flattering ring light photography lighting",
                    "tags": ["ring light", "flattering", "soft", "circular"],
                    "weight": 1.2
                },
                "LED Strip Color Wash": {
                    "prompt": "Modern LED strip lighting creating colored accent washes on walls and surfaces, vibrant saturated color in pink blue and purple, gradient transitions between colors, contemporary studio aesthetic, creative mixed color temperatures, artistic RGB illumination.",
                    "description": "Modern colored LED strip accent lighting",
                    "tags": ["LED", "colorful", "modern", "RGB", "artistic"],
                    "weight": 1.1
                },
                "Twilight Blue Hour": {
                    "prompt": "Blue hour twilight lighting with deep blue sky fading to warm horizon, soft cool ambient light with subtle warm accents from distant city lights, calm serene atmosphere, rich blue tones dominating the scene, peaceful transition between day and night.",
                    "description": "Twilight blue hour with cool blue tones",
                    "tags": ["twilight", "blue hour", "cool", "serene", "evening"],
                    "weight": 1.2
                },
                "Dramatic Side Light": {
                    "prompt": "Strong side lighting creating bold contrast, light raking across the scene from one side, deep shadows on the opposite side, pronounced texture enhancement, sculptural quality revealing every surface detail, intense dramatic mood, natural skin tones and rich color preserved.",
                    "description": "Strong side light creating texture and contrast",
                    "tags": ["side light", "dramatic", "texture", "contrast", "sculptural"],
                    "weight": 1.3
                },
                "Soft Porch Light": {
                    "prompt": "Warm welcoming porch light illumination, soft golden glow spreading across doorway and steps, gentle light pooling on the ground, inviting warm atmosphere, subtle insect shadows in the light cone, cozy domestic evening setting, nostalgic homely feeling.",
                    "description": "Warm welcoming porch light at evening",
                    "tags": ["porch light", "warm", "cozy", "home", "evening"],
                    "weight": 1.1
                },
                # --- Storybook Lighting (from reference images) ---
                "Soft Watercolor Wash": {
                    "prompt": "Soft watercolor wash background in pale mint and cream tones, diffused gentle light throughout the scene, muted natural colors including greens golds corals and soft blues, low contrast, peaceful dreamy atmosphere, watercolor bloom effects, gentle ethereal quality.",
                    "description": "Soft watercolor wash with muted pastel tones",
                    "tags": ["watercolor", "wash", "soft", "pastel", "dreamy"],
                    "weight": 1.1
                },
                "Pastel Dream Light": {
                    "prompt": "Bright cheerful even studio lighting, soft pastel colors with soft orange white gray and pink accents, saturated but gentle color palette, clear blue sky light, no harsh shadows, warm inviting atmosphere, diffused wraparound illumination.",
                    "description": "Bright cheerful pastel lighting with soft tones",
                    "tags": ["pastel", "bright", "cheerful", "soft", "even"],
                    "weight": 1.1
                },
                "Gentle Storybook Diffuse": {
                    "prompt": "Bright cheerful lighting with soft pastel palette dominated by mint green grass tones sky blue coral pink and soft golden tones, even illumination throughout, warm inviting mood, clear visibility, no harsh shadows, gentle dreamy quality, soft rounded light.",
                    "description": "Gentle even diffuse light with storybook warmth",
                    "tags": ["diffuse", "storybook", "gentle", "warm", "soft"],
                    "weight": 1.1
                },
                "Warm Pastoral Glow": {
                    "prompt": "Soft warm natural light with golden-hour quality, warm natural tones, muted earth tones mixed with gentle flower colors, diffused gentle light, warm spiritual mood, calm peaceful atmosphere, soft amber and cream highlights.",
                    "description": "Warm pastoral glow with golden-hour quality",
                    "tags": ["warm", "pastoral", "golden hour", "peaceful", "natural"],
                    "weight": 1.2
                }
            },
            "Apex Style": {
                "Fashion Editorial": {
                    "prompt": "Fashion editorial photography aesthetic, contemporary urban style, candid moment, cinematic atmosphere, ultra-detailed textures, realistic material detail, soft color grading, photorealistic, hyperrealistic, masterpiece, best quality, DSLR photography quality.",
                    "description": "Premium fashion editorial aesthetic with detailed textures",
                    "tags": ["fashion", "editorial", "cinematic", "urban"],
                    "weight": 1.3
                },
                "Cinematic Elegance": {
                    "prompt": "Ultra-realistic cinematic, premium movie-poster quality, photorealistic, 8K, HDR, low-contrast cinematic color grading, dramatic but peaceful mood, emotionally powerful, elegant, minimalist composition, Hollywood poster aesthetic.",
                    "description": "Cinematic elegant aesthetic with dramatic mood",
                    "tags": ["cinematic", "elegant", "emotional", "dramatic"],
                    "weight": 1.3
                },
                "Anime Painterly": {
                    "prompt": "Semi-realistic anime painting with subtle 3D depth, painterly anime realism, soft realistic shading, handcrafted digital painting look, Makoto Shinkai + Studio Ghibli inspired, semi-3D anime render, visual novel CG style, ultra detailed environment art.",
                    "description": "Anime painterly style with Studio Ghibli influence",
                    "tags": ["anime", "painterly", "ghibli", "3D"],
                    "weight": 1.2
                },
                "Premium Commercial": {
                    "prompt": "Premium social media aesthetic, clean premium look, commercial photography style, soft minimalist polished aesthetic, naturally captured instead of heavily staged, emphasizing realism and subtle elegance, high-end digital finish, fine textures preserved.",
                    "description": "Commercial premium polished aesthetic",
                    "tags": ["commercial", "premium", "clean", "polished"],
                    "weight": 1.2
                },
                "Photorealistic": {
                    "prompt": "Photorealistic photograph, candid real-life photo, natural skin texture with visible pores, shot on 35mm film, soft natural light, realistic imperfections, true-to-life colors, rich natural color palette, ultra-detailed, sharp focus, masterpiece, best quality.",
                    "description": "Ultra-realistic photographic photo",
                    "tags": ["photorealistic", "photograph", "detailed", "natural skin"],
                    "weight": 1.3
                },
                "Luxury Album Cover": {
                    "prompt": "Ultra-realistic cinematic album cover, premium movie-poster quality, photorealistic, 8K, HDR, rich vibrant color grading, premium Future Bass aesthetic, emotional and uplifting, luxury music album artwork, professional Spotify and Apple Music promotional artwork, minimalist elegant composition.",
                    "description": "Luxury music album artwork aesthetic",
                    "tags": ["album", "luxury", "music", "professional"],
                    "weight": 1.3
                },
                "Visual Novel CG": {
                    "prompt": "Visual novel CG style, detailed anime background, anime matte painting, soft rendered anime, cozy rural aesthetic, emotional anime scene, dreamy atmosphere, atmospheric perspective, immersive environmental storytelling, high detail environment art.",
                    "description": "Visual novel game CG aesthetic",
                    "tags": ["visual novel", "game", "CG", "atmospheric"],
                    "weight": 1.2
                },
                # --- Storybook Styles (from reference images) ---
                "Watercolor Storybook": {
                    "prompt": "Watercolor illustration, soft botanical aesthetic, whimsical children's book illustration, gentle and contemplative mood, hand-painted quality, delicate linework, subtle texture, artistic storybook aesthetic, soft watercolor washes, creative artistic style.",
                    "description": "Watercolor storybook illustration with soft botanical feel",
                    "tags": ["watercolor", "storybook", "illustration", "botanical", "artistic"],
                    "weight": 1.2
                },
                "3D Clay Render": {
                    "prompt": "3D rendered illustration, clay felt aesthetic, soft rounded forms, chibi cute design style, pastel color palette, toy-like quality, digital 3D art with soft shading, children's illustration style, playful and charming mood, soft surface texture quality.",
                    "description": "3D clay/felt rendered illustration with soft rounded forms",
                    "tags": ["3D", "clay", "render", "chibi", "toy-like", "cute"],
                    "weight": 1.2
                },
                "Children's Book Illustration": {
                    "prompt": "Children's book illustration style, soft narrative storytelling quality, gentle and compassionate mood, traditional storybook aesthetic, warm inviting visual language, whimsical playful charm, soft composition, delicate hand-painted look, charming storybook design.",
                    "description": "Classic children's book illustration with narrative warmth",
                    "tags": ["children's book", "illustration", "storybook", "whimsical", "narrative"],
                    "weight": 1.2
                },
                "Whimsical Pastel Art": {
                    "prompt": "Soft rounded volumetric forms, cute design aesthetic, digital 3D art with soft shading, children's book illustration style, playful whimsical mood, soft surface texture quality, charming storybook design, pastel color palette, dreamy storybook atmosphere.",
                    "description": "Whimsical pastel art with soft volumetric forms",
                    "tags": ["whimsical", "pastel", "volumetric", "cute", "playful"],
                    "weight": 1.2
                },
                "Fashion Collage Portrait": {
                    "prompt": "Ultra-realistic IMAX-level Netflix-style cinematic elegant collage visual, premium five-panel collage layout, premium luxury editorial collage aesthetic, ultra-rich color grading with deep saturated tones, sophisticated color palette, warm cinematic highlights against moody dark backdrop. Creamy bokeh, elegant visual separation, HDR lighting, global illumination, photorealistic rendering, shallow depth of field, masterpiece quality, ultra-sharp details, 8K production detail.",
                    "description": "Premium fashion collage with ultra-realistic cinematic rendering",
                    "tags": ["fashion", "collage", "cinematic", "ultra-realistic", "editorial"],
                    "weight": 1.3
                }
            },
            "Apex Camera Lens": {
                # === ULTRA WIDE ANGLE LENSES ===
                "14mm Fisheye": {
                    "prompt": "14mm fisheye lens, extreme wide angle of view, dramatic spherical barrel distortion, f/2.8 aperture, edge-to-edge coverage with curved perspective, artistic warped geometry, ultra-wide field of view capturing vast context.",
                    "description": "Fisheye lens - extreme wide with spherical distortion",
                    "tags": ["14mm", "fisheye", "extreme wide", "distortion", "barrel"],
                    "weight": 1.0
                },
                "16mm Ultra Wide": {
                    "prompt": "16mm ultra wide angle lens, expansive field of view, dramatic perspective with exaggerated depth, slight barrel distortion, f/2.8 aperture, sweeping coverage from foreground to horizon, architectural and landscape cinematography character.",
                    "description": "Ultra wide lens - expansive field of view",
                    "tags": ["16mm", "ultra wide", "expansive", "perspective", "vista"],
                    "weight": 1.1
                },
                "18mm Wide": {
                    "prompt": "18mm wide angle lens, broad field of view with dramatic perspective, natural proportions with architectural quality, minimal barrel distortion, f/3.5 aperture, landscape and environmental character, expansive spatial coverage.",
                    "description": "Wide lens - broad field with dramatic perspective",
                    "tags": ["18mm", "wide", "architectural", "perspective", "spatial"],
                    "weight": 1.1
                },
                
                # === WIDE ANGLE LENSES ===
                "24mm Wide Angle": {
                    "prompt": "24mm wide angle lens, moderate wide perspective with balanced coverage, slight barrel distortion, f/2.8 aperture, documentary and architectural photography character, natural spatial relationships with environmental depth.",
                    "description": "Wide angle - balanced perspective coverage",
                    "tags": ["24mm", "wide angle", "balanced", "documentary", "spatial"],
                    "weight": 1.2
                },
                "28mm Documentary": {
                    "prompt": "28mm documentary lens, natural wide perspective with minimal distortion, f/2.0 aperture, photojournalism and street photography character, comfortable viewing angle with environmental depth, authentic spatial relationships.",
                    "description": "Documentary lens - natural wide perspective",
                    "tags": ["28mm", "documentary", "photojournalism", "street", "natural"],
                    "weight": 1.2
                },
                "35mm Street": {
                    "prompt": "35mm lens, natural viewing angle approximating human perspective, minimal distortion, f/1.8 aperture, street photography character, comfortable field of view, versatile medium-wide coverage with spatial depth.",
                    "description": "Street lens - natural human perspective",
                    "tags": ["35mm", "street", "natural", "versatile", "comfortable"],
                    "weight": 1.3
                },
                
                # === STANDARD/NORMAL LENSES ===
                "40mm Standard": {
                    "prompt": "40mm standard lens, slightly compressed natural perspective, f/2.0 aperture, versatile focal length with balanced field of view, moderate depth of field characteristics, neutral compression and spatial relationships.",
                    "description": "Standard lens - balanced compression",
                    "tags": ["40mm", "standard", "balanced", "versatile", "neutral"],
                    "weight": 1.2
                },
                "50mm Classic": {
                    "prompt": "50mm classic standard lens, natural perspective matching human vision, moderate depth of field, f/1.8 aperture, neutral compression and distortion characteristics, versatile focal length with balanced optical properties.",
                    "description": "Classic 50mm - natural eye perspective",
                    "tags": ["50mm", "classic", "natural", "standard", "versatile"],
                    "weight": 1.3
                },
                "55mm Normal": {
                    "prompt": "55mm normal lens, light perspective compression, f/1.8 aperture, moderate background separation with shallow depth of field, transitional focal length between standard and short telephoto ranges.",
                    "description": "Normal lens - light compression",
                    "tags": ["55mm", "normal", "compression", "transitional", "moderate"],
                    "weight": 1.2
                },
                
                # === PORTRAIT TELEPHOTO LENSES ===
                "75mm Portrait": {
                    "prompt": "75mm short telephoto lens, light flattering compression, f/1.8 aperture, shallow depth of field with creamy background separation, natural perspective compression, tight field of view with moderate working distance.",
                    "description": "Portrait lens - light compression",
                    "tags": ["75mm", "portrait", "compression", "flattering", "shallow"],
                    "weight": 1.3
                },
                "85mm Portrait Classic": {
                    "prompt": "85mm classic portrait lens, flattering facial compression with natural perspective, f/1.4 wide aperture, shallow depth of field with creamy circular bokeh, tight field of view, professional rendering with smooth background separation.",
                    "description": "Classic 85mm portrait - flattering compression",
                    "tags": ["85mm", "portrait", "compression", "flattering", "bokeh"],
                    "weight": 1.4
                },
                "100mm Portrait": {
                    "prompt": "100mm short telephoto lens, pronounced compression with flattering perspective, f/2.0 aperture, strong background separation with shallow focus, smooth bokeh characteristics, tight field of view with minimal depth coverage.",
                    "description": "100mm portrait - pronounced compression",
                    "tags": ["100mm", "portrait", "tight", "compression", "bokeh"],
                    "weight": 1.3
                },
                "105mm Headshot": {
                    "prompt": "105mm short telephoto lens, strong flattering compression, f/2.0 aperture, very shallow depth of field with complete background defocus, narrow field of view, professional optical characteristics with smooth bokeh.",
                    "description": "105mm lens - strong compression",
                    "tags": ["105mm", "telephoto", "tight", "compression", "shallow"],
                    "weight": 1.3
                },
                
                # === TELEPHOTO LENSES ===
                "135mm Fashion": {
                    "prompt": "135mm telephoto lens, very strong compression flattening perspective, f/2.0 aperture, extremely shallow depth of field, background compressed into abstract color wash, narrow field of view with pronounced telephoto character, smooth bokeh rendering.",
                    "description": "Fashion telephoto - extreme compression",
                    "tags": ["135mm", "fashion", "compression", "telephoto", "beauty"],
                    "weight": 1.3
                },
                "150mm Telephoto": {
                    "prompt": "150mm telephoto lens, extreme compression and perspective flattening, f/2.8 aperture, razor-thin depth of field, background completely abstracted, distant working distance with narrow field of view, compressed spatial relationships.",
                    "description": "Telephoto - extreme compression",
                    "tags": ["150mm", "telephoto", "compression", "narrow", "distant"],
                    "weight": 1.2
                },
                "200mm Long Telephoto": {
                    "prompt": "200mm long telephoto lens, maximum compression flattening all perspective, f/2.8 aperture, paper-thin depth of field, background reduced to pure bokeh abstractions, distant working distance with very narrow field of view, wildlife and sports photography compression character.",
                    "description": "Long telephoto - maximum compression",
                    "tags": ["200mm", "long telephoto", "extreme compression", "narrow", "distant"],
                    "weight": 1.2
                },
                "300mm Super Telephoto": {
                    "prompt": "300mm super telephoto lens, extreme perspective compression collapsing depth, f/4.0 aperture, minimal depth of field, background utterly defocused into color fields, very narrow field of view from distant working distance, wildlife and sports photography aesthetic.",
                    "description": "Super telephoto - maximum compression",
                    "tags": ["300mm", "super telephoto", "compression", "wildlife", "distant"],
                    "weight": 1.1
                },
                
                # === MACRO LENSES ===
                "60mm Macro": {
                    "prompt": "60mm macro lens, close working distance with 1:2 magnification ratio, f/2.8 aperture, shallow depth of field revealing intricate texture, intimate detail rendering capabilities, moderate working distance for flexibility.",
                    "description": "Macro lens - close-up detail capability",
                    "tags": ["60mm", "macro", "close-up", "detail", "texture"],
                    "weight": 1.1
                },
                "100mm Macro": {
                    "prompt": "100mm macro lens, 1:1 life-size magnification ratio, f/2.8 aperture, razor-thin depth of field, ultra-sharp focus rendering of microscopic details, comfortable working distance with natural lighting capability, professional macro photography optics.",
                    "description": "Macro 100mm - 1:1 magnification capability",
                    "tags": ["100mm", "macro", "magnification", "detail", "texture"],
                    "weight": 1.2
                },
                "180mm Macro": {
                    "prompt": "180mm telephoto macro lens, 1:1 magnification with extended working distance, f/3.5 aperture, compressed perspective combined with macro magnification, distance-based isolation with smooth bokeh, professional nature macro photography optics.",
                    "description": "Telephoto macro - magnification with distance",
                    "tags": ["180mm", "macro", "telephoto", "detail", "distant"],
                    "weight": 1.1
                },
                
                # === SPECIALTY LENSES ===
                "45mm Tilt-Shift": {
                    "prompt": "45mm tilt-shift lens, creative focus plane manipulation capability, miniature effect optical characteristics, architectural perspective correction, f/2.8 aperture, unique depth of field control independent of aperture, technical photography optics.",
                    "description": "Tilt-shift - perspective control and selective plane",
                    "tags": ["45mm", "tilt-shift", "selective focus", "miniature", "architectural"],
                    "weight": 1.0
                },
                "Lensbaby Composer": {
                    "prompt": "Lensbaby selective focus lens, sweet spot sharpness with peripheral artistic blur, swirling bokeh characteristics, f/2.0 aperture, creative focus control through lens manipulation, whimsical ethereal rendering, painterly optical quality.",
                    "description": "Lensbaby - artistic selective focus optics",
                    "tags": ["lensbaby", "dreamy", "selective focus", "artistic", "whimsical"],
                    "weight": 1.0
                },
                "Petzval 85mm": {
                    "prompt": "85mm Petzval lens, characteristic swirling bokeh pattern, vintage optical formula with dreamy rendering, sharp center with artistic peripheral blur, f/2.2 aperture, warm nostalgic color cast, soft glow in highlights, unique bokeh personality.",
                    "description": "Petzval - vintage swirly bokeh optics",
                    "tags": ["85mm", "petzval", "vintage", "swirly bokeh", "artistic"],
                    "weight": 1.1
                },
                
                # === ZOOM LENSES ===
                "24-70mm Standard Zoom": {
                    "prompt": "24-70mm f/2.8 standard zoom lens, versatile focal range from environmental wide to medium telephoto, professional optics with consistent rendering throughout zoom range, f/2.8 constant aperture, workhorse lens optical quality, balanced perspective characteristics.",
                    "description": "Standard zoom - versatile focal range",
                    "tags": ["24-70mm", "zoom", "versatile", "standard", "professional"],
                    "weight": 1.2
                },
                "70-200mm Telephoto Zoom": {
                    "prompt": "70-200mm f/2.8 telephoto zoom lens, professional telephoto focal range with versatile compression characteristics, f/2.8 constant aperture, consistent creamy bokeh throughout zoom range, sports and portrait photography optics, flexible telephoto character.",
                    "description": "Telephoto zoom - professional telephoto range",
                    "tags": ["70-200mm", "telephoto zoom", "compression", "professional", "portrait"],
                    "weight": 1.3
                },
                "100-400mm Super Zoom": {
                    "prompt": "100-400mm super telephoto zoom lens, extreme compression and reach capability, f/4.5-5.6 variable aperture, wildlife and sports photography versatility, powerful magnification range, compressed perspective throughout focal range.",
                    "description": "Super zoom - extreme telephoto range",
                    "tags": ["100-400mm", "super zoom", "telephoto", "wildlife", "sports"],
                    "weight": 1.1
                },
                
                # === CINEMA PRIME LENSES ===
                "Zeiss Master Prime 25mm": {
                    "prompt": "Zeiss Master Prime 25mm cinema lens, wide focal length for film production, T1.3 maximum aperture, clinical sharpness with subtle organic character, minimal focus breathing, professional cinema rendering, Hollywood production optical quality.",
                    "description": "Cinema wide prime - professional wide optics",
                    "tags": ["25mm", "cinema", "zeiss", "master prime", "film production"],
                    "weight": 1.2
                },
                "Zeiss Master Prime 50mm": {
                    "prompt": "Zeiss Master Prime 50mm cinema lens, natural film perspective with subtle compression, T1.3 maximum aperture, clinical precision with organic falloff characteristics, minimal focus breathing, professional cinema production standard, Netflix and IMAX optical quality.",
                    "description": "Cinema standard prime - natural perspective optics",
                    "tags": ["50mm", "cinema", "zeiss", "master prime", "netflix"],
                    "weight": 1.3
                },
                "Zeiss Master Prime 85mm": {
                    "prompt": "Zeiss Master Prime 85mm cinema lens, short telephoto focal length for film, T1.3 maximum aperture, clinical sharpness with smooth bokeh falloff, professional portrait compression characteristics, minimal breathing, Hollywood cinematography optical standard.",
                    "description": "Cinema portrait prime - professional portrait optics",
                    "tags": ["85mm", "cinema", "zeiss", "portrait", "hollywood"],
                    "weight": 1.3
                },
                "Cooke S4 35mm": {
                    "prompt": "Cooke S4 35mm cinema lens, organic 'Cooke Look' optical character with warm rendering, T2.0 maximum aperture, gentle falloff and smooth bokeh characteristics, classic cinema rendering, soft organic optical quality, professional film production standard, warm cinematic color rendition.",
                    "description": "Cooke cinema lens - organic warm optics",
                    "tags": ["35mm", "cinema", "cooke", "organic", "film"],
                    "weight": 1.3
                },
                "Cooke S4 65mm": {
                    "prompt": "Cooke S4 65mm cinema lens, intimate 'Cooke Look' optical character, T2.0 maximum aperture, warm organic rendering with smooth falloff, gentle compression characteristics with beautiful tone rendition, classic cinema optics, professional production optical quality.",
                    "description": "Cooke cinema lens - warm intimate optics",
                    "tags": ["65mm", "cinema", "cooke", "intimate", "warm"],
                    "weight": 1.3
                },
                "Arri Signature Prime 40mm": {
                    "prompt": "Arri Signature Prime 40mm cinema lens, contemporary cinema optical design, T1.8 maximum aperture, large format coverage capability, smooth natural bokeh with modern optical formula, minimal aberrations, Netflix and IMAX production optical standard, modern digital cinema characteristics.",
                    "description": "Arri cinema prime - modern cinema optics",
                    "tags": ["40mm", "cinema", "arri", "signature", "modern"],
                    "weight": 1.2
                },
                
                # === ANAMORPHIC CINEMA LENSES ===
                "Anamorphic 35mm": {
                    "prompt": "35mm anamorphic cinema lens, 2.39:1 scope aspect ratio coverage, T2.0 aperture, characteristic horizontal blue lens flares, oval bokeh patterns, wide field of view with anamorphic optical character, cinematic widescreen scope format, Hollywood blockbuster optics.",
                    "description": "Anamorphic wide - widescreen scope optics",
                    "tags": ["35mm", "anamorphic", "widescreen", "scope", "flares"],
                    "weight": 1.3
                },
                "Anamorphic 50mm": {
                    "prompt": "50mm anamorphic cinema lens, 2.39:1 widescreen scope format coverage, T2.0 aperture, horizontal lens flares and oval bokeh patterns, natural perspective with anamorphic optical character, classic cinema widescreen scope optics, Hollywood aesthetic rendering.",
                    "description": "Anamorphic standard - widescreen scope optics",
                    "tags": ["50mm", "anamorphic", "medium shot", "scope", "cinema"],
                    "weight": 1.3
                },
                "Anamorphic 75mm": {
                    "prompt": "75mm anamorphic cinema lens, 2.39:1 scope format coverage, T2.0 aperture, characteristic horizontal streaking flares, oval bokeh patterns, cinematic portrait compression with anamorphic optical character, short telephoto field of view in scope format, Hollywood optics.",
                    "description": "Anamorphic portrait - widescreen scope optics",
                    "tags": ["75mm", "anamorphic", "portrait", "scope", "closeup"],
                    "weight": 1.3
                },
                "Panavision Anamorphic": {
                    "prompt": "Panavision anamorphic cinema lens, 2.39:1 Hollywood scope format coverage, legendary Panavision optical rendering, T2.3 aperture, iconic horizontal blue lens flares, smooth oval bokeh characteristics, classic Hollywood blockbuster optical quality, premium film production anamorphic optics.",
                    "description": "Panavision anamorphic - legendary Hollywood scope optics",
                    "tags": ["panavision", "anamorphic", "hollywood", "epic", "legendary"],
                    "weight": 1.4
                },
                "Atlas Orion Anamorphic": {
                    "prompt": "Vintage widescreen with Atlas Orion anamorphic lens, 2.39:1 scope with vintage character, T2.0 aperture, blue horizontal flares with vintage warmth, organic oval bokeh, classic anamorphic rendering with modern sharpness, retro-futuristic cinema aesthetic, vintage Hollywood scope character meets modern optical quality.",
                    "description": "Atlas Orion - vintage character anamorphic scope",
                    "tags": ["atlas orion", "anamorphic", "vintage", "scope", "character"],
                    "weight": 1.2
                },
                
                # === CINEMA ZOOM LENSES ===
                "Angenieux 25-250mm": {
                    "prompt": "Classic cinema zoom with Angenieux 25-250mm lens, versatile cinematic framing from wide to telephoto, T3.5 aperture, legendary Hollywood zoom lens, consistent rendering throughout range, vintage cinema character with modern sharpness, professional film production, flexible composition with classic cinema quality.",
                    "description": "Cinema zoom - legendary versatile range",
                    "tags": ["25-250mm", "cinema zoom", "angenieux", "classic", "versatile"],
                    "weight": 1.2
                },
                "Fujinon Premier 18-85mm": {
                    "prompt": "Documentary cinema shot with Fujinon Premier 18-85mm zoom, T2.0 constant aperture, flexible framing from wide environmental to portrait close-up, professional documentary cinema quality, consistent color and contrast throughout range, modern cinema zoom for Netflix and documentary production, natural rendering with cinema character.",
                    "description": "Cinema zoom - documentary production range",
                    "tags": ["18-85mm", "cinema zoom", "fujinon", "documentary", "netflix"],
                    "weight": 1.2
                },
                "Canon CN-E 30-300mm": {
                    "prompt": "Telephoto cinema shot with Canon CN-E 30-300mm zoom, professional cinematic compression throughout range, T2.95-3.7 aperture, powerful zoom reach from medium to extreme close-up, consistent bokeh and rendering, professional cinema production, sports and wildlife cinematography quality, flexible telephoto cinema framing.",
                    "description": "Cinema telephoto zoom - professional cinema reach",
                    "tags": ["30-300mm", "cinema zoom", "canon", "telephoto", "professional"],
                    "weight": 1.1
                },
                
                # === VINTAGE CINEMA CHARACTER LENSES ===
                "Vintage Cooke Panchro": {
                    "prompt": "Classic film look with vintage Cooke Panchro cinema lens, warm organic 'Cooke Look' with vintage character, T2.3 aperture, soft film-era glow in highlights, gentle falloff and warm tone rendition, classic Hollywood golden age rendering, romantic vintage cinema quality, nostalgic film aesthetic with authentic vintage optics.",
                    "description": "Vintage Cooke - classic Hollywood film look",
                    "tags": ["vintage", "cooke", "panchro", "classic", "hollywood"],
                    "weight": 1.2
                },
                "Vintage Helios 44-2": {
                    "prompt": "Swirly vintage look with Helios 44-2 58mm lens, characteristic swirling bokeh pattern, vintage Soviet optics, f/2.0 aperture, unique bokeh rendering with swirls and cats-eye effects, warm vintage color cast, soft glow in out-of-focus areas, artistic vintage optical character, cult classic vintage lens aesthetic.",
                    "description": "Helios vintage - iconic swirly bokeh character",
                    "tags": ["helios", "vintage", "swirly bokeh", "soviet", "artistic"],
                    "weight": 1.1
                },
                "Vintage Canon K35": {
                    "prompt": "Warm vintage cinema with Canon K35 cinema lens, legendary 1970s-80s cinema optics, T1.5 aperture, warm golden vintage rendering, soft dreamy character with sharp center, reduced contrast for film look, nostalgic Hollywood cinema aesthetic, authentic vintage cinema character.",
                    "description": "Canon K35 - warm vintage cinema classic",
                    "tags": ["canon k35", "vintage", "cinema", "warm", "1970s"],
                    "weight": 1.2
                }
            },
            "Apex Color": {
                "Full Natural Color": {
                    "weight": 1.3,
                    "description": "Accurate natural color with no stylistic cast",
                    "tags": [
                        "natural",
                        "neutral",
                        "true-to-life",
                        "accurate"
                    ],
                    "prompt": "Full natural true-to-life color, accurate skin tones, balanced neutral palette, faithful color reproduction across the whole frame, no stylistic color cast."
                },
                "Neutral Studio Color": {
                    "weight": 1.2,
                    "description": "Neutral studio color with no cast",
                    "tags": [
                        "neutral",
                        "studio",
                        "balanced",
                        "accurate"
                    ],
                    "prompt": "Neutral studio color reproduction, accurate neutral white balance, faithful color with no cast, clean color separation, true neutral greys."
                },
                "Rich Vibrant Color": {
                    "weight": 1.3,
                    "description": "Saturated punchy palette",
                    "tags": [
                        "vibrant",
                        "saturated",
                        "punchy",
                        "rich"
                    ],
                    "prompt": "Rich vibrant colors, deeply saturated punchy palette, clean strong primaries, glossy color depth, lively color energy throughout the image."
                },
                "High Saturation Punch": {
                    "weight": 1.1,
                    "description": "Bold high-chroma commercial color",
                    "tags": [
                        "high saturation",
                        "bold",
                        "commercial",
                        "contrast"
                    ],
                    "prompt": "Highly saturated color, bold juicy hues, strong complementary color contrast, high chroma commercial palette, attention-grabbing vivid color."
                },
                "Soft Pastel Palette": {
                    "weight": 1.1,
                    "description": "Gentle powdery pastel color",
                    "tags": [
                        "pastel",
                        "soft",
                        "airy",
                        "gentle"
                    ],
                    "prompt": "Soft pastel color palette, gentle powdery hues, low contrast color wash, delicate light tints, dreamy airy color harmony."
                },
                "Low Saturation Calm": {
                    "weight": 1.1,
                    "description": "Restrained low-chroma color",
                    "tags": [
                        "low saturation",
                        "calm",
                        "restrained",
                        "muted"
                    ],
                    "prompt": "Gently desaturated color, restrained low-saturation palette, soft muted tones with natural healthy skin color, calm understated color mood."
                },
                "Muted Earthy Palette": {
                    "weight": 1.1,
                    "description": "Desaturated natural earth tones",
                    "tags": [
                        "muted",
                        "earthy",
                        "natural",
                        "understated"
                    ],
                    "prompt": "Muted earthy color palette, desaturated natural browns, olive greens and warm clay tones, understated organic color harmony."
                },
                "Warm Golden Grade": {
                    "weight": 1.2,
                    "description": "Warm amber and honey color grade",
                    "tags": [
                        "warm",
                        "golden",
                        "amber",
                        "cozy"
                    ],
                    "prompt": "Warm golden color grade, amber and honey tones, cozy warm white balance, sunlit warm cast with rich golden highlights."
                },
                "Cool Blue Grade": {
                    "weight": 1.1,
                    "description": "Crisp cyan and steel color grade",
                    "tags": [
                        "cool",
                        "blue",
                        "cyan",
                        "crisp"
                    ],
                    "prompt": "Cool blue color grade, crisp cyan and steel tones, cool white balance, calm clean color cast with icy blue shadows."
                },
                "Jewel Tone Palette": {
                    "weight": 1.1,
                    "description": "Deep gemstone saturation",
                    "tags": [
                        "jewel tones",
                        "deep",
                        "luxurious",
                        "saturated"
                    ],
                    "prompt": "Deep jewel tone color palette, emerald sapphire and ruby saturation, rich luxurious color depth, luminous gemstone hues."
                },
                "Neon Color Pop": {
                    "weight": 1.1,
                    "description": "Glowing electric neon hues",
                    "tags": [
                        "neon",
                        "electric",
                        "glowing",
                        "vivid"
                    ],
                    "prompt": "Electric neon color pop, glowing magenta cyan and lime hues, luminous high chroma neon accents against darker surroundings."
                },
                "Candy Pop Palette": {
                    "weight": 1.1,
                    "description": "Playful bright candy colors",
                    "tags": [
                        "candy",
                        "playful",
                        "bright",
                        "high key"
                    ],
                    "prompt": "Bright candy pop color palette, playful bubblegum pink mint and lemon hues, cheerful high key saturated color."
                },
                "Autumnal Palette": {
                    "weight": 1.1,
                    "description": "Burnt orange and russet foliage tones",
                    "tags": [
                        "autumn",
                        "warm",
                        "foliage",
                        "seasonal"
                    ],
                    "prompt": "Autumnal color palette, burnt orange, russet red and amber gold foliage tones, warm seasonal color harmony."
                },
                "Tropical Color Palette": {
                    "weight": 1.1,
                    "description": "Vivid turquoise, palm green and coral",
                    "tags": [
                        "tropical",
                        "vivid",
                        "sunlit",
                        "saturated"
                    ],
                    "prompt": "Tropical color palette, vivid turquoise water, saturated palm green and coral orange, bright sunlit holiday color."
                },
                "Nordic Cool Palette": {
                    "weight": 1.1,
                    "description": "Restrained Scandinavian cool minimalism",
                    "tags": [
                        "nordic",
                        "cool",
                        "minimal",
                        "slate"
                    ],
                    "prompt": "Nordic cool color palette, pale grey blue, soft white and muted slate tones, restrained Scandinavian color minimalism."
                },
                "HDR Rich Color": {
                    "weight": 1.1,
                    "description": "Wide tonal color depth",
                    "tags": [
                        "hdr",
                        "rich",
                        "wide gamut",
                        "deep"
                    ],
                    "prompt": "HDR rich color, wide gamut highlights with deeply saturated color held in the shadows, extended tonal color depth."
                },
                "Monochromatic Tint": {
                    "weight": 1.1,
                    "description": "Single-hue unified colour wash",
                    "tags": [
                        "monochromatic",
                        "tint",
                        "unified",
                        "tonal"
                    ],
                    "prompt": "Monochromatic single hue color treatment, one dominant hue washing the whole frame with rich tonal variations, unified color scheme."
                },
                "Split Tone Teal Amber": {
                    "weight": 1.2,
                    "description": "Cool shadows against warm highlights",
                    "tags": [
                        "split tone",
                        "teal",
                        "amber",
                        "cinematic"
                    ],
                    "prompt": "Split toned color grade, cool teal shadows against warm amber highlights, dual tone color separation across the full tonal range."
                },
                "Duotone Two Color": {
                    "weight": 1.0,
                    "description": "Two-color graphic palette",
                    "tags": [
                        "duotone",
                        "two color",
                        "graphic",
                        "poster"
                    ],
                    "prompt": "Duotone color treatment, two color palette of deep navy and bright gold, graphic poster style color simplification."
                },
                "Cross Processed Color": {
                    "weight": 1.1,
                    "description": "Analogue chemical colour shift",
                    "tags": [
                        "cross process",
                        "analogue",
                        "shifted",
                        "green cyan"
                    ],
                    "prompt": "Cross processed color look, shifted color casts, green cyan shadows with yellow highlights, unpredictable analogue color chemistry."
                },
                "Bleach Bypass Steel": {
                    "weight": 1.1,
                    "description": "Silver retention metallic desaturation",
                    "tags": [
                        "bleach bypass",
                        "silver",
                        "desaturated",
                        "metallic"
                    ],
                    "prompt": "Bleach bypass color treatment, silver retention desaturation, crushed blacks and metallic steel color, hard industrial color contrast."
                },
                "Sepia Antique Tone": {
                    "weight": 1.0,
                    "description": "Warm brown archival toning",
                    "tags": [
                        "sepia",
                        "antique",
                        "brown",
                        "archival"
                    ],
                    "prompt": "Warm sepia antique tone, brown toned color, aged photographic warmth, archival vintage color character."
                },
                "Desaturated Cinematic": {
                    "weight": 1.2,
                    "description": "Restrained silvery low-chroma film color",
                    "tags": [
                        "desaturated",
                        "cinematic",
                        "muted",
                        "silvery"
                    ],
                    "prompt": "Desaturated cinematic color, muted low chroma palette, restrained color with silvery midtones, serious filmic color restraint."
                },
                "Warm Retro Fade": {
                    "weight": 1.1,
                    "description": "Sun-faded warm retro color",
                    "tags": [
                        "faded",
                        "retro",
                        "warm",
                        "lifted blacks"
                    ],
                    "prompt": "Sun faded retro color, milky lifted blacks, warm yellowed highlights, gentle analogue desaturation, nostalgic color fade."
                },
                "Cold Bleak Grey": {
                    "weight": 1.0,
                    "description": "Almost monochrome cold grey palette",
                    "tags": [
                        "grey",
                        "cold",
                        "bleak",
                        "minimal"
                    ],
                    "prompt": "Cold bleak grey color palette, almost monochrome grey tones with a faint blue cast, overcast despairing color mood."
                },
                "High Contrast Punchy": {
                    "weight": 1.1,
                    "description": "Bold clash of bright light and saturated color",
                    "tags": [
                        "high contrast",
                        "punchy",
                        "bold",
                        "vivid"
                    ],
                    "prompt": "Punchy high contrast color, deep saturated shadows against bright clean highlights, bold vibrant color separation."
                },
                "Soft High Key Color": {
                    "weight": 1.1,
                    "description": "Bright airy high-key pastel light",
                    "tags": [
                        "high key",
                        "bright",
                        "airy",
                        "soft"
                    ],
                    "prompt": "Soft high key color, bright airy pastel light, delicate washed tints, low contrast cheerful color lift."
                },
                "Low Key Moody Color": {
                    "weight": 1.1,
                    "description": "Dark deep-shadow color with rich darks",
                    "tags": [
                        "low key",
                        "moody",
                        "dark",
                        "deep"
                    ],
                    "prompt": "Low key moody color, deep shadow tonality with rich saturated color held in the darks, dramatic dark color atmosphere."
                },
                "Selective Color Accent": {
                    "weight": 1.0,
                    "description": "Desaturated frame with one vivid accent hue",
                    "tags": [
                        "selective color",
                        "accent",
                        "graphic",
                        "desaturated"
                    ],
                    "prompt": "Selective color treatment, desaturated monochrome frame with a single vivid accent hue kept on the subject, graphic color isolation."
                },
                "Monochrome Noir": {
                    "weight": 1.0,
                    "description": "Explicit black-and-white opt-in",
                    "tags": [
                        "monochrome",
                        "black and white",
                        "grayscale",
                        "noir"
                    ],
                    "prompt": "Monochrome black and white image, high contrast grayscale tonality, absolutely no color, deep blacks and clean bright whites."
                },
                "Kodak Portra Color": {
                    "weight": 1.2,
                    "description": "Warm gentle editorial film color",
                    "tags": [
                        "kodak",
                        "portra",
                        "film",
                        "editorial"
                    ],
                    "prompt": "Kodak Portra 400 color rendition, softly warm flattering skin tones, gentle creamy pastel color, natural highlight rolloff, editorial film color."
                },
                "Kodak Ektar Color": {
                    "weight": 1.1,
                    "description": "Punchy ultra-clean film color",
                    "tags": [
                        "kodak",
                        "ektar",
                        "saturated",
                        "clean"
                    ],
                    "prompt": "Kodak Ektar 100 color rendition, punchy saturated color, vivid blues and deep reds, ultra clean fine grain film color."
                },
                "Kodak Ektachrome Color": {
                    "weight": 1.1,
                    "description": "Cool crisp slide film color",
                    "tags": [
                        "ektachrome",
                        "slide film",
                        "cool",
                        "crisp"
                    ],
                    "prompt": "Kodak Ektachrome slide film color, crisp cool blues, clean saturated transparency color, sharp color separation and clarity."
                },
                "Kodak Gold Cast": {
                    "weight": 1.1,
                    "description": "Nostalgic sunny consumer film warmth",
                    "tags": [
                        "kodak gold",
                        "nostalgic",
                        "warm",
                        "sunny"
                    ],
                    "prompt": "Kodak Gold 200 color rendition, nostalgic warm yellow amber cast, sunny consumer film color, soft nostalgic palette."
                },
                "Kodachrome Vintage": {
                    "weight": 1.2,
                    "description": "Dense vintage saturated reds",
                    "tags": [
                        "kodachrome",
                        "vintage",
                        "saturated",
                        "dense"
                    ],
                    "prompt": "Kodachrome 64 color rendition, dense saturated reds, deep rich blacks, mid century vintage film color palette."
                },
                "Kodak Vision3 250D": {
                    "weight": 1.2,
                    "description": "Natural daylight cinema film color",
                    "tags": [
                        "vision3",
                        "cinema",
                        "daylight",
                        "filmic"
                    ],
                    "prompt": "Kodak Vision3 250D daylight film color, natural cinematic color science, gentle highlight rolloff, accurate daylight balance."
                },
                "Kodak Vision3 500T": {
                    "weight": 1.2,
                    "description": "Tungsten night cinema warmth",
                    "tags": [
                        "vision3",
                        "tungsten",
                        "night",
                        "cinema"
                    ],
                    "prompt": "Kodak Vision3 500T tungsten film color, warm amber interiors, rich practical light color, filmic tungsten balance for night scenes."
                },
                "CineStill 800T Color": {
                    "weight": 1.1,
                    "description": "Halated neon tungsten night color",
                    "tags": [
                        "cinestill",
                        "tungsten",
                        "halation",
                        "neon"
                    ],
                    "prompt": "CineStill 800T tungsten color, halated red glow around light sources, cool blue night shadows, neon drenched urban film color."
                },
                "Fujifilm Eterna Color": {
                    "weight": 1.2,
                    "description": "Soft restrained green-leaning cinema color",
                    "tags": [
                        "fuji",
                        "eterna",
                        "cinema",
                        "restrained"
                    ],
                    "prompt": "Fujifilm Eterna cinema color, softly muted green leaning palette, low contrast filmic color, elegant restrained cinema tone."
                },
                "Fujifilm Velvia Color": {
                    "weight": 1.1,
                    "description": "Intense landscape slide film color",
                    "tags": [
                        "velvia",
                        "saturated",
                        "landscape",
                        "slide film"
                    ],
                    "prompt": "Fujifilm Velvia slide film color, intensely saturated deep greens and crimson reds, dramatic landscape slide film color."
                },
                "Fujifilm Pro 400H Color": {
                    "weight": 1.1,
                    "description": "Cool mint pastel editorial film color",
                    "tags": [
                        "fuji",
                        "400h",
                        "pastel",
                        "airy"
                    ],
                    "prompt": "Fujifilm Pro 400H color rendition, cool mint leaning pastel greens, delicate soft color, airy bright editorial film tone."
                },
                "Agfa Vintage Color": {
                    "weight": 1.0,
                    "description": "Warm European film cast",
                    "tags": [
                        "agfa",
                        "vintage",
                        "warm",
                        "european"
                    ],
                    "prompt": "Agfa vintage film color, warm yellow green cast, soft contrast European film palette, small format analogue color."
                },
                "Polaroid Instant Color": {
                    "weight": 1.0,
                    "description": "Washed soft instant film color",
                    "tags": [
                        "polaroid",
                        "instant",
                        "soft",
                        "nostalgic"
                    ],
                    "prompt": "Polaroid instant film color, soft washed pastel tones, slight warm cyan shift, nostalgic instant photo color character."
                },
                "Lomo Analogue Punch": {
                    "weight": 1.0,
                    "description": "Toy-camera saturation with vignette tint",
                    "tags": [
                        "lomo",
                        "saturated",
                        "analogue",
                        "vignette"
                    ],
                    "prompt": "Lomo toy camera color, heavy analogue saturation with green cyan vignette tint, punchy unpredictable analogue color."
                },
                "Teal and Orange Blockbuster": {
                    "weight": 1.3,
                    "description": "Warm skin tones against cool teal backgrounds",
                    "tags": [
                        "teal and orange",
                        "blockbuster",
                        "hollywood",
                        "commercial"
                    ],
                    "prompt": "Teal and orange blockbuster color grade, warm orange skin tones against cool teal backgrounds, big budget Hollywood action color contrast."
                },
                "Film Print Emulation 2383": {
                    "weight": 1.2,
                    "description": "Kodak print film depth and rolloff",
                    "tags": [
                        "2383",
                        "print film",
                        "cinema",
                        "deep blacks"
                    ],
                    "prompt": "Kodak 2383 film print emulation, rich filmic color depth, deep blacks, gentle highlight rolloff, cinema print color."
                },
                "ACES Neutral Grade": {
                    "weight": 1.1,
                    "description": "Wide-gamut faithful modern pipeline color",
                    "tags": [
                        "aces",
                        "neutral",
                        "accurate",
                        "modern"
                    ],
                    "prompt": "ACES neutral color grade, accurate wide gamut color, faithful tones with balanced contrast, modern ACES color pipeline."
                },
                "Rec.709 Broadcast Color": {
                    "weight": 1.0,
                    "description": "Compliant neutral broadcast color",
                    "tags": [
                        "rec709",
                        "broadcast",
                        "neutral",
                        "television"
                    ],
                    "prompt": "Rec.709 broadcast color standard, accurate neutral color for television, no stylistic cast, clean compliant color."
                },
                "Log Flat Ungraded": {
                    "weight": 1.0,
                    "description": "Flat low-contrast ungraded log color",
                    "tags": [
                        "log",
                        "flat",
                        "ungraded",
                        "lifted"
                    ],
                    "prompt": "Flat log color profile, low contrast washed color, wide dynamic range ungraded look, lifted blacks and muted flat color."
                },
                "Technicolor Three Strip": {
                    "weight": 1.2,
                    "description": "Luscious golden-age Technicolor",
                    "tags": [
                        "technicolor",
                        "saturated",
                        "golden age",
                        "glamour"
                    ],
                    "prompt": "Three strip Technicolor color, luscious saturated reds and greens, glossy golden age musical color, rich Technicolor glamour."
                },
                "Two Strip Technicolor": {
                    "weight": 1.0,
                    "description": "Restricted early colour range",
                    "tags": [
                        "two strip",
                        "technicolor",
                        "vintage",
                        "limited"
                    ],
                    "prompt": "Two strip Technicolor color, limited red orange and blue green palette, early sound era color, restricted vintage color range."
                },
                "Day for Night Blue": {
                    "weight": 1.1,
                    "description": "Cool moonlit night illusion",
                    "tags": [
                        "day for night",
                        "blue",
                        "moonlight",
                        "cinematic"
                    ],
                    "prompt": "Day for night color grade, cool moonlit blue tones, underexposed night illusion, cinematic blue night color."
                },
                "Cold Cyan Thriller": {
                    "weight": 1.1,
                    "description": "Clinical cyan-green thriller grade",
                    "tags": [
                        "cyan",
                        "thriller",
                        "cold",
                        "clinical"
                    ],
                    "prompt": "Cold cyan and green thriller color grade, desaturated shadowy palette, clinical cool color, precise modern thriller look."
                },
                "Muted Steel Drama": {
                    "weight": 1.1,
                    "description": "Cool restrained large-format color",
                    "tags": [
                        "steel",
                        "muted",
                        "cool",
                        "drama"
                    ],
                    "prompt": "Cool steel color grade, muted cold palette with clean bright highlights, restrained large format cinematic color."
                },
                "Pastel Storybook Palette": {
                    "weight": 1.1,
                    "description": "Curated flat pastel colour harmony",
                    "tags": [
                        "pastel",
                        "storybook",
                        "flat",
                        "quirky"
                    ],
                    "prompt": "Symmetrical pastel storybook color palette, candy pink mustard yellow and mint, flat even color, whimsical curated color harmony."
                },
                "Warm Retro Seventies": {
                    "weight": 1.1,
                    "description": "Golden amber interiors with red accents",
                    "tags": [
                        "70s",
                        "warm",
                        "retro",
                        "amber"
                    ],
                    "prompt": "Warm retro 1970s color, golden amber interiors with saturated red accents, grainy vintage studio color."
                },
                "Sun Scorched Orange Turquoise": {
                    "weight": 1.1,
                    "description": "Extreme desert complementary clash",
                    "tags": [
                        "orange",
                        "turquoise",
                        "desert",
                        "high contrast"
                    ],
                    "prompt": "Sun blasted hot orange and turquoise color grade, scorched sand tones, extreme complementary color clash, desert apocalypse color palette."
                },
                "Surveillance Green Tint": {
                    "weight": 1.0,
                    "description": "Sickly fluorescent monochromatic green",
                    "tags": [
                        "green tint",
                        "surveillance",
                        "monochromatic",
                        "cyber"
                    ],
                    "prompt": "Green tinted color grade, sickly fluorescent green cast, cool cyberspace color, monochromatic green palette."
                },
                "Parisian Golden Green": {
                    "weight": 1.0,
                    "description": "Warm red-green romantic palette",
                    "tags": [
                        "golden green",
                        "romantic",
                        "warm",
                        "saturated"
                    ],
                    "prompt": "Warm golden green color grade, red and green romantic palette, saturated nostalgic warmth, whimsical Parisian color."
                },
                "Neon Amber Noir": {
                    "weight": 1.1,
                    "description": "Dense amber and magenta glow",
                    "tags": [
                        "neon",
                        "amber",
                        "magenta",
                        "noir"
                    ],
                    "prompt": "Neon amber and magenta color grade, dense atmospheric glow, smoke diffused colored light, hi tech noir city color palette."
                },
                "Cyberpunk Magenta Cyan": {
                    "weight": 1.1,
                    "description": "Hard neon cyber palette",
                    "tags": [
                        "cyberpunk",
                        "magenta",
                        "cyan",
                        "futuristic"
                    ],
                    "prompt": "Cyberpunk magenta and cyan color grade, hard neon color contrast, holographic color spill on wet surfaces, futuristic chromatic palette."
                },
                "Saturated Crimson Romance": {
                    "weight": 1.0,
                    "description": "Moody deep-red romantic color",
                    "tags": [
                        "crimson",
                        "saturated",
                        "moody",
                        "romantic"
                    ],
                    "prompt": "Saturated deep red color grade, moody jewel toned shadows, lush romantic color with intense crimson accents."
                },
                "Eighties VHS Color": {
                    "weight": 1.0,
                    "description": "Analogue tape chroma artifacts",
                    "tags": [
                        "80s",
                        "vhs",
                        "chroma",
                        "retro"
                    ],
                    "prompt": "1980s VHS color, chroma bleed and color fringing, over saturated magenta and green, analogue tape color artifacts."
                },
                "Nineties Music Video Color": {
                    "weight": 1.0,
                    "description": "Punchy stage-lit chromatic look",
                    "tags": [
                        "90s",
                        "music video",
                        "punchy",
                        "stage lit"
                    ],
                    "prompt": "1990s music video color, high contrast saturated color with cool shadows, punchy stage lit chromatic look."
                },
                "Y2K Digicam Color": {
                    "weight": 1.0,
                    "description": "Cool chrome digital flash color",
                    "tags": [
                        "y2k",
                        "digicam",
                        "cool",
                        "flash"
                    ],
                    "prompt": "Y2K digicam color, slightly cool chrome blue cast, flash lit saturated color, early digital camera color character."
                },
                "False Color Infrared": {
                    "weight": 1.0,
                    "description": "Surreal pink foliage and cyan skies",
                    "tags": [
                        "infrared",
                        "false color",
                        "surreal",
                        "dreamlike"
                    ],
                    "prompt": "False color infrared look, foliage rendered in surreal pink and red, cyan skies, dreamlike infrared color palette."
                },
                "Thermal Heat Map": {
                    "weight": 1.0,
                    "description": "Heat-signature false colour encoding",
                    "tags": [
                        "thermal",
                        "heat map",
                        "false color",
                        "scientific"
                    ],
                    "prompt": "Thermal imaging false color palette, hot orange and yellow against deep blue violet, heat map color encoding."
                },
                "Anaglyph Stereo Color": {
                    "weight": 1.0,
                    "description": "Red-cyan stereo print color",
                    "tags": [
                        "anaglyph",
                        "stereo",
                        "red cyan",
                        "retro"
                    ],
                    "prompt": "Anaglyph stereo color look, red and cyan channel separation, retro 3D glasses color fringing, printed stereo color character."
                }
            }
        }

    @classmethod
    def get_all_presets_in_category(cls, category: str) -> List[str]:
        """Read the same library used by execution and the management API."""
        return list(get_store().snapshot()["presets"].get(category, {}))

    def get_categories(self) -> List[str]:
        """Get list of all categories."""
        return list(self.presets.keys())

    def get_presets_in_category(self, category: str) -> List[str]:
        """Get preset names in a specific category (loaded presets)."""
        if category in self.presets:
            return list(self.presets[category].keys())
        return []

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

    def get_random_preset(self, category: str, seed: int) -> tuple:
        """Randomly select a preset from a category using weighted random selection.
        Returns tuple of (selected_name, prompt_text)."""
        if not self._random_names.get(category):
            return (None, None)
        
        # Build weighted lists of preset names and prompts
        presets = self._factory_presets[category]
        names = self._random_names[category]
        weights = [presets[name].get("weight", 1.0) for name in names]
        
        # Seed random selection so same seed produces same result
        rng = random.Random()
        rng.seed(seed)
        
        selected_name = rng.choices(names, weights=weights, k=1)[0]
        prompt_text = presets[selected_name].get("prompt", "")
        return (selected_name, prompt_text)

    def process_random_brackets(self, text: str, seed: int) -> str:
        """
        Process brackets with random selection.
        Example: "woman in a [flower field, alien landscape, new york street]"
        Will randomly pick one option from the bracketed list.
        """
        rng = random.Random()
        rng.seed(seed)
        pattern = r'\[([^\]]+)\]'
        
        def replace_bracket(match):
            content = match.group(1)
            options = [opt.strip() for opt in content.split(',') if opt.strip()]
            if not options:
                return ""
            return rng.choice(options)
        
        return re.sub(pattern, replace_bracket, text)

    def _get_preset_text(self, category: str, preset_name: str, seed_offset: int) -> tuple:
        """Helper method to get preset text with random support.
        Returns tuple of (selected_name, prompt_text)."""
        if preset_name == "Random":
            return self.get_random_preset(category, seed_offset)
        elif preset_name != "Disabled" and preset_name != "None":
            preset_data = self.get_preset_data(category, preset_name)
            if preset_data is None:
                raise ValueError("Missing preset in " + category + ": " + str(preset_name)
                                 + ". Import the user preset or select another entry.")
            prompt_text = preset_data.get("prompt", "")
            return (preset_name, prompt_text)
        return (preset_name, "")
    
    def combine_prompts(self, input_text: str, seed: int = 0, environment_preset: str = "Disabled", 
                       lighting_preset: str = "Disabled", style_preset: str = "Disabled", 
                       camera_lens_preset: str = "Disabled", color_preset: str = "Disabled") -> tuple:
        """Combine input text with environment, lighting, style, colour grade, and camera lens prompts."""
        self._refresh_presets()
        seed = seed if seed is not None else 0
        
        # Process random brackets in input text (uses deterministic seeding)
        if input_text.strip():
            input_text = self.process_random_brackets(input_text, seed)
        
        # Get preset texts with weighted random selection support
        env_name, env_text = self._get_preset_text("Apex Environment", environment_preset, seed + 1)
        light_name, light_text = self._get_preset_text("Apex Lighting", lighting_preset, seed + 2)
        style_name, style_text = self._get_preset_text("Apex Style", style_preset, seed + 3)
        camera_lens_name, camera_lens_text = self._get_preset_text("Apex Camera Lens", camera_lens_preset, seed + 4)
        _color_name, color_text = self._get_preset_text("Apex Color", color_preset, seed + 5)
        
        # Store selected lens name for UI update (stored in node instance for JavaScript access)
        if hasattr(self, '_selected_lens_name'):
            self._selected_lens_name = camera_lens_name if camera_lens_name and camera_lens_name != "Disabled" else None
        
        # Combine all parts in order: input → environment → lighting → style → color → camera lens
        parts = [p for p in [input_text.strip(), env_text, light_text, style_text, color_text, camera_lens_text] if p]
        combined = self.clean_prompt(", ".join(parts))

        return (combined, env_text, light_text, style_text, camera_lens_text, color_text)

    def clean_prompt(self, prompt: str) -> str:
        """Clean and format the final prompt."""
        prompt = ", ".join([part.strip() for part in prompt.split(",") if part.strip()])
        return prompt

# Node registration
NODE_CLASS_MAPPINGS = {
    "ApexPromptPreset": ApexPromptPreset
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ApexPromptPreset": "Apex Prompt"
}
