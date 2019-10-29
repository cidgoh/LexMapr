"""Helper functions for lexmapr.pipeline.run."""

from collections import OrderedDict
from itertools import combinations
import re

from dateutil.parser import parse
import inflection
from nltk.tokenize.moses import MosesDetokenizer
from nltk.tokenize import word_tokenize


def singularize_token(tkn, lookup_table, micro_status):
    lemma=tkn
    if (tkn.endswith("us") or tkn.endswith("ia") or tkn.endswith(
            "ta")):  # for inflection exception in general-takes into account both lower and upper case (apart from some inflection-exception list used also in next
        lemma = tkn
    elif (tkn not in lookup_table[
        "inflection_exceptions"]):  # Further Inflection Exception list is taken into account
        lemma = inflection.singularize(tkn)
    if (tkn != lemma):  # Only in case when inflection makes some changes in lemma
        micro_status.append("Inflection (Plural) Treatment: " + tkn)

    return lemma


def spelling_correction(lemma, lookup_table, status_addendum):
    if (lemma in lookup_table["spelling_mistakes"].keys()):  # spelling mistakes taken care of
        lemma = lookup_table["spelling_mistakes"][lemma]
        status_addendum.append("Spelling Correction Treatment: " + lemma)
    return lemma


def abbreviation_normalization_token(lemma, lookup_table, status_addendum):
    if (lemma in lookup_table[
        "abbreviations"].keys()):
        lemma = lookup_table["abbreviations"][lemma]
        status_addendum.append("Abbreviation-Acronym Treatment: " + lemma)
    return lemma


def abbreviation_normalization_phrase(phrase, lookup_table, status_addendum):
    if (phrase in lookup_table[
        "abbreviations"].keys()):  # NEED HERE AGAIN ? Abbreviations, acronyms, non English words taken care of- need rule for abbreviation
        cleaned_sample = lookup_table["abbreviations"][phrase]
        status_addendum.append("Abbreviation-Acronym Treatment: " + phrase)
    return phrase


def non_English_normalization_token(lemma, lookup_table, status_addendum):
    if (lemma in lookup_table["non_english_words"].keys()):  # Non English language words taken care of
        lemma = lookup_table["non_english_words"][lemma]
        status_addendum.append("Non English Language Words Treatment: " + lemma)
    return lemma


def non_English_normalization_phrase(phrase, lookup_table, status_addendum):
    if (phrase in lookup_table["non_english_words"].keys()):  # non English words taken care of
        phrase = lookup_table["non_english_words"][phrase]
        status_addendum.append("Non English Language Words Treatment: " + phrase)
    return phrase


def get_cleaned_sample(cleaned_sample,lemma, lookup_table):
    if (not cleaned_sample and lemma not in lookup_table[
        "stop_words"]):  # if newphrase is empty and lemma is in not in stopwordlist (abridged according to domain)
        cleaned_sample = lemma
    elif (
                lemma not in lookup_table[
                "stop_words"]):  # if newphrase is not empty and lemma is in not in stopwordlist (abridged according to domain)

        cleaned_sample = cleaned_sample + " " + lemma
    return cleaned_sample


def remove_duplicate_tokens(input_string):
    refined_phrase_list = []
    new_phrase_list = input_string.split(' ')
    for token in new_phrase_list:
        if token not in refined_phrase_list:
            refined_phrase_list.append(token)
    refined_string = MosesDetokenizer().detokenize(refined_phrase_list, return_str=True)
    refined_string=refined_string.strip()
    return refined_string

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
    except (ValueError, OverflowError):
        return False


# 3-Method to get ngrams with a given value of n (i.e. n=1 means unigram, n=2 means bigram, n=3 means trigram and so on)
def ngrams(input, n):
    input = input.split(' ')
    output = []
    for i in range(len(input) - n + 1):
        output.append(input[i:i + n])
    return output


def get_gram_chunks(input, num):
    """Make ``num``-gram chunks from ``input``.

    If ``input`` contains less than 15 tokens, returns all
    ``num``-length token combinations. Otherwise, returns all tokenized
    ``num``-length substrings of ``input``.

    :param str input: Value to get ``num``-gram chunks of
    :param int num: Size of gram chunks to return
    :return: ``num``-gram chunks of ``input``
    :rtype: list[tuple[str]]
    """
    # List of tokens from input
    input_tokens = word_tokenize(input)
    # input_tokens has less than 7 tokens
    if len(input_tokens) < 15:
        # Return all num-token combinations of input_tokens
        return list(combinations(input_tokens, num))
    # input_tokens has 15 or more tokens
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


def punctuation_treatment(term):
    """Remove punctuations from ``term``.

    These punctuations are ``-``, ``_``, ``(``, ``)``, ``;``, ``/``,
    ``:`` and ``%``.

    :type term: str
    :returns: ``term`` with punctuations removed
    :rtype: str
    """
    punctuations_regex_char_class = "[-_();/:%]"
    ret = re.sub(punctuations_regex_char_class, " ", term)

    # Remove excess white space and return
    return " ".join(ret.split())


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
        returnedSetFinal = list(OrderedDict.fromkeys(returnedSet))
    return returnedSetFinal


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


def get_term_parent_hierarchies(term_id, lookup_table):
    """Get the parent hierarchies for a resource.

    ``term_id`` is included in each returned hierarchy.

    :param str term_id: ID of some resource cached in ``lookup_table``
    :param dict[str, dict] lookup_table: Nested dictionary containing
        data needed to retrieve a parent hierarchy
    :returns: parent hierarchies of resource with id value of
        ``term_id``
    :rtype: list[list[str]]

    **TODO**: Expand this to return all hierarchies
    """
    hierarchies = [[term_id]]

    i = 0

    while i < len(hierarchies):
        hierarchy = hierarchies[i]
        node = hierarchy[-1]

        if node in lookup_table["parents"]:
            node_parents = lookup_table["parents"][node]
            for node_parent in node_parents:
                hierarchies.append(hierarchy + [node_parent])
            hierarchies.pop(i)
            continue
        else:
            i += 1

    return hierarchies


def map_term(term, lookup_table, consider_suffixes=False):
    """Map ``term`` to some resource in ``lookup_table``.

    Attempts to map to any resource term, or permutation a resource
    term. Will attempt to map synonyms in case of failure.

    If a mapping is found, returns a dictionary detailing the mapped
    resource label, mapped resource ontology ID and a status detailing
    the work needs to perform the mapping.

    :param str term: To be mapped to resource
    :param dict[str, dict] lookup_table: See
        ``create_lookup_table_skeleton``
    :param bool consider_suffixes: Try to match ``term`` using suffixes
        in ``lookup_table``
    :returns: Mapping for ``term``, or ``None`` if mapping not found
    :rtype: dict[str, str or list[str]] or None
    """
    if consider_suffixes:
        # Try mapping term with suffixes
        for suffix in lookup_table["suffixes"]:
            mapping = _map_term_helper(term + " " + suffix, lookup_table)
            if mapping:
                mapping["status"].insert(-2, "Suffix Addition")
                return mapping
    else:
        # Try mapping term without suffixes
        mapping = _map_term_helper(term, lookup_table)
        if mapping:
            return mapping

    # No mapping yet
    if term in lookup_table["synonyms"]:
        synonym = lookup_table["synonyms"][term]

        if consider_suffixes:
            # Try mapping synonym with suffixes
            for suffix in lookup_table["suffixes"]:
                mapping = _map_term_helper(synonym + " " + suffix, lookup_table)
                if mapping:
                    mapping["status"].insert(-2, "Suffix Addition")
                    mapping["status"].insert(-2, "Synonym Usage")
                    return mapping
        else:
            # Try mapping just the synonym
            mapping = _map_term_helper(synonym, lookup_table)
            if mapping:
                mapping["status"].insert(-2, "Synonym Usage")
                return mapping

    # No mapping
    return None


def _map_term_helper(term, lookup_table):
    # Map ``term`` to ``lookup_table`` resource or resource permutation
    if term in lookup_table["resource_terms"]:
        return {
            "term": term,
            "id": lookup_table["resource_terms"][term],
            "status": ["A Direct Match"]
        }
    elif term in lookup_table["resource_permutation_terms"]:
        term_id = lookup_table["resource_permutation_terms"][term]
        return {
            "term": lookup_table["resource_terms_id_based"][term_id],
            "id": term_id,
            "status": ["Permutation of Tokens in Resource Term"]
        }
    else:
        return None
