"""胸牌数据输入必须在写工程前完成核对。"""
import importlib.util
from pathlib import Path
import unittest
s=importlib.util.spec_from_file_location('badges',Path(__file__).resolve().parents[1]/'skills/designcraft-data-merge-badges/scripts/build_badges.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class BadgeInputTests(unittest.TestCase):
    def test_unicode_and_quoted_comma_preserved(self):
        self.assertEqual(m.parse_rows('\ufeffName,Role\n"Guest, A",演讲者\n'),[{'Name':'Guest, A','Role':'演讲者'}])
    def test_missing_duplicate_empty_and_ragged_rejected(self):
        for text in ['Name\nA\n','Name,Name,Role\nA,B,Speaker\n','Name,Role\n','Name,Role\n,Speaker\n','Name,Role\nA\n','Name,Role\nA,Speaker,extra\n']:
            with self.subTest(text=text),self.assertRaises(ValueError):m.parse_rows(text)
if __name__=='__main__':unittest.main()
