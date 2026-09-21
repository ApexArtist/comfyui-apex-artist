#!/usr/bin/env python3
"""
Validate the Apex Character Prompt node, its preset library, and its API routes.

Checks (no ComfyUI server required):
  1. character_presets.json matches the built-in library and is well formed
  2. INPUT_TYPES expose the 12 Disabled / Random preset dropdowns plus a trailing input_text box
  3. combine_prompts() returns 13 outputs with deterministic seeding and correct ordering, and
     merges the free-text input box ahead of the preset categories
  4. VALIDATE_INPUTS accepts dynamically added preset names
  5. The API module registers all five /apex/character_presets routes and its CRUD works

Usage (always use the ComfyUI virtual environment Python):
    & "F:\\AI\\ComfyUI Sandbox\\ComfyUI\\.venv\\Scripts\\python.exe" scripts\\validate_character_prompt.py
"""

import asyncio
import ast
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import types

NODE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE_NAME = "apex_character_validate_pkg"
FAILURES = []

WIDGET_ATTRIBUTES = (
    ("gender_preset", "CATEGORY_GENDER"),
    ("age_preset", "CATEGORY_AGE"),
    ("ethnicity_preset", "CATEGORY_ETHNICITY"),
    ("face_preset", "CATEGORY_FACE"),
    ("eye_color_preset", "CATEGORY_EYE_COLOR"),
    ("skin_tone_preset", "CATEGORY_SKIN_TONE"),
    ("hair_preset", "CATEGORY_HAIR"),
    ("headwear_preset", "CATEGORY_HEADWEAR"),
    ("top_preset", "CATEGORY_TOP"),
    ("bottom_preset", "CATEGORY_BOTTOM"),
    ("shoes_preset", "CATEGORY_SHOES"),
    ("hand_accessory_preset", "CATEGORY_HAND"),
)

NEGATIVE_MARKERS = (" no ", " not ", "avoid", "without ", "excluding")


def check(condition, message):
    print(f"[{'PASS' if condition else 'FAIL'}] {message}")
    if not condition:
        FAILURES.append(message)
    return bool(condition)


def load_module(module_name, file_name):
    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE_NAME}.{module_name}", os.path.join(NODE_DIR, file_name))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def bootstrap():
    """Load apex_prompt and apex_character_prompt through a synthetic package."""
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [NODE_DIR]
    sys.modules[PACKAGE_NAME] = package
    load_module("apex_prompt", "apex_prompt.py")
    return load_module("apex_character_prompt", "apex_character_prompt.py")


def validate_library(node_module, tmp_dir):
    """Check the built-in library structure, counts, and content quality."""
    cls = node_module.ApexCharacterPrompt
    library = cls.get_default_presets()

    check(list(library.keys()) == list(cls.CHARACTER_CATEGORIES),
          f"Library exposes the 12 character categories in order")

    total = 0
    for category, entries in library.items():
        total += len(entries)
        problems = []
        for name, data in entries.items():
            prompt = (data.get("prompt") or "").strip()
            if not prompt:
                problems.append(f"{name}: empty prompt")
            if not isinstance(data.get("description"), str) or not data["description"].strip():
                problems.append(f"{name}: missing description")
            if not isinstance(data.get("tags"), list) or not data["tags"]:
                problems.append(f"{name}: missing tags")
            if not isinstance(data.get("weight"), (int, float)):
                problems.append(f"{name}: non-numeric weight")
            lowered = f" {prompt.lower()} "
            sanitized = lowered.replace(" no sharp angles", " ")
            for marker in NEGATIVE_MARKERS:
                if marker in sanitized:
                    problems.append(f"{name}: negative wording '{marker.strip()}'")
        check(not problems, f"{category}: {len(entries)} presets well formed"
                            + ("" if not problems else f" -> {problems[:3]}"))

    check(total == 221, f"Library total is 221 presets (got {total})")

    face = library[cls.CATEGORY_FACE]
    check("Universal Beauty" in face and "American Beauty" in face,
          "Facial feature presets include Universal Beauty and American Beauty")
    check("Micro Drama" not in face and "Pale Porcelain Beauty" not in face,
          "Micro Drama and Pale Porcelain Beauty have been removed (merged into Universal Beauty)")
    check(face.get("Universal Beauty", {}).get("weight") == 1.3
          and face.get("American Beauty", {}).get("weight") == 1.3,
          "Universal Beauty and American Beauty carry weight 1.3")

    # Temporary store so the repo file is never written by the node
    store_path = os.path.join(tmp_dir, "character_presets_test.json")
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(library, f)
    return store_path


def validate_node(node_module, store_path):
    """Check dropdowns, output count, ordering, determinism, and dynamic validation."""
    cls = node_module.ApexCharacterPrompt
    library = cls.get_default_presets()
    inputs = cls.INPUT_TYPES()["required"]

    expected_widgets = ["seed"] + [name for name, _ in WIDGET_ATTRIBUTES] + ["input_text"]
    check(list(inputs.keys()) == expected_widgets,
          f"Widgets are seed, the 12 preset dropdowns, then input_text: {list(inputs.keys())}")

    check(list(inputs)[-1] == "input_text",
          "input_text is appended last so existing workflows keep their widget values")
    check(inputs["input_text"][0] == "STRING" and inputs["input_text"][1]["multiline"] is True
          and inputs["input_text"][1]["default"] == "",
          "input_text is an empty multiline STRING box")

    for widget, attribute in WIDGET_ATTRIBUTES:
        category = getattr(cls, attribute)
        options = inputs[widget][0]
        check(options[:2] == ["Disabled", "Random"], f"{widget} starts with Disabled and Random")
        check(len(options) == len(library[category]) + 2,
              f"{widget} lists all {len(library[category])} presets from {category}")
        check(inputs[widget][1]["default"] == "Random", f"{widget} defaults to Random")

    check(cls.RETURN_TYPES == ("STRING",) * 13, "Node returns 13 STRING outputs")
    check(len(cls.RETURN_NAMES) == 13, "Return names match the 13 outputs")
    check(cls.FUNCTION == "combine_prompts" and cls.CATEGORY == "Apex Artist/Text",
          "FUNCTION and CATEGORY are set")
    check("input box" in cls.DESCRIPTION.lower(), "DESCRIPTION documents the free-text input box")

    node = cls()
    node.presets_file = store_path
    node.presets = node.load_presets()
    node.presets[cls.CATEGORY_FACE] = dict(node.presets[cls.CATEGORY_FACE])
    node.presets[cls.CATEGORY_FACE]["Bracket Probe"] = {
        "prompt": "warm [dark brown eyes, deep brown eyes] with soft lashes",
        "description": "Temporary bracket probe",
        "tags": ["probe"],
        "weight": 1.0,
    }
    with open(store_path, "w", encoding="utf-8") as stream:
        json.dump(node.presets, stream)

    first = node.combine_prompts(seed=1234)
    check(len(first) == 13, f"combine_prompts returns 13 values (got {len(first)})")
    check(len(first[0]) > 100 and all(part for part in first[1:]),
          "Random on every category fills all 13 outputs")
    check(first[0].startswith(first[1].rstrip(". ")) and first[0].endswith(first[12].rstrip(". ")),
          "Combined prompt runs gender -> age -> ethnicity -> face -> eye color -> skin tone -> hair -> headwear -> top -> bottom -> shoes -> hand accessory")

    check(node.combine_prompts(seed=1234) == first, "Same seed produces the same character")
    check(node.combine_prompts(seed=1235) != first, "A different seed produces a different character")

    exact = node.combine_prompts(
        seed=0,
        gender_preset="Female",
        age_preset="Mid Twenties 26-29",
        ethnicity_preset="East Asian",
        face_preset="American Beauty",
        eye_color_preset="Disabled",
        skin_tone_preset="Disabled",
        hair_preset="Blunt Bob",
        headwear_preset="Ribbed Beanie",
        top_preset="Trench Coat",
        bottom_preset="Pleated Mini Skirt",
        shoes_preset="Combat Boots",
        hand_accessory_preset="Chronograph Wristwatch",
    )
    check(exact[1] == library[cls.CATEGORY_GENDER]["Female"]["prompt"],
          "A named gender preset resolves to its exact prompt text")
    check(exact[3] == library[cls.CATEGORY_ETHNICITY]["East Asian"]["prompt"],
          "A named ethnicity preset resolves to its exact prompt text")
    check(exact[4] == library[cls.CATEGORY_FACE]["American Beauty"]["prompt"],
          "A named face preset resolves to its exact prompt text")
    check(exact[12] == library[cls.CATEGORY_HAND]["Chronograph Wristwatch"]["prompt"],
          "A named hand accessory preset resolves to its exact prompt text")
    check(all(part.rstrip(". ") in exact[0] for part in exact[1:]),
          "Every category text appears in the combined prompt (trailing periods trimmed)")

    # Free-text input box: leads the combined prompt, never leaks into the category outputs,
    # leaves the old empty-box behavior byte-identical, and expands its own brackets.
    user_text = node.combine_prompts(input_text="35mm film photograph, natural skin texture", seed=1234)
    check(user_text[0].startswith("35mm film photograph, natural skin texture"),
          "Input box text leads the combined prompt")
    check(user_text[1:] == first[1:],
          "Input box text never leaks into the per-category outputs")
    check(node.combine_prompts(input_text="", seed=1234) == first,
          "An empty input box leaves the combined prompt unchanged")

    bracketed_input = node.combine_prompts(input_text="wearing a [red, blue] scarf", seed=3)
    check(bracketed_input[0].split(", ")[0] in ("wearing a red scarf", "wearing a blue scarf"),
          f"Input box brackets resolve to one option ({bracketed_input[0].split(', ')[0]!r})")
    check(node.combine_prompts(input_text="wearing a [red, blue] scarf", seed=3) == bracketed_input,
          "Input box brackets are seed-deterministic")

    input_only = node.combine_prompts(
        input_text="35mm film photograph",
        seed=0,
        gender_preset="Disabled",
        age_preset="Disabled",
        ethnicity_preset="Disabled",
        face_preset="Disabled",
        eye_color_preset="Disabled",
        skin_tone_preset="Disabled",
        hair_preset="Disabled",
        headwear_preset="Disabled",
        top_preset="Disabled",
        bottom_preset="Disabled",
        shoes_preset="Disabled",
        hand_accessory_preset="Disabled",
    )
    check(input_only[0] == "35mm film photograph" and all(part == "" for part in input_only[1:]),
          "The input box alone still produces a combined prompt")

    disabled = node.combine_prompts(
        seed=0,
        gender_preset="Disabled",
        age_preset="Disabled",
        ethnicity_preset="Disabled",
        face_preset="Disabled",
        eye_color_preset="Disabled",
        skin_tone_preset="Disabled",
        hair_preset="Disabled",
        headwear_preset="Disabled",
        top_preset="Disabled",
        bottom_preset="Disabled",
        shoes_preset="Disabled",
        hand_accessory_preset="Disabled",
    )
    check(disabled[0] == "" and all(part == "" for part in disabled[1:]),
          "Every output is empty when all categories are Disabled")

    unknown = node.combine_prompts(
        seed=0,
        gender_preset="Disabled",
        age_preset="Disabled",
        ethnicity_preset="Disabled",
        face_preset="Added In The Manager UI",
        eye_color_preset="Disabled",
        skin_tone_preset="Disabled",
        hair_preset="Disabled",
        headwear_preset="Disabled",
        top_preset="Disabled",
        bottom_preset="Disabled",
        shoes_preset="Disabled",
        hand_accessory_preset="Disabled",
    )
    check(unknown[0] == "" and unknown[1] == "",
          "An unknown preset name yields empty text instead of raising")

    check(cls.VALIDATE_INPUTS(face_preset="Anything At All") is True,
          "VALIDATE_INPUTS accepts dynamically added preset names")

    probe_seeds = (
        node.combine_prompts(seed=seed, face_preset="Random", eye_color_preset="Disabled",
                             skin_tone_preset="Disabled", hair_preset="Disabled",
                             headwear_preset="Disabled", top_preset="Disabled", bottom_preset="Disabled",
                             shoes_preset="Disabled", hand_accessory_preset="Disabled")
        for seed in range(40)
    )
    distinct_face = {result[4] for result in probe_seeds}
    check(len(distinct_face) > 1, f"Random face selection varies across seeds ({len(distinct_face)} distinct)")

    bracketed = node.combine_prompts(
        seed=3,
        gender_preset="Disabled",
        age_preset="Disabled",
        ethnicity_preset="Disabled",
        face_preset="Bracket Probe",
        eye_color_preset="Disabled",
        skin_tone_preset="Disabled",
        hair_preset="Disabled",
        headwear_preset="Disabled",
        top_preset="Disabled",
        bottom_preset="Disabled",
        shoes_preset="Disabled",
        hand_accessory_preset="Disabled",
    )
    check(bracketed[4] in ("warm dark brown eyes with soft lashes", "warm deep brown eyes with soft lashes"),
          f"Bracket variants resolve to one option ({bracketed[4]!r})")


def validate_store(node_module, store_path):
    """Check the committed character_presets.json matches the built-in library."""
    committed = os.path.join(NODE_DIR, node_module.ApexCharacterPrompt.PRESET_FILE_NAME)
    check(os.path.exists(committed), f"{node_module.ApexCharacterPrompt.PRESET_FILE_NAME} exists")

    if os.path.exists(committed):
        with open(committed, "r", encoding="utf-8") as f:
            stored = json.load(f)
        check(stored == node_module.ApexCharacterPrompt.get_default_presets(),
              "Committed store matches the built-in library (regenerate with generate_character_presets.py)")

    # A store missing categories must still be filled from the library
    partial_path = os.path.join(os.path.dirname(store_path), "character_presets_partial.json")
    with open(partial_path, "w", encoding="utf-8") as f:
        json.dump({"Apex Character Face": {"Universal Beauty": {"prompt": "test", "tags": ["x"], "weight": 1.0}}}, f)

    node = node_module.ApexCharacterPrompt()
    node.presets_file = partial_path
    merged = node.load_presets()
    check(len(merged) == 12 and merged["Apex Character Face"] == {"Universal Beauty": {"prompt": "test", "tags": ["x"], "weight": 1.0}},
          "Partial store keeps stored categories and fills the missing ones from the library")

    check(node._store_data().get("Apex Character Face") is not None
          or os.path.getmtime(partial_path) > 0,
          "Store reader returns the on-disk store data")

    # A damaged store must not stop the node from loading, and must not be rewritten
    cls = node_module.ApexCharacterPrompt
    corrupt_path = os.path.join(os.path.dirname(store_path), "character_presets_corrupt.json")
    with open(corrupt_path, "w", encoding="utf-8") as f:
        f.write('{"Apex Character Face": {truncated')

    damaged = cls()
    damaged.presets_file = corrupt_path
    damaged.presets = damaged.load_presets()
    check(set(damaged.presets) == set(cls.CHARACTER_CATEGORIES),
          "A malformed store falls back to all 12 built-in categories instead of failing")
    check(damaged.combine_prompts(seed=5)[0].strip() != "",
          "A malformed store still produces a character prompt")
    with open(corrupt_path, "r", encoding="utf-8") as f:
        check(f.read() == '{"Apex Character Face": {truncated',
              "A malformed store is left untouched on disk for the user to repair")

    # A missing store must also load from the built-in library
    missing = cls()
    missing.presets_file = os.path.join(os.path.dirname(store_path), "does_not_exist.json")
    missing.presets = missing.load_presets()
    check(set(missing.presets) == set(cls.CHARACTER_CATEGORIES),
          "A missing store loads all 12 built-in categories")
    check(len(cls.IS_CHANGED()) == 64,
          "IS_CHANGED still reports a usable revision when the store is missing")

    # Dropdowns survive a damaged store by falling back to the built-in names
    cls._store_cache["mtime"] = None
    cls._store_cache["data"] = {}
    options = cls.INPUT_TYPES()["required"]["face_preset"][0]
    check(len(options) >= len(cls.get_default_presets()[cls.CATEGORY_FACE]) + 2,
          "Face dropdown still lists the built-in presets after a damaged store")


def validate_api(tmp_dir):
    """Register the API against a stubbed PromptServer, then exercise its CRUD routes."""
    handlers = {}

    class FakeRoutes:
        def _register(self, method, path):
            def decorator(func):
                handlers[(method, path)] = func
                return func
            return decorator

        def get(self, path): return self._register("GET", path)
        def post(self, path): return self._register("POST", path)
        def delete(self, path): return self._register("DELETE", path)

    server_module = types.ModuleType("server")
    server_module.PromptServer = types.SimpleNamespace(
        instance=types.SimpleNamespace(routes=FakeRoutes()))
    sys.modules["server"] = server_module

    api_module = load_module("apex_character_prompt_api", "apex_character_prompt_api.py")
    api = api_module.api_instance

    expected_routes = {
        ("GET", "/apex/character_presets"),
        ("POST", "/apex/character_presets"),
        ("GET", "/apex/character_presets/{category}"),
        ("POST", "/apex/character_presets/{category}/{name}"),
        ("DELETE", "/apex/character_presets/{category}/{name}"),
    }
    check(set(handlers) == expected_routes,
          f"API registers all 5 character preset routes ({len(handlers)} found)")
    check(api.presets_file == os.path.join(NODE_DIR, "character_presets.json"),
          "API targets character_presets.json (prompt_presets.json is untouched)")

    # Point the API at a temp store so the repo file is never written during validation
    api.presets_file = os.path.join(tmp_dir, "character_presets_api.json")

    class FakeRequest:
        def __init__(self, payload=None, **match_info):
            self._payload = payload if payload is not None else {}
            self.match_info = match_info

        async def json(self):
            return self._payload

    async def run():
        response = await handlers[("POST", "/apex/character_presets")](FakeRequest({
            "Apex Character Top": {
                "Test Tee": {"prompt": "a test tee", "description": "d", "tags": ["t"], "weight": 1.0}
            }
        }))
        check(response.status == 200, "POST /apex/character_presets saves the whole store")

        response = await handlers[("GET", "/apex/character_presets")](FakeRequest())
        payload = json.loads(response.text)
        check(payload.get("Apex Character Top", {}).get("Test Tee", {}).get("prompt") == "a test tee",
              "GET /apex/character_presets returns the saved store")

        response = await handlers[("POST", "/apex/character_presets/{category}/{name}")](
            FakeRequest({"prompt": "second preset", "description": "d2", "tags": ["t2"], "weight": 1.1},
                        category="Apex Character Shoes", name="Test Boots"))
        check(response.status == 200, "POST .../{category}/{name} upserts a single preset")

        response = await handlers[("GET", "/apex/character_presets/{category}")](
            FakeRequest(category="Apex Character Shoes"))
        check("Test Boots" in json.loads(response.text),
              "GET .../{category} returns just that category")

        response = await handlers[("DELETE", "/apex/character_presets/{category}/{name}")](
            FakeRequest(category="Apex Character Shoes", name="Test Boots"))
        check(response.status == 200, "DELETE .../{category}/{name} removes a preset")

        response = await handlers[("DELETE", "/apex/character_presets/{category}/{name}")](
            FakeRequest(category="Apex Character Shoes", name="Missing"))
        check(response.status == 404, "DELETE on a missing preset returns 404")

        if os.path.exists(api.presets_file):
            os.remove(api.presets_file)
        response = await handlers[("GET", "/apex/character_presets")](FakeRequest())
        check(len(json.loads(response.text)) == 12, "An empty store falls back to the built-in library")

    asyncio.run(run())


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("Apex Character Prompt validation")
    print("=" * 64)
    tmp_dir = tempfile.mkdtemp(prefix="apex_character_")
    try:
        node_module = bootstrap()
        store_path = validate_library(node_module, tmp_dir)
        validate_store(node_module, store_path)
        validate_node(node_module, store_path)
        validate_api(tmp_dir)
        # Execute the actual package initializer with unrelated heavyweight nodes
        # stubbed. This catches missing exports, not just standalone module imports.
        init_path = os.path.join(NODE_DIR, "__init__.py")
        with open(init_path, encoding="utf-8") as stream:
            source = stream.read()
        tree = ast.parse(source)
        for item in tree.body:
            if isinstance(item, ast.ImportFrom) and item.level == 1 and item.module:
                module_name = PACKAGE_NAME + "." + item.module
                if module_name not in sys.modules:
                    stub = types.ModuleType(module_name)
                    for alias in item.names:
                        setattr(stub, alias.name, type(alias.name, (), {}))
                    sys.modules[module_name] = stub
        for api_name in ("apex_prompt_api", "apex_lora_api", "apex_prompt_lens_api", "apex_hdri_preview_api"):
            sys.modules[PACKAGE_NAME + "." + api_name] = types.ModuleType(api_name)
        namespace = {"__name__": PACKAGE_NAME, "__package__": PACKAGE_NAME, "__file__": init_path}
        exec(compile(source, init_path, "exec"), namespace)
        cls = namespace["NODE_CLASS_MAPPINGS"].get("ApexCharacterPrompt")
        check(cls is node_module.ApexCharacterPrompt, "Package initializer exports the real ApexCharacterPrompt class")
        check(namespace["NODE_DISPLAY_NAME_MAPPINGS"].get("ApexCharacterPrompt") == "Apex Character Prompt",
              "Package initializer exports the character display name")
        check(any(isinstance(item, ast.ImportFrom) and any(alias.name == "apex_character_prompt_api" for alias in item.names)
                  for item in ast.walk(tree)), "Package initializer imports character API routes")
        check(set(cls().presets) == set(cls.CHARACTER_CATEGORIES), "Registered character node loads only character categories")
        check(len(cls.IS_CHANGED()) == 64, "Character change detection hashes its own library without the prompt store")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print("=" * 64)
    if FAILURES:
        print(f" {len(FAILURES)} check(s) failed")
        return 1
    print("✓ All checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
