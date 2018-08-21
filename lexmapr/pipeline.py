#!/usr/bin/env python

import csv
import nltk
import re
import inflection
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk import pos_tag, ne_chunk
import wikipedia
import itertools
from itertools import combinations
from dateutil.parser import parse
import sys
from pkg_resources import resource_filename, resource_listdir
import logging
import collections
import json
import os

logger = logging.getLogger("pipeline")
logger.disabled = True

# DIFFERENT METHODS USED (Will be organized in Modular arrangement later on)

# 1-Method to determine  whether a string is a number (Used for Cardinal-Ordinal Tagging)
def is_number(inputstring):
    try:
        float(inputstring)
        return True
    except ValueError:
        pass
    try:
        import unicodedata
        unicodedata.numeric(inputstring)
        return True
    except (TypeError, ValueError):
        pass
    return False


# 2-Method to determine  whether a string is a date or day (Used for DateOrDay Tagging)
def is_date(inputstring):
    try:
        parse(inputstring)
        return True
    except ValueError:
        return False


# 3-Method to get ngrams with a given value of n (i.e. n=1 means unigram, n=2 means bigram, n=3 means trigram and so on)
def ngrams(input, n):
    input = input.split(' ')
    output = []
    for i in range(len(input) - n + 1):
        output.append(input[i:i + n])
    return output

def get_gram_chunks(input, num):
    """Make num-gram chunks from input.

    If input contains less than seven tokens, this function returns all
    num-length token combinations of input. Otherwise, this function
    returns all num-length token combinations that form a substring of
    input.

    Arguments:
        * input <"str">: String used to retrieve num-gram chunks
        * num <"int">: Number of grams per returned chunks
    Return values;
        * <"list">: Contains num-gram chunks as described above
    """
    # List of tokens from input
    input_tokens = word_tokenize(input)
    # input_tokens has less than 7 tokens
    if len(input_tokens) < 7:
        # Return all num-token combinations of input_tokens
        return list(combi(input_tokens, num))
    # input_tokens has 7 or more tokens
    else:
        # Return all num-length substrings of input
        return ngrams(input, num)

def preprocess(token):
    """Removes characters in token that are irrelevant to run.

    The characters removed are possessives, rightmost comma and
    rightmost period.

    Arguments:
        * token <class "str">: Token from string being processed in
            run
    Return values:
        * <class "str">: Token with irrelevant characters removed
    """
    # drop possessives, rightmost comma and rightmost period and return
    return token.replace("\'s", "").rstrip("', ").rstrip(". ")

# 5-Method to find the string between two characters  first and last
def find_between_r( s, first, last ):
    try:
        start = s.rindex( first ) + len( first )
        end = s.rindex( last, start )
        return s[start:end]
    except ValueError:
        return ""


# 6-Method to find the string left to  the character  first
def find_left_r(s, first, last):
    try:
        start = s.rindex(first) + len(first)
        end = s.rindex(last, start)
        return s[0:start - 2]
    except ValueError:
        return ""

# 8-Method to get all permutations of input string          -has overhead so the size of the phrase has been limited to 4-grams
def all_permutations(inputstring):
    listOfPermutations = inputstring.split()
    setPerm = set(itertools.permutations(listOfPermutations))
    return setPerm


# 9-Method to get all combinations of input string
# TODO: This function seems unneccessary. Delete it.
def combi(input, n):
    output=combinations(input, n)
    return output


# 10-Method to get the punctuation treatment of input string - removes some predetermined punctuation and replaces it with a space
def punctuationTreatment(inputstring, punctuationList):
    finalSample = ""
    sampleTokens = word_tokenize(inputstring)
    for token in sampleTokens:
        withoutPunctuation = ""
        number_result = is_number(token)
        date_result = is_date(token)
        if (number_result is True or date_result is True):   #Skips the punctuation treatment for date and number
            withoutPunctuation = token
        else:
            for char in token:
                if char in punctuationList:
                    withoutPunctuation = withoutPunctuation + " "
                else:
                    withoutPunctuation = withoutPunctuation + char
        if (finalSample):
            finalSample = finalSample + " " + withoutPunctuation
        else:
            finalSample = withoutPunctuation
    return finalSample


# 22-Method to get the final retained set of matched terms
def retainedPhrase(termList):
    returnedSetFinal = []
    logger.debug(termList)
    termDict = {}
    termDictAdd = {}
    wordList = []
    retainedSet = []
    returnedSet = []
    termList = termList.replace("{", "")
    termList = termList.replace("}", "")
    #termList = termList.replace("'", "")
    lst = termList.split("',")
    # print("ddddddddddddddddeeeee   " + str(lst))
    for x in lst:
        lst2 = x.split(":")
        a = lst2[0]
        a = a.replace("=", ",")
        a = a.replace("'", "")
        b = lst2[1]
        if a.strip() not in termDict.keys():
            termDict[a.strip()] = b.strip()
            wordList.append(a.strip())
            retainedSet.append(a.strip())
        if a.strip() in termDict.keys():
            termDictAdd[a.strip()] = b.strip()
            wordList.append(a.strip())
            retainedSet.append(a.strip())
    for wrd in wordList:
        if " " not in wrd:
            for othrwrd in wordList:
                #product egg raw yolk   {'egg yolk (raw):FOODON_03301439', 'egg (raw):FOODON_03301075', 'egg product:zFOODON_BaseTerm_368'}
                if wrd in retainedSet and wrd in othrwrd and wrd != othrwrd:
                    retainedSet.remove(wrd)
        else:# compound word
            ctr = 0
            for othrwrd in wordList:
                # product egg raw yolk   {'egg yolk (raw):FOODON_03301439', 'egg (raw):FOODON_03301075', 'egg product:zFOODON_BaseTerm_368'}
                input = wrd.split(' ')
                for i in range(len(input)):
                    if othrwrd.find(input[i]) == -1:
                        ctr += 1
                if wrd in retainedSet and ctr == 0 and wrd != othrwrd:
                    retainedSet.remove(wrd)

    for item in retainedSet:
        if item in termDict.keys():
            ky = termDict[item]
            returnItem = item + ":" + ky
            returnedSet.append(returnItem)
        if item in termDictAdd.keys():
            ky = termDictAdd[item]
            returnItem = item + ":" + ky
            returnedSet.append(returnItem)
        returnedSetFinal = set(returnedSet)
    return returnedSetFinal

def get_resource_dict(file_name, lower=False):
    """Return dictionary containing resource data from a CSV file.

    Arguments:
        * file_name <class "str">: CSV file containing key-value
            information on resources relevant to pipeline
    Return values:
        * class <"dict">: Contains key-value pairs from file_name
            * key: class <"str">
            * val: class <"str">
    Restrictions:
        * No information will be taken from the first row of file_name
        * Unique keys must appear as the first term on unique rows
        * Values should appear immediately after their corresponding
            key and a comma
            * Otherwise, an empty string value will be used
    Optional arguments:
        * lower <class "bool">: If set to True, all keys in the return
            value are converted to lowercase
    """
    # Return value
    ret = {}
    # Open file_name
    with open(resource_filename('lexmapr.resources', file_name)) as csvfile:
        # Skip first line
        next(csvfile)
        # Read file_name
        file_contents = csv.reader(csvfile, delimiter=",")
        # Iterate across rows in file_contents
        for row in file_contents:
            # Get key
            key = row[0].strip()
            # Lowercase key requested
            if lower:
                # Convert key to lowercase
                key = key.lower()
            try:
                # Get corresponding value
                val = row[1].strip()
            except IndexError:
                # No corresponding value
                val = ""
            # Add key-value pair to ret
            ret[key] = val
    # Return
    return ret

def get_all_resource_dicts():
    """Returns collection of all dictionaries used in pipeline.run.

    Return values:
        * class <"dict">: Contains key-value pairs corresponding to
            files in "resources/"
            * key: class <"str">
            * val: class <"dict">
    """
    # return value
    ret = {}
    # Synonyms of resource terms
    ret["synonyms"] = get_resource_dict("SynLex.csv")
    # Abbreviations of resource terms
    ret["abbreviations"] = get_resource_dict("AbbLex.csv")
    # Abbreviations of resource terms, all lowercase
    ret["abbreviation_lower"] = get_resource_dict("AbbLex.csv", True)
    # Non-english translations of resource terms
    ret["non_english_words"] = get_resource_dict("NefLex.csv")
    # Non-english translations of resource terms, all lowercase
    ret["non_english_words_lower"] = get_resource_dict("NefLex.csv", True)
    # Common misspellings of resource terms
    ret["spelling_mistakes"] = get_resource_dict("ScorLex.csv")
    # Common misspellings of resource terms, all lowercase
    ret["spelling_mistakes_lower"] = get_resource_dict("ScorLex.csv", True)
    # Terms corresponding to candidate processes
    ret["processes"] = get_resource_dict("candidateProcesses.csv")
    # Terms corresponding to semantic taggings
    ret["qualities"] = get_resource_dict("SemLex.csv")
    # Terms corresponding to semantic taggings, all lowercase
    ret["qualities_lower"] = get_resource_dict("SemLex.csv", True)
    # Terms corresponding to wikipedia collocations
    ret["collocations"] = get_resource_dict("wikipediaCollocations.csv")
    # Terms excluded from inflection treatment
    ret["inflection_exceptions"] = get_resource_dict("inflection-exceptions.csv", True)
    # Constrained list of stop words considered to be meaningless
    ret["stop_words"] = get_resource_dict("mining-stopwords.csv", True)
    # Suffixes to consider appending to terms when mining ontologies
    ret["suffixes"] = get_resource_dict("suffixes.csv")
    # ID-resource combinations
    ret["resource_terms_ID_based"] = get_resource_dict("CombinedResourceTerms.csv")
    # Swap keys and values in resource_terms_ID_based
    ret["resource_terms"] = {v:k for k,v in ret["resource_terms_ID_based"].items()}
    # Convert keys in resource_terms to lowercase
    ret["resource_terms_revised"] = {k.lower():v for k,v in ret["resource_terms"].items()}

    # Will contain permutations of resource terms
    ret["resource_permutation_terms"] = {}
    # Will contain permutations of resource terms with brackets
    ret["resource_bracketed_permutation_terms"] = {}
    # Iterate across resource_terms_revised
    for resource_term in ret["resource_terms_revised"]:
        # ID corresponding to resource_term
        resource_id = ret["resource_terms_revised"][resource_term]
        # List of tokens in resource_term
        resource_tokens = word_tokenize(resource_term.lower())
        # To limit performance overhead, we ignore resource_terms with
        # more than 7 tokens, as permutating too many tokens can be
        # costly. We also ignore NCBI taxon terms, as there are
        # ~160000 such terms.
        if len(resource_tokens)<7 and "NCBITaxon" not in resource_id:
            # resource_term contains a bracket
            if "(" in resource_term:
                # This will contain the term we permutate, as resource
                # terms with brackets cannot be permutated as is.
                term_to_permutate = ""
                # Portion of resource_term before brackets
                unbracketed_component = find_left_r(resource_term, "(", ")")
                # Portion of resource_term inside brackets
                bracketed_component = find_between_r(resource_term, "(", ")")
                # bracketed_component contains one or more commas
                if "," in bracketed_component:
                    # Parts of bracketed_component separated by commas
                    bracketed_component_parts = bracketed_component.split(",")
                    # bracketed_component_parts joined into one string
                    new_bracketed_component = " ".join(bracketed_component_parts)
                    # Adjust term_to_permutate accordingly
                    term_to_permutate = new_bracketed_component + " " + unbracketed_component
                # bracketed_component does not contain a comma
                else:
                    # Adjust term_to_permutate accordingly
                    term_to_permutate = bracketed_component + " " + unbracketed_component
                # All permutations of tokens in term_to_permutate
                permutations = all_permutations(term_to_permutate)
                # Iterate across permutated lists of tokens
                for permutation_tokens in permutations:
                    # permutation_tokens joined into string
                    permutation = ' '.join(permutation_tokens)
                    # Add permutation to appropriate dictionary
                    ret["resource_bracketed_permutation_terms"][permutation] = resource_id
            # resource_term does not contain a bracket
            else:
                # All permutations of tokens in resource_term
                permutations = all_permutations(resource_term)
                # Iterate across permutated lists of tokens
                for permutation_tokens in permutations:
                    # permutation_tokens joined into string
                    permutation = ' '.join(permutation_tokens)
                    # Add permutation to appropriate dictionary
                    ret["resource_permutation_terms"][permutation] = resource_id
    return ret

def get_path(file_name, prefix=""):
    """Returns path of file_name relative to pipeline.py.

    Specifically, returns a path with the following pattern:

        {path to pipeline.py}/{prefix}file_name

    The path does not need to currently exist.

    Arguments:
        * file_name <class "str">: Name of file we want the relative
            path to from pipeline.py.
    Return values:
        * <class "str">: Path to file_name
    Optional arguments:
        * prefix <class "str">: characters desired directly before
            file_name in returned path
    """
    # Return file_name appended to prefix and absolute path to
    # pipeline.py.
    return os.path.join(os.path.dirname(__file__), prefix+file_name)

def is_lookup_table_outdated():
    """Returns True if lookup_table.json is outdated.

    lookup_table.json is considered outdated if it has an older last
    modification time than any file in /resources.

    Return values:
        * <class "bool">: Indicates whether lookup_table.json is
            outdated
    Restrictions:
        * should only be called if lookup_table.json exists
    """
    # last modification time of lookup_table.json
    lookup_table_modification_time = os.path.getmtime(get_path("lookup_table.json"))

    # list of all file names in resources folder
    resource_names = [file_name for file_name in os.listdir(get_path("resources"))]
    # list of paths to all files in resources folder
    resource_paths = [get_path(file_name, "resources/") for file_name in resource_names]
    # list of last modification times for files in resources folder
    resources_files_modification_times = [os.path.getmtime(path) for path in resource_paths]
    # most recent modification time of a file in resources folder
    resources_folder_modification_time = max(resources_files_modification_times)

    # resources modified more recently than lookup_table.json
    if resources_folder_modification_time > lookup_table_modification_time:
        return True
    else:
        return False

def add_lookup_table_to_cache():
    """Saves nested dictionary of resources to a local file.

    The nested dictionary corresponds to the return value of
    get_all_resource_dicts, and is saved as lookup_table.json. If such
    a file already exists, it will be overwritten.
    """
    # Nested dictionary of all resource dictionaries used in run
    lookup_table = get_all_resource_dicts()
    # Open and write to lookup_table.json
    with open(get_path("lookup_table.json"), "w") as file:
        # Write lookup_table in JSON format
        json.dump(lookup_table, file)

def get_lookup_table_from_cache():
    """Return contents of lookup_table.json.

    The contents of lookup_table.json correspond to the return value of
    get_all_resource_dicts. Retrieving said contents from
    lookup_table.json is faster than running get_all_resource_dicts.

    If lookup_table.json does not exist, or is outdated (see
    is_lookup_table_outdated for details), a new lookup_table.json file
    is generated.

    Return values:
        * <class "dict">: Contains key-value pairs corresponding to
            files in "resources/"
            * key: <class "str">
            * val: <class "dict">
    """
    # lookup_table.json exists
    if os.path.isfile(get_path("lookup_table.json")):
        # lookup_table.json out of date
        if is_lookup_table_outdated():
            # add new lookup table to cache
            add_lookup_table_to_cache()
    # lookup_table.json does not exist
    else:
        # add lookup table to cache
        add_lookup_table_to_cache()
    # Open and read lookup_table.json
    with open(get_path("lookup_table.json"), "r") as file:
        # Python 3
        if sys.version_info[0] >= 3:
            # Return lookup_table contents in unicode
            return json.load(file)
        # Python 2
        else:
            # Return lookup_table contents in utf-8
            return json.load(file, object_pairs_hook=unicode_to_utf_8)

def unicode_to_utf_8(decoded_pairs):
    """object_pairs_hook to load json files without unicode values.

    Arguments:
        * decoded_pairs <class "list"> of <class "tuple">: Each tuple
            contains a key-value pair from a json file being loaded
    Return values:
        * <class "dict">: This corresponds to a value from the JSON
            file. Any unicode strings have been converted to utf-8.
    Restrictiond:
        * Should be called as the object_pairs_hook inside json.load
        * Should only be called in Python 2
    """
    # Return value
    ret = {}
    # Iterate over tuples in decoded_pairs
    for key, val in decoded_pairs:
        # key is unicode
        if isinstance(key, unicode):
            # Convert key to utf-8
            key = key.encode("utf-8")
        # val is unicode
        if isinstance(val, unicode):
            # Convert val to utf-8
            val = val.encode("utf-8")
        # Add key-val pair to ret
        ret[key] = val
    # Return ret
    return ret

def find_full_term_match(sample, lookup_table, cleaned_sample, status_addendum):
    """Retrieve an annotated, full-term match for a sample.

    Also returns relevant information for empty samples.

    Arguments:
        * sample <"str">: Name of sample we want to find a full-term
            match for.
        * lookup_table <"dict">: Nested dictionary containing resources
            needed to find a full_term_match. See
            get_lookup_table_from_cache for details.
        * cleaned_sample <"str">: Vleaned version of sample we will
            use to look for a full-term match, if one for sample does
            not exist.
        * status_addendum <"list"> of <"str">: Modifications made to
            sample in preprocessing.
    Return values:
        * <"dict">: Contains all relevant annotations for
            output headers.
            * key <"str">
            * val <"str">
    Restrictions:
        * cleaned_sample and status_addendum makes this function
            dependent on being called where it is called inside of run
            right now
    Exceptions raised:
        * MatchNotFoundError: Full-term match not found

    TODO:
        * simplify change-of-case treatments as follows:
            * resource dictionaries only contain lower-case
                words
            * check if sample.lower() is in a given dictionary
            * add appropriate status addendum
            * check if sample != sample.lower()
                * if true, add change-of-case treatment to
                    status addendum
        * reduce number of parameters
            * what we need, and makes sense as a parameter for this
                type of function
                * sample
                * lookup_table
                    * Rather than make lookup_table into a global
                        variable, we should pass it as a parameter
                        * It will allow us to more easily separate
                            pipeline.py functions into different files
                            in the future (if we choose to do so)
            * what does not look good as a parameter
                * cleaned_sample
                    * if we can make a helper function that generates
                        cleaned_sample, we can simply call it
                    * we can also call find_full_term_match in run with
                        sample, and then if nothing is found, with
                        cleaned_sample
                        * this would involve adjusting the outputted
                            annotations of run, so sample and
                            cleaned_sample outputs are more similar,
                            and we just have to add something like
                            "cleaned sample" to the beginning of
                            cleaned_sample output annotations
                * status_addendum
                    * Call to some sort of a preprocessing method to
                        get changes to status_addendum that occur
                        before find_full_term_match
                        * A function for component matching could have
                            the same call
    """
    # Tokens to retain for all_match_terms_with_resource_ids
    retained_tokens = []
    # Dictionary to return
    ret = dict.fromkeys([
        "matched_term",
        "all_match_terms_with_resource_ids",
        "retained_terms_with_resource_ids",
        "match_status_macro_level",
        "match_status_micro_level"],
        # Initialize values with empty string
        "")
    # Empty sample
    if sample == "":
        # Update ret
        ret.update({
            "matched_term": "--",
            "all_match_terms_with_resource_ids": "--",
            "match_status_micro_level": "Empty Sample",
        })
        # Return
        return ret
    # Full-term match without any treatment
    elif sample in lookup_table["resource_terms"]:
        # Term with we found a full-term match for
        matched_term = sample
        # Resource ID for matched_term
        resource_id = lookup_table["resource_terms"][matched_term]
        # Update retained_tokens
        retained_tokens.append(matched_term + ":" + resource_id)
        # Update status_addendum
        status_addendum.append("A Direct Match")
    # Full-term match with change-of-case in input data
    elif sample.lower() in lookup_table["resource_terms"]:
        # Term with we found a full-term match for
        matched_term = sample.lower()
        # Resource ID for matched_term
        resource_id = lookup_table["resource_terms"][matched_term]
        # Update retained_tokens
        retained_tokens.append(matched_term + ":" + resource_id)
        # Update status_addendum
        status_addendum.append("Change of Case in Input Data")
    # Full-term match with change-of-case in resource data
    elif sample.lower() in lookup_table["resource_terms_revised"]:
        # Term with we found a full-term match for
        matched_term = sample.lower()
        # Resource ID for matched_term
        resource_id = lookup_table["resource_terms_revised"][matched_term]
        # Update retained_tokens
        retained_tokens.append(matched_term + ":" + resource_id)
        # Update status_addendum
        status_addendum.append("Change of Case in Resource Data")
    # Full-term match with permutation of resource term
    elif sample.lower() in lookup_table["resource_permutation_terms"]:
        # Term we found a permutation for
        matched_term = sample.lower()
        # Resource ID for matched_term's permutation
        resource_id = lookup_table["resource_permutation_terms"][matched_term]
        # Permutation corresponding to matched_term
        matched_permutation = lookup_table["resource_terms_ID_based"][resource_id]
        # Update retained_tokens
        retained_tokens.append(matched_permutation + ":" + resource_id)
        # Update status_addendum
        status_addendum.append("Permutation of Tokens in Resource Term")
    # Full-term match with permutation of bracketed resource term
    elif sample.lower() in lookup_table["resource_bracketed_permutation_terms"]:
        # Term we found a permutation for
        matched_term = sample.lower()
        # Resource ID for matched_term's permutation
        resource_id = lookup_table["resource_bracketed_permutation_terms"][matched_term]
        # Permutation corresponding to matched_term
        matched_permutation = lookup_table["resource_terms_ID_based"][resource_id]
        # Update retained_tokens
        retained_tokens.append(matched_permutation + ":" + resource_id)
        # Update status_addendum
        status_addendum.append("Permutation of Tokens in Bracketed Resource Term")
    # Full-term cleaned sample match without any treatment
    elif cleaned_sample.lower() in lookup_table["resource_terms"]:
        # Term with we found a full-term match for
        matched_term = cleaned_sample.lower()
        # Resource ID for matched_term
        resource_id = lookup_table["resource_terms"][matched_term]
        # Update retained_tokens
        retained_tokens.append(matched_term + ":" + resource_id)
        # Update status_addendum
        status_addendum.append("A Direct Match with Cleaned Sample")
    # Full-term cleaned sample match with change-of-case in
    # resource data.
    elif cleaned_sample.lower() in lookup_table["resource_terms_revised"]:
        # Term with we found a full-term match for
        matched_term = cleaned_sample.lower()
        # Resource ID for matched_term
        resource_id = lookup_table["resource_terms_revised"][matched_term]
        # Update retained_tokens
        retained_tokens.append(matched_term + ":" + resource_id)
        # Update status_addendum
        status_addendum.append("Change of Case of Resource Terms")
    # Full-term cleaned sample match with permutation of
    # resource term.
    elif cleaned_sample.lower() in lookup_table["resource_permutation_terms"]:
        # Term we found a permutation for
        matched_term = cleaned_sample.lower()
        # Resource ID for matched_term's permutation
        resource_id = lookup_table["resource_permutation_terms"][matched_term]
        # Permutation corresponding to matched_term
        matched_permutation = lookup_table["resource_terms_ID_based"][resource_id]
        # Update retained_tokens
        retained_tokens.append(matched_permutation + ":" + resource_id)
        # Update status_addendum
        status_addendum.append("Permutation of Tokens in Resource Term")
    # Full-term cleaned sample match with permutation of
    # bracketed resource term.
    elif cleaned_sample.lower() in lookup_table["resource_bracketed_permutation_terms"]:
        # Term we found a permutation for
        matched_term = cleaned_sample.lower()
        # Resource ID for matched_term's permutation
        resource_id = lookup_table["resource_bracketed_permutation_terms"][matched_term]
        # Permutation corresponding to matched_term
        matched_permutation = lookup_table["resource_terms_ID_based"][resource_id]
        # Update retained_tokens
        retained_tokens.append(matched_permutation + ":" + resource_id)
        # Update status_addendum
        status_addendum.append("Permutation of Tokens in Bracketed Resource Term")
    # A full-term cleaned sample match with multi-word
    # collocation from Wikipedia exists.
    elif cleaned_sample.lower() in lookup_table["collocations"]:
        # Term we found a full-term match for
        matched_term = cleaned_sample.lower()
        # Resource ID for matched_term
        resource_id = lookup_table["collocations"][matched_term]
        # Update retained_tokens
        retained_tokens.append(matched_term + ":" + resource_id)
        # Update status_addendum
        status_addendum.append(
            "New Candidadte Terms -validated with Wikipedia Based Collocation Resource"
        )
    # Full-term match not found
    else:
        resource_terms_revised = lookup_table["resource_terms_revised"]
        # Find all suffixes that when appended to sample, are
        # in resource_terms_revised.
        matched_suffixes = [
            s for s in lookup_table["suffixes"] if sample+" "+s in resource_terms_revised
        ]
        # Find all suffixes that when appended to cleaned
        # sample, are in resource_terms_revised.
        matched_clean_suffixes = [
            s for s in lookup_table["suffixes"] if cleaned_sample+" "+s in resource_terms_revised
        ]
        # A full-term match with change of resource and suffix
        # addition exists.
        if matched_suffixes:
            # Term with first suffix in suffixes that provides
            # a full-term match.
            term_with_suffix = sample + " " + matched_suffixes[0]
            # Term we add a suffix to
            matched_term = sample.lower()
            # Resource ID for matched_term
            resource_id = resource_terms_revised[term_with_suffix]
            # Update retained_tokens
            retained_tokens.append(term_with_suffix + ":" + resource_id)
            # Update status_addendum
            status_addendum.append(
                "[Change of Case of Resource and Suffix Addition- "
                + matched_suffixes[0]
                + " to the Input]"
            )
        # A full-term cleaned sample match with change of resource and
        # suffix addition exists.
        elif matched_clean_suffixes:
            # Term with first suffix in suffixes that provides
            # a full-term match.
            term_with_suffix = cleaned_sample.lower() + " " + matched_clean_suffixes[0]
            # Term we cleaned and added a suffix to
            matched_term = sample.lower()
            # Resource ID for matched_term
            resource_id = resource_terms_revised[term_with_suffix]
            # Update retained_tokens
            retained_tokens.append(term_with_suffix + ":" + resource_id)
            # Update status_addendum
            status_addendum.append(
                "[CleanedSample-Change of Case of Resource and Suffix Addition- "
                + matched_clean_suffixes[0]
                + " to the Input]"
            )
        # No full-term match possible with suffixes either
        else:
            raise MatchNotFoundError("Full-term match not found for: " + sample)

    # If we reach here, we had a full-term match with a
    # non-empty sample.

    # status_addendum without duplicates
    final_status = set(status_addendum)
    # Update ret
    ret.update({
        "matched_term": matched_term,
        "all_match_terms_with_resource_ids":
            str(list(retained_tokens)),
        "retained_terms_with_resource_ids":
            str(list(retained_tokens)),
        "match_status_macro_level": "Full Term Match",
        "match_status_micro_level": str(list(final_status)),
    })
    # Return
    return ret

def find_component_match(cleaned_sample, lookup_table, status_addendum):
    """Finds 1-5 gram component matches of cleaned_sample.

    Arguments:
        * cleaned_sample <"str">: Sample that has been cleaned up in
            run
            * See TODO list about eventually using sample instead
        * lookup_table <"dict">: Nested dictionary containing resources
            needed to find a component match. See
            get_lookup_table_from_cache for details.
        * status_addendum <"list"> of <"str">: Modifications made to
            sample in preprocessing.
    Return values:
        * <"dict">: Contains a list of 1-5 gram component matches, and
            tokens covered by said matches.
            * key <"str">
            * val <"list" of "str">
    Restrictions:
        * cleaned_sample and status_addendum makes this function
            dependent on being called where it is called inside of run
            right now

    TODO:
        * discuss whether we should allow updating of status_addendum
            when the permutatation does not get added as a component
            match
        * eliminate unneccessary parameters
            * what we should keep
                * cleaned_sample
                    * this should really be sample, for greater
                        function independence
                * lookup_table
            * what we should try to get rid of
                * status_addendum
                    * Suggest in find_full_term_match to call some sort
                        of preprocessing method to get changes to
                        status_addendum prior to find_full_term_match
                        * Could do something similar in
                            find_component_match
                            * Would also allow use of sample instead of
                                cleaned_sample as parameter
    """
    # Return value
    ret = {
        # Component matches made from cleaned_sample
        "component_matches": [],
        # Tokens covered in component matches
        "token_matches": [],
    }
    # Iterate through numbers 5 to 1
    for i in range(5, 0, -1):
        # Iterate through i-gram chunks of cleaned_chunk
        for gram_chunk in get_gram_chunks(cleaned_sample, i):
            # gram_chunk concatenated into a single string
            concatenated_gram_chunk = " ".join(gram_chunk)
            # Tokenized list of concatenated_gram_chunk
            gram_tokens = word_tokenize(concatenated_gram_chunk)
            # Flag indicating successful component match for i
            match_found = False
            # Permutations of concatenated_gram_chunk
            permutations = all_permutations(concatenated_gram_chunk)
            # Iterate over all permutations
            for permutation in permutations:
                # Join elements of permutation into a single string
                joined_permutation = ' '.join(permutation)
                # joined_permutation is an abbreviation or acronym
                if joined_permutation in lookup_table["abbreviations"]:
                    # Expand joined_permutation
                    joined_permutation = lookup_table["abbreviations"][joined_permutation]
                    # Adjust status_addendum accordingly
                    status_addendum.append("Abbreviation-Acronym Treatment")
                # joined_permutation is a non-english word
                if joined_permutation in lookup_table["non_english_words"]:
                    # Translate joined_permutation
                    joined_permutation = lookup_table["non_english_words"][joined_permutation]
                    # Adjust status_addendum accordingly
                    status_addendum.append("Non English Language Words Treatment")
                # joined_permutation is a synonym
                if joined_permutation in lookup_table["synonyms"]:
                    # Translate joined_permutation to synonym
                    joined_permutation = lookup_table["synonyms"][joined_permutation]
                    # Adjust status_addendum accordingly
                    status_addendum.append("Synonym Usage")

                def handle_component_match(component_match):
                    """Changes local variables upon component match.
                    """
                    ret["component_matches"].append(component_match)
                    ret["token_matches"] += gram_tokens

                # Component match not yet found
                if not match_found:
                    # There is a full-term component match with no
                    # treatment or change-of-case in resource term.
                    if (joined_permutation in lookup_table["resource_terms"]
                        or joined_permutation in lookup_table["resource_terms_revised"]):
                        # Adjust local variables as needed
                        handle_component_match(joined_permutation)
                        # Set match_found to True
                        match_found = True
                    # There is a full-term component match with
                    # permutation of bracketed resource term.
                    elif (joined_permutation in
                        lookup_table["resource_bracketed_permutation_terms"]):

                        # Adjust local variables as needed
                        handle_component_match(joined_permutation)
                        # Adjust status_addendum accordingly
                        status_addendum.append("Permutation of Tokens in Bracketed Resource Term")
                        # Set match_found to True
                        match_found = True
                    else:
                        # Find all suffixes that when appended to
                        # joined_permutation, are in
                        # resource_terms_revised.
                        matched_suffixes = [
                            s for s in lookup_table["suffixes"]
                            if joined_permutation+" "+s in lookup_table["resource_terms_revised"]
                            ]
                        # A full-term component match with change of
                        # resource and suffix addition exists.
                        if matched_suffixes:
                            # Component with first suffix in suffixes
                            # that provides a full-term match.
                            component_with_suffix = joined_permutation + " " + matched_suffixes[0]
                            # Adjust local variables as needed
                            handle_component_match(component_with_suffix)
                            # Adjust status_addendum accordingly
                            status_addendum.append(
                                "Suffix Addition- " + matched_suffixes[0] + " to the Input"
                            )
                            # Set match_found to True
                            match_found = True
                        # 1- or 2-gram component match
                        elif i < 3:
                            # A full-term component match using
                            # semantic resources exists.
                            if (joined_permutation in lookup_table["qualities_lower"]):
                                # Adjust local variables as needed
                                handle_component_match(joined_permutation)
                                # Adjust status_addendum accordingly
                                status_addendum.append("Using Semantic Tagging Resources")
                                # Set match_found to True
                                match_found = True
                            # A full-term 1-gram component match using
                            # candidate processes exists.
                            elif i==1 and joined_permutation in lookup_table["processes"]:
                                # Adjust local variables as needed
                                handle_component_match(joined_permutation)
                                # Adjust status_addendum accordingly
                                status_addendum.append("Using Candidate Processes")
                                # Set match_found to True
                                match_found = True
                            # No component match for permutation
                            else:
                                # Move to next permutation
                                continue
    return ret

class MatchNotFoundError(Exception):
    """Exception class for indicating failed full-term matches.

    This subclass inherits it behaviour from the Exception class, and
    should be raised when a full-term match for a sample is
    not found.

    Instance variables:
        * message <class "str">

    TODO:
        * do we need this class?
            * perhaps the try clause that relied on this exception
                could instead use KeyError
    """

    def __init__(self, message):
        """Creates instance variable used as error message.

        Arguments:
            * message: User-inputted error message to be raised
        """
        self.message = message

    def __str__(self):
        """Return message when this class is raised as an exception."""
        return repr(self.message)

def run(args):
    """
    Main text mining pipeline.
    """
    punctuations = ['-', '_', '(', ')', ';', '/', ':', '%']  # Current punctuations for basic treatment
    covered_tokens = []
    remainingAllTokensSet = []
    remainingTokenSet = []
    prioritizedRetainedSet=[]
    samplesDict = collections.OrderedDict()
    samplesList = []
    samplesSet = []

    # This will be a nested dictionary of all resource dictionaries used by
    # run. It is retrieved from cache if possible. See
    # get_lookup_table_from_cache docstring for details.
    lookup_table = get_lookup_table_from_cache()

    # Output file Column Headings
    OUTPUT_FIELDS = [
        "Sample_Id",
        "Sample_Desc",
        "Cleaned_Sample"
    ]

    if args.format == 'full':
        OUTPUT_FIELDS += [
            "Phrase_POS_Tagged",
            "Probable_Candidate_Terms",
            "Matched_Term",
            "All_matched_Terms_with_Resource_IDs",
            "Retained_Terms_with_Resource_IDs",
            "Number of Components(In case of Component Match)",
            "Match_Status(Macro Level)",
            "Match_Status(Micro Level)",
            "Remaining_Tokens",
            "Different Components(In case of Component Match)"
        ]
    
    fw = open(args.output, 'w') if args.output else sys.stdout     # Main output file
    fw.write('\t'.join(OUTPUT_FIELDS))
    
    with open(args.input_file) as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')
        ctr = 0
        for row in readCSV:
            if ctr > 0:  # skips the first row in CSV file as header row
                samplesList.append(row[1])
                samid = row[0]
                samp = row[1]
                # termFreq=row[2]
                samplesDict[samid.strip()] = samp.strip()
            ctr += 1
    
    # Iterate over samples for matching to ontology terms
    for k, v in samplesDict.items():
        sampleid = k
        sample = v
        trigger = False
        status = ""  # variable reflecting status of Matching to be displayed for evry rule/section
        status_addendum = []
        final_status = []
        del final_status [:]
        remaining_tokens = []
        #Writing in the output file with sampleid and sample to start with
        # output fields:
        #   sample_id:   sampleid
        #   sample_desc: sample
        fw.write('\n' + sampleid + '\t' + sample)

        sample = punctuationTreatment(sample, punctuations)  # Sample gets simple punctuation treatment
        sample = re.sub(' +', ' ', sample)  # Extra innner spaces are removed
        sampleTokens = word_tokenize(sample.lower())    #Sample is tokenized into tokenList

        cleaned_sample = ""  # Phrase that will be used for cleaned sample
        lemma = ""

        for tkn in sampleTokens:
            remaining_tokens.append(tkn.lower())  # To start with all remaining tokens in set

        # ===Few preliminary things- Inflection,spelling mistakes, Abbreviations, acronyms, foreign words, Synonyms taken care of
        for tkn in sampleTokens:

            # Some preprocessing (only limited or controlled) Steps
            tkn = preprocess(tkn)

            # Plurals are converted to singulars with exceptions
            if (tkn.endswith("us") or tkn.endswith("ia") or tkn.endswith("ta")):  # for inflection exception in general-takes into account both lower and upper case (apart from some inflection-exception list used also in next
                lemma = tkn
            elif (tkn not in lookup_table["inflection_exceptions"]):  # Further Inflection Exception list is taken into account
                lemma = inflection.singularize(tkn)
                if (tkn != lemma):  #Only in case when inflection makes some changes in lemma
                    status_addendum.append("Inflection (Plural) Treatment")
            else:
                lemma = tkn

            # Misspellings are dealt with  here
            if (lemma in lookup_table["spelling_mistakes"].keys()):  # spelling mistakes taken care of
                lemma = lookup_table["spelling_mistakes"][lemma]
                status_addendum.append("Spelling Correction Treatment")
            elif (lemma.lower() in lookup_table["spelling_mistakes_lower"].keys()):
                lemma = lookup_table["spelling_mistakes_lower"][lemma.lower()]
                status_addendum.append("Change Case and Spelling Correction Treatment")
            if (lemma in lookup_table["abbreviations"].keys()):  # Abbreviations, acronyms, foreign language words taken care of- need rule for abbreviation e.g. if lemma is Abbreviation
                lemma = lookup_table["abbreviations"][lemma]
                status_addendum.append("Abbreviation-Acronym Treatment")
            elif (lemma.lower() in lookup_table["abbreviation_lower"].keys()):
                lemma = lookup_table["abbreviation_lower"][lemma.lower()]
                status_addendum.append("Change Case and Abbreviation-Acronym Treatment")

            if (lemma in lookup_table["non_english_words"].keys()):  # Non English language words taken care of
                lemma = lookup_table["non_english_words"][lemma]
                status_addendum.append("Non English Language Words Treatment")
            elif (lemma.lower() in lookup_table["non_english_words_lower"].keys()):
                lemma = lookup_table["non_english_words_lower"][lemma.lower()]
                status_addendum.append("Change Case and Non English Language Words Treatment")


            # ===This will create a cleaned sample after above treatments [Here we are making new phrase now in lower case]
            if (not cleaned_sample and lemma.lower() not in lookup_table["stop_words"]):  # if newphrase is empty and lemma is in not in stopwordlist (abridged according to domain)
                cleaned_sample = lemma.lower()
            elif (
                lemma.lower() not in lookup_table["stop_words"]):  # if newphrase is not empty and lemma is in not in stopwordlist (abridged according to domain)
                cleaned_sample = cleaned_sample + " " + lemma.lower()

            cleaned_sample = re.sub(' +', ' ', cleaned_sample)  # Extra innner spaces removed from cleaned sample

            if (cleaned_sample in lookup_table["abbreviations"].keys()):  # NEED HERE AGAIN ? Abbreviations, acronyms, non English words taken care of- need rule for abbreviation
                cleaned_sample = lookup_table["abbreviations"][cleaned_sample]
                status_addendum.append("Cleaned Sample and Abbreviation-Acronym Treatment")
            elif (cleaned_sample in lookup_table["abbreviation_lower"].keys()):
                cleaned_sample = lookup_table["abbreviation_lower"][cleaned_sample]
                status_addendum.append("Cleaned Sample and Abbreviation-Acronym Treatment")

            if (cleaned_sample in lookup_table["non_english_words"].keys()):  # non English words taken care of
                cleaned_sample = lookup_table["non_english_words"][cleaned_sample]
                status_addendum.append("Cleaned Sample and Non English Language Words Treatment")
            elif (cleaned_sample in lookup_table["non_english_words_lower"].keys()):
                cleaned_sample = lookup_table["non_english_words_lower"][cleaned_sample]
                status_addendum.append("Cleaned Sample and Non English Language Words Treatment")

        # Here we are making the tokens of cleaned sample phrase
        newSampleTokens = word_tokenize(cleaned_sample.lower())
        tokens_pos = pos_tag(newSampleTokens)
        if args.format == "full":
            # output fields:
            #   'cleaned_sample': cleaned_sample
            #   'phrase_pos_tagged': str(tokens_pos)
            fw.write('\t' + cleaned_sample + '\t' + str(tokens_pos))
        else:
            # output_fields:
            #   'cleaned_sample': cleaned_sample
            fw.write('\t' + cleaned_sample )

        # This part works for getting the Candidate phrase based on POS tagging and application of the relevant rule  [Not a major contributor -not used now except for printing]
        qualityList = []
        phraseStr = ""
        prevPhraseStr = ""
        prevTag = "X"
        for tkp in tokens_pos:
            # print(tkp)
            currentTag = tkp[1]
            # qualityListForSet.append(tkp[1])
            if ((tkp[1] == 'NN' or tkp[1] == 'NNS') and (prevTag == "X" or prevTag == "NN" or prevTag == "NNS")):
                phraseStr = tkp[0]
                if not prevPhraseStr:
                    prevPhraseStr = phraseStr
                else:
                    prevPhraseStr = prevPhraseStr + " " + phraseStr
                    prevTag = currentTag
        if args.format == 'full':
            # output field:
            #   'probable_candidate_terms': str(prevPhraseStr)
            fw.write('\t' + str(prevPhraseStr))

        #---------------------------STARTS APPLICATION OF RULES-----------------------------------------------
        try:
            # Find full-term match for sample
            full_term_match = find_full_term_match(sample, lookup_table, cleaned_sample, status_addendum)
            # Write to all headers
            if args.format == "full":
                fw.write("\t" + full_term_match["matched_term"] + "\t"
                    + full_term_match["all_match_terms_with_resource_ids"]
                    + "\t"
                    + full_term_match["retained_terms_with_resource_ids"]
                    + "\t" + "\t"
                    + full_term_match["match_status_macro_level"] + "\t"
                    + full_term_match["match_status_micro_level"])
            # Write to some headers
            else:
                fw.write("\t" + full_term_match["matched_term"] + "\t"
                    + full_term_match["all_match_terms_with_resource_ids"])
            # Tokenize sample
            sample_tokens = word_tokenize(sample.lower())
            # Add all tokens to covered_tokens
            [covered_tokens.append(token) for token in sample_tokens]
            # Remove all tokens from remaining_tokens
            [remaining_tokens.remove(token) for token in sample_tokens]
            # Set trigger to True
            trigger = True
        # Full-term match not found
        except MatchNotFoundError:
            # Continue on
            pass

        # Component Matches Section
        if (not trigger):
            logger.debug("We will go further with other rules now targetting components of input data")

            # 1-5 gram component matches for cleaned_sample, and
            # tokens covered by said matches. See find_component_match
            # docstring for details.
            component_and_token_matches = find_component_match(cleaned_sample, lookup_table,
                                               status_addendum)

            partial_matches = set(component_and_token_matches["component_matches"])  # Makes a set of all matched components from the above processing
            status = "GComponent Match"             #Note: GComponent instead of is used as tag to help sorting later in result file

            # Iterate over token_matches in component_and_token_matches
            for token in component_and_token_matches["token_matches"]:
                # Add token to covered_tokens
                covered_tokens.append(token)
                # Token is in remaining_tokens
                if token in remaining_tokens:
                    # Remove token from remaining_tokens
                    remaining_tokens.remove(token)

            remSetConv = set(remaining_tokens)
            coveredAllTokensSetConv=set(covered_tokens)
            remSetDiff = remSetConv.difference(coveredAllTokensSetConv)
            # Checking of coverage of tokens for sample as well overall dataset
            coveredTSet = []
            remainingTSet = []
            for tknstr in partial_matches:
                strTokens = word_tokenize(tknstr.lower())
                for eachTkn in strTokens:
                    if ("==" in eachTkn):
                        resList = eachTkn.split("==")
                        entityPart = resList[0]
                        entityTag = resList[1]
                        coveredTSet.append(entityPart)
                        covered_tokens.append(entityPart)
                    else:
                        coveredTSet.append(eachTkn)
                        covered_tokens.append(eachTkn)

            # To find the remaining unmatched token set (Currently has those ones also which otherwise are removed by lexicons such as - synonyms. So need to be removed)
            for chktkn in sampleTokens:
                if (chktkn not in coveredTSet):
                    remainingTSet.append(chktkn)
                if (chktkn not in covered_tokens):
                    remainingTokenSet.append(chktkn)

            # Matches in partial_matches, and their corresponding IDs
            partial_matches_with_ids = []
            #Decoding the partial matched set to get back resource ids
            for matchstring in partial_matches:
                if (matchstring in lookup_table["resource_terms"].keys()):
                    resourceId = lookup_table["resource_terms"][matchstring]
                    partial_matches_with_ids.append(matchstring + ":" + resourceId)
                elif (matchstring in lookup_table["resource_terms_revised"].keys()):
                    resourceId = lookup_table["resource_terms_revised"][matchstring]
                    partial_matches_with_ids.append(matchstring + ":" + resourceId)
                elif (matchstring in lookup_table["resource_permutation_terms"].keys()):
                    resourceId = lookup_table["resource_permutation_terms"][matchstring]
                    resourceOriginalTerm = lookup_table["resource_terms_ID_based"][resourceId]
                    partial_matches_with_ids.append(resourceOriginalTerm.lower() + ":" + resourceId)
                elif (matchstring in lookup_table["resource_bracketed_permutation_terms"].keys()):
                    resourceId = lookup_table["resource_bracketed_permutation_terms"][matchstring]
                    resourceOriginalTerm = lookup_table["resource_terms_ID_based"][resourceId]
                    resourceOriginalTerm = resourceOriginalTerm.replace(",", "=")
                    partial_matches_with_ids.append(resourceOriginalTerm.lower() + ":" + resourceId)
                elif (matchstring in lookup_table["processes"].keys()):
                    resourceId = lookup_table["processes"][matchstring]
                    partial_matches_with_ids.append(matchstring + ":" + resourceId)
                elif (matchstring in lookup_table["qualities"].keys()):
                    resourceId = lookup_table["qualities"][matchstring]
                    partial_matches_with_ids.append(matchstring + ":" + resourceId)
                elif (matchstring in lookup_table["qualities_lower"].keys()):
                    resourceId = lookup_table["qualities_lower"][matchstring]
                    partial_matches_with_ids.append(matchstring + ":" + resourceId)
                elif ("==" in matchstring):
                    resList = matchstring.split("==")
                    entityPart = resList[0]
                    entityTag = resList[1]
                    partial_matches_with_ids.append(entityPart + ":" + entityTag)

            partialMatchedResourceListSet = set(partial_matches_with_ids)   # Makes a set from list of all matched components with resource ids
            retainedSet = []

            # If size of set is more than one member, looks for the retained matched terms by defined criteria
            if (len(partialMatchedResourceListSet) > 0):
                retainedSet = retainedPhrase(str(partialMatchedResourceListSet))
                logger.debug("retainedSet " + str(retainedSet))
                # HERE SHOULD HAVE ANOTHER RETAING SET

            final_status = set(status_addendum)

            # In case it is for componet matching and we have at least one component matched
            if (len(partial_matches) > 0):
                if args.format == 'full':
                    fw.write('\t' + str(list(partial_matches)) + '\t' + str(list(partialMatchedResourceListSet)) + '\t' + str(list(retainedSet)) + '\t' + str(len(retainedSet)) + '\t' + status + '\t' + str(list(final_status)) + '\t' + str(list(remSetDiff)))
                compctr = 0
                if args.format == 'full':
                    fw.write("\t")
                
                if args.format != 'full':
                    for memb in retainedSet:   # This for indv column print
                        fw.write("\t" + str(memb))

                if args.format == 'full':
                    for comp in retainedSet:
                        compctr += 1
                        if (compctr == 1):
                            fw.write("Component" + str(compctr) + "-> " + str(comp))
                        else:
                            fw.write(", Component" + str(compctr) + "-> " + str(comp))
                    trigger = True
                else:        # In case of no matching case
                    if args.format == 'full':
                        fw.write('\t' + str(list(partial_matches)) + '\t' + str(list(partial_matches_with_ids)) + '\t\t' + "\t" + "Sorry No Match" + "\t" + str(list(remaining_tokens)))

    #Output files closed
    if fw is not sys.stdout:
        fw.close()
