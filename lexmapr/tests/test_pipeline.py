import sys
import os
import unittest
import tempfile

import lexmapr.pipeline

class TestPipelineMethods(unittest.TestCase):

    def test_is_number_true_00(self):
        self.assertTrue(lexmapr.pipeline.is_number("0"))

    def test_is_number_false_00(self):
        self.assertFalse(lexmapr.pipeline.is_number(""))
        
    def test_is_number_false_01(self):
        self.assertFalse(lexmapr.pipeline.is_number("foo"))

    def test_is_date_true_00(self):
        self.assertTrue(lexmapr.pipeline.is_date("2018-05-07"))

    def test_is_date_false_00(self):
        self.assertFalse(lexmapr.pipeline.is_date(""))

    def test_ngrams_00(self):
        self.assertEqual(lexmapr.pipeline.ngrams("", 1), [['']],)
        
    def test_ngrams_01(self):
        self.assertEqual(lexmapr.pipeline.ngrams("hello world", 1), [['hello'], ['world']])

    def test_ngrams_02(self):
        self.assertEqual(lexmapr.pipeline.ngrams("hello world", 2), [['hello', 'world']])

    def test_preProcess_00(self):
        self.assertEqual(lexmapr.pipeline.preProcess("cow"), "cow")

    def test_preProcess_01(self):
        self.assertEqual(lexmapr.pipeline.preProcess("cow's"), 'cow')

    def test_preProcess_02(self):
        self.assertEqual(lexmapr.pipeline.preProcess("cow, "), 'cow')

    def test_preProcess_03(self):
        self.assertEqual(lexmapr.pipeline.preProcess("cow. "), 'cow')

    def test_find_between_r_00(self):
        self.assertEqual(lexmapr.pipeline.find_between_r("^string$", '^', '$'), 'string')

class TestPipeline(unittest.TestCase):
    def test_pipeline_input_small_simple_format_full(self):
        infile_path = os.path.join(os.path.dirname(__file__), 'input/small_simple.csv')
        outfile_path = tempfile.mkstemp()[1]
        correctfile_path = os.path.join(os.path.dirname(__file__), 'output/small_simple.tsv')
        lexmapr.pipeline.run(type('',(object,),{"input_file": infile_path, "output": outfile_path, "format": "full"})())
        with open(outfile_path, 'r') as outfile:
            outfile_contents = outfile.read()
        with open(correctfile_path, 'r') as correctfile:
            correctfile_contents = correctfile.read()
        self.assertMultiLineEqual(outfile_contents, correctfile_contents)

if __name__ == '__main__':
    unittest.main()
