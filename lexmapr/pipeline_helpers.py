"""Helper functions for lexmapr.pipeline."""

import collections
import csv
import itertools
from itertools import combinations

from dateutil.parser import parse
import inflection
from nltk.tokenize.moses import MosesDetokenizer
from nltk.tokenize import word_tokenize
from pkg_resources import resource_filename


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
    return lemma


def abbreviation_normalization_token(lemma, lookup_table, status_addendum):
    if (lemma in lookup_table[
        "abbreviations"].keys()):
        lemma = lookup_table["abbreviations"][lemma]
        status_addendum.append("Abbreviation-Acronym Treatment")
    return lemma


def abbreviation_normalization_phrase(phrase, lookup_table, status_addendum):
    if (phrase in lookup_table[
        "abbreviations"].keys()):  # NEED HERE AGAIN ? Abbreviations, acronyms, non English words taken care of- need rule for abbreviation
        cleaned_sample = lookup_table["abbreviations"][phrase]
        status_addendum.append("Cleaned Sample and Abbreviation-Acronym Treatment")
    return phrase


def non_English_normalization_token(lemma, lookup_table, status_addendum):
    if (lemma in lookup_table["non_english_words"].keys()):  # Non English language words taken care of
        lemma = lookup_table["non_english_words"][lemma]
        status_addendum.append("Non English Language Words Treatment")
    return lemma


def non_English_normalization_phrase(phrase, lookup_table, status_addendum):
    if (phrase in lookup_table["non_english_words"].keys()):  # non English words taken care of
        phrase = lookup_table["non_english_words"][phrase]
        status_addendum.append("Cleaned Sample and Non English Language Words Treatment")
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


def get_resource_id(resource_label, lookup_table):
    """Translate a resource label to a resource ID.

    :param str resource_label: Resource label to translate
    :param dict[str, dict] lookup_table: Nested dictionary containing
        data needed to retrieve a resource ID
    :returns: resource ID corresponding to ``resource_label``
    :rtype: str
    """
    if resource_label in lookup_table["resource_terms"]:
        return lookup_table["resource_terms"][resource_label]
    elif resource_label in lookup_table["resource_permutation_terms"]:
        return lookup_table["resource_permutation_terms"][resource_label]
    elif resource_label in lookup_table["resource_bracketed_permutation_terms"]:
        return lookup_table["resource_bracketed_permutation_terms"][resource_label]
    elif resource_label in lookup_table["processes"]:
        return lookup_table["processes"][resource_label]
    else:
        return ""


def remove_duplicate_tokens(input_string):
    refined_string=""
    new_phrase_set = []
    string_tokens = word_tokenize(input_string)
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


def get_resource_dict(resource_file_name):
    """Get dictionary containing data from a ``resources/`` csv file.

    The data is standardized to lowercase.

    :param resource_file_name: Name of file (with extension) in
        ``resources/``
    :type resource_file_name: str
    :return: data in ``resource_file_name``
    :rtype: dict
    """
    # Return value
    ret = {}
    # Open file_name
    with open(resource_filename('lexmapr.resources', resource_file_name)) as fp:
        # Skip first line
        next(fp)
        # Read file_name
        file_contents = csv.reader(fp, delimiter=",")
        # Iterate across rows in file_contents
        for row in file_contents:
            # Get key
            key = row[0].strip()
            try:
                # Get corresponding value
                val = row[1].strip()
            except IndexError:
                # No corresponding value
                val = ""
            # Convert key and val to lowercase
            key = key.lower()
            val = val.lower()
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
            "non_english_words": {},
            "spelling_mistakes": {},
            "processes": {},
            "collocations": {},
            "inflection_exceptions": {},
            "stop_words": {},
            "suffixes": {},
            "parents": {},
            "resource_terms_id_based": {},
            "resource_terms": {},
            "resource_permutation_terms": {},
            "resource_bracketed_permutation_terms": {},
            "buckets_ifsactop": {},
            "buckets_lexmapr": {},
            "ifsac_labels": {},
            "ifsac_refinement": {},
            "ifsac_default": {}
            }


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
    # Non-english translations of resource terms
    lookup_table["non_english_words"] = get_resource_dict("NefLex.csv")
    # Common misspellings of resource terms
    lookup_table["spelling_mistakes"] = get_resource_dict("ScorLex.csv")
    # Terms corresponding to candidate processes
    lookup_table["processes"] = get_resource_dict("candidateProcesses.csv")
    # Terms corresponding to wikipedia collocations
    lookup_table["collocations"] = get_resource_dict("wikipediaCollocations.csv")
    # Terms excluded from inflection treatment
    lookup_table["inflection_exceptions"] = get_resource_dict("inflection-exceptions.csv")
    # Constrained list of stop words considered to be meaningless
    lookup_table["stop_words"] = get_resource_dict("mining-stopwords.csv")
    # Suffixes to consider appending to terms when mining ontologies
    lookup_table["suffixes"] = get_resource_dict("suffixes.csv")
    # ID-resource combinations
    lookup_table["resource_terms_id_based"] = get_resource_dict("CombinedResourceTerms.csv")
    # Swap keys and values in resource_terms_id_based
    lookup_table["resource_terms"] = {
        v: k for k, v in lookup_table["resource_terms_id_based"].items()
    }

    # Will contain permutations of resource terms
    lookup_table["resource_permutation_terms"] = {}
    # Will contain permutations of resource terms with brackets
    lookup_table["resource_bracketed_permutation_terms"] = {}
    # Iterate across resource_terms
    for resource_term in lookup_table["resource_terms"]:
        # ID corresponding to resource_term
        resource_id = lookup_table["resource_terms"][resource_term]
        # List of tokens in resource_term
        resource_tokens = word_tokenize(resource_term)
        # To limit performance overhead, we ignore resource_terms with
        # more than 7 tokens, as permutating too many tokens can be
        # costly. We also ignore NCBI taxon terms, as there are
        # ~160000 such terms.
        if len(resource_tokens)<7 and "ncbitaxon" not in resource_id:
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

            # Standardize values
            resource_id = resource_id.replace(":", "_")
            resource_id = resource_id.lower()
            resource_label = resource_label.lower()

            lookup_table["resource_terms_id_based"][resource_id] = resource_label
            lookup_table["resource_terms"][resource_label] = resource_id

            # List of tokens in resource_label
            resource_tokens = word_tokenize(resource_label)
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

            if "oboInOwl:hasSynonym" in resource:
                synonyms = resource["oboInOwl:hasSynonym"]
                for synonym in synonyms:
                    # Standardize synonym
                    synonym = synonym.lower()

                    lookup_table["synonyms"][synonym] = resource_label

            if "oboInOwl:hasBroadSynonym" in resource:
                synonyms = resource["oboInOwl:hasBroadSynonym"]
                for synonym in synonyms:
                    # Standardize synonym
                    synonym = synonym.lower()

                    lookup_table["synonyms"][synonym] = resource_label

            if "oboInOwl:hasNarrowSynonym" in resource:
                synonyms = resource["oboInOwl:hasNarrowSynonym"]
                for synonym in synonyms:
                    # Standardize synonym
                    synonym = synonym.lower()

                    lookup_table["synonyms"][synonym] = resource_label

            if "oboInOwl:hasExactSynonym" in resource:
                synonyms = resource["oboInOwl:hasExactSynonym"]
                for synonym in synonyms:
                    # Standardize synonym
                    synonym = synonym.lower()

                    lookup_table["synonyms"][synonym] = resource_label

            if "parent_id" in resource:
                # Standardize parent_id
                parent_id = resource["parent_id"].replace(":", "_")
                parent_id = parent_id.lower()

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
                    # Standardize values
                    other_parents = list(map(lambda x: x.replace(":", "_").lower(),
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


def find_full_term_match(sample, lookup_table, cleaned_sample, status_addendum):
    """Retrieve an annotated, full-term match for a sample.

    :param str sample: Sample to match
    :param dict[str, dict] lookup_table: Nested dictionary containing
        resources needed to find a component match
    :param str cleaned_sample: Cleaned-up version of sample that may be
        needed to find a match
    :param list[str] status_addendum: Modifications made to sample in
        pre-processing
    :returns: Relevant match-annotations for pipeline output
    :rtype: dict[str, str or list[str]]
    :raises MatchNotFoundError: If a match is not found
    """
    # Tokens to retain for all_match_terms_with_resource_ids
    retained_tokens = []
    # Dictionary to return
    ret = dict.fromkeys([
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
    # Full-term match with permutation of resource term
    elif sample in lookup_table["resource_permutation_terms"]:
        # Term we found a permutation for
        matched_term = sample
        # Resource ID for matched_term's permutation
        resource_id = lookup_table["resource_permutation_terms"][matched_term]
        # Permutation corresponding to matched_term
        matched_permutation = lookup_table["resource_terms_id_based"][resource_id]
        # Update retained_tokens
        retained_tokens.append(matched_permutation + ":" + resource_id)
        # Update status_addendum
        status_addendum.append("Permutation of Tokens in Resource Term")
    # Full-term match with permutation of bracketed resource term
    elif sample in lookup_table["resource_bracketed_permutation_terms"]:
        # Term we found a permutation for
        matched_term = sample
        # Resource ID for matched_term's permutation
        resource_id = lookup_table["resource_bracketed_permutation_terms"][matched_term]
        # Permutation corresponding to matched_term
        matched_permutation = lookup_table["resource_terms_id_based"][resource_id]
        # Update retained_tokens
        retained_tokens.append(matched_permutation + ":" + resource_id)
        # Update status_addendum
        status_addendum.append("Permutation of Tokens in Bracketed Resource Term")
    # Full-term cleaned sample match without any treatment
    elif cleaned_sample in lookup_table["resource_terms"]:
        # Term with we found a full-term match for
        matched_term = cleaned_sample
        # Resource ID for matched_term
        resource_id = lookup_table["resource_terms"][matched_term]
        # Update retained_tokens
        retained_tokens.append(matched_term + ":" + resource_id)
        # Update status_addendum
        status_addendum.append("A Direct Match with Cleaned Sample")
    # Full-term cleaned sample match with permutation of
    # resource term.
    elif cleaned_sample in lookup_table["resource_permutation_terms"]:
        # Term we found a permutation for
        matched_term = cleaned_sample
        # Resource ID for matched_term's permutation
        resource_id = lookup_table["resource_permutation_terms"][matched_term]
        # Permutation corresponding to matched_term
        matched_permutation = lookup_table["resource_terms_id_based"][resource_id]
        # Update retained_tokens
        retained_tokens.append(matched_permutation + ":" + resource_id)
        # Update status_addendum
        status_addendum.append("Permutation of Tokens in Resource Term")
    # Full-term cleaned sample match with permutation of
    # bracketed resource term.
    elif cleaned_sample in lookup_table["resource_bracketed_permutation_terms"]:
        # Term we found a permutation for
        matched_term = cleaned_sample
        # Resource ID for matched_term's permutation
        resource_id = lookup_table["resource_bracketed_permutation_terms"][matched_term]
        # Permutation corresponding to matched_term
        matched_permutation = lookup_table["resource_terms_id_based"][resource_id]
        # Update retained_tokens
        retained_tokens.append(matched_permutation + ":" + resource_id)
        # Update status_addendum
        status_addendum.append("Permutation of Tokens in Bracketed Resource Term")
    # A full-term cleaned sample match with multi-word
    # collocation from Wikipedia exists.
    elif cleaned_sample in lookup_table["collocations"]:
        # Term we found a full-term match for
        matched_term = cleaned_sample
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
        resource_terms = lookup_table["resource_terms"]
        # Find all suffixes that when appended to sample, are
        # in resource_terms.
        matched_suffixes = [
            s for s in lookup_table["suffixes"] if sample+" "+s in resource_terms
        ]
        # Find all suffixes that when appended to cleaned
        # sample, are in resource_terms.
        matched_clean_suffixes = [
            s for s in lookup_table["suffixes"] if cleaned_sample+" "+s in resource_terms
        ]
        # A full-term match with change of resource and suffix
        # addition exists.
        if matched_suffixes:
            # Term with first suffix in suffixes that provides
            # a full-term match.
            term_with_suffix = sample + " " + matched_suffixes[0]
            # Resource ID for matched_term
            resource_id = resource_terms[term_with_suffix]
            # Update retained_tokens
            retained_tokens.append(term_with_suffix + ":" + resource_id)
            # Update status_addendum
            status_addendum.append(
                "[Suffix Addition- " + matched_suffixes[0] + " to the Input]"
            )
        # A full-term cleaned sample match with change of resource and
        # suffix addition exists.
        elif matched_clean_suffixes:
            # Term with first suffix in suffixes that provides
            # a full-term match.
            term_with_suffix = cleaned_sample + " " + matched_clean_suffixes[0]
            # Resource ID for matched_term
            resource_id = resource_terms[term_with_suffix]
            # Update retained_tokens
            retained_tokens.append(term_with_suffix + ":" + resource_id)
            # Update status_addendum
            status_addendum.append(
                "[CleanedSample-Suffix Addition- " + matched_clean_suffixes[0] + " to the Input]"
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
        "all_match_terms_with_resource_ids":
            sorted(list(retained_tokens)),
        "retained_terms_with_resource_ids":
            sorted(list(retained_tokens)),
        "match_status_macro_level": "Full Term Match",
        "match_status_micro_level": sorted(list(final_status)),
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

            # Abort if all tokens already covered
            if set(gram_tokens) <= set(ret["token_matches"]):
                continue

            # Iterate over all permutations
            for permutation in permutations:
                # Join elements of permutation into a single string
                joined_permutation = " ".join(permutation)

                if i >= 3:
                    component_match = find_component_match(joined_permutation, lookup_table,
                                                           status_addendum)
                    if not component_match:
                        component_match = find_component_match(joined_permutation, lookup_table,
                                                               status_addendum,
                                                               additional_processing=True)
                else:
                    component_match = find_component_match(joined_permutation, lookup_table,
                                                           status_addendum, consider_processes=True)
                    if not component_match:
                        component_match = find_component_match(joined_permutation, lookup_table,
                                                               status_addendum,
                                                               consider_processes=True,
                                                               additional_processing=True)

                # Match found
                if component_match:
                    ret["component_matches"].append(component_match)
                    ret["token_matches"] += gram_tokens
                    break

    return ret


def find_component_match(component, lookup_table, status_addendum, consider_processes=False,
                         additional_processing=False):
    """Attempt to match component with a term from lookup_table.

    Modifies ``status_addendum``.

    :param str component: Component to match
    :param dict[str, dict] lookup_table: Nested dictionary containing
        resources needed to find a component match
    :param list[str] status_addendum: Modifications made to sample in
        pre-processing
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

    # There is a full-term component match with no treatment in
    # resource term.
    if component in lookup_table["resource_terms"]:
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
            if component_with_suffix in lookup_table["resource_terms"]:
                status_addendum.append("Suffix Addition- "+suffix+" to the Input")
                return component_with_suffix

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


