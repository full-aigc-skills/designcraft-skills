"""Research-source inventory stays distinct from the installed native catalog."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('research_inventory',ROOT/'scripts/check_research_inventory.py')
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class ResearchInventoryContract(unittest.TestCase):
    def source(self, root):
        (root/'apps/designcraft-cli/src').mkdir(parents=True)
        (root/'crates/engine/src/cmd').mkdir(parents=True)
        (root/'apps/designcraft-cli/src/main.rs').write_text('''fn main() { match args.first() { Some("run") => {}, Some("commands") => {}, Some("--version" | "-V" | "version") => {}, _ => {} } }\nfn report() {}''')
        (root/'crates/engine/src/cmd/mod.rs').write_text('''mod file;\npub mod layout;\n''')
        (root/'crates/engine/src/cmd/file.rs').write_text('''cmd!("file.new", "New", [], None, "{}", always, run);''')
        (root/'crates/engine/src/cmd/layout.rs').write_text('''cmd!(query "layout.inspect", "Inspect", [], None, "{}", always, run);''')

    def test_inventory_records_static_ids_and_source_hashes_without_native_claims(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.source(root)
            inventory=MODULE.build_inventory(root,'a'*40)
            self.assertEqual(inventory['classification'],'RESEARCH_SOURCE_ONLY')
            self.assertEqual(inventory['nativeCatalogStatus'],'NOT_RUN')
            self.assertEqual(inventory['cliSubcommands'],['run','commands','--version','-V','version'])
            self.assertEqual([item['id'] for item in inventory['commands']],['file.new','layout.inspect'])
            self.assertTrue(all(item['validationStatus']=='RESEARCH_SOURCE_ONLY' for item in inventory['commands']))
            self.assertTrue(all(len(item['sha256'])==64 for item in inventory['sourceFiles']))
            self.assertNotIn('ownerSkill',inventory['commands'][0])

    def test_inventory_verification_rejects_changed_research_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.source(root)
            pinned=MODULE.build_inventory(root,'a'*40)
            self.assertTrue(MODULE.inventory_matches(pinned,root,'a'*40))
            (root/'crates/engine/src/cmd/file.rs').write_text('cmd!("file.changed", "New", [], None, "{}", always, run);')
            self.assertFalse(MODULE.inventory_matches(pinned,root,'a'*40))

if __name__=='__main__':unittest.main()
