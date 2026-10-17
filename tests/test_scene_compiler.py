import importlib.util
from pathlib import Path
import unittest

P=Path(__file__).resolve().parents[1]/'skills/designcraft-scenario-playbooks/scripts/write_script.py'
spec=importlib.util.spec_from_file_location('design_script',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class ReferenceTests(unittest.TestCase):
    def test_existing_file_reindexes_return_reference(self):
        r={'steps':[{'command':'file.new','params':{},'newDocumentOnly':True},{'command':'frame.create','params':{},'capture':'body'},{'command':'story.get','params':{'story':{'$ref':'body.story'}}}]}
        fresh,_=m.compile_steps(r);existing,_=m.compile_steps(r,True)
        self.assertEqual(fresh[-1]['params']['story'],'$1.story');self.assertEqual(existing[-1]['params']['story'],'$0.story')
        self.assertEqual(existing[0]['command'],'frame.create')
    def test_forward_reference_cannot_be_sent(self):
        with self.assertRaisesRegex(ValueError,'forward'):m.compile_steps({'steps':[{'command':'story.get','params':{'story':{'$ref':'missing.story'}}}]})
    def test_table_uses_actual_returned_table_field(self):
        steps,_=m.compile_steps({'steps':[{'command':'table.convertFromText','params':{},'capture':'table'},{'command':'table.get','params':{'table':{'$ref':'table.table'}}}]})
        self.assertEqual(steps[-1]['params']['table'],'$0.table')


if __name__=='__main__':unittest.main()
