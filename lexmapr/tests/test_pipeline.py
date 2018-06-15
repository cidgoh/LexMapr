"""
TODO:
    * Make consistent with PEP8 style guidelines
        * Add appropriate docstring documentation
    * Refactor test suites as needed, after refactoring pipeline.py
        * Likely will not need new tests, but may want to break test
            classes up into a pattern more consistent with end-result
            of pipeline.py
"""

import sys
import os
import unittest
import tempfile

from lexmapr import pipeline

class TestPipelineMethods(unittest.TestCase):
    """Unit test suite for pipeline methods outside pipeline.run.
    
    Public methods:
        * test_is_number()
        * test_is_date()
        * test_ngrams()
        * test_preProcess
        * test_find_between_r()
        * test_find_left_r()
        * test_addSuffix()
        * test_allPermutations()
        * test_combi()
    """

    def test_is_number(self):
        """Tests is_number."""
        # 0 value
        self.assertTrue(pipeline.is_number("0"))
        # Positive float value
        self.assertTrue(pipeline.is_number("1.5"))
        # Negative float value
        self.assertTrue(pipeline.is_number("-1.5"))
        # Empty string
        self.assertFalse(pipeline.is_number(""))
        # Non-empty string
        self.assertFalse(pipeline.is_number("foo"))

    def test_is_date(self):
        """Tests is_date_true."""
        # Year, month and day with dashes
        self.assertTrue(pipeline.is_date("2018-05-07"))
        # American month, day and year
        self.assertTrue(pipeline.is_date("12/22/78"))
        # Textual month, day and year
        self.assertTrue(pipeline.is_date("July 1st, 2008"))
        # Empty string
        self.assertFalse(pipeline.is_date(""))
        # Non-empty string
        self.assertFalse(pipeline.is_date("foo"))

    def test_ngrams(self):
        """Tests ngrams."""
        # Empty string and n = 1
        self.assertEqual(pipeline.ngrams("", 1), [[""]],)
        # Empty string and n=2
        self.assertEqual(pipeline.ngrams("", 1), [[""]],)
        # Two-word string and n=1
        self.assertEqual(pipeline.ngrams("hello world!", 1),
            [["hello"], ["world!"]])
        # Two-word string and n=2
        self.assertEqual(pipeline.ngrams("hello world!", 2),
            [["hello", "world!"]])
        # Three-word string and n=2
        self.assertEqual(pipeline.ngrams("why, hello world!", 2),
            [["why,", "hello"], ["hello", "world!"]])

    def test_preProcess(self):
        """Tests preProcess.
        
        TODO:
            * Some of these tests fail. This may be due to an error
                with preProcess. Consult with Gurinder.
            * Problems with string tokens containing multiple
                instances of:
                * the same character
                * different characters (if they do not appear left to
                    right in the order of the if-statements in
                    preProcess)
        """
        # No special characters
        self.assertEqual(pipeline.preProcess("cow"), "cow")
        # One "'s"
        self.assertEqual(pipeline.preProcess("cow's"), "cow")
        # Two "'s"
        self.assertEqual(pipeline.preProcess("cow's and chicken's"),
            "cow and chicken")
        # One ", "
        self.assertEqual(pipeline.preProcess("cow, "), "cow")
        # Two ", "
        self.assertEqual(pipeline.preProcess("cow, horse, and goat"),
            "cow horse and goat")
        # One "."
        self.assertEqual(pipeline.preProcess("cow. "), "cow")
        # Two "."
        self.assertEqual(pipeline.preProcess("cow. horse. "), "cow horse")
        # "'s" and ","
        self.assertEqual(pipeline.preProcess("cow's, "), "cow")
        # "'", "." and ","
        self.assertEqual(pipeline.preProcess("cow's. , "), "cow")
        # "'", "," and "."
        self.assertEqual(pipeline.preProcess("cow's, . "), "cow")

    def test_find_between_r(self):
        """Tests find_between_r."""
        # Between first and last indices
        self.assertEqual(pipeline.find_between_r("^string$", "^", "$"),
            "string")
        # Between non-first and last indices
        self.assertEqual(pipeline.find_between_r("^string$", "s", "$"),
            "tring")
        # Between first and non-last indices
        self.assertEqual(pipeline.find_between_r("^string$", "^", "g"),
            "strin")
        # Between non-first and non-last indices
        self.assertEqual(pipeline.find_between_r("^string$", "s", "g"),
            "trin")
        # Same character for first and last parameters
        self.assertEqual(pipeline.find_between_r("^string$", "r", "r"),
            "")
        # Invalid first parameter
        self.assertEqual(pipeline.find_between_r("^string$", "e", "g"),
            "")
        # Invalid last parameter
        self.assertEqual(pipeline.find_between_r("^string$", "^", "q"),
            "")
        # Invalid first and last parameters
        self.assertEqual(pipeline.find_between_r("^string$", "e", "q"),
            "")

    def test_find_left_r(self):
        """Tests find_left_r.

        TODO:
            * Some of these tests fail. This may be due to an error
                with preProcess. Consult with Gurinder.
            * Problems with preProcess:
                * Incorrect calculation of start
                    * 1 is added to index
                * Unnecessary calculation of end
                    * Incorrect calculation of start sometimes causes
                        ValueError to be thrown
                * Incorrect range is returned
                    * Partly due to incorrect calculation of start, but
                        also due to us returning a substring between
                        the 0 and start-2 indices
        """
        # Left of first index
        self.assertEqual(pipeline.find_left_r("foo", "f", "o"), "")
        # Left of last index
        self.assertEqual(pipeline.find_left_r("bar", "r", "r"), "ba")
        # Left of non-first and non-last index
        self.assertEqual(pipeline.find_left_r("bar", "a", "r"), "b")

    def test_addSuffix(self):
        """Tests addSuffix."""
        # Empty input and suffix strings
        self.assertEqual(pipeline.addSuffix("", ""), " ")
        # Empty input string
        self.assertEqual(pipeline.addSuffix("", "bar"), " bar")
        # Empty suffix string
        self.assertEqual(pipeline.addSuffix("foo", ""), "foo ")
        # Non-empty input and suffix strings
        self.assertEqual(pipeline.addSuffix("foo", "bar"), "foo bar")

    def test_allPermutations(self):
        """Tests allPermutations."""
        # Empty input string
        self.assertSetEqual(pipeline.allPermutations(""), set([()]))
        # 1-gram input string
        self.assertSetEqual(pipeline.allPermutations("a"), set([("a",)]))
        # 2-gram input string
        self.assertSetEqual(pipeline.allPermutations("a b"),
            set([("a", "b"), ("b", "a")]))
        # 4-gram input string
        self.assertEqual(len(pipeline.allPermutations("a b c d")), 24)
    
    def test_combi(self):
        """Tests combi."""
        # Empty input string and n=1
        self.assertCountEqual(list(pipeline.combi("", 1)), [])
        # Empty input string and n=2
        self.assertCountEqual(list(pipeline.combi("", 2)), [])
        # 1-char input string and n=1
        self.assertCountEqual(list(pipeline.combi("a", 1)), [("a",)])
        # 1-char input string and n=2
        self.assertCountEqual(list(pipeline.combi("a", 2)), [])
        # 3-char input string with unique letters and n=1
        self.assertCountEqual(list(pipeline.combi("bar", 1)),
            [("b",), ("a",), ("r",)])
        # 3-char input string and n=2
        self.assertCountEqual(list(pipeline.combi("bar", 2)),
            [("b", "a"), ("a", "r"), ("b", "r")])
        # 3-char input string and n=3
        self.assertCountEqual(list(pipeline.combi("bar", 3)),
            [("b", "a", "r")])

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
