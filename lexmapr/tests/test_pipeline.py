#!/usr/bin/env python
"""Tests functionality of lexmapr.pipeline.

This script uses unit testing to test the helper and run functions
found in lexmapr.pipeline. It is currently only compatible with
Python 3. To run these tests, enter the following command line
arguments from the root directory:

    $ PYTHONHASHSEED=0 python3 lexmapr/tests/test_pipeline.py

TODO:
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

import argparse
import json
import os
import tempfile
import unittest

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
            * The commented-out tests fail due to an error with
                preProcess. Based on the specifiction of preProcess,
                the commented-out tests should pass, and the
                uncommented-out tests should fail. For the purposes of
                refactoring, where we must retain original
                functionality of pipeline.py, this is currently
                sufficient.
            * Problems with string tokens containing multiple
                instances of:
                * the same character
                * different characters (if they do not appear left to
                    right in the order of the if-statements in
                    preProcess)
        """
        # No special characters
        self.assertEqual(pipeline.preprocess("cow"), "cow")
        # One "'s"
        self.assertEqual(pipeline.preprocess("cow's"), "cow")
        # Two "'s"
        self.assertEqual(pipeline.preprocess("cow's and chicken's"),
            "cow and chicken")
        # One ", "
        self.assertEqual(pipeline.preprocess("cow, "), "cow")
        # Two ", "
        # self.assertEqual(pipeline.preProcess("cow, horse, and goat"),
        #     "cow horse and goat")
        self.assertEqual(pipeline.preprocess("cow, horse, and goat"),
            "cow, horse, and goat")
        # One "."
        self.assertEqual(pipeline.preprocess("cow. "), "cow")
        # Two "."
        self.assertEqual(pipeline.preprocess("cow. horse. "), "cow. horse")
        # "'s" and ","
        self.assertEqual(pipeline.preprocess("cow's, "), "cow")
        # "'", "." and ","
        self.assertEqual(pipeline.preprocess("cow's. , "), "cow")
        # "'", "," and "."
        self.assertEqual(pipeline.preprocess("cow's, . "), "cow,")

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
            * The commented-out tests fail due to an error with
                find_left_r. Based on the specifiction of find_left_r,
                the commented-out tests should pass, and the
                uncommented-out tests should fail. For the purposes of
                refactoring, where we must retain original
                functionality of pipeline.py, this is currently
                sufficient.
            * Problems with find_left_r:
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
        # self.assertEqual(pipeline.find_left_r("foo", "f", "o"), "")
        self.assertEqual(pipeline.find_left_r("foo", "f", "o"), "fo")
        # Left of last index
        # self.assertEqual(pipeline.find_left_r("bar", "r", "r"), "ba")
        self.assertEqual(pipeline.find_left_r("bar", "r", "r"), "")
        # Left of non-first and non-last index
        # self.assertEqual(pipeline.find_left_r("bar", "a", "r"), "b")
        self.assertEqual(pipeline.find_left_r("bar", "a", "r"), "")

    def test_allPermutations(self):
        """Tests allPermutations."""
        # Empty input string
        self.assertSetEqual(pipeline.all_permutations(""), set([()]))
        # 1-gram input string
        self.assertSetEqual(pipeline.all_permutations("a"), set([("a",)]))
        # 2-gram input string
        self.assertSetEqual(pipeline.all_permutations("a b"),
            set([("a", "b"), ("b", "a")]))
        # 4-gram input string
        self.assertEqual(len(pipeline.all_permutations("a b c d")), 24)
    
    def test_combi(self):
        """Tests combi."""
        # Empty input string and n=1
        self.assertSetEqual(set(pipeline.combi("", 1)), set([]))
        # Empty input string and n=2
        self.assertSetEqual(set(pipeline.combi("", 2)), set([]))
        # 1-char input string and n=1
        self.assertSetEqual(set(pipeline.combi("a", 1)), set([("a",)]))
        # 1-char input string and n=2
        self.assertSetEqual(set(pipeline.combi("a", 2)), set([]))
        # 3-char input string and n=1
        self.assertSetEqual(set(pipeline.combi("bar", 1)),
            set([("b",), ("a",), ("r",)]))
        # 3-char input string and n=2
        self.assertSetEqual(set(pipeline.combi("bar", 2)),
            set([("b", "a"), ("a", "r"), ("b", "r")]))
        # 3-char input string and n=3
        self.assertSetEqual(set(pipeline.combi("bar", 3)),
            set([("b", "a", "r")]))

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
            pipeline.retainedPhrase(['foo:bar']),
            set(["foo:bar"]))
        # Multi-term list
        self.assertSetEqual(
            pipeline.retainedPhrase(['foo:bar', 'hello:world']),
            set(["foo:bar", "hello:world"]))
        # Multi-term list with "="
        self.assertSetEqual(
            pipeline.retainedPhrase(['foo:b=ar', 'he=llo:world']),
            set(["foo:b=ar", "he,llo:world"]))
        # Key substring of a key
        self.assertSetEqual(
            pipeline.retainedPhrase(['foo:bar', 'foofoo:bar']),
            set(["foofoo:bar"]))
        # Key substring of a compound key (multi-word)
        self.assertSetEqual(
            pipeline.retainedPhrase(['foo:bar', 'foo bar:bar']),
            set(["foo bar:bar"]))
        # Compound key substring of a compound key
        self.assertSetEqual(
            pipeline.retainedPhrase(['foo bar hello:world', 'foo bar:bar']),
            set(["foo bar hello:world"]))
        # Compound key overlapping, but not substring of a compound key
        self.assertSetEqual(
            pipeline.retainedPhrase(['foo hello:world', 'foo bar:bar']),
            set(["foo hello:world", "foo bar:bar"]))
        # Compound key substring of a compound key (no differing words)
        self.assertEqual(
            pipeline.retainedPhrase(['foo bar:bar', 'foo bar bar:bar']),
            [])
        # Identical keys, but different values
        self.assertEqual(
            pipeline.retainedPhrase(['foo:bar', 'foo:foo']),
            set(["foo:bar", "foo:foo"]))
        self.assertEqual(
            pipeline.retainedPhrase(['foo bar:bar', 'foo bar:foo']),
            set(["foo bar:bar", "foo bar:foo"]))

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
        * Utilize parallel programming to speed up these unit tests
        * Cannot figure out a way to cause the following:
            * "Cleaned Sample and Abbreviation-Acronym Treatment"
            * "Cleaned Sample and Non English Language Words Treatment"
        * Test component matching
            * Skipped this currently, because it has been somewhat
                indirectly tested in other tests, and because the
                code is difficult to test
            * Upon refactoring the code into a more elegant format,
                we will write tests for component matching
        * Potential bugs:
            * args.format should be optional, but several calls are
                made to args.format in pipeline.run
                * Throws an attribute error without format argument
                * We are currently using "not full" to test
                    pipeline.run without "full" format
            * If args.format != full, the values for matched_term and
                all_matched_terms_with_resource_ids are outputted, but
                there are no headers for these values in the first row
            * change of case in input data not recorded if the cleaned
                sample is direct matched
                * e.g.,
                    * Chicken Pie -> "Change of Case in Input Data"
                    * Chicken Pie's -> "A Direct Match with Cleaned
                        Sample"
            * Full-term matches made with a cleaned sample using a
                change-of-case or permutations should have some record
                of the comparison being made with a cleaned sample.
            * Cleaned phrases undergo punctuation treatment, but
                resourceTermsDict and resourceRevisedTermsDict do not,
                which means that it is impossible to match cleaned
                samples to terms they should be matched to
                * e.g.,
                    * cleaned sample: straight chain saturated fatty
                        acid
                    * term in resourceTermsDict and
                        resourceRevisedTermsDict: straight-chain
                        saturated fatty acid
    """
    
    maxDiff = None

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
        "test_spelling_corrections": ["test_spelling_corrections", "full"],
        # Some tokens require abbreviation or acronym translation
        "test_abbreviations": ["test_abbreviations", "full"],
        # Some tokens require non-english to english translation
        # TODO: We must add capitalized non-english words to
        #       ../resources/NefLex, and then makes tests for potential
        #       translations from nonEnglishWordsLowerDict.
        "test_non_english_words": ["test_non_english_words", "full"],
        # Some tokens are stop-words
        "test_stop_word_handling": ["test_stop_word_handling", "full"],
        # Varying paths of candidate phrase creations
        "test_candidate_phrase": ["test_candidate_phrase", "full"],
        # Some Sample_Id's are missing a sample
        "test_sample_id_only": ["test_sample_id_only", "full"],
        # Some samples are a full-term direct match
        "test_full_term_dir_match": ["test_full_term_dir_match", "full"],
        # Some samples are a full-term match, provided a change-of-case
        # in input or resource data.
        "test_full_term_coc_match": ["test_full_term_coc_match", "full"],
        # Some samples are a full-term match, if permutated
        "test_full_term_perm_match": ["test_full_term_perm_match", "full"],
        # Some samples are a full-term match, if given an added suffix
        "test_full_term_sfx_match": ["test_full_term_sfx_match", "full"],
        # Some samples are a full-term match, based on a
        # Wikipedia-based collocation resource.
        "test_full_term_wiki_match": ["test_full_term_wiki_match", "full"],
    }

    def test_pipeline_with_files(self):
        """Compares actual pipeline.run outputs to expected outputs.

        For each expected output and input pair in self.test_files, we
        compare the contents of the actual output of pipeline.run (when
        given input) to the contents of the expected output. This
        function raises a single assertion error that lists all failed
        assertions.
        """
        # This will be a multi-line string containing all expected
        # outputs that are not equal to their actual outputs.
        failures = []
        # Iterate over all expected outputs
        for expected_output in self.test_files:
            # Path of expected output file
            expected_output_path = os.path.join(os.path.dirname(__file__),
                "output/" + expected_output + ".tsv")
            # Path of input file
            input = self.test_files[expected_output][0]
            input_path = os.path.join(os.path.dirname(__file__),
                "input/" + input + ".csv")
            # Format value
            format = self.test_files[expected_output][1]
            # Temporary file path to store actual output of input file
            actual_output_path = tempfile.mkstemp()[1]
            # Run pipeline.run using input_path and actual_output_path
            pipeline.run(type("",(object,),{"input_file": input_path,
                "output": actual_output_path, "format": format, "web": None})())
            # Get actual_output_path contents
            with open(actual_output_path, "r") as actual_output_file:
                actual_output_contents = actual_output_file.read()
            # Get expected_output_path contents
            with open(expected_output_path, "r") as expected_output_file:
                expected_output_contents = expected_output_file.read()
            try:
                # Compare expected output with actual output
                self.assertMultiLineEqual(expected_output_contents, actual_output_contents)
            except AssertionError as e:
                print(e)
                failures += [expected_output]
        if failures:
            print("Failed files:")
            for failure in failures:
                print(failure)
            raise AssertionError


class TestOntologyMapping(unittest.TestCase):
    """...

    **TODO:**

    * convert each fetched json file into an "ontology table" json
      * done whenever web ontology is fetched
    * wrap ontology fetching mechanism in method
    * eliminate fetched_ontologies folder
    """

    @classmethod
    def setUpClass(cls):
        # Change directory to same as pipeline
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(os.path.abspath(".."))
        # Commonly used values
        cls.small_simple_path = "tests/input/small_simple.csv"
        cls.pizza_url = "https://protege.stanford.edu/ontologies/pizza/pizza.owl"
        cls.pizza_DomainThing_iri = "http://www.co-ode.org/ontologies/pizza/pizza.owl#DomainConcept"

    def setUp(self):
        # Un-cache pizza ontology if it exists
        if os.path.exists(os.path.abspath("fetched_ontologies/pizza.json")):
            os.remove(os.path.abspath("fetched_ontologies/pizza.json"))
            os.remove(os.path.abspath("fetched_ontologies/pizza.tsv"))

    def tearDown(self):
        # Un-cache pizza ontology
        os.remove(os.path.abspath("fetched_ontologies/pizza.json"))
        os.remove(os.path.abspath("fetched_ontologies/pizza.tsv"))
        os.remove(os.path.abspath("ontology_lookup_tables/pizza.json"))

    @staticmethod
    def run_pipeline_with_args(input_file, web=None, root=None):
        """Run pipeline with some default arguments.

        input_file must be specified. web and root can be specified,
        but otherwise are ``None`` by default.
        """
        pipeline.run(argparse.Namespace(input_file=input_file,web=web, root=root,
                                        format="basic", output=None, version=False))

    def test_fetch_ontology(self):
        self.run_pipeline_with_args(input_file=self.small_simple_path)
        self.assertFalse(os.path.exists(os.path.abspath("fetched_ontologies/pizza.json")))

        self.run_pipeline_with_args(input_file=self.small_simple_path, web=self.pizza_url)
        self.assertTrue(os.path.exists(os.path.abspath("fetched_ontologies/pizza.json")))

    def test_fetch_ontology_specify_root(self):
        self.run_pipeline_with_args(input_file=self.small_simple_path, web=self.pizza_url)
        with open(os.path.abspath("fetched_ontologies/pizza.json")) as file:
            pizza_json = json.load(file)
        self.assertFalse(pizza_json["specifications"])

        self.run_pipeline_with_args(input_file=self.small_simple_path,
                                    web=self.pizza_url,
                                    root=self.pizza_DomainThing_iri)
        with open(os.path.abspath("fetched_ontologies/pizza.json")) as file:
            pizza_json = json.load(file)
        self.assertTrue(pizza_json["specifications"])

    def test_ontology_table_creation(self):
        self.assertFalse(os.path.exists(os.path.abspath("ontology_lookup_tables/pizza.json")))
        self.run_pipeline_with_args(input_file=self.small_simple_path,
                                    web=self.pizza_url,
                                    root=self.pizza_DomainThing_iri)
        self.assertTrue(os.path.exists(os.path.abspath("ontology_lookup_tables/pizza.json")))

    def test_ontology_table_keys(self):
        self.run_pipeline_with_args(input_file=self.small_simple_path,
                                    web=self.pizza_url,
                                    root=self.pizza_DomainThing_iri)
        with open(os.path.abspath("ontology_lookup_tables/pizza.json")) as file:
            pizza_table_json = json.load(file)

        expected_keys = ["synonyms", "abbreviations", "abbreviations_lower", "non_english_words",
                         "non_english_words_lower","spelling_mistakes", "spelling_mistakes_lower",
                         "processes", "qualities", "qualities_lower", "collocations",
                         "inflection_exceptions", "stop_words", "suffixes",
                         "resource_terms_ID_based", "resource_terms", "resource_terms_revised",
                         "resource_permutation_terms", "resource_bracketed_permutation_terms"]
        for expected_key in expected_keys:
            try:
                self.assertTrue(expected_key in pizza_table_json)
            except AssertionError:
                raise AssertionError(expected_key + " is not in pizza_table_json")


if __name__ == '__main__':
    unittest.main()
