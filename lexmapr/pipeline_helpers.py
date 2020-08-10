"""Helper functions for lexmapr.pipeline.run."""

from collections import OrderedDict
from itertools import combinations
import re

from dateutil.parser import parse
import inflection
from nltk.tokenize import word_tokenize
from nltk.tokenize.treebank import TreebankWordDetokenizer
from nltk import pos_tag


def singularize_token(token, lookup_table, micro_status):
    """Singularizes the string token, if applicable.

    :param str token: input token to be singularized
    :param dict lookup_table: lookup table of resources
    :param str micro_status: micro level status of rule/treatment
    :return: singularized token
    :rtype: str
    """

    lemma = token
    # Performs siingularization if tokens not in exception list
    if token not in lookup_table["inflection_exceptions"]:
        lemma = inflection.singularize(token)

    # Overrides the singularization based on general inflection exception
    # in the domain - accounts both lower and upper case
    exception_tail_chars_list = ["us", "ia", "ta"]
    for char in exception_tail_chars_list:
        if token.endswith(char):
            lemma = token

    if token != lemma:  # if inflection makes some changes in lemma
        micro_status.append("Inflection (Plural) Treatment: " + token)

    return lemma


def spelling_correction(token, lookup_table, micro_status):
    """Corrects the spelling of input token, if available in resource.

    :param str token: input token to be spell corrected
    :param dict lookup_table: lookup table of resources
    :param str micro_status: micro level status of rule/treatment
    :return: spell corrected token
    :rtype: str
    """

    if token in lookup_table["spelling_mistakes"]:
        token = lookup_table["spelling_mistakes"][token]
        micro_status.append("Spelling Correction Treatment: " + token)
    return token


def abbreviation_normalization_token(
            token, lookup_table, micro_status):
    """Normalizes token for abbreviation, if available in resource

    :param str token: input token to be normalized
    :param dict lookup_table: lookup table of resources
    :param str micro_status: micro level status of rule/treatment
    :return: normalized token for abbreviation (if applicable)
    :rtype: str
    """

    if token in lookup_table["abbreviations"]:
        token = lookup_table["abbreviations"][token]
        micro_status.append("Abbreviation-Acronym Treatment: " + token)
    return token


def abbreviation_normalization_phrase(
        phrase, lookup_table, micro_status):
    """Normalizes phrase (multi-token) for abbreviation, if in resource.

    :param str phrase: input phrase to be normalized
    :param dict lookup_table: lookup table of resources
    :param str micro_status: micro level status of rule/treatment
    :return: normalized phrase for abbreviation (if applicable)
    :rtype: str
    """

    if phrase in lookup_table["abbreviations"]:
        phrase = lookup_table["abbreviations"][phrase]
        micro_status.append("Abbreviation-Acronym Treatment: " + phrase)
    return phrase


def non_English_normalization_token(
        token, lookup_table, micro_status):
    """Normalizes token for non-English usage, if in resource.

    :param str token: input token to be spell corrected
    :param dict lookup_table: lookup table of resources
    :param str micro_status: micro level status of rule/treatment
    :return: normalized (if applicable) token
    :rtype: str
    """

    if token in lookup_table["non_english_words"]:
        token = lookup_table["non_english_words"][token]
        micro_status.append("Non English Language Words Treatment: "
                            + token)
    return token


def non_English_normalization_phrase(
        phrase, lookup_table, micro_status):
    """Normalizes phrase (multi-token) for non-English usage.

    :param str phrase: input phrase to be normalized
    :param dict lookup_table: lookup table of resources
    :param str micro_status: micro level status of rule/treatment
    :return: normalized phrase for abbreviation (if applicable)
    :rtype: str
    """

    if phrase in lookup_table["non_english_words"]:
        phrase = lookup_table["non_english_words"][phrase]
        micro_status.append("Non English Language Words Treatment: "
                            + phrase)
    return phrase


def get_cleaned_sample(input_sample, token, lookup_table):
    """Prepares the cleaned sample phrase using the inputted token.

    Skips the token if it is in given stop words list

    :param input_sample:
    :param token:
    :param lookup_table:
    :return: cleaned_sample
    :rtype: str
    """

    cleaned_sample = input_sample
    if (not input_sample and token not in lookup_table[
            "stop_words"]):
        cleaned_sample = token
    elif (token not in lookup_table[
            "stop_words"]):
        cleaned_sample = input_sample + " " + token
    return cleaned_sample


def remove_duplicate_tokens(input_string):
    """Removes duplicate tokens from input string, unless permitted

    :param input_string:
    :return: output string without duplicate tokens unless allowed
    :rtype: str
    """

    refined_phrase_list = []
    new_phrase_list = input_string.split(' ')
    for token in new_phrase_list:
        if token not in refined_phrase_list:
            refined_phrase_list.append(token)
    refined_string = TreebankWordDetokenizer().detokenize(refined_phrase_list)
    refined_string = refined_string.strip()

    # Permitted duplicate tokens restored (for more such tokens, in
    # future it can be dealt by storing in pre-defined resources)
    if "gallus gallus" in input_string \
            and "gallus gallus" not in refined_string:
        refined_string = refined_string.replace("gallus", "gallus gallus")

    return refined_string


def refine_sample_sc_name(
        sample, cleaned_sample, cleaned_sample_scientific_name,
        third_party_classification):
    """Refines the sample with embedded scientific name.

    Uses domain specific customized rules

    :param sample:
    :param cleaned_sample:
    :param cleaned_sample_scientific_name:
    :param third_party_classification:
    :return: cleaned_sample_scientific_name
    :rtype: str
    """

    if "gallus" in sample or (
            "dog" in sample and "companion animal" not in
            str(third_party_classification)):
        cleaned_sample_scientific_name = cleaned_sample

    return cleaned_sample_scientific_name


def is_number(inputstring):
    """Determines whether a string is a number

    :param inputstring:
    :return:
    :rtype: bool
    """

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


def is_date(inputstring):
    """Determines  whether a string is a date or day

    :param inputstring:
    :return:
    :rtype: bool
    """
    try:
        parse(inputstring)
        return True
    except (ValueError, OverflowError):
        return False


def ngrams(input, gram_value):
    """Get ngrams with a given value of gram_value.

    gram_value=1 means unigram, gram_value=2 means bigram,
    gram_value=3 means trigram and so on

    :param input:
    :param gram_value:
    :return:
    :rtype: list
    """
    input = input.split(' ')
    output = []
    for i in range(len(input) - gram_value + 1):
        output.append(input[i:i + gram_value])
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
    # input_tokens has less than 15 tokens
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
    ``:``, ``%`` and ``,``.

    :type term: str
    :returns: ``term`` with punctuations removed
    :rtype: str
    """

    punctuations_regex_char_class = "[-_();/:%,]"
    ret = re.sub(punctuations_regex_char_class, " ", term)

    # Remove excess white space and return
    return " ".join(ret.split())


def discard_subsumed_words(word_list, retained_list):
    """Discards the words from list if subsumed in other words.

    :param word_list:
    :param retained_list:
    :return: returns the non-subsumed words in list
    :rtype: list
    """

    for word in word_list:
        # for a single token word
        if " " not in word:
            for other_word in word_list:
                if word in retained_list and word in other_word and word != other_word:
                    retained_list.remove(word)
        # for a multi-token word or compound word
        else:
            for other_word in word_list:
                ctr = 0
                input = word.split(' ')
                for i in range(len(input)):
                    if other_word.find(input[i]) == -1:
                        ctr += 1
                if word in retained_list and ctr == 0 and word != other_word:
                    retained_list.remove(word)

    return retained_list


def retain_phrase(term_list):
    """Gets final retained set of matched terms after post-processing.

    :param term_list:
    :return:
    :rtype: list
    """

    returned_set_final = []
    term_dict = {}
    word_list = []
    retained_set = []
    returned_set = []

    for term in term_list:
        term.replace("'", "")
        split_term = term.split(":", 1)
        token_part = split_term[0]
        termid_part = split_term[1]
        term_dict[token_part.strip()] = termid_part.strip()
        word_list.append(token_part.strip())
        retained_set.append(token_part.strip())
    retained_set = discard_subsumed_words(word_list, retained_set)

    for item in retained_set:
        if item in term_dict.keys():
            onto_id = term_dict[item]
            returned_item = item + ":" + onto_id
            returned_set.append(returned_item)
            returned_set_final = list(OrderedDict.fromkeys(returned_set))
    returned_set_final = sorted(returned_set_final)

    return returned_set_final


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

        if str(node) == 'bfo_0000001':  # To break the cycle
            break
        elif node in lookup_table["parents"]:
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
    """Maps ``term`` to ``lookup_table`` resource/resource permutation

    :param term:
    :param lookup_table:
    :return:
    """
    # Map ``term`` to ``lookup_table`` resource or resource permutation
    if term in lookup_table["standard_resource_labels"]:
        term_id = lookup_table["standard_resource_labels"][term]
        return {
            "term": lookup_table["non_standard_resource_ids"][term_id],
            "id": term_id,
            "status": ["A Direct Match"]
        }
    elif term in lookup_table["standard_resource_label_permutations"]:
        term_id = lookup_table["standard_resource_label_permutations"][term]
        return {
            "term": lookup_table["non_standard_resource_ids"][term_id],
            "id": term_id,
            "status": ["Permutation of Tokens in Resource Term"]
        }
    else:
        return None


def get_annotated_sample(annotated_sample, lemma, scientific_names_dict):
    """Embeds scientific name in the sample, if available.

    :param annotated_sample:
    :param lemma:
    :param scientific_names_dict:
    :return: annotated_sample
    :rtype: str
    """

    if not annotated_sample:
        annotated_sample = lemma
    else:
        annotated_sample = annotated_sample + " " + lemma
    if lemma in scientific_names_dict.keys():
        scintific_name = scientific_names_dict[lemma]
        annotated_sample = annotated_sample + "  {" + scintific_name + "}"
    if annotated_sample in scientific_names_dict.keys():
        scintific_name = scientific_names_dict[annotated_sample]
        annotated_sample = annotated_sample + "  {" + scintific_name + "}"

    return annotated_sample


def get_matched_component_standardized(matched_component):
    """Converts matched components to standard upper case ontology ids.

    :param matched_component:
    :return: updated_matched_component_list
    :rtype: list
    """

    updated_matched_component_list = []
    if len(matched_component) > 0:
        for item in matched_component:
            matched_component_item = str(item).split(":")
            matched_component_first = matched_component_item[0]
            matched_component_second = matched_component_item[1]
            matched_component_second_standard = matched_component_second.upper()
            updated_matched_component = \
                matched_component_first + ":" + matched_component_second_standard
            updated_matched_component_list.append(updated_matched_component)

    return updated_matched_component_list


def get_head_noun(text_segment):
    """Get nouns from a given text segment.

    This function is for future use.

    :param str text_segment: See
        Takes a text_segment (phrase, word or sentence)
    :type text_segment: str
    :return: The nouns in the text segment
    :rtype: list
    """
    # Check if noun (=NN)
    def is_noun(pos): return pos[:2] == 'NN'
    # Tokenise text and keep only nouns
    tokenized_text = word_tokenize(text_segment)
    nouns = [word for (word, pos) in pos_tag(tokenized_text) if is_noun(pos)]
    return nouns


def calculate_penalty_weight(micro_status, confidence_weight_penalty_dict):
    """Calculate ``total penalty`` for usage of rules in case of no
    ``direct match``.

    This function is for future use.

    :param list micro_status: The list showing different rules applied
        to the sample
    :param dict[str, str] confidence_weight_penalty_dict: See
        dictionary of penalty score for different rules affecting
        confidence
    :returns: A score of total penalty to be used for calculating
        overall confidence score
    :rtype: float
    """

    total_penalty_weight = 0.0
    # This applies penalty weight according to the rules applied
    for applied_rule in micro_status:
        applied_rule_string = str(applied_rule).lower()
        for key, value in confidence_weight_penalty_dict.items():
            if key in applied_rule_string:
                penalty_weight = int(value)
                total_penalty_weight = total_penalty_weight + int(penalty_weight)

    return total_penalty_weight


def decode_confidence_level(confidence_score):
    """ Decodes the confidence level from confidence score

    This function is for future use.

    :param  float confidence_score: See
        Takes a final calculated confidence score
    :type confidence_score: float
    :return: The assigned confidence level
    :rtype: str
    """

    if confidence_score > 89.0:
        confidence_level = "Highest"
    elif confidence_score > 79.0:
        confidence_level = "High"
    elif confidence_score > 69.0:
        confidence_level = "Moderately High"
    elif confidence_score > 59.0:
        confidence_level = "Medium"
    else:
        confidence_level = "Low"
    return confidence_level


def assign_confidence_level(sample_tokens, match_status, micro_status,
                            confidence_weight_penalty_dict,
                            sample_covered_tokens, head_nouns):
    """Calculates ``confidence level`` for term mapping.

     Uses ``confidence score`` by incorporating penalty weight based
     on the rules applied to term mapping for sample

    This function is for future use.

    :param list sample_tokens: The list of tokens in the sample
    :param str match_status: The type of match for sample
    :param list micro_status: The list showing different rules applied
        to the sample
    :param dict[str, str] confidence_weight_penalty_dict: See
        Dictionary of penalty sc ore for different rules affecting
        confidence
    :param set sample_covered_tokens: The set of covered tokens from
        all the tokens
    :param list head_nouns: The list of head nouns found in the sample
    :returns: A confidence level for the term mapping of sample
    :rtype: str
    """

    confidence_score = 0
    total_penalty_weight = calculate_penalty_weight(
        micro_status, confidence_weight_penalty_dict)
    if "Full Term Match" in match_status:
        confidence_score = 100
        confidence_score = confidence_score - total_penalty_weight
    elif "Component Match" in match_status:
        confidence_score = 90
        not_covered_tokens = set()
        not_covered_head_nouns = set()
        for token in head_nouns:
            if token not in str(sample_covered_tokens):
                not_covered_head_nouns.add(token)
        for token in sample_tokens:
            if token not in str(sample_covered_tokens) and token \
                    not in str(not_covered_head_nouns):
                not_covered_tokens.add(token)    # Why this
        length_of_not_covered_tokens = len(not_covered_tokens)
        length_of_not_covered_head_nouns = len(not_covered_head_nouns)
        component_penalty_weight = length_of_not_covered_tokens * 6
        head_nouns_penalty_weight = length_of_not_covered_head_nouns * 10
        confidence_score = confidence_score - total_penalty_weight \
            - component_penalty_weight - head_nouns_penalty_weight
    elif "No Match" in match_status:
        confidence_score = 0

    confidence_level = decode_confidence_level(confidence_score)
    assigned_confidence = confidence_level \
        + " (" + str(confidence_score) + "%)"

    return assigned_confidence
