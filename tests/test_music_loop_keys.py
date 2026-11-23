"""Cache-policy regressions for the scoped native-loop adapter."""
import asyncio,importlib.util,pathlib,sys,types,unittest
from unittest.mock import patch

HERE=pathlib.Path(__file__).resolve();ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT.parents[1]))
source=ROOT/'apex_loop_cache_keys.py'
import nodes
from comfy_execution.caching import CacheKeySetInputSignature,HierarchicalCache,LRUCache,RAMPressureCache,NullCache
spec=importlib.util.spec_from_file_location('music_key_test',source);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class Dummy:
 RETURN_TYPES=('INT',)
 @classmethod
 def INPUT_TYPES(cls):return {'required':{},'hidden':{}}
class Changed:
 async def get(self,key):return False
class Graph:
 def __init__(self,cached=False):
  self.prompt={'shared':{'class_type':'Scalar','inputs':{'value':7}},
               'plan':{'class_type':'Plan','inputs':{'count':72}},
               'loop':{'class_type':'StartLoop','inputs':{'mode.num_iterations':['plan',0],'cache_iterations':cached}},
               'iteration':{'class_type':'Scalar','inputs':{'value':0}},
               'expanded':{'class_type':'Scalar','inputs':{'first':['iteration',0],'model':['shared',0]}}}
  self.parents={'iteration':'loop','expanded':'loop'}
 def get_node(self,key):return self.prompt[key]
 def has_node(self,key):return key in self.prompt
 def all_node_ids(self):return self.prompt.keys()
 def get_parent_node_id(self,key):return self.parents.get(key)

class LoopKeyTests(unittest.TestCase):
 def setUp(self):
  self.mapping=patch.dict(nodes.NODE_CLASS_MAPPINGS,{'Scalar':Dummy,'Plan':Dummy,'StartLoop':Dummy});self.mapping.start()
 def tearDown(self):self.mapping.stop()
 def run_async(self,coro):return asyncio.run(coro)
 def cache(self,kind,g):
  c=kind(CacheKeySetInputSignature);self.run_async(c.set_prompt(g,['shared','plan','loop'],Changed()));return c
 def test_all_native_cache_backends_preserve_shared_results(self):
  for kind in [HierarchicalCache,LRUCache,RAMPressureCache]:
   with self.subTest(cache=kind.__name__):
    g=Graph();c=self.cache(kind,g);self.run_async(c.set('shared',123));old=c.cache_key_set.get_data_key('shared')
    result=mod.enable_uncached_music_loop_keys(g,types.SimpleNamespace(output_cache=c),'plan')
    self.assertEqual(result['status'],'scoped_uncached_iteration_keys')
    self.assertEqual(c.cache_key_set.get_data_key('shared'),old);self.assertEqual(c.get_local('shared'),123)
    sub=self.run_async(c.ensure_subcache_for('loop',{'iteration','expanded'}))
    key=sub.cache_key_set.get_data_key('expanded');self.assertEqual(len(key),5)
    sub.set_local('expanded',456);self.assertEqual(sub.get_local('expanded'),456)
 def test_nonloop_signatures_are_identical_to_native(self):
  g=Graph();c=self.cache(RAMPressureCache,g);mod.enable_uncached_music_loop_keys(g,types.SimpleNamespace(output_cache=c),'plan')
  native=CacheKeySetInputSignature(g,[],Changed())
  self.assertEqual(self.run_async(c.cache_key_set.get_node_signature(g,'shared')),self.run_async(native.get_node_signature(g,'shared')))
 def test_uncached_key_never_matches_another_prompt(self):
  keys=[]
  for _ in range(2):
   g=Graph();c=self.cache(RAMPressureCache,g);mod.enable_uncached_music_loop_keys(g,types.SimpleNamespace(output_cache=c),'plan')
   self.run_async(c.cache_key_set.add_keys(['expanded']));keys.append(c.cache_key_set.get_data_key('expanded'))
  self.assertNotEqual(keys[0],keys[1])
 def test_explicit_cached_loop_is_untouched(self):
  g=Graph(cached=True);c=self.cache(RAMPressureCache,g)
  r=mod.enable_uncached_music_loop_keys(g,types.SimpleNamespace(output_cache=c),'plan')
  self.assertEqual(r['status'],'no_matching_uncached_music_loop');self.assertIs(c.key_class,CacheKeySetInputSignature)
 def test_unrelated_uncached_loop_is_untouched(self):
  g=Graph();g.prompt['loop']['inputs']['mode.num_iterations']=['shared',0];c=self.cache(RAMPressureCache,g)
  self.assertEqual(mod.enable_uncached_music_loop_keys(g,types.SimpleNamespace(output_cache=c),'plan')['status'],'no_matching_uncached_music_loop')
 def test_music_preflight_rejects_enabled_iteration_caching(self):
  g=Graph(cached=True);c=self.cache(RAMPressureCache,g)
  with self.assertRaisesRegex(ValueError,'keep Cache Iterations off'):
   mod.enable_uncached_music_loop_keys(g,types.SimpleNamespace(output_cache=c),'plan',require_uncached=True)
 def test_music_preflight_rejects_unknown_linked_cache_policy(self):
  g=Graph();g.prompt['loop']['inputs']['cache_iterations']=['shared',0];c=self.cache(RAMPressureCache,g)
  with self.assertRaisesRegex(ValueError,'keep Cache Iterations off'):
   mod.enable_uncached_music_loop_keys(g,types.SimpleNamespace(output_cache=c),'plan',require_uncached=True)
 def test_future_nonmusic_prompt_uses_normal_signatures(self):
  g=Graph();c=self.cache(RAMPressureCache,g);self.run_async(c.set('shared',123))
  mod.enable_uncached_music_loop_keys(g,types.SimpleNamespace(output_cache=c),'plan')
  g2=Graph();self.run_async(c.set_prompt(g2,['shared'],Changed()))
  self.assertEqual(c.get_local('shared'),123)
 def test_null_cache_is_left_as_is(self):
  r=mod.enable_uncached_music_loop_keys(Graph(),types.SimpleNamespace(output_cache=NullCache()),'plan')
  self.assertEqual(r['status'],'native_cache_disabled')
 def test_unknown_cache_fails_before_mutation(self):
  with self.assertRaisesRegex(ValueError,'unsupported'):
   mod.enable_uncached_music_loop_keys(Graph(),types.SimpleNamespace(output_cache=object()),'plan')
 def test_unknown_key_layout_fails_before_mutation(self):
  g=Graph();c=self.cache(RAMPressureCache,g);c.cache_key_set.future_field=True
  with self.assertRaisesRegex(ValueError,'layout has changed'):
   mod.enable_uncached_music_loop_keys(g,types.SimpleNamespace(output_cache=c),'plan')
  self.assertIs(c.key_class,CacheKeySetInputSignature)
 def test_constant_size_keys_on_deep_expanded_chain(self):
  g=Graph();c=self.cache(RAMPressureCache,g);mod.enable_uncached_music_loop_keys(g,types.SimpleNamespace(output_cache=c),'plan')
  for i in range(3000):
   key='child'+str(i);g.prompt[key]={'class_type':'Scalar','inputs':{'value':['child'+str(i-1) if i else 'iteration',0]}};g.parents[key]='loop'
  self.run_async(c.cache_key_set.add_keys(['child'+str(i) for i in range(3000)]))
  self.assertEqual(len(c.cache_key_set.get_data_key('child2999')),5)
 def test_uncached_keys_do_not_go_to_external_provider(self):
  g=Graph();c=self.cache(RAMPressureCache,g);mod.enable_uncached_music_loop_keys(g,types.SimpleNamespace(output_cache=c),'plan')
  self.run_async(c.cache_key_set.add_keys(['expanded']));key=c.cache_key_set.get_data_key('expanded')
  from comfy_execution.cache_provider import _contains_self_unequal
  self.assertTrue(_contains_self_unequal(key))

 def test_scoped_key_uses_native_signature_container(self):
  g=Graph();c=self.cache(RAMPressureCache,g)
  mod.enable_uncached_music_loop_keys(g,types.SimpleNamespace(output_cache=c),'plan')
  self.run_async(c.cache_key_set.add_keys(['expanded']))
  scoped=c.cache_key_set.get_data_key('expanded')
  native=c.cache_key_set.get_data_key('shared')
  self.assertIs(type(scoped),type(native))
 def test_ram_pressure_eviction_with_equal_priority_and_timestamp(self):
  g=Graph();c=self.cache(RAMPressureCache,g)
  mod.enable_uncached_music_loop_keys(g,types.SimpleNamespace(output_cache=c),'plan')
  self.run_async(c.cache_key_set.add_keys(['expanded']))
  for node_id in ('shared','expanded'):
   c.set_local(node_id,types.SimpleNamespace(outputs=[7]))
   key=c.cache_key_set.get_data_key(node_id)
   c.timestamps[key]=1000.0
   c.used_generation[key]=c.generation-1
  with patch('comfy_execution.caching.virtual_memory_available',return_value=0):
   self.assertGreater(c.ram_release(1),0)
  self.assertEqual(c.cache,{})

if __name__=='__main__':unittest.main()
