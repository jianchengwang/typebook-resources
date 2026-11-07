"""Lossless audit split, integrity failures and runtime compatibility."""
import copy
import json
import pathlib
import sys
import tempfile
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'tools'))
from manifest_io import load_manifest, finish_manifest, SOURCE_PATH, INVENTORY_PATH

class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {'schema_version':1,'revision':'keep-me','catalogs':{},'files':[
            {'path':'a.txt','bytes':2,'sha256':'abc','content_type':'text/plain','category':'book','source':{'kind':'test','unicode':'来源'}},
            {'path':'b.txt','bytes':3,'sha256':'def','content_type':'text/plain','category':'book','source':{'kind':'test','unicode':'来源'}},
            {'path':'c.txt','bytes':4,'sha256':'ghi','category':'book','future_field':{'keep':True}}]}
    def save(self, root, outputs):
        for name, data in outputs.items():
            path=root/name;path.parent.mkdir(parents=True, exist_ok=True);path.write_bytes(data)
    def test_legacy_load_without_sidecar(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);(root/'manifest.json').write_text(json.dumps(self.manifest))
            self.assertEqual(load_manifest(root),self.manifest)
    def test_lossless_deduplicated_roundtrip(self):
        original=copy.deepcopy(self.manifest);outputs={};finish_manifest(self.manifest,outputs)
        self.assertEqual(original,self.manifest)
        index=json.loads(outputs[SOURCE_PATH]);self.assertEqual(len(index['sources']),1)
        self.assertEqual(index['files'],{'a.txt':0,'b.txt':0})
        raw=json.loads(outputs['manifest.json'])
        self.assertTrue(all('source' not in f for f in json.loads(outputs[INVENTORY_PATH])['files']))
        self.assertEqual(raw['revision'],'keep-me')
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);self.save(root,outputs);expanded=load_manifest(root)
            self.assertEqual([f for f in expanded['files'] if f['path'] not in (SOURCE_PATH, INVENTORY_PATH)],original['files'])
            again={};finish_manifest(expanded,again);self.assertEqual(again,outputs)
    def test_runtime_fields_unchanged(self):
        outputs={};finish_manifest(self.manifest,outputs)
        new={f['path']:f for f in json.loads(outputs[INVENTORY_PATH])['files']}
        for old in self.manifest['files']:
            self.assertEqual(new[old['path']],{k:v for k,v in old.items() if k!='source'})
    def test_corrupt_source_index_rejected(self):
        outputs={};finish_manifest(self.manifest,outputs)
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);self.save(root,outputs);(root/SOURCE_PATH).write_text('{}')
            with self.assertRaisesRegex(ValueError,'integrity'):load_manifest(root)
    def test_unsafe_reference_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);self.manifest['file_sources']={'path':'../secret.json'}
            (root/'manifest.json').write_text(json.dumps(self.manifest))
            with self.assertRaises(ValueError):load_manifest(root)
    def test_empty_sources_supported(self):
        self.manifest['files']=[];outputs={};finish_manifest(self.manifest,outputs)
        self.assertEqual(json.loads(outputs[SOURCE_PATH])['files'],{})

    def test_root_is_lightweight_v2_and_integrity_linked(self):
        outputs={};finish_manifest(self.manifest,outputs)
        root=json.loads(outputs['manifest.json'])
        self.assertEqual(root['schema_version'],2)
        self.assertNotIn('files',root)
        self.assertEqual(root['file_inventory']['bytes'],len(outputs[INVENTORY_PATH]))
        self.assertEqual(root['total_bytes'],sum(x['bytes'] for x in json.loads(outputs[INVENTORY_PATH])['files']) + len(outputs[INVENTORY_PATH]))
    def test_inventory_tampering_rejected(self):
        outputs={};finish_manifest(self.manifest,outputs)
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);self.save(root,outputs)
            (root/INVENTORY_PATH).write_text('{}')
            with self.assertRaisesRegex(ValueError,'inventory integrity'):load_manifest(root)
    def test_catalog_hash_must_match_inventory(self):
        self.manifest['catalogs']={'books':{'path':'a.txt'}}
        outputs={};finish_manifest(self.manifest,outputs)
        m=json.loads(outputs['manifest.json']);m['catalogs']['books']['sha256']='changed'
        outputs['manifest.json']=json.dumps(m).encode()
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);self.save(root,outputs)
            with self.assertRaisesRegex(ValueError,'Discovery reference differs'):load_manifest(root)
    def test_actual_root_stays_small(self):
        data=(pathlib.Path(__file__).resolve().parents[1]/'manifest.json').read_bytes()
        self.assertLess(len(data),8192)
        self.assertNotIn('files',json.loads(data))
