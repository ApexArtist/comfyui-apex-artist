"""Isolated preset store/node/API regressions; never writes real user data."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import importlib
import json
from pathlib import Path
import random
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "apex_preset_tests"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = package
store_module = importlib.import_module(PACKAGE + ".apex_prompt_store")
node_module = importlib.import_module(PACKAGE + ".apex_prompt")
Node = node_module.ApexPromptPreset
CAT = "Apex Lighting"


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.factory_path = ROOT / "prompt_presets.json"
        self.original_factory = self.factory_path.read_bytes()
        self.store = store_module.PromptPresetStore(self.factory_path,
            Path(self.temp.name) / "user" / "presets.json", Node.get_default_presets)
        self.patch = patch.object(store_module, "_store", self.store)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def tearDown(self):
        self.assertEqual(self.factory_path.read_bytes(), self.original_factory)

    def save(self, name="My Light", text="soft user light", **extra):
        payload = {"revision": self.store.snapshot()["revision"], "source": "user",
                   "category": CAT, "name": name, "preset": {"prompt": text}}
        payload.update(extra)
        return self.store.mutate("save", payload)

    def test_factory_preserved_and_reconciled(self):
        snap = self.store.snapshot()
        raw = json.loads(self.original_factory)
        for cat in store_module.CATEGORIES:
            for name, data in raw[cat].items():
                self.assertEqual(snap["factory"][cat][name], data)
            self.assertTrue(set(Node.get_default_presets()[cat]) <= set(snap["factory"][cat]))
        self.assertFalse(self.store.user_path.exists())

    def test_save_reload_edit_rename_delete(self):
        snap = self.save()
        self.assertIn("User: My Light", snap["presets"][CAT])
        reopened = store_module.PromptPresetStore(self.factory_path, self.store.user_path, Node.get_default_presets)
        self.assertEqual(reopened.snapshot(), snap)
        self.save(name="Renamed", text="new text", original={"category": CAT, "name": "My Light"})
        snap = self.store.snapshot()
        self.assertNotIn("My Light", snap["user"][CAT])
        self.assertEqual(snap["user"][CAT]["Renamed"]["prompt"], "new text")
        self.store.mutate("delete", {"revision": snap["revision"], "source": "user", "category": CAT, "name": "Renamed"})
        self.assertEqual(self.store.snapshot()["user"][CAT], {})

    def test_factory_protection_and_duplicate_namespace(self):
        name = next(iter(self.store.snapshot()["factory"][CAT]))
        self.save(name=name)
        snap = self.store.snapshot()
        self.assertNotEqual(snap["presets"][CAT][name], snap["presets"][CAT]["User: " + name])
        with self.assertRaises(store_module.PresetError):
            self.save(source="factory")
        with self.assertRaises(store_module.PresetConflict):
            self.save(name=name)

    def test_validation_and_corruption_preserve_file(self):
        self.save()
        before = self.store.user_path.read_bytes()
        for data in [{"prompt": ""}, {"prompt": "x", "weight": float("nan")},
                     {"prompt": "x", "weight": 0}, {"prompt": "x", "tags": "bad"}]:
            with self.subTest(data=data), self.assertRaises(store_module.PresetError):
                self.save(name="Invalid", preset=data)
        with self.assertRaises(store_module.PresetNotFound):
            self.save(original={"category": CAT, "name": []})
        self.assertEqual(before, self.store.user_path.read_bytes())
        self.store.user_path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(store_module.PresetStorageError):
            self.save()
        self.assertEqual(self.store.user_path.read_text(), "{broken")

    def test_atomic_failure_leaves_original(self):
        self.save()
        before = self.store.user_path.read_bytes()
        with patch.object(store_module.os, "replace", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                self.save(name="Other")
        self.assertEqual(before, self.store.user_path.read_bytes())
        self.assertEqual(list(self.store.user_path.parent.glob("*.tmp")), [])

    def test_concurrent_revision_conflict(self):
        revision = self.store.snapshot()["revision"]
        def attempt(index):
            try:
                self.save(name=str(index), revision=revision)
                return "saved"
            except store_module.PresetConflict:
                return "conflict"
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(attempt, [1, 2])), ["saved", "conflict"])

    def test_import_export_and_conflict_is_atomic(self):
        snap = self.save()
        document = {"schema_version": 1, "presets": snap["user"]}
        self.store.mutate("import", {"revision": snap["revision"], "document": document})
        before = self.store.user_path.read_bytes()
        document["presets"][CAT]["My Light"]["prompt"] = "conflicting"
        with self.assertRaises(store_module.PresetConflict):
            self.store.mutate("import", {"revision": snap["revision"], "document": document})
        self.assertEqual(before, self.store.user_path.read_bytes())

    def test_existing_node_refresh_and_change_detection(self):
        node = Node()
        revision = Node.IS_CHANGED()
        self.save()
        self.assertNotEqual(revision, Node.IS_CHANGED())
        self.assertIn("User: My Light", Node.INPUT_TYPES()["optional"]["lighting_preset"][0])
        self.assertEqual(node.combine_prompts("subject", lighting_preset="User: My Light")[2], "soft user light")
        self.save(text="changed", original={"category": CAT, "name": "My Light"})
        self.assertEqual(node.combine_prompts("subject", lighting_preset="User: My Light")[2], "changed")
        self.assertEqual(len(node.combine_prompts("subject")), 5)
        with self.assertRaisesRegex(ValueError, "Missing preset"):
            node.combine_prompts("subject", lighting_preset="User: Missing")

    def test_random_legacy_order_and_global_rng(self):
        raw = json.loads(self.original_factory)
        node = Node()
        state = random.getstate()
        before = [node.combine_prompts("[a,b]", seed=seed, lighting_preset="Random") for seed in range(50)]
        self.save()
        after = [node.combine_prompts("[a,b]", seed=seed, lighting_preset="Random") for seed in range(50)]
        self.assertEqual(before, after)
        self.assertEqual(state, random.getstate())
        for seed in range(50):
            name = random.Random(seed + 2).choices(list(raw[CAT]), weights=[d.get("weight", 1) for d in raw[CAT].values()], k=1)[0]
            self.assertEqual(after[seed][2], raw[CAT][name]["prompt"])

    def test_http_routes(self):
        async def exercise():
            server = types.ModuleType("server")
            server.PromptServer = types.SimpleNamespace(instance=types.SimpleNamespace(
                routes=web.RouteTableDef(), send_sync=lambda *args: None))
            with patch.dict(sys.modules, {"server": server}):
                sys.modules.pop(PACKAGE + ".apex_prompt_api", None)
                importlib.import_module(PACKAGE + ".apex_prompt_api")
                app = web.Application()
                app.add_routes(server.PromptServer.instance.routes)
                async with TestClient(TestServer(app)) as client:
                    response = await client.get("/apex/prompt_library")
                    self.assertEqual(response.status, 200)
                    snap = await response.json()
                    payload = {"revision": snap["revision"], "source": "user", "category": CAT, "name": "HTTP", "preset": {"prompt": "http light"}}
                    response = await client.post("/apex/prompt_library/save", json=payload)
                    self.assertEqual(response.status, 200)
                    response = await client.post("/apex/prompt_library/save", json=payload)
                    self.assertEqual(response.status, 409)
                    for path in ["/apex/prompt_presets", "/apex/prompt_presets/category/name"]:
                        self.assertEqual((await client.post(path, json={})).status, 403)
                    self.assertEqual((await client.delete("/apex/prompt_presets/category/name")).status, 403)
                    self.assertEqual((await client.post("/apex/prompt_library/save", data="invalid")).status, 400)
                    self.assertEqual((await client.get("/apex/prompt_presets")).status, 200)
        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main(verbosity=2)