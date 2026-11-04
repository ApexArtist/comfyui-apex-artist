"""Captured loop results must be freed without invalidating live consumers."""
import importlib
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1]))
package = types.ModuleType('apex_loop_memory_tests')
package.__path__ = [str(ROOT)]
sys.modules[package.__name__] = package
memory = importlib.import_module(package.__name__ + '.apex_loop_memory')
from comfy_execution.caching import CacheKeySetInputSignature, NullCache, RAMPressureCache
from comfy_execution.graph import DynamicPrompt


class LoopMemory(unittest.TestCase):
    def setUp(self):
        self.graph = DynamicPrompt({
            'loop': {'class_type': 'StartLoop', 'inputs': {'cache_iterations': False}},
            'shared': {'class_type': 'Models', 'inputs': {}},
        })
        for name, inputs in (
            ('frames', {'model': ['shared', 0]}),
            ('video', {'images': ['frames', 0]}),
            ('timeline', {'video': ['video', 0]}),
        ):
            self.graph.add_ephemeral_node(name, {'class_type': name, 'inputs': inputs}, 'loop', name)
        self.cache = RAMPressureCache(CacheKeySetInputSignature)
        self.cache.initialized = True
        self.cache.cache_key_set = types.SimpleNamespace(get_data_key=lambda node_id: node_id)
        for table in (self.cache.cache, self.cache.used_generation, self.cache.children, self.cache.timestamps):
            table.update({name: object() for name in ('shared', 'frames', 'video')})
        self.execution = types.SimpleNamespace(output_cache=self.cache, pendingNodes={'timeline': True})

    def release(self):
        return memory.release_captured_loop_outputs(self.graph, self.execution, 'timeline')

    def add_pending_consumer(self, name, source):
        self.graph.add_ephemeral_node(name, {'class_type': name, 'inputs': {'input': [source, 0]}}, 'loop', name)
        self.execution.pendingNodes[name] = True

    def test_completed_results_and_bookkeeping_are_released(self):
        self.assertEqual(self.release(), 2)
        for table in (self.cache.cache, self.cache.used_generation, self.cache.children, self.cache.timestamps):
            self.assertEqual(set(table), {'shared'})

    def test_pending_reader_keeps_its_source(self):
        self.add_pending_consumer('late_reader', 'frames')
        self.assertEqual(self.release(), 1)
        self.assertEqual(set(self.cache.cache), {'shared', 'frames'})

    def test_carried_value_is_kept_for_next_iteration(self):
        self.add_pending_consumer('next_iteration', 'video')
        self.assertEqual(self.release(), 1)
        self.assertIn('video', self.cache.cache)

    def test_shared_cache_key_is_kept_for_pending_alias(self):
        self.graph.add_ephemeral_node('alias', {'class_type': 'frames', 'inputs': {}}, 'loop', 'alias')
        self.cache.cache_key_set.get_data_key = lambda node_id: 'frames' if node_id == 'alias' else node_id
        self.add_pending_consumer('late_reader', 'alias')
        self.assertEqual(self.release(), 1)
        self.assertIn('frames', self.cache.cache)

    def test_pending_producer_is_not_evicted(self):
        self.execution.pendingNodes['frames'] = True
        self.assertEqual(self.release(), 1)
        self.assertIn('frames', self.cache.cache)

    def test_explicit_iteration_caching_is_preserved(self):
        self.graph.get_node('loop')['inputs']['cache_iterations'] = True
        self.assertEqual(self.release(), 0)
        self.assertEqual(len(self.cache.cache), 3)

    def test_standalone_timeline_does_not_clear_cache(self):
        del self.graph.ephemeral_parents['timeline']
        self.assertEqual(self.release(), 0)

    def test_none_cache_and_direct_node_calls_are_safe(self):
        self.execution.output_cache = NullCache()
        self.assertEqual(self.release(), 0)
        self.assertEqual(memory.release_captured_loop_outputs(None, None, 'timeline'), 0)


if __name__ == '__main__':
    unittest.main()
