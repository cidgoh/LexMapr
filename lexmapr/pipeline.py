#!/usr/bin/env python

import collections
import csv
import itertools
from itertools import combinations
import json
import os
import re
import sys

from dateutil.parser import parse
import inflection
from nltk.tokenize import word_tokenize
from nltk.tokenize.moses import MosesDetokenizer
from nltk import pos_tag
from pkg_resources import resource_filename

from lexmapr.ontofetch import Ontology


def singularize_token(tkn, lookup_table, status_addendum):
    lemma=tkn
    if (tkn.endswith("us") or tkn.endswith("ia") or tkn.endswith(
            "ta")):  # for inflection exception in general-takes into account both lower and upper case (apart from some inflection-exception list used also in next
        lemma = tkn
    elif (tkn not in lookup_table[
        "inflection_exceptions"]):  # Further Inflection Exception list is taken into account
        lemma = inflection.singularize(tkn)
    if (tkn != lemma):  # Only in case when inflection makes some changes in lemma
        status_addendum.append("Inflection (Plural) Treatment")

    return lemma


def spelling_correction(lemma, lookup_table, status_addendum):
    if (lemma in lookup_table["spelling_mistakes"].keys()):  # spelling mistakes taken care of
        lemma = lookup_table["spelling_mistakes"][lemma]
        status_addendum.append("Spelling Correction Treatment")
    elif (lemma.lower() in lookup_table["spelling_mistakes_lower"].keys()):
        lemma = lookup_table["spelling_mistakes_lower"][lemma.lower()]
        status_addendum.append("Change Case and Spelling Correction Treatment")
    return lemma


def abbreviation_normalization_token(lemma, lookup_table, status_addendum):
    if (lemma in lookup_table[
        "abbreviations"].keys()):
        lemma = lookup_table["abbreviations"][lemma]
        status_addendum.append("Abbreviation-Acronym Treatment")
    elif (lemma.lower() in lookup_table["abbreviations_lower"].keys()):
        lemma = lookup_table["abbreviations_lower"][lemma.lower()]
        status_addendum.append("Change Case and Abbreviation-Acronym Treatment")
    return lemma


def abbreviation_normalization_phrase(phrase, lookup_table, status_addendum):
    if (phrase in lookup_table[
        "abbreviations"].keys()):  # NEED HERE AGAIN ? Abbreviations, acronyms, non English words taken care of- need rule for abbreviation
        cleaned_sample = lookup_table["abbreviations"][phrase]
        status_addendum.append("Cleaned Sample and Abbreviation-Acronym Treatment")
    elif (phrase in lookup_table["abbreviations_lower"].keys()):
        cleaned_sample = lookup_table["abbreviations_lower"][phrase]
        status_addendum.append("Cleaned Sample and Abbreviation-Acronym Treatment")
    return phrase


def non_English_normalization_token(lemma, lookup_table, status_addendum):
    if (lemma in lookup_table["non_english_words"].keys()):  # Non English language words taken care of
        lemma = lookup_table["non_english_words"][lemma]
        status_addendum.append("Non English Language Words Treatment")
    elif (lemma.lower() in lookup_table["non_english_words_lower"].keys()):
        lemma = lookup_table["non_english_words_lower"][lemma.lower()]
        status_addendum.append("Change Case and Non English Language Words Treatment")
    return lemma


def non_English_normalization_phrase(phrase, lookup_table, status_addendum):
    if (phrase in lookup_table["non_english_words"].keys()):  # non English words taken care of
        phrase = lookup_table["non_english_words"][phrase]
        status_addendum.append("Cleaned Sample and Non English Language Words Treatment")
    elif (phrase in lookup_table["non_english_words_lower"].keys()):
        phrase = lookup_table["non_english_words_lower"][phrase]
        status_addendum.append("Cleaned Sample and Non English Language Words Treatment")
    return phrase


def get_cleaned_sample(cleaned_sample,lemma, lookup_table):
    if (not cleaned_sample and lemma.lower() not in lookup_table[
        "stop_words"]):  # if newphrase is empty and lemma is in not in stopwordlist (abridged according to domain)
        cleaned_sample = lemma.lower()
    elif (
                lemma.lower() not in lookup_table[
                "stop_words"]):  # if newphrase is not empty and lemma is in not in stopwordlist (abridged according to domain)

        cleaned_sample = cleaned_sample + " " + lemma.lower()
    return cleaned_sample


def get_component_match_withids(partial_matches, lookup_table):
    # Matches in partial_matches, and their corresponding IDs
    partial_matches_with_ids = []
    # Decoding the partial matched set to get back resource ids
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
    return partial_matches_with_ids


def remove_duplicate_tokens(input_string):
    refined_string=""
    new_phrase_set = []
    string_tokens = word_tokenize(input_string.lower())
    for tkn in string_tokens:
        new_phrase_set.append(tkn)
    refined_string = MosesDetokenizer().detokenize(new_phrase_set, return_str=True)
    refined_string=refined_string.strip()
    return refined_string


def read_input_file(input_file):
    sample_list=[]
    sample_dict = collections.OrderedDict()
    with open(input_file) as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')
        ctr = 0
        for row in readCSV:
            if ctr > 0:  # skips the first row in CSV file as header row
                sample_list.append(row[1])
                samid = row[0]
                samp = row[1]
                # termFreq=row[2]               #NN To be removed
                sample_dict[samid.strip()] = samp.strip()
            ctr += 1
    return sample_dict


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
        * token <"str">: Token from string being processed in
            run
    Return values:
        * <"str">: token with irrelevant characters removed
    """
    # drop possessives, rightmost comma and rightmost period and return
    return token.replace("\'s", "").rstrip("', ").rstrip(". ")


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
    termDict = {}
    termDictAdd = {}
    wordList = []
    retainedSet = []
    returnedSet = []
    for x in termList:
        x.replace("'", "")
        lst2 = x.split(":", 1)
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
            for othrwrd in wordList:
                ctr = 0
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


def create_lookup_table_skeleton():
    """Generate an empty lookup table.

    This means it has all necessary keys, but the values are empty
    dictionaries.

    :return: Empty lookup table
    :rtype: dict
    """
    return {"synonyms": {},
            "abbreviations": {},
            "abbreviations_lower": {},
            "non_english_words": {},
            "non_english_words_lower": {},
            "spelling_mistakes": {},
            "spelling_mistakes_lower": {},
            "processes": {},
            "qualities": {},
            "qualities_lower": {},
            "collocations": {},
            "inflection_exceptions": {},
            "stop_words": {},
            "suffixes": {},
            "parents": {},
            "resource_terms_ID_based": {},
            "resource_terms": {},
            "resource_terms_revised": {},
            "resource_permutation_terms": {},
            "resource_bracketed_permutation_terms": {}}


def add_predefined_resources_to_lookup_table(lookup_table):
    """Add elements from ``resources/`` to lookup table.

    :param lookup_table: See create_lookup_table_skeleton for the
                         expected format of this parameter
    :type lookup_table: dict
    :return: Modified ``lookup_table``
    :rtype: dict
    """
    # Synonyms of resource terms
    lookup_table["synonyms"] = get_resource_dict("SynLex.csv")
    # Abbreviations of resource terms
    lookup_table["abbreviations"] = get_resource_dict("AbbLex.csv")
    # Abbreviations of resource terms, all lowercase
    lookup_table["abbreviations_lower"] = get_resource_dict("AbbLex.csv", True)
    # Non-english translations of resource terms
    lookup_table["non_english_words"] = get_resource_dict("NefLex.csv")
    # Non-english translations of resource terms, all lowercase
    lookup_table["non_english_words_lower"] = get_resource_dict("NefLex.csv", True)
    # Common misspellings of resource terms
    lookup_table["spelling_mistakes"] = get_resource_dict("ScorLex.csv")
    # Common misspellings of resource terms, all lowercase
    lookup_table["spelling_mistakes_lower"] = get_resource_dict("ScorLex.csv", True)
    # Terms corresponding to candidate processes
    lookup_table["processes"] = get_resource_dict("candidateProcesses.csv")
    # Terms corresponding to semantic taggings
    lookup_table["qualities"] = get_resource_dict("SemLex.csv")
    # Terms corresponding to semantic taggings, all lowercase
    lookup_table["qualities_lower"] = get_resource_dict("SemLex.csv", True)
    # Terms corresponding to wikipedia collocations
    lookup_table["collocations"] = get_resource_dict("wikipediaCollocations.csv")
    # Terms excluded from inflection treatment
    lookup_table["inflection_exceptions"] = get_resource_dict("inflection-exceptions.csv", True)
    # Constrained list of stop words considered to be meaningless
    lookup_table["stop_words"] = get_resource_dict("mining-stopwords.csv", True)
    # Suffixes to consider appending to terms when mining ontologies
    lookup_table["suffixes"] = get_resource_dict("suffixes.csv")
    # ID-resource combinations
    lookup_table["resource_terms_ID_based"] = get_resource_dict("CombinedResourceTerms.csv")
    # Swap keys and values in resource_terms_ID_based
    lookup_table["resource_terms"] = {
        v: k for k, v in lookup_table["resource_terms_ID_based"].items()
    }
    # Convert keys in resource_terms to lowercase
    lookup_table["resource_terms_revised"] = {
        k.lower(): v for k, v in lookup_table["resource_terms"].items()
    }

    # Will contain permutations of resource terms
    lookup_table["resource_permutation_terms"] = {}
    # Will contain permutations of resource terms with brackets
    lookup_table["resource_bracketed_permutation_terms"] = {}
    # Iterate across resource_terms_revised
    for resource_term in lookup_table["resource_terms_revised"]:
        # ID corresponding to resource_term
        resource_id = lookup_table["resource_terms_revised"][resource_term]
        # List of tokens in resource_term
        resource_tokens = word_tokenize(resource_term.lower())
        # To limit performance overhead, we ignore resource_terms with
        # more than 7 tokens, as permutating too many tokens can be
        # costly. We also ignore NCBI taxon terms, as there are
        # ~160000 such terms.
        if len(resource_tokens)<7 and "NCBITaxon" not in resource_id:
            # Add all bracketed permutations of resource_term to
            # appropriate dictionary.
            bracketed_perms = get_resource_bracketed_permutation_terms(resource_term)
            for bracketed_perm in bracketed_perms:
                lookup_table["resource_bracketed_permutation_terms"][bracketed_perm] = resource_id
            # Add all permutations of resource_term to appropriate
            # dictionary.
            permutations = get_resource_permutation_terms(resource_term)
            for permutation in permutations:
                lookup_table["resource_permutation_terms"][permutation] = resource_id
    return lookup_table


def get_resource_permutation_terms(resource_label):
    """Get permutations of some term.

    :param resource_label: Name of some resource
    :type resource_label: str
    :return: All permutations of resource_label
    :rtype: list
    """
    # Set of tuples, where each tuple is a different permutation of
    # tokens from label
    permutations_set = all_permutations(resource_label)
    # Return value
    ret = []
    # Generate a string from each tuple, and add it to ret
    for permutation_tuple in permutations_set:
        permutation_string = " ".join(permutation_tuple)
        ret = ret + [permutation_string]

    return ret


def get_resource_bracketed_permutation_terms(resource_label):
    """Get bracketed permutations of some term.

    Bracketed permutations follows the following definition:

    * If a term has no bracketed content, it returns has no bracketed
      permutations
    * If a term has bracketed content, the bracketed permutations are
      comprised of all permutations of the term with the bracket
      characters removed

    :param resource_label: Name of some resource
    :type resource_label: str
    :return: All bracketed permutations of resource_label
    :rtype: list
    """
    if "(" not in resource_label or ")" not in resource_label:
        return []

    # Portion of label before brackets
    unbracketed_component = resource_label.split("(")[0]
    # Portion of label inside brackets
    bracketed_component = resource_label.split("(")[1]
    bracketed_component = bracketed_component.split(")")[0]
    # Replace any commas in bracketed_component with spaces
    bracketed_component = bracketed_component.replace(",", " ")

    return get_resource_permutation_terms(bracketed_component + " " + unbracketed_component)


def add_fetched_ontology_to_lookup_table(lookup_table, fetched_ontology):
    """Add terms from fetched_ontology to lookup_table.

    lookup_table can be used to map terms in run. See
    create_lookup_table_skeleton for the expected format of
    lookup_table.

    :param lookup_table: See create_lookup_table_skeleton for the
                         expected format of this parameter
    :param fetched_ontology: See JSON output of ontofetch.py for the
                             expected format of this parameter
    :type lookup_table: dict
    :type fetched_ontology: dict
    :return: Modified ``lookup_table``
    :rtype: dict
    """
    # Parse content from fetched_ontology and add it to lookup_table
    for resource in fetched_ontology["specifications"].values():
        if "id" in resource and "label" in resource:
            resource_id = resource["id"]
            resource_label = resource["label"]

            # Keep consistent with resource_id values in resources/
            resource_id = resource_id.replace(":", "_")

            lookup_table["resource_terms_ID_based"][resource_id] = resource_label
            lookup_table["resource_terms"][resource_label] = resource_id
            lookup_table["resource_terms_revised"][resource_label.lower()] = resource_id

            # List of tokens in resource_label
            resource_tokens = word_tokenize(resource_label.lower())
            # Add permutations if there are less than seven tokens.
            # Permutating more tokens than this can lead to performance
            # issues.
            if len(resource_tokens) < 7:
                permutations = get_resource_permutation_terms(resource_label)
                for permutation in permutations:
                    lookup_table["resource_permutation_terms"][permutation] = resource_id

                bracketed_permutations = get_resource_bracketed_permutation_terms(resource_label)
                for permutation in bracketed_permutations:
                    lookup_table["resource_bracketed_permutation_terms"][permutation] = resource_id

            if "synonyms" in resource:
                synonyms = resource["synonyms"].split(";")
                for synonym in synonyms:
                    lookup_table["synonyms"][synonym] = resource_label

            if "parent_id" in resource:
                # Keep parent_id consistent with resource_id values
                parent_id = resource["parent_id"].replace(":", "_")

                # Instead of overwriting parents like we do with
                # synonyms, we will concatenate parents from different
                # fetches.
                if resource_id in lookup_table["parents"]:
                    # Prevent duplicates
                    if not parent_id in lookup_table["parents"][resource_id]:
                        lookup_table["parents"][resource_id] += [parent_id]
                else:
                    lookup_table["parents"][resource_id] = [parent_id]

                if "other_parents" in resource:
                    # Keep values consistent with resource_id values
                    other_parents = list(map(lambda x: x.replace(":", "_"),
                                             resource["other_parents"]))

                    # Prevent duplicates
                    other_parents = list(filter(
                        lambda x: x not in lookup_table["parents"][resource_id], other_parents))

                    lookup_table["parents"][resource_id] += other_parents

    return lookup_table


def merge_lookup_tables(lookup_table_one, lookup_table_two):
    """Merges lookup tables.

    Lookup tables, in the context of this pipeline, are dictionaries.
    They have the same keys, but can have different values. The values
    are also dictionaries.

    If their is a conflict between identical keys during merging,
    priority is given to lookup_table_two.

    :param dict lookup_table_one: lookup table
    :param dict lookup_table_two: lookup table
    :return: lookup table with the combined values for each key from
             lookup_table_one and lookup_table_two
    :rtype: dict
    :raises ValueError: if the definition of lookup table is not
                        adhered to by the parameters
    """
    if lookup_table_one.keys() != lookup_table_two.keys():
        raise ValueError("lookup_table_one and lookup_table_two do not have the same keys")

    # Set of keys from lookup_table_one, which are identical to the
    # keys from lookup_table_two. So these are just the common set of
    # lookup table keys.
    lookup_table_keys = lookup_table_one.keys()

    for key in lookup_table_keys:
        if type(lookup_table_one[key]) is not dict:
            raise ValueError("lookup_table_one values are not all dictionaries")
        if type(lookup_table_two[key]) is not dict:
            raise ValueError("lookup_table_two values are not all dictionaries")

    # Merge values from lookup_table_two into lookup_table_one
    for key in lookup_table_keys:
        for nested_key in lookup_table_two[key]:
            lookup_table_one[key][nested_key] = lookup_table_two[key][nested_key]

    return lookup_table_one


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
            str(sorted(list(retained_tokens))),
        "retained_terms_with_resource_ids":
            str(sorted(list(retained_tokens))),
        "match_status_macro_level": "Full Term Match",
        "match_status_micro_level": str(sorted(list(final_status))),
    })
    # Return
    return ret


def find_component_matches(cleaned_sample, lookup_table, status_addendum):
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
        # Iterate through i-gram chunks of cleaned_sample
        for gram_chunk in get_gram_chunks(cleaned_sample, i):
            # gram_chunk concatenated into a single string
            concatenated_gram_chunk = " ".join(gram_chunk)
            # Tokenized list of concatenated_gram_chunk
            gram_tokens = word_tokenize(concatenated_gram_chunk)
            # Permutations of concatenated_gram_chunk
            permutations = all_permutations(concatenated_gram_chunk)

            # Iterate over all permutations
            for permutation in permutations:
                # Join elements of permutation into a single string
                joined_permutation = " ".join(permutation)

                if i >= 3:
                    component_match = find_component_match(joined_permutation, lookup_table,
                                                           status_addendum)
                elif i > 1:
                    component_match = find_component_match(joined_permutation, lookup_table,
                                                           status_addendum, consider_qualities=True)
                else:
                    component_match = find_component_match(joined_permutation, lookup_table,
                                                           status_addendum, consider_qualities=True,
                                                           consider_processes=True)

                # Match found
                if component_match:
                    ret["component_matches"].append(component_match)
                    ret["token_matches"] += gram_tokens
                    break

    return ret


def find_component_match(component, lookup_table, status_addendum, consider_qualities=False,
                         consider_processes=False, additional_processing=True):
    """Attempt to match component with a term from lookup_table.

    Modifies ``status_addendum``.

    :param str component: Component to match
    :param dict[str, dict] lookup_table: Nested dictionary containing
        resources needed to find a component match
    :param list[str] status_addendum: Modifications made to sample in
        pre-processing
    :param bool consider_qualities: Attempt to match component to
        qualities
    :param bool consider_processes: Attempt to match component to
        processes
    :param bool additional_processing: Attempt abbreviation, acronym,
        non-english and synonym translation before matching
    :returns: Resource term matching ``component``, or None a match is
        not found
    :rtype: str or None

    **TODO:**

    * In the future, we may want find_full_term_match and this method
      to have the same functionality, and then we do not need both
    """
    if additional_processing:
        # component is an abbreviation or acronym
        if component in lookup_table["abbreviations"]:
            # Expand component
            component = lookup_table["abbreviations"][component]
            status_addendum.append("Abbreviation-Acronym Treatment")
        # component is a non-english word
        if component in lookup_table["non_english_words"]:
            # Translate component
            component = lookup_table["non_english_words"][component]
            status_addendum.append("Non English Language Words Treatment")
        # component is a synonym
        if component in lookup_table["synonyms"]:
            # Translate component to synonym
            component = lookup_table["synonyms"][component]
            status_addendum.append("Synonym Usage")

    # There is a full-term component match with no treatment or
    # change-of-case in resource term.
    if component in lookup_table["resource_terms"]\
            or component in lookup_table["resource_terms_revised"]:
        return component
    # There is a full-term component match with permutation of
    # bracketed resource term.
    elif component in lookup_table["resource_bracketed_permutation_terms"]:
        status_addendum.append("Permutation of Tokens in Bracketed Resource Term")
        return component
    else:
        for suffix in lookup_table["suffixes"]:
            component_with_suffix = component+" "+suffix
            # A full-term component match with change of resource and
            # suffix addition exists.
            if component_with_suffix in lookup_table["resource_terms_revised"]:
                status_addendum.append("Suffix Addition- "+suffix+" to the Input")
                return component_with_suffix

        if consider_qualities:
            # A full-term component match using semantic resources
            # exists.
            if component in lookup_table["qualities_lower"]:
                status_addendum.append("Using Semantic Tagging Resources")
                return component

        if consider_processes:
            # A full-term 1-gram component match using candidate
            # processes exists.
            if component in lookup_table["processes"]:
                status_addendum.append("Using Candidate Processes")
                return component

    # Component match not found
    return None


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
    samples_dict = collections.OrderedDict()
    samplesList = []
    samplesSet = []

    # Cache (or get from cache) the lookup table containing pre-defined
    # resources used for matching.
    lookup_table_path = os.path.abspath("lookup_table.json")
    if os.path.exists(lookup_table_path):
        with open(lookup_table_path) as fp:
            lookup_table = json.load(fp)
    else:
        lookup_table = create_lookup_table_skeleton()
        lookup_table = add_predefined_resources_to_lookup_table(lookup_table)
        with open(lookup_table_path, "w") as fp:
            json.dump(lookup_table, fp)

    # Lookup table will also consist of terms fetched from an online
    # ontology.
    if args.config is not None:
        # Make fetched_ontologies folder if it does not already exist
        if not os.path.isdir(os.path.abspath("fetched_ontologies")):
            os.makedirs("fetched_ontologies")
        # Make ontology_lookup_tables folder if it does not already exist
        if not os.path.isdir(os.path.abspath("ontology_lookup_tables")):
            os.makedirs("ontology_lookup_tables")

        config_file_name = os.path.basename(args.config).rsplit('.', 1)[0]
        ontology_lookup_table_abs_path = os.path.abspath("ontology_lookup_tables/lookup_%s.json")
        ontology_lookup_table_abs_path = ontology_lookup_table_abs_path % config_file_name

        # Retrieve lookup table for fetched ontology from cache
        try:
            with open(ontology_lookup_table_abs_path) as file:
                ontology_lookup_table = json.load(file)
        # Generate new ontology lookup table
        except FileNotFoundError:
            # Load user-specified config file into an OrderedDict
            with open(os.path.abspath(args.config)) as file:
                config_json = json.load(file)

            # Create empty ontology lookup table
            ontology_lookup_table = create_lookup_table_skeleton()

            # Iterate over config_json backwards
            for json_object in reversed(config_json):
                (ontology_iri, root_entity_iri), = json_object.items()
                # Arguments for ontofetch.py
                if root_entity_iri == "":
                    sys.argv = ["", ontology_iri, "-o", "fetched_ontologies"]
                else:
                    sys.argv = ["", ontology_iri, "-o", "fetched_ontologies", "-r", root_entity_iri]
                # Call ontofetch.py
                ontofetch = Ontology()
                ontofetch.__main__()
                # Load fetched_ontology from JSON, and add the
                # appropriate terms to lookup_table.
                ontology_file_name = os.path.basename(ontology_iri).rsplit('.', 1)[0]
                fetched_ontology_rel_path = "fetched_ontologies/%s.json" % ontology_file_name
                with open(os.path.abspath(fetched_ontology_rel_path)) as file:
                    fetched_ontology = json.load(file)
                ontology_lookup_table = add_fetched_ontology_to_lookup_table(ontology_lookup_table,
                                                                             fetched_ontology)

            # Add ontology_lookup_table to cache
            with open(ontology_lookup_table_abs_path, "w") as file:
                json.dump(ontology_lookup_table, file)

        # Merge ontology_lookup_table into lookup_table
        lookup_table = merge_lookup_tables(lookup_table, ontology_lookup_table)

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
    else:
        OUTPUT_FIELDS += [
            "Matched_Components"
        ]
    
    fw = open(args.output, 'w') if args.output else sys.stdout     # Main output file
    fw.write('\t'.join(OUTPUT_FIELDS))
    
    samples_dict = read_input_file(args.input_file)
    
    # Iterate over samples for matching to ontology terms
    for k, v in samples_dict.items():
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
            lemma = singularize_token(tkn, lookup_table, status_addendum)

            # Misspellings are dealt with  here
            lemma = spelling_correction(lemma, lookup_table, status_addendum)

            # Abbreviations, acronyms, taken care of- need rule for abbreviation e.g. if lemma is Abbreviation
            lemma = abbreviation_normalization_token(lemma, lookup_table, status_addendum)

            # non-EngLish language words taken care of
            lemma = non_English_normalization_token(lemma, lookup_table, status_addendum)

            # ===This will create a cleaned sample after above treatments [Here we are making new phrase now in lower case]
            cleaned_sample = get_cleaned_sample(cleaned_sample, lemma, lookup_table)
            cleaned_sample = re.sub(' +', ' ', cleaned_sample)

            # Phrase being cleaned for
            cleaned_sample = abbreviation_normalization_phrase(cleaned_sample, lookup_table, status_addendum)

            # Phrase being cleaned for
            cleaned_sample = non_English_normalization_phrase(cleaned_sample, lookup_table, status_addendum)

        #  Here we are making the tokens of cleaned sample phrase
        cleaned_sample = remove_duplicate_tokens(cleaned_sample)
        cleaned_sample_tokens = word_tokenize(cleaned_sample.lower())

        # Part of Speech tags assigned to the tokens
        tokens_pos = pos_tag(cleaned_sample_tokens)

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
                fw.write("\t" + str([full_term_match["matched_term"]]) + "\t"
                    + full_term_match["all_match_terms_with_resource_ids"]
                    + "\t"
                    + full_term_match["retained_terms_with_resource_ids"]
                    + "\t" + "\t"
                    + full_term_match["match_status_macro_level"] + "\t"
                    + full_term_match["match_status_micro_level"])
            # Write to some headers
            else:
                fw.write("\t" + full_term_match["all_match_terms_with_resource_ids"])
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
            # 1-5 gram component matches for cleaned_sample, and
            # tokens covered by said matches. See find_component_match
            # docstring for details.
            component_and_token_matches = find_component_matches(cleaned_sample, lookup_table,
                                                                 status_addendum)

            partial_matches = set(component_and_token_matches["component_matches"])  # Makes a set of all matched components from the above processing
            status = "Component Match"

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

            partial_matches_with_ids=get_component_match_withids(partial_matches, lookup_table)

            partialMatchedResourceListSet = set(partial_matches_with_ids)   # Makes a set from list of all matched components with resource ids
            retainedSet = []

            # If size of set is more than one member, looks for the retained matched terms by defined criteria
            if (len(partialMatchedResourceListSet) > 0):
                retainedSet = retainedPhrase(list(partialMatchedResourceListSet))
                # HERE SHOULD HAVE ANOTHER RETAING SET

            final_status = set(status_addendum)

            # In case it is for componet matching and we have at least one component matched
            if (len(partial_matches) > 0):
                if args.format == 'full':
                    fw.write('\t' + str(sorted(list(partial_matches))) + '\t' + str(sorted(list(partialMatchedResourceListSet))) + '\t' + str(sorted(list(retainedSet))) + '\t' + str(len(retainedSet)) + '\t' + status + '\t' + str(sorted(list(final_status))) + '\t' + str(sorted(list(remSetDiff))))

                compctr = 0
                if args.format == 'full':
                    fw.write("\t")
                
                if args.format != 'full':
                    fw.write("\t" + str(sorted(list(retainedSet))))

                if args.format == 'full':
                    for comp in sorted(list(retainedSet)):
                        compctr += 1
                        if (compctr == 1):
                            fw.write("Component" + str(compctr) + "-> " + str(comp))
                        else:
                            fw.write(", Component" + str(compctr) + "-> " + str(comp))
                    trigger = True
                else:        # In case of no matching case
                    if args.format == 'full':
                        fw.write('\t' + str(sorted(list(partial_matches))) + '\t' + str(sorted(list(partial_matches_with_ids))) + '\t\t' + "\t" + "Sorry No Match" + "\t" + str(sorted(list(remaining_tokens))))

    fw.write('\n')
    #Output files closed
    if fw is not sys.stdout:
        fw.close()
