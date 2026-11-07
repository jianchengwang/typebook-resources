import copy
import json
import pathlib
import sys
import unittest
from unittest.mock import patch
import tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import rebuild_metadata as metadata
from rebuild_metadata import localized_dictionaries

class DictionaryTitleTests(unittest.TestCase):
    def setUp(self):
        self.rows=[{'id':'dict:1','name':'Original','revision':2,'body':{'path':'keep.json','sha256':'unchanged'}}]
        self.titles={'schema_version':1,'dictionaries':{'dict:1':{'en':'English','zh-CN':'中文','ja':'日本語'}}}
    def test_only_metadata_and_revision_change(self):
        original=copy.deepcopy(self.rows);result=localized_dictionaries(self.rows,self.titles)
        self.assertEqual(result[0]['title_i18n'],self.titles['dictionaries']['dict:1'])
        self.assertEqual(result[0]['revision'],3);result[0].pop('title_i18n');result[0]['revision']=2
        self.assertEqual(result,self.rows);self.assertEqual(self.rows,original)
    def test_idempotent(self):
        result=localized_dictionaries(self.rows,self.titles)
        self.assertEqual(result,localized_dictionaries(result,self.titles))
    def test_missing_id_rejected(self):
        self.titles['dictionaries']={}
        with self.assertRaises(ValueError):localized_dictionaries(self.rows,self.titles)
    def test_missing_locale_rejected(self):
        del self.titles['dictionaries']['dict:1']['ja']
        with self.assertRaises(ValueError):localized_dictionaries(self.rows,self.titles)
    def test_invalid_title_rejected(self):
        self.titles['dictionaries']['dict:1']['ja']=' '
        with self.assertRaises(ValueError):localized_dictionaries(self.rows,self.titles)
    def test_real_catalog(self):
        rows=json.loads((ROOT/'catalogs/dictionaries.json').read_text());titles=json.loads((ROOT/'tools/dictionary_titles.json').read_text())
        self.assertEqual(len(rows),28);self.assertEqual(localized_dictionaries(rows,titles),rows)
        for row in rows:self.assertEqual(set(row['title_i18n']),{'en','zh-CN','ja'})

    def test_recover_runs_before_manifest_read(self):
        with patch.object(sys, 'argv', ['rebuild_metadata.py', '--recover']), \
             patch.object(metadata, 'recover_transaction') as recover, \
             patch.object(metadata, 'make_plan') as plan:
            metadata.main()
            recover.assert_called_once_with(metadata.ROOT)
            plan.assert_not_called()
    def test_pending_transaction_blocks_rebuild_before_read(self):
        with tempfile.TemporaryDirectory() as d, \
             patch.object(sys, 'argv', ['rebuild_metadata.py', '--write']), \
             patch.object(metadata, 'transaction_directory', return_value=pathlib.Path(d)), \
             patch.object(metadata, 'make_plan') as plan:
            with self.assertRaisesRegex(ValueError, 'run --recover first'): metadata.main()
            plan.assert_not_called()
