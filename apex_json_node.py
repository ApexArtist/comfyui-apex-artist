"""
Apex JSON Lookup Node (Single Key)

- Accepts JSON or plain text
- Extracts a single value using key or dotted path
- Outputs a plain STRING
- ComfyUI-safe: explicit inputs, no kwargs
"""

import json
import re
from typing import Any

_MISSING = object()


def _reject_constant(value):
    raise ValueError(f"Non-finite number {value!r} is not valid JSON")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key {key!r}")
        result[key] = value
    return result


def _decode(text, strict):
    source = text.lstrip("\ufeff").strip()
    fenced = re.fullmatch(r"```(?:json)?\s*([\s\S]*?)\s*```", source, re.IGNORECASE)
    if fenced:
        source = fenced.group(1)
    if strict:
        return json.loads(source, parse_constant=_reject_constant, object_pairs_hook=_unique_object)
    try:
        return json.loads(source)
    except (ValueError, TypeError):
        decoder = json.JSONDecoder()
        for match in re.finditer(r"[\{\[]", source):
            try:
                value, _ = decoder.raw_decode(source, match.start())
                return value
            except ValueError:
                continue
        return _MISSING


def _resolve(value, path):
    for part in path.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            return _MISSING
    return value


def _validate(value, schema_text, key):
    # Legacy text-only workflows do not load schema validation libraries.
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError
    from referencing import Registry
    from referencing.exceptions import NoSuchResource
    try:
        schema = json.loads(schema_text, parse_constant=_reject_constant, object_pairs_hook=_unique_object)
        Draft202012Validator.check_schema(schema)
    except (ValueError, SchemaError) as exc:
        raise ValueError("Apex JSON: invalid validation schema") from exc

    def offline_only(uri):
        raise NoSuchResource(ref=uri)

    validator = Draft202012Validator(schema, registry=Registry(retrieve=offline_only))
    try:
        error = next(validator.iter_errors(value), None)
    except Exception as exc:
        raise ValueError("Apex JSON: schema reference cannot be resolved; external retrieval is disabled") from exc
    if error is not None:
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        raise ValueError(f"Apex JSON: {key or '$'} fails schema at {location}: {error.message[:300]}")


class ApexJSON:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "key": ("STRING", {"default": ""}),
            },
            "optional": {
                "strict": ("BOOLEAN", {"default": False, "tooltip": "Require complete valid JSON and an existing path. Stop on bad data instead of returning empty text."}),
                "schema": ("STRING", {"default": "", "multiline": True, "tooltip": "Optional JSON Schema (2020-12) for the extracted value. Enables strict parsing. External schema references are never fetched."}),
                "as_json": ("BOOLEAN", {"default": False, "tooltip": "Return JSON, including quoted strings and JSON booleans/null. Enables strict parsing; an empty key or $ selects the whole document."}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("value",)

    FUNCTION = "lookup"
    CATEGORY = "Apex Artist/Text"

    # --------------------------------------------------

    def _get_from_path(self, obj: Any, path: str):
        cur = obj
        for part in path.split("."):
            if isinstance(cur, dict):
                if part not in cur:
                    return None
                cur = cur[part]
            elif isinstance(cur, list):
                if not part.isdigit():
                    return None
                idx = int(part)
                if idx < 0 or idx >= len(cur):
                    return None
                cur = cur[idx]
            else:
                return None
        return cur

    def _regex_lookup(self, text: str, key: str):
        # safer: stop at line break or closing brace
        pattern = rf'"{re.escape(key)}"\s*:\s*("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|[^,\n\r}}]+)'
        m = re.search(pattern, text)
        if not m:
            return None

        val = m.group(1).strip()

        if (
            (val.startswith('"') and val.endswith('"')) or
            (val.startswith("'") and val.endswith("'"))
        ):
            val = val[1:-1]

        return val.strip()

    # --------------------------------------------------

    def lookup(self, text: str, key: str, strict=False, schema="", as_json=False):
        key = key.strip()
        strict_mode = bool(strict or schema.strip() or as_json)
        if not key and not strict_mode:
            return ("",)
        try:
            parsed = _decode(text, strict_mode)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Apex JSON: expected complete valid JSON for {key or '$'}") from exc
        value = _MISSING
        if parsed is not _MISSING:
            value = parsed if strict_mode and key in ("", "$") else _resolve(parsed, key)
        if strict_mode and value is _MISSING:
            raise ValueError(f"Apex JSON: missing path {key!r}")
        if not strict_mode and (value is _MISSING or value is None):
            value = self._regex_lookup(text, key)
        if not strict_mode and (value is None or value is _MISSING):
            return ("",)
        if schema.strip():
            _validate(value, schema, key)
        if as_json:
            return (json.dumps(value, ensure_ascii=False, allow_nan=False),)
        if strict_mode and value is None:
            return ("null",)
        if isinstance(value, (dict, list)):
            return (json.dumps(value, ensure_ascii=False),)

        return (str(value),)
