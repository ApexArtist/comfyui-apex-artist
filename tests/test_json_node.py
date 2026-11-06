"""Pure CPU JSON tests; no ComfyUI, model or server imports."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('apex_json_test', ROOT/'apex_json_node.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class JSONLookupTests(unittest.TestCase):
    def setUp(self):
        self.node = module.ApexJSON()

    def test_old_schema_and_defaults(self):
        schema = self.node.INPUT_TYPES()
        self.assertEqual(list(schema['required']), ['text','key'])
        self.assertEqual(list(schema['optional']), ['strict','schema','as_json'])
        self.assertFalse(schema['optional']['strict'][1]['default'])

    def test_old_calls(self):
        for source,key,want in [('{"name":"Lina"}','name','Lina'),('{"n":3}','n','3'),('{"a":1}','',''),('{"a":1}','b',''),('note: "name": "Lina"','name','Lina')]:
            with self.subTest(key=key):self.assertEqual(self.node.lookup(source,key),(want,))

    def test_fenced_nested_json(self):
        data={'script':{'shots':[{'at':0}],'event':'She says "stay".\n\u96ea'}}
        for kwargs in ({},{'strict':True}):
            text='```json\n'+json.dumps(data,ensure_ascii=False)+'\n```'
            self.assertEqual(json.loads(self.node.lookup(text,'script',**kwargs)[0]),data['script'])

    def test_legacy_prefix(self):
        self.assertEqual(self.node.lookup('Answer: {"name":"Lina"}','name'),('Lina',))

    def test_strict_bad_documents(self):
        for text in ('','{"script":','{"a":1} {"a":2}','Answer: {"a":1}','{"a":NaN}','{"a":Infinity}'):
            with self.subTest(text=text),self.assertRaisesRegex(ValueError,'complete valid JSON'):
                self.node.lookup(text,'a',strict=True)

    def test_strict_duplicate_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'complete valid JSON'):
            self.node.lookup('{"a":1,"a":2}','a',strict=True)
        self.assertEqual(self.node.lookup('{"a":1,"a":2}','a'),('2',))

    def test_strict_bad_paths(self):
        for key in ('missing','beats.2','beats.-1','beats.abc','beats.0.missing'):
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'missing path'):
                self.node.lookup('{"beats":[{"clip":1}]}',key,strict=True)

    def test_null_is_not_missing(self):
        self.assertEqual(self.node.lookup('{"v":null}','v',strict=True),('null',))

    def test_json_scalar_serialization(self):
        for value in ('Lina says "stay".\n\u96ea \\ {}',True,False,None,3):
            source=json.dumps({'v':value},ensure_ascii=False)
            self.assertEqual(json.loads(self.node.lookup(source,'v',as_json=True)[0]),value)

    def test_root_extraction(self):
        for key in ('','$'):
            self.assertEqual(json.loads(self.node.lookup('{"a":1}',key,strict=True)[0]),{'a':1})
            self.assertEqual(json.loads(self.node.lookup('[1,2]',key,as_json=True)[0]),[1,2])

    def test_nested_array_index(self):
        self.assertEqual(json.loads(self.node.lookup('{"beats":[{"clip":7}]}','beats.0',strict=True)[0]),{'clip':7})

    def test_schema_enables_strict(self):
        schema=json.dumps({'type':'object','required':['shots'],'properties':{'shots':{'type':'array','minItems':1}}})
        self.assertEqual(json.loads(self.node.lookup('{"script":{"shots":[{}]}}','script',schema=schema)[0]),{'shots':[{}]})
        for source in ('{"script":{}}','{"script":{"shots":[]}}','{"script":"bad"}'):
            with self.subTest(source=source),self.assertRaisesRegex(ValueError,'fails schema'):
                self.node.lookup(source,'script',schema=schema)

    def test_dynamic_clip_and_time_bounds(self):
        schema=json.dumps({'type':'object','required':['clip','at'],'properties':{'clip':{'const':7},'at':{'type':'number','minimum':0,'exclusiveMaximum':10}}})
        self.node.lookup('{"clip":7,"at":9.5}','$',schema=schema)
        for source in ('{"clip":6,"at":0}','{"clip":7,"at":10}','{"clip":7,"at":-1}'):
            with self.subTest(source=source),self.assertRaisesRegex(ValueError,'fails schema'):
                self.node.lookup(source,'$',schema=schema)

    def test_bad_schema(self):
        for schema in ('{','{"type":17}','NaN'):
            with self.subTest(schema=schema),self.assertRaisesRegex(ValueError,'invalid validation schema'):
                self.node.lookup('{"a":1}','$',schema=schema)

    def test_local_schema_reference(self):
        schema=json.dumps({'$defs':{'count':{'type':'integer','minimum':1}},'$ref':'#/$defs/count'})
        self.assertEqual(self.node.lookup('{"count":2}','count',schema=schema),('2',))

    def test_no_network_for_schema_references(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError('Network forbidden')):
            with self.assertRaisesRegex(ValueError,'external retrieval is disabled'):
                self.node.lookup('{"a":1}','$',schema='{"$ref":"https://example.com/schema.json"}')


if __name__=='__main__':unittest.main()
