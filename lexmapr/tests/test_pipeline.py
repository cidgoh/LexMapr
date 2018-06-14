"""
TODO:
    * Make consistent with PEP8 style guidelines
        * Add appropriate docstring documentation
    * Abstract TestPipelineMethods into more classes
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

    def test_preProcess_04(self):
        """Test preProcess with all three characters in another order.

        TODO: This test fails due to a problem with preProcess.
            If'.' is to the right of ',', then it rstrip will not remove
            ',' first. Ask Gurinder is this fits the intended
            specification.
        """
        self.assertEqual(pipeline.preProcess("cow's, . "), "cow")

    def test_find_between_r_00(self):
        """Test find_between_r with first and last indices."""
        self.assertEqual(pipeline.find_between_r("^string$", "^", "$"),
            "string")

    def test_find_between_r_01(self):
        """Test find_between_r with non-first and last indices."""
        self.assertEqual(pipeline.find_between_r("^string$", "s", "$"),
            "tring")

    def test_find_between_r_02(self):
        """Test find_between_r with first and non-last indices."""
        self.assertEqual(pipeline.find_between_r("^string$", "^", "g"),
            "strin")

    def test_find_between_r_03(self):
        """Test find_between_r with non-first and non-last indices.
        """
        self.assertEqual(pipeline.find_between_r("^string$", "s", "g"),
            "trin")

    def test_find_between_r_04(self):
        """Test find_between_r with same first and last indices.
        """
        self.assertEqual(pipeline.find_between_r("^string$", "r", "r"),
            "")

    def test_find_between_r_05(self):
        """Test find_between_r with an invalid first parameter.
        """
        self.assertEqual(pipeline.find_between_r("^string$", "e", "g"),
            "")

    def test_find_between_r_06(self):
        """Test find_between_r with an invalid last parameter.
        """
        self.assertEqual(pipeline.find_between_r("^string$", "^", "q"),
            "")

    def test_find_between_r_07(self):
        """Test find_between_r with invalid first and last parameters.
        """
        self.assertEqual(pipeline.find_between_r("^string$", "e", "q"),
            "")

    def test_find_left_r_00(self):
        """Test find_left_r with first index.

        TODO: This test fails, but that is due to a problem with
            find_left_r. start-2 in the original function is -1, which
            means this currently returns s[0:-1]
        """
        self.assertEqual(pipeline.find_left_r("foo", "f", "o"), "")

    def test_find_left_r_01(self):
        """Test find_left_r with last index.

        TODO: This test fails, but that is due to a problem with
            find_left_r. start in the original function is 3, so
            calculating end throws a value error.
        """
        self.assertEqual(pipeline.find_left_r("bar", "r", "r"), "ba")

    def test_find_left_r_02(self):
        """Test find_left_r with non-first and non-last index.

        TODO: This test fails, but that is due to a problem with
            find_left_r. start-2 in the original function is 0, which
            means this currently returns s[0:0]
        """
        self.assertEqual(pipeline.find_left_r("bar", "a", "r"), "b")

    def test_addSuffix_00(self):
        """Test addSuffix with empty input and suffix strings."""
        self.assertEqual(pipeline.addSuffix("", ""), " ")

    def test_addSuffix_01(self):
        """Test addSuffix with empty input string."""
        self.assertEqual(pipeline.addSuffix("", "bar"), " bar")

    def test_addSuffix_02(self):
        """Test addSuffix with empty suffix string."""
        self.assertEqual(pipeline.addSuffix("foo", ""), "foo ")

    def test_addSuffix_03(self):
        """Test addSuffix with non-empty input and suffix strings."""
        self.assertEqual(pipeline.addSuffix("foo", "bar"), "foo bar")

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
