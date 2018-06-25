"""
TODO:
    * Make consistent with PEP8 style guidelines
        * Add appropriate docstring documentation
    * Refactor test suites as needed, after refactoring pipeline.py
        * Add new tests as needed for greater path/branch coverage
            * There are many internals within lexmapr.pipeline.run that
                are difficult to test, due to the lack of modularity
                * For now, we will take a black box approach for the
                    entirety of lexmapr.pipeline.run, but revisit with
                    more in-depth testing later
        * Break test classes up into a pattern more consistent with
            end-result of pipeline.py
"""

import sys
import os
import unittest
import tempfile

from lexmapr import pipeline

class TestPipelineMethods(unittest.TestCase):
    """Unit test suite for pipeline methods outside pipeline.run.

    Subclass of unittest.TestCase.

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
        * test_punctuationTreatment()
        * test_retainedPhrase()
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
        # 3-char input string and n=1
        self.assertCountEqual(list(pipeline.combi("bar", 1)),
            [("b",), ("a",), ("r",)])
        # 3-char input string and n=2
        self.assertCountEqual(list(pipeline.combi("bar", 2)),
            [("b", "a"), ("a", "r"), ("b", "r")])
        # 3-char input string and n=3
        self.assertCountEqual(list(pipeline.combi("bar", 3)),
            [("b", "a", "r")])

    def test_punctuationTreatment(self):
        """Tests punctuationTreatment.

        TODO:
            * The tests follow the specifications, but some of expected
                values may be unintended bugs. Consult with Gurinder.
            * Potential bugs:
                * Three spaces between words, if there is a token
                    consisting of a single punctuation mark between
                    the words
                    * e.g., foo;bar -> ["foo", ";", "bar] -> foo   bar
                * Spaces at the beginning and/or end of the the
                    returned string, if the input string begins and/or
                    ends with a punctuation mark
                    * e.g., _foo_ -> ["_foo_"] -> " foo "
        """
        # Punctuation list used in pipeline
        punctuationList = ["-", "_", "(", ")", ";", "/", ":", "%"]
        # Empty input string
        self.assertEqual(
            pipeline.punctuationTreatment("", punctuationList),
            "")
        # Single-token input string with no punctuation
        self.assertEqual(
            pipeline.punctuationTreatment("foo", punctuationList),
            "foo")
        # Multi-token input string with no punctuation
        self.assertEqual(
            pipeline.punctuationTreatment("foo bar", punctuationList),
            "foo bar")
        # Single-token input string with punctuation
        self.assertEqual(
            pipeline.punctuationTreatment("_foo-bar_", punctuationList),
            " foo bar ")
        # Multi-token input string with punctuation
        self.assertEqual(
            pipeline.punctuationTreatment("_foo;ba r_", punctuationList),
            " foo   ba r ")
        # Multi-token input string with number, date and punctuation
        self.assertEqual(
            pipeline.punctuationTreatment("a-b 12/22/78 -1", punctuationList),
            "a b 12/22/78 -1")

    def test_retainedPhrase(self):
        """Tests retainedPhrase.

        TODO:
            * Cannot test empty term list, because retainedPhrase
                assumes the term list will not be empty, and
                consequentially throws an IndexError
            * If retainedPhrase is changed in the future to a more
                independent function, test empty term list
            * The tests follow the specifications, but some of expected
                values may be unintended bugs. Consult with Gurinder.
            * Potential bugs:
                * If the last key-value pair in an inputted termlist is
                    in the returned set, the value will have an single
                    quotation mark at the end
                    * e.g., "{'foo:bar', 'hello:world'}"
                        -> set(["foo:bar", "hello:world'"])
                    * This is because pipeline.retainedPhrase
                        eliminates "'," from values--not "'"
                * Potential to return no key-value pairs
                    * This happens if a compound key is a subset of
                        another compound key, but with no differing
                        words
                    * e.g., "{'foo bar:bar', 'foo bar bar:bar'}"
                        -> []
                * If no key-value pairs are to be included in the
                    return value, an empty list--not set--is
                    returned
        """
        # Single-term list
        self.assertSetEqual(
            pipeline.retainedPhrase("{'foo:bar'}"),
            set(["foo:bar'"]))
        # Multi-term list
        self.assertSetEqual(
            pipeline.retainedPhrase("{'foo:bar', 'hello:world'}"),
            set(["foo:bar", "hello:world'"]))
        # Multi-term list with "="
        self.assertSetEqual(
            pipeline.retainedPhrase("{'foo:b=ar', 'he=llo:world'}"),
            set(["foo:b=ar", "he,llo:world'"]))
        # Key substring of a key
        self.assertSetEqual(
            pipeline.retainedPhrase("{'foo:bar', 'foofoo:bar'}"),
            set(["foofoo:bar'"]))
        # Key substring of a compound key (multi-word)
        self.assertSetEqual(
            pipeline.retainedPhrase("{'foo:bar', 'foo bar:bar'}"),
            set(["foo bar:bar'"]))
        # Compound key substring of a compound key
        self.assertSetEqual(
            pipeline.retainedPhrase("{'foo bar hello:world', 'foo bar:bar'}"),
            set(["foo bar hello:world"]))
        # Compound key overlapping, but not substring of a compound key
        self.assertSetEqual(
            pipeline.retainedPhrase("{'foo hello:world', 'foo bar:bar'}"),
            set(["foo hello:world", "foo bar:bar'"]))
        # Compound key substring of a compound key (no differing words)
        self.assertEqual(
            pipeline.retainedPhrase("{'foo bar:bar', 'foo bar bar:bar'}"),
            [])
        # Identical keys, but different values
        self.assertEqual(
            pipeline.retainedPhrase("{'foo:bar', 'foo:foo'}"),
            set(["foo:bar", "foo:foo'"]))
        self.assertEqual(
            pipeline.retainedPhrase("{'foo bar:bar', 'foo bar:foo'}"),
            set(["foo bar:bar", "foo bar:foo'"]))

class TestPipeline(unittest.TestCase):
    """Unit test suite for pipeline.run.

    Subclass of unittest.TestCase.

    This test suite takes a black box approach, by using input and
    expected output files, and examining the multiple ways an output
    file can be written to.

    Public methods:
        * test_pipeline_with_files

    Class variables:
        * test_files <class "dict">
            * key <class "str">
            * val <class "str">

    TODO:
        * If multiple assertions fail, show all failing assertions--not
            just one
        * Utilize parallel programming to speed up these unit tests
        * Potential bugs:
            * args.format should be optional, but several calls are
                made to args.format in pipeline.run
                * Throws an attribute error without format argument
                * We are currently using "not full" to test
                    pipeline.run without "full" format
            * If args.format != full, the values for matched_term and
                all_matched_terms_with_resource_ids are outputted, but
                there are no headers for these values in the first row
            * "Change Case and Spelling Correction Treatment" not
                possible
                * Tokens are always converted to lowercase format
                    before spelling corrections
    """

    # Dictionary containing the names of input and expected output
    # file test cases without extensions. The keys are expected
    # output files, and the values are a list with two values: the
    # input file, and format value. It is assumed input and output
    # files have .csv and .tsv extensions, and are in
    # ./lexmapr/tests/input and ./lexmapr/tests/input respectively.
    # All future test cases must be added here.
    test_files = {
        # Empty file without "full" format argument
        "empty_not_full": ["empty", "not full"],
        # Empty file with "full" format argument
        "empty": ["empty", "full"],
        # Non-empty file without "full" format argument
        "small_simple_not_full": ["small_simple", "not full"],
        # Non-empty file with "full" format argument
        "small_simple": ["small_simple", "full"],
        # Some rows requires punctuation treatment
        "test_punctuation": ["test_punctuation", "full"],
        # Some rows require extra inner spaces to be removed--
        # some due to punctuation treatment.
        "test_extra_inner_spaces": ["test_extra_inner_spaces", "full"],
        # Varying number of tokens per row
        "test_tokenization": ["test_tokenization", "full"],
        # Some tokens require preprocessing
        "test_preprocessing": ["test_preprocessing", "full"],
        # Some tokens require inflection treatment
        "test_pluralization": ["test_pluralization", "full"],
        # Some tokens require spelling corrections
        "test_spelling_corrections": ["test_spelling_corrections", "full"]
    }

    def test_pipeline_with_files(self):
        """Compares actual pipeline.run outputs to expected outputs.

        For each expected output and input pair in self.test_files, we
        compare the contents of the actual output of pipeline.run (when
        given input) to the contents of the expected output.
        """
        # Iterate over all expected outputs
        for expected_output in self.test_files:
            # Relative path of expected output file
            expected_output_path = "output/" + expected_output + ".tsv"
            # Relative path of input file
            input = self.test_files[expected_output][0]
            input_path = "input/" + input + ".csv"
            # Format value
            format = self.test_files[expected_output][1]
            # Temporary file path to store actual output of input file
            actual_output_path = tempfile.mkstemp()[1]
            # Run pipeline.run using input_path and actual_output_path
            pipeline.run(type('',(object,),{"input_file": input_path,
                "output": actual_output_path, "format": format})())
            # Get actual_output_path contents
            with open(actual_output_path, 'r') as actual_output_file:
                actual_output_contents = actual_output_file.read()
            # Get expected_output_path contents
            with open(expected_output_path, 'r') as expected_output_file:
                expected_output_contents = expected_output_file.read()
            # TODO: remove these print statements later
            print(expected_output_contents)
            print(actual_output_contents)
            # Compare expected output with actual output
            self.assertMultiLineEqual(expected_output_contents,
                actual_output_contents)

if __name__ == '__main__':
    unittest.main()
