#!/usr/bin/env python

"""Tests functionality of LexMapr.

Requires environmental variable ``PYTHONHASHSEED=0`` for tests to pass.
"""

import argparse
import json
import os
import shutil
import tempfile
import unittest

import pkg_resources

import lexmapr.pipeline as pipeline
import lexmapr.pipeline_helpers as pipeline_helpers


class TestPipelineHelpers(unittest.TestCase):

    def test_is_number(self):
        """Tests is_number."""
        # 0 value
        self.assertTrue(pipeline_helpers.is_number("0"))
        # Positive float value
        self.assertTrue(pipeline_helpers.is_number("1.5"))
        # Negative float value
        self.assertTrue(pipeline_helpers.is_number("-1.5"))
        # Empty string
        self.assertFalse(pipeline_helpers.is_number(""))
        # Non-empty string
        self.assertFalse(pipeline_helpers.is_number("foo"))

    def test_is_date(self):
        """Tests is_date_true."""
        # Year, month and day with dashes
        self.assertTrue(pipeline_helpers.is_date("2018-05-07"))
        # American month, day and year
        self.assertTrue(pipeline_helpers.is_date("12/22/78"))
        # Textual month, day and year
        self.assertTrue(pipeline_helpers.is_date("July 1st, 2008"))
        # Empty string
        self.assertFalse(pipeline_helpers.is_date(""))
        # Non-empty string
        self.assertFalse(pipeline_helpers.is_date("foo"))

    def test_ngrams(self):
        """Tests ngrams."""
        # Empty string and n = 1
        self.assertEqual(pipeline_helpers.ngrams("", 1), [[""]],)
        # Empty string and n=2
        self.assertEqual(pipeline_helpers.ngrams("", 1), [[""]],)
        # Two-word string and n=1
        self.assertEqual(pipeline_helpers.ngrams("hello world!", 1),
            [["hello"], ["world!"]])
        # Two-word string and n=2
        self.assertEqual(pipeline_helpers.ngrams("hello world!", 2),
            [["hello", "world!"]])
        # Three-word string and n=2
        self.assertEqual(pipeline_helpers.ngrams("why, hello world!", 2),
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
                functionality of pipeline_helpers.py, this is currently
                sufficient.
            * Problems with string tokens containing multiple
                instances of:
                * the same character
                * different characters (if they do not appear left to
                    right in the order of the if-statements in
                    preProcess)
        """
        # No special characters
        self.assertEqual(pipeline_helpers.preprocess("cow"), "cow")
        # One "'s"
        self.assertEqual(pipeline_helpers.preprocess("cow's"), "cow")
        # Two "'s"
        self.assertEqual(pipeline_helpers.preprocess("cow's and chicken's"),
            "cow and chicken")
        # One ", "
        self.assertEqual(pipeline_helpers.preprocess("cow, "), "cow")
        # Two ", "
        # self.assertEqual(pipeline_helpers.preProcess("cow, horse, and goat"),
        #     "cow horse and goat")
        self.assertEqual(pipeline_helpers.preprocess("cow, horse, and goat"),
            "cow, horse, and goat")
        # One "."
        self.assertEqual(pipeline_helpers.preprocess("cow. "), "cow")
        # Two "."
        self.assertEqual(pipeline_helpers.preprocess("cow. horse. "), "cow. horse")
        # "'s" and ","
        self.assertEqual(pipeline_helpers.preprocess("cow's, "), "cow")
        # "'", "." and ","
        self.assertEqual(pipeline_helpers.preprocess("cow's. , "), "cow")
        # "'", "," and "."
        self.assertEqual(pipeline_helpers.preprocess("cow's, . "), "cow,")

    def test_allPermutations(self):
        """Tests allPermutations."""
        # Empty input string
        self.assertSetEqual(pipeline_helpers.all_permutations(""), set([()]))
        # 1-gram input string
        self.assertSetEqual(pipeline_helpers.all_permutations("a"), set([("a",)]))
        # 2-gram input string
        self.assertSetEqual(pipeline_helpers.all_permutations("a b"),
            set([("a", "b"), ("b", "a")]))
        # 4-gram input string
        self.assertEqual(len(pipeline_helpers.all_permutations("a b c d")), 24)

    def test_get_resource_permutation_terms(self):
        self.assertCountEqual(pipeline_helpers.get_resource_permutation_terms(""), [""])
        self.assertCountEqual(pipeline_helpers.get_resource_permutation_terms("a"), ["a"])
        self.assertCountEqual(pipeline_helpers.get_resource_permutation_terms("a b"),
                              ["a b", "b a"])

        self.assertCountEqual(pipeline_helpers.get_resource_permutation_terms("a (b)"),
                              ["a (b)", "(b) a"])

    def test_get_resource_bracketed_permutation_terms(self):
        self.assertCountEqual(pipeline_helpers.get_resource_bracketed_permutation_terms(""), [])
        self.assertCountEqual(pipeline_helpers.get_resource_bracketed_permutation_terms("a"), [])
        self.assertCountEqual(pipeline_helpers.get_resource_bracketed_permutation_terms("a b"), [])
        self.assertCountEqual(pipeline_helpers.get_resource_bracketed_permutation_terms("a (b"), [])
        self.assertCountEqual(pipeline_helpers.get_resource_bracketed_permutation_terms("a b)"), [])

        self.assertCountEqual(pipeline_helpers.get_resource_bracketed_permutation_terms("a (b)"),
                              ["a b", "b a"])
        self.assertCountEqual(pipeline_helpers.get_resource_bracketed_permutation_terms("(a) b"),
                              ["a"])
        self.assertCountEqual(pipeline_helpers.get_resource_bracketed_permutation_terms("(a b)"),
                              ["a b", "b a"])
        self.assertCountEqual(pipeline_helpers.get_resource_bracketed_permutation_terms("a (b c)"),
                              ["a b c", "a c b", "b a c", "b c a", "c a b", "c b a"])
        self.assertCountEqual(pipeline_helpers.get_resource_bracketed_permutation_terms("a (b,c)"),
                              ["a b c", "a c b", "b a c", "b c a", "c a b", "c b a"])

    def test_combi(self):
        """Tests combi."""
        # Empty input string and n=1
        self.assertSetEqual(set(pipeline_helpers.combi("", 1)), set([]))
        # Empty input string and n=2
        self.assertSetEqual(set(pipeline_helpers.combi("", 2)), set([]))
        # 1-char input string and n=1
        self.assertSetEqual(set(pipeline_helpers.combi("a", 1)), set([("a",)]))
        # 1-char input string and n=2
        self.assertSetEqual(set(pipeline_helpers.combi("a", 2)), set([]))
        # 3-char input string and n=1
        self.assertSetEqual(set(pipeline_helpers.combi("bar", 1)),
            set([("b",), ("a",), ("r",)]))
        # 3-char input string and n=2
        self.assertSetEqual(set(pipeline_helpers.combi("bar", 2)),
            set([("b", "a"), ("a", "r"), ("b", "r")]))
        # 3-char input string and n=3
        self.assertSetEqual(set(pipeline_helpers.combi("bar", 3)),
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
        # Punctuation list used in pipeline_helpers
        punctuationList = ["-", "_", "(", ")", ";", "/", ":", "%"]
        # Empty input string
        self.assertEqual(
            pipeline_helpers.punctuationTreatment("", punctuationList),
            "")
        # Single-token input string with no punctuation
        self.assertEqual(
            pipeline_helpers.punctuationTreatment("foo", punctuationList),
            "foo")
        # Multi-token input string with no punctuation
        self.assertEqual(
            pipeline_helpers.punctuationTreatment("foo bar", punctuationList),
            "foo bar")
        # Single-token input string with punctuation
        self.assertEqual(
            pipeline_helpers.punctuationTreatment("_foo-bar_", punctuationList),
            " foo bar ")
        # Multi-token input string with punctuation
        self.assertEqual(
            pipeline_helpers.punctuationTreatment("_foo;ba r_", punctuationList),
            " foo   ba r ")
        # Multi-token input string with number, date and punctuation
        self.assertEqual(
            pipeline_helpers.punctuationTreatment("a-b 12/22/78 -1", punctuationList),
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
                    * This is because pipeline_helpers.retainedPhrase
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
            pipeline_helpers.retainedPhrase(['foo:bar']),
            set(["foo:bar"]))
        # Multi-term list
        self.assertSetEqual(
            pipeline_helpers.retainedPhrase(['foo:bar', 'hello:world']),
            set(["foo:bar", "hello:world"]))
        # Multi-term list with "="
        self.assertSetEqual(
            pipeline_helpers.retainedPhrase(['foo:b=ar', 'he=llo:world']),
            set(["foo:b=ar", "he,llo:world"]))
        # Key substring of a key
        self.assertSetEqual(
            pipeline_helpers.retainedPhrase(['foo:bar', 'foofoo:bar']),
            set(["foofoo:bar"]))
        # Key substring of a compound key (multi-word)
        self.assertSetEqual(
            pipeline_helpers.retainedPhrase(['foo:bar', 'foo bar:bar']),
            set(["foo bar:bar"]))
        # Compound key substring of a compound key
        self.assertSetEqual(
            pipeline_helpers.retainedPhrase(['foo bar hello:world', 'foo bar:bar']),
            set(["foo bar hello:world"]))
        # Compound key overlapping, but not substring of a compound key
        self.assertSetEqual(
            pipeline_helpers.retainedPhrase(['foo hello:world', 'foo bar:bar']),
            set(["foo hello:world", "foo bar:bar"]))
        # Compound key substring of a compound key (no differing words)
        self.assertEqual(
            pipeline_helpers.retainedPhrase(['foo bar:bar', 'foo bar bar:bar']),
            [])
        # Identical keys, but different values
        self.assertEqual(
            pipeline_helpers.retainedPhrase(['foo:bar', 'foo:foo']),
            set(["foo:bar", "foo:foo"]))
        self.assertEqual(
            pipeline_helpers.retainedPhrase(['foo bar:bar', 'foo bar:foo']),
            set(["foo bar:bar", "foo bar:foo"]))

    def test_merge_lookup_tables(self):
        self.assertRaises(ValueError, pipeline_helpers.merge_lookup_tables, {}, {"a": {}})
        self.assertRaises(ValueError, pipeline_helpers.merge_lookup_tables, {"a": {}}, {})

        self.assertRaises(ValueError, pipeline_helpers.merge_lookup_tables, {"a": {}}, {"b": {}})
        self.assertRaises(ValueError, pipeline_helpers.merge_lookup_tables, {"a": {}, "b": {}},
                                                                    {"a": {}, "c": {}})

        self.assertRaises(ValueError, pipeline_helpers.merge_lookup_tables, {"a": "b"}, {"a": {}})
        self.assertRaises(ValueError, pipeline_helpers.merge_lookup_tables, {"a": {}}, {"a": "b"})
        self.assertRaises(ValueError, pipeline_helpers.merge_lookup_tables, {"a": "b"}, {"a": "b"})
        self.assertRaises(ValueError, pipeline_helpers.merge_lookup_tables, {"a": {}, "b": "c"},
                                                                    {"a": {}, "b": {}})
        self.assertRaises(ValueError, pipeline_helpers.merge_lookup_tables, {"a": {}, "b": {}},
                                                                    {"a": {}, "b": "c"})
        self.assertRaises(ValueError, pipeline_helpers.merge_lookup_tables, {"a": {}, "b": "c"},
                                                                    {"a": {}, "b": "c"})

        self.assertDictEqual({}, pipeline_helpers.merge_lookup_tables({}, {}))
        self.assertDictEqual({"a": {}}, pipeline_helpers.merge_lookup_tables({"a": {}}, {"a": {}}))

        self.assertDictEqual({"a": {"b": "c"}},
                             pipeline_helpers.merge_lookup_tables({"a": {"b": "c"}}, {"a": {}}))
        self.assertDictEqual({"a": {"b": "c"}}, pipeline_helpers.merge_lookup_tables({"a": {}},
                                                                             {"a": {"b": "c"}}))
        self.assertDictEqual({"a": {"b": "c"}},
                             pipeline_helpers.merge_lookup_tables({"a": {"b": "c"}},
                                                                  {"a": {"b": "c"}}))
        self.assertDictEqual({"a": {"b": "c"}},
                             pipeline_helpers.merge_lookup_tables({"a": {"b": "d"}},
                                                                  {"a": {"b": "c"}}))
        self.assertDictEqual({"a": {"b": "d"}},
                             pipeline_helpers.merge_lookup_tables({"a": {"b": "c"}},
                                                                  {"a": {"b": "d"}}))

        self.assertDictEqual({"a": {"b": "c", "d": "e"}},
                             pipeline_helpers.merge_lookup_tables({"a": {"b": "c","d": "e"}},
                                                          {"a": {"b": "c"}}))
        self.assertDictEqual({"a": {"b": "c", "d": "e"}},
                             pipeline_helpers.merge_lookup_tables({"a": {"b": "c"}},
                                                          {"a": {"b": "c", "d": "e"}}))
        self.assertDictEqual({"a": {"b": "c", "d": "e"}},
                             pipeline_helpers.merge_lookup_tables({"a": {"b": "f","d": "e"}},
                                                          {"a": {"b": "c"}}))
        self.assertDictEqual({"a": {"b": "f", "d": "e"}},
                             pipeline_helpers.merge_lookup_tables({"a": {"b": "c"}},
                                                          {"a": {"b": "f", "d": "e"}}))
        self.assertDictEqual({"a": {"b": "c", "d": "e"}},
                             pipeline_helpers.merge_lookup_tables({"a": {"b": "c", "d": "e"}},
                                                          {"a": {"b": "c", "d": "e"}}))
        self.assertDictEqual({"a": {"b": "c", "d": "e"}},
                             pipeline_helpers.merge_lookup_tables({"a": {"b": "f", "d": "g"}},
                                                          {"a": {"b": "c", "d": "e"}}))

        self.assertDictEqual({"a": {"b": "c", "d": "e"}, "f": {"h": "m", "j": "k"}},
                             pipeline_helpers.merge_lookup_tables({"a": {"b": "c", "d": "l"},
                                                           "f": {"h": "i", "j": "k"}},
                                                          {"a": {"b": "c", "d": "e"},
                                                           "f": {"h": "m", "j": "k"}}))
        self.assertDictEqual({"a": {"b": "c", "d": "e", "n": "o"},
                              "f": {"h": "m", "j": "k", "p": "q"}},
                             pipeline_helpers.merge_lookup_tables(
                                 {"a": {"b": "c", "d": "l", "n": "o"}, "f": {"h": "i", "j": "k"}},
                                 {"a": {"b": "c", "d": "e"}, "f": {"h": "m", "j": "k", "p": "q"}}))


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
            * Full-term matches made with a cleaned sample using a
                permutations should have some record of the comparison
                being made with a cleaned sample.
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

    # Dictionary containing pipeline arguments (values), and the names
    # of their expected output files (keys). These are not technically
    # valid arguments because we should supply the paths of input
    # files, but we will convert the values for input to paths later,
    # to avoid long strings here.
    test_files = {
        # Empty file without "full" format argument
        "empty_not_full": {"input": "empty", "format": "not full"},
        # Empty file with "full" format argument
        "empty": {"input": "empty"},
        # Non-empty file without "full" format argument
        "small_simple_not_full": {"input": "small_simple", "format": "not full"},
        # Non-empty file with "full" format argument
        "small_simple": {"input": "small_simple"},
        # Some rows requires punctuation treatment
        "test_punctuation": {"input": "test_punctuation"},
        # Some rows require extra inner spaces to be removed--
        # some due to punctuation treatment.
        "test_extra_inner_spaces": {"input": "test_extra_inner_spaces"},
        # Varying number of tokens per row
        "test_tokenization": {"input": "test_tokenization"},
        # Some tokens require preprocessing
        "test_preprocessing": {"input": "test_preprocessing"},
        # Some tokens require inflection treatment
        "test_pluralization": {"input": "test_pluralization"},
        # Some tokens require spelling corrections
        "test_spelling_corrections": {"input": "test_spelling_corrections"},
        # Some tokens require abbreviation or acronym translation
        "test_abbreviations": {"input": "test_abbreviations"},
        # Some tokens require non-english to english translation
        # TODO: We must add capitalized non-english words to
        #       ../resources/NefLex, and then makes tests for potential
        #       translations from nonEnglishWordsLowerDict.
        "test_non_english_words": {"input": "test_non_english_words"},
        # Some tokens are stop-words
        "test_stop_word_handling": {"input": "test_stop_word_handling"},
        # Varying paths of candidate phrase creations
        "test_candidate_phrase": {"input": "test_candidate_phrase"},
        # Some Sample_Id's are missing a sample
        "test_sample_id_only": {"input": "test_sample_id_only"},
        # Some samples are a full-term direct match
        "test_full_term_dir_match": {"input": "test_full_term_dir_match"},
        # Some samples are a full-term match, provided a change-of-case
        # in input or resource data.
        "test_full_term_coc_match": {"input": "test_full_term_coc_match"},
        # Some samples are a full-term match, if permutated
        "test_full_term_perm_match": {"input": "test_full_term_perm_match"},
        # Some samples are a full-term match, if given an added suffix
        "test_full_term_sfx_match": {"input": "test_full_term_sfx_match"},
        # Some samples are a full-term match, based on a
        # Wikipedia-based collocation resource.
        "test_full_term_wiki_match": {"input": "test_full_term_wiki_match"},
        # Bucket classification
        "empty_buckets_not_full": {"input": "empty", "format": "not full", "bucket": True},
        "empty_buckets": {"input": "empty", "bucket": True},
    }

    @classmethod
    def setUpClass(cls):
        # Convert input file names to paths in test_files.
        for expected_output_filename, pipeline_args in cls.test_files.items():
            input_path = pkg_resources.resource_filename("lexmapr.tests.test_input",
                                                         pipeline_args["input"] + ".csv")
            cls.test_files[expected_output_filename]["input"] = input_path

        # Change working directory to temporary directory
        cls.tmp_dir = tempfile.mkdtemp()
        os.chdir(cls.tmp_dir)

    @classmethod
    def tearDownClass(cls):
        # Remove temporary directory
        shutil.rmtree(cls.tmp_dir)

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
        for expected_output_filename, pipeline_args in self.test_files.items():
            # Path of expected output file
            expected_output_path = pkg_resources.resource_filename("lexmapr.tests.test_output",
                                                                   expected_output_filename
                                                                   + ".tsv")
            # File path to store actual output of input file
            actual_output_path = "actual_output.tsv"
            # Run pipeline.run using input_path and actual_output_path
            default_args = {"format": "full", "bucket": False}
            default_args.update(pipeline_args)
            pipeline.run(argparse.Namespace(input_file=default_args["input"], config=None,
                                            format=default_args["format"],
                                            output=actual_output_path, version=False,
                                            bucket=default_args["bucket"]))
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
                failures += [expected_output_path]
        if failures:
            print("Failed files:")
            for failure in failures:
                print(failure)
            raise AssertionError


class TestOntologyMapping(unittest.TestCase):
    """Test fetching and use of resources from online ontologies."""

    @classmethod
    def setUpClass(cls):
        # Change working directory to temporary directory
        cls.tmp_dir = tempfile.mkdtemp()
        os.chdir(cls.tmp_dir)

    @classmethod
    def tearDownClass(cls):
        # Remove temporary directory
        shutil.rmtree(cls.tmp_dir)

    def tearDown(self):
        # Remove cached ontology resources between tests
        shutil.rmtree("fetched_ontologies/")
        shutil.rmtree("ontology_lookup_tables/")

    @staticmethod
    def run_pipeline_with_args(config_file_name=None):
        """Run pipeline with some default arguments."""

        # Path to input file used in all tests
        small_simple_path =\
            pkg_resources.resource_filename("lexmapr.tests.test_input", "small_simple.csv")

        if config_file_name:
            config_file_path = pkg_resources.resource_filename("lexmapr.tests.test_config",
                                                               config_file_name)
            pipeline.run(argparse.Namespace(input_file=small_simple_path, config=config_file_path,
                                            format="basic", output=None, version=False,
                                            bucket=False))
        else:
            pipeline.run(argparse.Namespace(input_file=small_simple_path, config=None,
                                            format="basic", output=None, version=False,
                                            bucket=False))

    @staticmethod
    def get_fetched_ontology(file_name):
        with open("fetched_ontologies/%s" % file_name) as file:
            return json.load(file)

    @staticmethod
    def get_ontology_lookup_table(file_name):
        with open("ontology_lookup_tables/%s" % file_name) as file:
            return json.load(file)

    def test_fetch_ontology(self):
        self.run_pipeline_with_args()
        self.assertFalse(os.path.exists("fetched_ontologies/pizza.json"))

        self.run_pipeline_with_args(config_file_name="pizza.json")
        self.assertTrue(os.path.exists("fetched_ontologies/pizza.json"))

    def test_fetch_ontologies(self):
        self.run_pipeline_with_args()
        self.assertFalse(os.path.exists("fetched_ontologies/bfo.json"))
        self.assertFalse(os.path.exists("fetched_ontologies/pizza.json"))

        self.run_pipeline_with_args(config_file_name="bfo_and_pizza.json")
        self.assertTrue(os.path.exists("fetched_ontologies/bfo.json"))
        self.assertTrue(os.path.exists("fetched_ontologies/pizza.json"))

    def test_fetch_ontology_specify_no_root(self):
        self.run_pipeline_with_args(config_file_name="bfo.json")
        bfo_fetched_ontology = self.get_fetched_ontology("bfo.json")
        self.assertEqual(36, len(bfo_fetched_ontology["specifications"]))

    def test_fetch_ontology_specify_with_root(self):
        self.run_pipeline_with_args(config_file_name="bfo_process.json")
        bfo_process_fetched_ontology = self.get_fetched_ontology("bfo.json")
        self.assertEqual(3, len(bfo_process_fetched_ontology["specifications"]))

    def test_ontology_table_creation(self):
        self.assertFalse(os.path.exists("ontology_lookup_tables/lookup_bfo.json"))
        self.run_pipeline_with_args(config_file_name="bfo.json")
        self.assertTrue(os.path.exists("ontology_lookup_tables/lookup_bfo.json"))

    def test_ontology_table_creation_with_multiple_ontologies(self):
        expected_lookup_table_rel_path = "ontology_lookup_tables/lookup_bfo_and_pizza.json"
        self.assertFalse(os.path.exists(expected_lookup_table_rel_path))
        self.run_pipeline_with_args(config_file_name="bfo_and_pizza.json")
        self.assertTrue(os.path.exists(expected_lookup_table_rel_path))

    def test_ontology_table_keys(self):
        self.run_pipeline_with_args(config_file_name="bfo.json")
        ontology_lookup_table = self.get_ontology_lookup_table("lookup_bfo.json")

        expected_keys = ["synonyms", "abbreviations", "non_english_words", "spelling_mistakes",
                         "processes", "qualities", "collocations", "inflection_exceptions",
                         "stop_words", "suffixes", "parents", "resource_terms_id_based",
                         "resource_terms", "resource_permutation_terms",
                         "resource_bracketed_permutation_terms",
                         "buckets_ifsactop", "buckets_lexmapr", "ifsac_labels", "ifsac_refinement",
                         "ifsac_default"]

        self.assertCountEqual(expected_keys, ontology_lookup_table.keys())

    def test_ontology_table_keys_with_multiple_ontologies(self):
        self.run_pipeline_with_args(config_file_name="bfo_and_pizza.json")
        ontology_lookup_table = self.get_ontology_lookup_table("lookup_bfo_and_pizza.json")

        expected_keys = ["synonyms", "abbreviations", "non_english_words", "spelling_mistakes",
                         "processes", "qualities", "collocations", "inflection_exceptions",
                         "stop_words", "suffixes", "parents", "resource_terms_id_based",
                         "resource_terms", "resource_permutation_terms",
                         "resource_bracketed_permutation_terms",
                         "buckets_ifsactop", "buckets_lexmapr", "ifsac_labels", "ifsac_refinement",
                         "ifsac_default"]

        self.assertCountEqual(expected_keys, ontology_lookup_table.keys())

    def test_ontology_table_resource_terms_id_based(self):
        self.run_pipeline_with_args(config_file_name="bfo_material_entity.json")
        ontology_lookup_table = self.get_ontology_lookup_table("lookup_bfo_material_entity.json")

        expected_resource_terms_id_based = {
            "bfo_0000024": "fiat object part",
            "bfo_0000027": "object aggregate",
            "bfo_0000030": "object"
        }
        actual_resource_terms_id_based = ontology_lookup_table["resource_terms_id_based"]
        self.assertDictEqual(expected_resource_terms_id_based, actual_resource_terms_id_based)

    def test_ontology_table_resource_terms_id_based_with_multiple_ontologies(self):
        config_file_name = "bfo_material_entity_and_pizza_spiciness.json"
        expected_lookup_table_name = "lookup_" + config_file_name
        self.run_pipeline_with_args(config_file_name=config_file_name)
        ontology_lookup_table = self.get_ontology_lookup_table(expected_lookup_table_name)

        expected_resource_terms_id_based = {
            "bfo_0000024": "fiat object part",
            "bfo_0000027": "object aggregate",
            "bfo_0000030": "object",
            "pizza.owl_hot": "picante",
            "pizza.owl_medium": "media",
            "pizza.owl_mild": "naopicante"
        }
        actual_resource_terms_id_based = ontology_lookup_table["resource_terms_id_based"]
        self.assertDictEqual(expected_resource_terms_id_based, actual_resource_terms_id_based)

    def test_ontology_table_resource_terms_id_based_with_multiple_root_entities(self):
        config_file_name = "bfo_process_and_material_entity.json"
        expected_lookup_table_name = "lookup_" + config_file_name
        self.run_pipeline_with_args(config_file_name=config_file_name)
        ontology_lookup_table = self.get_ontology_lookup_table(expected_lookup_table_name)

        expected_resource_terms_id_based = {
            "bfo_0000024": "fiat object part",
            "bfo_0000027": "object aggregate",
            "bfo_0000030": "object",
            "bfo_0000144": "process profile",
            "bfo_0000182": "history"
        }
        actual_resource_terms_id_based = ontology_lookup_table["resource_terms_id_based"]
        self.assertDictEqual(expected_resource_terms_id_based, actual_resource_terms_id_based)

    def test_ontology_table_resource_terms(self):
        self.run_pipeline_with_args(config_file_name="bfo_material_entity.json")
        ontology_lookup_table = self.get_ontology_lookup_table("lookup_bfo_material_entity.json")

        expected_resource_terms = {
            "fiat object part": "bfo_0000024",
            "object aggregate": "bfo_0000027",
            "object": "bfo_0000030"
        }
        actual_resource_terms = ontology_lookup_table["resource_terms"]
        self.assertDictEqual(expected_resource_terms, actual_resource_terms)

    def test_ontology_table_resource_terms_with_multiple_ontologies(self):
        config_file_name = "bfo_material_entity_and_pizza_spiciness.json"
        expected_lookup_table_name = "lookup_" + config_file_name
        self.run_pipeline_with_args(config_file_name=config_file_name)
        ontology_lookup_table = self.get_ontology_lookup_table(expected_lookup_table_name)

        expected_resource_terms = {
            "fiat object part": "bfo_0000024",
            "object aggregate": "bfo_0000027",
            "object": "bfo_0000030",
            "picante": "pizza.owl_hot",
            "media": "pizza.owl_medium",
            "naopicante": "pizza.owl_mild"
        }
        actual_resource_terms = ontology_lookup_table["resource_terms"]
        self.assertDictEqual(expected_resource_terms, actual_resource_terms)

    def test_ontology_table_synonyms(self):
        self.run_pipeline_with_args(config_file_name="bfo.json")
        ontology_lookup_table = self.get_ontology_lookup_table("lookup_bfo.json")

        expected_synonyms = {
            "temporal instant.": "zero-dimensional temporal region",
            "lonely-dimensional continuant fiat boundary.":
                "two-dimensional continuant fiat boundary",
            "lonelier-dimensional continuant fiat boundary.":
                "one-dimensional continuant fiat boundary",
            "loneliest-dimensional continuant fiat boundary.":
                "zero-dimensional continuant fiat boundary",
            "loneliestest-dimensional continuant fiat boundary.":
                "zero-dimensional continuant fiat boundary",
        }
        actual_synonyms = ontology_lookup_table["synonyms"]
        self.assertDictEqual(expected_synonyms, actual_synonyms)

    def test_ontology_table_parents_one_level_one_parent(self):
        self.run_pipeline_with_args(config_file_name="bfo_process.json")
        ontology_lookup_table = self.get_ontology_lookup_table("lookup_bfo_process.json")

        expected_parents = {
            "bfo_0000182": ["bfo_0000015"],
            "bfo_0000144": ["bfo_0000015"]
        }
        actual_parents = ontology_lookup_table["parents"]

        self.assertDictEqual(expected_parents, actual_parents)

    def test_ontology_table_parents_one_level_two_parents(self):
        config_file_name = "bfo_process_and_material_entity.json"
        expected_lookup_table_name = "lookup_" + config_file_name
        self.run_pipeline_with_args(config_file_name=config_file_name)
        ontology_lookup_table = self.get_ontology_lookup_table(expected_lookup_table_name)

        expected_parents = {
            "bfo_0000182": ["bfo_0000015"],
            "bfo_0000144": ["bfo_0000015"],
            "bfo_0000024": ["bfo_0000040"],
            "bfo_0000027": ["bfo_0000040"],
            "bfo_0000030": ["bfo_0000040"]
        }
        actual_parents = ontology_lookup_table["parents"]

        self.assertDictEqual(expected_parents, actual_parents)

    def test_ontology_table_parents_multiple_levels_one_branch(self):
        self.run_pipeline_with_args(config_file_name="bfo_realizable_entity.json")
        ontology_lookup_table = self.get_ontology_lookup_table("lookup_bfo_realizable_entity.json")

        expected_parents = {
            "bfo_0000034": ["bfo_0000016"],
            "bfo_0000016": ["bfo_0000017"],
            "bfo_0000023": ["bfo_0000017"]
        }
        actual_parents = ontology_lookup_table["parents"]

        self.assertDictEqual(expected_parents, actual_parents)

    def test_ontology_table_parents_multiple_levels_multiple_branches(self):
        config_file_name = "bfo_specifically_dependent_continuant.json"
        expected_lookup_table_name = "lookup_" + config_file_name
        self.run_pipeline_with_args(config_file_name=config_file_name)
        ontology_lookup_table = self.get_ontology_lookup_table(expected_lookup_table_name)

        expected_parents = {
            "bfo_0000034": ["bfo_0000016"],
            "bfo_0000016": ["bfo_0000017"],
            "bfo_0000023": ["bfo_0000017"],
            "bfo_0000145": ["bfo_0000019"],
            "bfo_0000017": ["bfo_0000020"],
            "bfo_0000019": ["bfo_0000020"]
        }
        actual_parents = ontology_lookup_table["parents"]

        self.assertDictEqual(expected_parents, actual_parents)

    def test_ontology_table_multiple_parents_per_resource(self):
        config_file_name = "bfo_duplicate_entities_specifically_dependent_continuant.json"
        expected_lookup_table_name = "lookup_" + config_file_name
        self.run_pipeline_with_args(config_file_name=config_file_name)
        ontology_lookup_table = self.get_ontology_lookup_table(expected_lookup_table_name)

        expected_parents = {
            "bfo_0000019": ["bfo_0000020"],
            "bfo_0000017": ["bfo_0000020"],
            "bfo_0000145": ["bfo_0000019", "bfo_0000017"],
            "bfo_0000016": ["bfo_0000017"],
            "bfo_0000023": ["bfo_0000017"],
            "bfo_0000034": ["bfo_0000016"],
        }
        actual_parents = ontology_lookup_table["parents"]

        # Sort lists to ignore order in assertion
        sorted_expected_parents = {}
        for key, value in expected_parents.items():
            sorted_expected_parents[key] = sorted(value)
        sorted_actual_parents = {}
        for key, value in actual_parents.items():
            sorted_actual_parents[key] = sorted(value)

        self.assertDictEqual(sorted_expected_parents, sorted_actual_parents)

    def test_ontology_table_overlapping_parents_from_different_fetches(self):
        config_file_name = "bfo_duplicate_entities_process_and_material_entity.json"
        expected_lookup_table_name = "lookup_" + config_file_name
        self.run_pipeline_with_args(config_file_name=config_file_name)
        ontology_lookup_table = self.get_ontology_lookup_table(expected_lookup_table_name)

        expected_parents = {
            "bfo_0000182": ["bfo_0000015"],
            "bfo_0000144": ["bfo_0000015"],
            "bfo_0000024": ["bfo_0000040", "bfo_0000015"],
            "bfo_0000027": ["bfo_0000040", "bfo_0000015"],
            "bfo_0000030": ["bfo_0000040", "bfo_0000015"]
        }
        actual_parents = ontology_lookup_table["parents"]

        self.assertDictEqual(expected_parents, actual_parents)

        # Sort lists to ignore order in assertion
        sorted_expected_parents = {}
        for key, value in expected_parents.items():
            sorted_expected_parents[key] = sorted(value)
        sorted_actual_parents = {}
        for key, value in actual_parents.items():
            sorted_actual_parents[key] = sorted(value)

        self.assertDictEqual(sorted_expected_parents, sorted_actual_parents)

    def test_ontology_table_duplicate_parents(self):
        config_file_name = "bfo_process_twice.json"
        expected_lookup_table_name = "lookup_" + config_file_name
        self.run_pipeline_with_args(config_file_name=config_file_name)
        ontology_lookup_table = self.get_ontology_lookup_table(expected_lookup_table_name)

        expected_parents = {
            "bfo_0000182": ["bfo_0000015"],
            "bfo_0000144": ["bfo_0000015"]
        }
        actual_parents = ontology_lookup_table["parents"]

        self.assertDictEqual(expected_parents, actual_parents)

        # Sort lists to ignore order in assertion
        sorted_expected_parents = {}
        for key, value in expected_parents.items():
            sorted_expected_parents[key] = sorted(value)
        sorted_actual_parents = {}
        for key, value in actual_parents.items():
            sorted_actual_parents[key] = sorted(value)

        self.assertDictEqual(sorted_expected_parents, sorted_actual_parents)

    def test_ontology_table_duplicate_other_parents(self):
        config_file_name = "bfo_duplicate_entities_specifically_dependent_continuant_twice.json"
        expected_lookup_table_name = "lookup_" + config_file_name
        self.run_pipeline_with_args(config_file_name=config_file_name)
        ontology_lookup_table = self.get_ontology_lookup_table(expected_lookup_table_name)

        expected_parents = {
            "bfo_0000019": ["bfo_0000020"],
            "bfo_0000017": ["bfo_0000020"],
            "bfo_0000145": ["bfo_0000019", "bfo_0000017"],
            "bfo_0000016": ["bfo_0000017"],
            "bfo_0000023": ["bfo_0000017"],
            "bfo_0000034": ["bfo_0000016"],
        }
        actual_parents = ontology_lookup_table["parents"]

        # Sort lists to ignore order in assertion
        sorted_expected_parents = {}
        for key, value in expected_parents.items():
            sorted_expected_parents[key] = sorted(value)
        sorted_actual_parents = {}
        for key, value in actual_parents.items():
            sorted_actual_parents[key] = sorted(value)

        self.assertDictEqual(sorted_expected_parents, sorted_actual_parents)

    def test_ontology_table_resource_permutation_terms(self):
        self.run_pipeline_with_args(config_file_name="bfo_material_entity.json")
        ontology_lookup_table = self.get_ontology_lookup_table("lookup_bfo_material_entity.json")

        expected_resource_permutation_terms = {
           "fiat object part": "bfo_0000024",
            "fiat part object": "bfo_0000024",
            "object fiat part": "bfo_0000024",
            "object part fiat": "bfo_0000024",
            "part fiat object": "bfo_0000024",
            "part object fiat": "bfo_0000024",
            "object aggregate": "bfo_0000027",
            "aggregate object": "bfo_0000027",
            "object": "bfo_0000030"
        }
        actual_resource_permutation_terms = ontology_lookup_table["resource_permutation_terms"]
        self.assertDictEqual(expected_resource_permutation_terms, actual_resource_permutation_terms)

    def test_ontology_table_resource_bracketed_permutation_terms(self):
        self.run_pipeline_with_args(config_file_name="bfo_spatial_region.json")
        ontology_lookup_table = self.get_ontology_lookup_table("lookup_bfo_spatial_region.json")

        expected_resource_bracketed_permutation_terms = {
            "one-dimensional region spatial": "bfo_0000026",
            "one-dimensional spatial region": "bfo_0000026",
            "region one-dimensional spatial": "bfo_0000026",
            "region spatial one-dimensional": "bfo_0000026",
            "spatial one-dimensional region": "bfo_0000026",
            "spatial region one-dimensional": "bfo_0000026",
            "two-dimensional region spatial": "bfo_0000009",
            "two-dimensional spatial region": "bfo_0000009",
            "region two-dimensional spatial": "bfo_0000009",
            "region spatial two-dimensional": "bfo_0000009",
            "spatial two-dimensional region": "bfo_0000009",
            "spatial region two-dimensional": "bfo_0000009",
            "three-dimensional region spatial": "bfo_0000028",
            "three-dimensional spatial region": "bfo_0000028",
            "region three-dimensional spatial": "bfo_0000028",
            "region spatial three-dimensional": "bfo_0000028",
            "spatial three-dimensional region": "bfo_0000028",
            "spatial region three-dimensional": "bfo_0000028"
        }
        actual_resource_bracketed_permutation_terms =\
            ontology_lookup_table["resource_bracketed_permutation_terms"]
        self.assertDictEqual(expected_resource_bracketed_permutation_terms,
                             actual_resource_bracketed_permutation_terms)

    def test_ontology_table_resource_terms_prioritisation_pizza_first(self):
        config_file_name = "pizza_spiciness_and_pizza_two_spiciness.json"
        expected_lookup_table_name = "lookup_" + config_file_name
        self.run_pipeline_with_args(config_file_name=config_file_name)
        ontology_lookup_table = self.get_ontology_lookup_table(expected_lookup_table_name)

        expected_resource_terms = {
            "picante": "pizza.owl_hot",
            "media": "pizza.owl_medium",
            "naopicante": "pizza.owl_mild"
        }
        actual_resource_terms = ontology_lookup_table["resource_terms"]
        self.assertDictEqual(expected_resource_terms, actual_resource_terms)

    def test_ontology_table_resource_terms_prioritisation_pizza_two_first(self):
        config_file_name = "pizza_two_spiciness_and_pizza_spiciness.json"
        expected_lookup_table_name = "lookup_" + config_file_name
        self.run_pipeline_with_args(config_file_name=config_file_name)
        ontology_lookup_table = self.get_ontology_lookup_table(expected_lookup_table_name)

        expected_resource_terms = {
            "picante": "pizza.owl_hottwo",
            "media": "pizza.owl_mediumtwo",
            "naopicante": "pizza.owl_mildtwo"
        }
        actual_resource_terms = ontology_lookup_table["resource_terms"]
        self.assertDictEqual(expected_resource_terms, actual_resource_terms)


class TestClassification(unittest.TestCase):
    """Tests processes of classification of samples into buckets.

    This differs from the black-box approach taken in TestPipeline, as
    we are concerned with the mechanics behind the classification.
    """

    @classmethod
    def setUpClass(cls):
        # Change working directory to temporary directory
        cls.tmp_dir = tempfile.mkdtemp()
        os.chdir(cls.tmp_dir)

    @classmethod
    def tearDownClass(cls):
        # Remove temporary directory
        shutil.rmtree(cls.tmp_dir)

    def tearDown(self):
        # Remove cached classification lookup table between tests
        os.remove("classification_lookup_table.json")

    @staticmethod
    def run_pipeline_with_args(bucket=False):
        """Run pipeline with some default arguments."""

        # Path to input file used in all tests
        small_simple_path =\
            pkg_resources.resource_filename("lexmapr.tests.test_input", "small_simple.csv")

        pipeline.run(argparse.Namespace(input_file=small_simple_path, config=None, format="basic",
                                        output=None, version=False, bucket=bucket))

    @staticmethod
    def get_classification_lookup_table():
        with open("classification_lookup_table.json") as fp:
            return json.load(fp)

    def test_generate_classification_table(self):
        self.run_pipeline_with_args()
        self.assertFalse(os.path.exists("classification_lookup_table.json"))

        self.run_pipeline_with_args(bucket=True)
        self.assertTrue(os.path.exists("classification_lookup_table.json"))

    def test_classification_table_keys(self):
        self.run_pipeline_with_args(bucket=True)
        classification_table = self.get_classification_lookup_table()

        expected_keys = ["synonyms", "abbreviations", "abbreviations_lower", "non_english_words",
                         "non_english_words_lower", "spelling_mistakes", "spelling_mistakes_lower",
                         "processes", "qualities", "qualities_lower", "collocations",
                         "inflection_exceptions", "stop_words", "suffixes", "parents",
                         "resource_terms_ID_based", "resource_terms", "resource_terms_revised",
                         "resource_permutation_terms", "resource_bracketed_permutation_terms",
                         "buckets_ifsactop", "buckets_lexmapr", "ifsac_labels", "ifsac_refinement",
                         "ifsac_default"]

        self.assertCountEqual(expected_keys, classification_table.keys())


if __name__ == '__main__':
    unittest.main()
