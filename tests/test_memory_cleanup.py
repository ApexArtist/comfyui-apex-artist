"""Cleanup preserves live consumers while releasing completed loop expansions."""
import importlib
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parents[1]))
package=types.ModuleType("apex_cleanup_tests");package.__path__=[str(ROOT)];sys.modules[package.__name__]=package
memory=importlib.import_module(package.__name__+".apex_loop_memory")
node=importlib.import_module(package.__name__+".apex_memory_cleanup")
from comfy_execution.caching import CacheKeySetInputSignature,RAMPressureCache
from comfy_execution.graph import DynamicPrompt

class Cleanup(unittest.TestCase):
 def setUp(self):
  self.graph=DynamicPrompt({"loop":{"class_type":"StartLoop","inputs":{"cache_iterations":False}},"shared":{"class_type":"Models","inputs":{}}})
  for name,inputs,parent in [("frames",{},"loop"),("internal",{},"frames"),("saved",{"value":["frames",0]},"loop"),("cleanup",{"trigger":["saved",0]},"loop")]:
   self.graph.add_ephemeral_node(name,{"class_type":name,"inputs":inputs},parent,name)
  self.cache=RAMPressureCache(CacheKeySetInputSignature);self.cache.initialized=True
  self.cache.cache_key_set=types.SimpleNamespace(get_data_key=lambda key:key)
  for table in [self.cache.cache,self.cache.used_generation,self.cache.children,self.cache.timestamps]:table.update({key:object() for key in ["shared","frames","internal","saved"]})
  self.execution=types.SimpleNamespace(output_cache=self.cache,pendingNodes={"cleanup":True},execution_cache={})
 def release(self):return memory.release_completed_outputs(self.graph,self.execution,"cleanup")
 def test_includes_expanded_internal_outputs(self):
  count,scope=self.release();self.assertEqual(count,3);self.assertEqual(scope,"current_loop");self.assertEqual(set(self.cache.cache),{"shared"})
 def test_later_reader_keeps_source(self):
  self.graph.add_ephemeral_node("later",{"class_type":"later","inputs":{"source":["internal",0]}},"loop","later")
  self.execution.pendingNodes["later"]=True
  self.release();self.assertIn("internal",self.cache.cache)
 def test_execution_binding_protects_expansion_output(self):
  self.execution.pendingNodes["wrapper"]=True
  self.graph.add_ephemeral_node("wrapper",{"class_type":"wrapper","inputs":{}},"loop","wrapper")
  self.execution.execution_cache["wrapper"]={"internal":self.cache.cache["internal"]}
  self.release();self.assertIn("internal",self.cache.cache)
 def test_explicit_iteration_cache_is_preserved(self):
  self.graph.get_node("loop")["inputs"]["cache_iterations"]=True
  self.assertEqual(self.release(),(0,"cached_loop_preserved"));self.assertEqual(len(self.cache.cache),4)
 def test_standalone_only_upstream(self):
  self.graph.ephemeral_parents.clear()
  self.release();self.assertIn("shared",self.cache.cache);self.assertIn("internal",self.cache.cache);self.assertNotIn("frames",self.cache.cache)
 def test_unknown_cache_is_not_modified(self):
  self.execution.output_cache=object();self.assertEqual(self.release(),(0,"unsupported_cache"))
 def test_absent_execution_is_safe(self):self.assertEqual(memory.release_completed_outputs(None,None,"cleanup"),(0,"no_execution_context"))
 def test_node_order_passthrough_and_defaults(self):
  value=object();calls=[]
  with patch.object(node.ApexMemoryCleanup,"hidden",types.SimpleNamespace(dynprompt=self.graph,execution_list=self.execution,unique_id="cleanup")),patch.object(node.mm,"get_torch_device",return_value="cpu"),patch.object(node.mm,"get_free_memory",side_effect=[100,140]),patch.object(node.mm,"unload_all_models",side_effect=lambda:calls.append("unload")),patch.object(node.gc,"collect",side_effect=lambda:calls.append("gc")),patch.object(node.mm,"soft_empty_cache",side_effect=lambda:calls.append("empty")):
   result=node.ApexMemoryCleanup.execute(value).result
  self.assertIs(result[0],value);self.assertEqual(calls,["gc","empty"]);self.assertEqual(result[2],3);self.assertEqual(json.loads(result[1])["device_free_change_bytes"],40)
 def test_optional_unload_precedes_gc_and_empty(self):
  calls=[]
  with patch.object(node.ApexMemoryCleanup,"hidden",types.SimpleNamespace(dynprompt=None,execution_list=None,unique_id="cleanup")),patch.object(node.mm,"get_torch_device",return_value="cpu"),patch.object(node.mm,"get_free_memory",return_value=100),patch.object(node.mm,"unload_all_models",side_effect=lambda:calls.append("unload")),patch.object(node.gc,"collect",side_effect=lambda:calls.append("gc")),patch.object(node.mm,"soft_empty_cache",side_effect=lambda:calls.append("empty")):
   node.ApexMemoryCleanup.execute(None,unload_models=True)
  self.assertEqual(calls,["unload","gc","empty"])
