"""Read-only factory presets and an installation-shared, revisioned user library.

No writes target the extension directory. The JSON factory library is authoritative;
Python defaults supply missing names only. User entries have a separate namespace.
"""

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import threading

CATEGORIES = ("Apex Environment", "Apex Lighting", "Apex Style", "Apex Camera Lens", "Apex Color")
USER_PREFIX = "User: "
MAX_BYTES = 4 * 1024 * 1024
MAX_PRESETS = 2000


class PresetError(ValueError):
    status = 400


class PresetConflict(PresetError):
    status = 409


class PresetNotFound(PresetError):
    status = 404


class PresetStorageError(PresetError):
    status = 500


def digest(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_name(name):
    if (not isinstance(name, str) or not name.strip() or name != name.strip()
            or len(name) > 120 or any(ord(c) < 32 for c in name)):
        raise PresetError("Preset names must contain 1–120 characters without surrounding whitespace or control characters.")
    if name in ("Disabled", "Random", "None") or name.startswith(USER_PREFIX):
        raise PresetError("This preset name is reserved.")
    return name


def validate_preset(data):
    if not isinstance(data, dict):
        raise PresetError("Each preset must be an object.")
    prompt = data.get("prompt")
    description = data.get("description", "")
    tags = data.get("tags", [])
    weight = data.get("weight", 1.0)
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 32000:
        raise PresetError("Prompt text must contain 1–32000 characters.")
    if not isinstance(description, str) or len(description) > 2000:
        raise PresetError("Description must be text, at most 2000 characters.")
    if (not isinstance(tags, list) or len(tags) > 32
            or any(not isinstance(t, str) or not t.strip() or len(t) > 80 for t in tags)):
        raise PresetError("Tags must be a list of up to 32 nonempty strings, each at most 80 characters.")
    if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not 0 < weight <= 1000 or not math.isfinite(weight):
        raise PresetError("Weight must be a finite number greater than zero and at most 1000.")
    return {"prompt": prompt, "description": description, "tags": tags, "weight": weight}


def validate_library(library, categories=CATEGORIES):
    if not isinstance(library, dict) or any(c not in categories for c in library):
        raise PresetError("Unknown preset category.")
    result = {c: {} for c in categories}
    count = 0
    for category, entries in library.items():
        if not isinstance(entries, dict):
            raise PresetError("Each category must be an object.")
        for name, data in entries.items():
            result[category][validate_name(name)] = validate_preset(data)
            count += 1
    if count > MAX_PRESETS:
        raise PresetError("The user library may contain at most 2000 presets.")
    return result


class PromptPresetStore:
    def __init__(self, factory_path, user_path, defaults, categories=CATEGORIES, complete_library=False):
        self.factory_path = Path(factory_path)
        self.user_path = Path(user_path)
        self.defaults = defaults
        self.categories = categories
        self.complete_library = complete_library
        self.lock = threading.RLock()

    def _factory(self):
        defaults = self.defaults()
        try:
            raw = json.loads(self.factory_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raw = defaults
        except (OSError, ValueError, UnicodeError) as exc:
            raise PresetStorageError("Cannot read the factory library; restore its JSON file. " + str(exc)) from exc
        if not isinstance(raw, dict) or any(not isinstance(raw.get(c, {}), dict) for c in self.categories):
            raise PresetStorageError("The factory preset library has an invalid structure.")
        if self.complete_library:
            factory = validate_library(raw, self.categories)
            for category in self.categories:
                if category not in raw:
                    factory[category] = copy.deepcopy(defaults.get(category, {}))
            return factory, {c: list(factory[c]) for c in self.categories}
        factory = copy.deepcopy(raw)
        for category in self.categories:
            entries = factory.setdefault(category, {})
            for name, data in defaults.get(category, {}).items():
                entries.setdefault(name, data)
        # The legacy Random pool is deliberately NOT expanded by reconciliation.
        return factory, {c: list(raw.get(c, {})) for c in self.categories}

    def _users(self):
        try:
            with self.user_path.open("rb") as stream:
                content = stream.read(MAX_BYTES + 1)
        except FileNotFoundError:
            return {c: {} for c in self.categories}
        except OSError as exc:
            raise PresetStorageError("Cannot read user presets: " + str(exc)) from exc
        try:
            if len(content) > MAX_BYTES:
                raise PresetError("User preset file exceeds 4 MiB.")
            document = json.loads(content.decode("utf-8"))
            if not isinstance(document, dict) or document.get("schema_version") != 1:
                raise PresetError("Unsupported user preset schema; expected schema_version 1.")
            return validate_library(document.get("presets"), self.categories)
        except (ValueError, UnicodeError) as exc:
            raise PresetStorageError(
                "User presets are invalid. The original file was left untouched; repair or restore "
                + str(self.user_path) + ": " + str(exc)
            ) from exc

    def snapshot(self):
        with self.lock:
            factory, random_names = self._factory()
            user = self._users()
            if self.complete_library:
                if not self.user_path.exists():
                    user = copy.deepcopy(factory)
                return {"schema_version": 1, "revision": digest(user), "scope": "installation",
                        "factory": factory, "user": user, "presets": user, "random_names": random_names}
            merged = {c: dict(factory[c]) for c in self.categories}
            for category in self.categories:
                for name, data in user[category].items():
                    token = USER_PREFIX + name
                    if token in merged[category]:
                        raise PresetStorageError("Factory preset conflicts with reserved user namespace: " + token)
                    merged[category][token] = data
            # Include ordering: seeded weighted choice depends on insertion order.
            revision = digest({"factory": factory, "user": user, "random_names": random_names})
            return {"schema_version": 1, "revision": revision, "scope": "installation",
                    "factory": factory, "user": user, "presets": merged,
                    "random_names": random_names}

    def _write(self, user):
        user = validate_library(user, self.categories)
        data = json.dumps({"schema_version": 1, "presets": user}, indent=2,
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(data) > MAX_BYTES:
            raise PresetError("User preset file would exceed 4 MiB.")
        self.user_path.parent.mkdir(parents=True, exist_ok=True)
        temp = None
        try:
            with tempfile.NamedTemporaryFile(dir=str(self.user_path.parent), prefix=".apex-presets-",
                                             suffix=".tmp", delete=False) as stream:
                temp = stream.name
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, self.user_path)
        finally:
            if temp and os.path.exists(temp):
                os.unlink(temp)

    def mutate(self, operation, payload):
        """One lock covers revision comparison, validation and atomic replacement."""
        if not isinstance(payload, dict):
            raise PresetError("Request must be a JSON object.")
        with self.lock:
            snapshot = self.snapshot()
            if payload.get("revision") != snapshot["revision"]:
                raise PresetConflict("The library changed. Refresh the manager before saving again.")
            user = snapshot["user"]
            if operation == "replace" and self.complete_library:
                self._write(payload.get("presets"))
                return self.snapshot()
            if operation == "import":
                document = payload.get("document")
                if isinstance(document, dict) and "schema_version" in document:
                    if document["schema_version"] != 1:
                        raise PresetError("Unsupported import schema.")
                    document = document.get("presets")
                imported = validate_library(document, self.categories)
                # Import is all-or-nothing; never silently replace existing entries.
                for category in self.categories:
                    for name, data in imported[category].items():
                        if name in user[category] and user[category][name] != data:
                            raise PresetConflict("Import conflicts with user preset: " + name + ". Rename it before importing.")
                        user[category][name] = data
            else:
                category = payload.get("category")
                if category not in self.categories:
                    raise PresetError("Unknown preset category.")
                name = validate_name(payload.get("name"))
                if payload.get("source") != "user":
                    raise PresetError("Factory presets are read-only. Save a user copy instead.")
                if operation == "save":
                    original = payload.get("original")
                    if original is not None:
                        if (not isinstance(original, dict) or original.get("category") not in self.categories
                                or not isinstance(original.get("name"), str)
                                or original.get("name") not in user[original["category"]]):
                            raise PresetNotFound("The original user preset no longer exists.")
                    same = original == {"category": category, "name": name}
                    if name in user[category] and not same:
                        raise PresetConflict("A user preset with that name already exists in this category.")
                    data = validate_preset(payload.get("preset"))
                    if original is not None:
                        del user[original["category"]][original["name"]]
                    user[category][name] = data
                elif operation == "delete":
                    if name not in user[category]:
                        raise PresetNotFound("User preset not found.")
                    del user[category][name]
                else:
                    raise PresetError("Unknown operation.")
            for category in self.categories:
                if any(USER_PREFIX + name in snapshot["factory"][category] for name in user[category]):
                    raise PresetConflict("A factory entry already uses this reserved user name. Choose another name.")
            self._write(user)
            return self.snapshot()


_store = None
_store_lock = threading.Lock()


def get_store():
    global _store
    with _store_lock:
        if _store is None:
            import folder_paths
            from .apex_prompt import ApexPromptPreset
            _store = PromptPresetStore(
                Path(__file__).with_name("prompt_presets.json"),
                Path(folder_paths.get_user_directory()) / "apex_artist" / "prompt_presets.json",
                ApexPromptPreset.get_default_presets,
            )
        return _store

_character_store = None


def get_character_store():
    global _character_store
    with _store_lock:
        if _character_store is None:
            import folder_paths
            from .apex_character_prompt import ApexCharacterPrompt
            _character_store = PromptPresetStore(
                Path(__file__).with_name("character_presets.json"),
                Path(folder_paths.get_user_directory()) / "apex_artist" / "character_presets.json",
                ApexCharacterPrompt.get_default_presets,
                categories=ApexCharacterPrompt.CHARACTER_CATEGORIES, complete_library=True,
            )
        return _character_store
