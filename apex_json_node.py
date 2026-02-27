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


class ApexJSON:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "key": ("STRING", {"default": ""}),
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

    def lookup(self, text: str, key: str):
        key = key.strip()
        if not key:
            return ("",)

        parsed = None
        try:
            parsed = json.loads(text)
        except Exception:
            pass

        value = None

        if parsed is not None:
            value = self._get_from_path(parsed, key)

        if value is None:
            value = self._regex_lookup(text, key)

        if value is None:
            return ("",)

        if isinstance(value, (dict, list)):
            return (json.dumps(value, ensure_ascii=False),)

        return (str(value),)
