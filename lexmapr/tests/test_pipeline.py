"""
TODO:
    * Make consistent with PEP8 style guidelines
        * Add appropriate docstring documentation
"""

import sys
import os
import unittest
import tempfile

from lexmapr import pipeline

class TestPipelineMethods(unittest.TestCase):

    def test_is_number_true_00(self):
        """Test is_number with 0 value."""
        self.assertTrue(pipeline.is_number("0"))

    def test_is_number_true_01(self):
        """Test is_number with positive float value."""
        self.assertTrue(pipeline.is_number("1.5"))

    def test_is_number_true_02(self):
        """Test is_number with negative float value."""
        self.assertTrue(pipeline.is_number("-1.5"))

    def test_is_number_false_00(self):
        """Test is_number with empty string."""
        self.assertFalse(pipeline.is_number(""))
        
    def test_is_number_false_01(self):
        """Test is_number with non-empty string."""
        self.assertFalse(pipeline.is_number("foo"))

    def test_is_date_true_00(self):
        """Test is_date_true with year, month and day with dashes."""
        self.assertTrue(pipeline.is_date("2018-05-07"))

    def test_is_date_true_01(self):
        """Test is_date_true with American month, day and year."""
        self.assertTrue(pipeline.is_date("12/22/78"))

    def test_is_date_true_02(self):
        """Test is_date_true with textual month, day and year."""
        self.assertTrue(pipeline.is_date("July 1st, 2008"))

    def test_is_date_false_00(self):
        """Test is_date_true with empty string."""
        self.assertFalse(pipeline.is_date(""))

    def test_is_date_false_01(self):
        """Test is_date_true with non-empty string."""
        self.assertFalse(pipeline.is_date("foo"))

    def test_ngrams_00(self):
        """Test ngrams with empty string and n=1."""
        self.assertEqual(pipeline.ngrams("", 1), [[""]],)
        
    def test_ngrams_01(self):
        """Test ngrams with empty string and n=2."""
        self.assertEqual(pipeline.ngrams("", 1), [[""]],)
        
    def test_ngrams_02(self):
        """Test ngrams with two-word string and n=1."""
        self.assertEqual(pipeline.ngrams("hello world!", 1),
            [["hello"], ["world!"]])

    def test_ngrams_03(self):
        """Test ngrams with two-word string and n=2."""
        self.assertEqual(pipeline.ngrams("hello world!", 2),
            [["hello", "world!"]])

    def test_ngrams_04(self):
        """Test ngrams with three-word string and n=2."""
        self.assertEqual(pipeline.ngrams("why, hello world!", 2),
            [["why,", "hello"], ["hello", "world!"]])

    def test_preProcess_00(self):
        """Test preProcess on a string without a special character."""
        self.assertEqual(pipeline.preProcess("cow"), "cow")

    def test_preProcess_01(self):
        """Test preProcess on a string with a ''s'."""
        self.assertEqual(pipeline.preProcess("cow's"), "cow")

    def test_preProcess_02(self):
        """Test preProcess on a string with a ','."""
        self.assertEqual(pipeline.preProcess("cow, "), "cow")

    def test_preProcess_03(self):
        """Test preProcess on a string with a '.'."""
        self.assertEqual(pipeline.preProcess("cow. "), "cow")

    def test_preProcess_04(self):
        """Test preProcess on a string with a ''s' and ','."""
        self.assertEqual(pipeline.preProcess("cow's, "), "cow")

    def test_preProcess_04(self):
        """Test preProcess on a string with all three characters."""
        self.assertEqual(pipeline.preProcess("cow's. , "), "cow")

    def test_find_between_r_00(self):
        """Test find_between_r with first and last indices."""
        self.assertEqual(pipeline.find_between_r("^string$", '^', '$'),
            'string')

    def test_find_between_r_01(self):
        """Test find_between_r with non-first and last indices."""
        self.assertEqual(pipeline.find_between_r("^string$", 's', '$'),
            'tring')

    def test_find_between_r_02(self):
        """Test find_between_r with first and non-last indices."""
        self.assertEqual(pipeline.find_between_r("^string$", '^', 'g'),
            'strin')

    def test_find_between_r_03(self):
        """Test find_between_r with non-first and non-last indices."""
        self.assertEqual(pipeline.find_between_r("^string$", 's', 'g'),
            'trin')

class TestPipeline(unittest.TestCase):
    def test_pipeline_input_small_simple_format_full(self):
        infile_path = os.path.join(os.path.dirname(__file__),
            'input/small_simple.csv')
        outfile_path = tempfile.mkstemp()[1]
        correctfile_path = os.path.join(os.path.dirname(__file__),
            'output/small_simple.tsv')
        pipeline.run(type('',(object,),{"input_file": infile_path,
            "output": outfile_path, "format": "full"})())
        with open(outfile_path, 'r') as outfile:
            outfile_contents = outfile.read()
        with open(correctfile_path, 'r') as correctfile:
            correctfile_contents = correctfile.read()
        self.assertMultiLineEqual(outfile_contents, correctfile_contents)

if __name__ == '__main__':
    unittest.main()
