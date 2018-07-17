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


# 4-Method to simply pre-process the string token on some pre-determined parts [\ , . ]
def preProcess(stringToken):
    if ('\'s' in stringToken):
        stringToken1 = stringToken.replace("\'s", "")  # for cow's to cow
        stringToken = stringToken1
    if (',' in stringToken):  # comma concatenated in token is get rid of
        stringToken1 = stringToken.rstrip(', ')
        stringToken = stringToken1
    if ('.' in stringToken):  # dot concatenated in token is get rid of
        stringToken1 = stringToken.rstrip('. ')
        stringToken = stringToken1
    return stringToken


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


# 7-Methods to add suffixes such as food product or product to input phrase to improve Term matching
def addSuffix(inputstring, suffixString):
    output = inputstring + " " + suffixString
    return output


# 8-Method to get all permutations of input string          -has overhead so the size of the phrase has been limited to 4-grams
def allPermutations(inputstring):
    listOfPermutations = inputstring.split()
    setPerm = set(itertools.permutations(listOfPermutations))
    return setPerm


# 9-Method to get all combinations of input string
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

class MatchNotFoundError(Exception):
    """Exception class for indicating failed full-term matches.

    This subclass inherits it behaviour from the Exception class, and
    should be raised when a full-term match for a sample is
    not found.

    Instance variables:
        * message <class "str">
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
    punctuationsList = ['-', '_', '(', ')', ';', '/', ':', '%']  # Current punctuationsList for basic treatment
    covered_tokens = []
    remainingAllTokensSet = []
    remainingTokenSet = []
    prioritizedRetainedSet=[]
    samplesDict = collections.OrderedDict()
    samplesList = []
    samplesSet = []
    resource_terms = {}
    resource_terms_revised = {}
    resource_terms_ID_based = {}

    # 11-Get all synonyms from resource in CSV file format and put in a dictionary to be used further
    synonyms = get_resource_dict("SynLex.csv")

    # 12-Get all abbreviation/acronyms from resource in CSV file format and put in a dictionary to be used further
    abbreviations = get_resource_dict("AbbLex.csv")
    abbreviation_lower = get_resource_dict("AbbLex.csv", True)

    # 13-Get all Non English Language words mappings from resource in CSV file format and put in a dictionary to be used further
    non_english_words = get_resource_dict("NefLex.csv")
    non_english_words_lower = get_resource_dict("NefLex.csv", True)

    # 14-Get all spelling mistake examples from resource in CSV file format and put in a dictionary to be used further
    spelling_mistakes = get_resource_dict("ScorLex.csv")
    spelling_mistakes_lower = get_resource_dict("ScorLex.csv", True)

    # 15-Get candidate processes from resource in a CSV file format and put in a dictionary to be used further
    processes = get_resource_dict("candidateProcesses.csv")
    
    # 16-Get all semantic tags (e.g.qualities) from resource in a CSV file format and put in a dictionary to be used further
    qualities = get_resource_dict("SemLex.csv")
    qualities_lower = get_resource_dict("SemLex.csv", True)

    # 17-Get all collocations (Wikipedia) from resource in a CSV file format and put in a dictionary to be used further
    collocations = get_resource_dict("wikipediaCollocations.csv")

    # 18-Method to get all inflection exception words from resource in CSV file format -Needed to supercede the general inflection treatment
    inflection_exceptions = get_resource_dict("inflection-exceptions.csv", True)
    
    # 19-Method to Get all stop words from resource in CSV file format -A very constrained lists of stop words is
    # used as other stop words are assumed to have some useful semantic meaning
    stop_words = get_resource_dict("mining-stopwords.csv", True)
    
    # 21- To get all terms from resources- right now in a CSV file extracted from ontologies using another external script
    resource_terms_ID_based = get_resource_dict("CombinedResourceTerms.csv")
    # Swap keys and values in resourceTermsIDBasedDict
    resource_terms = {v:k for k,v in resource_terms_ID_based.items()}
    # Convert keys in resourceTermsDict to lowercase
    resource_terms_revised = {k.lower():v for k,v in resource_terms.items()}

    # 23-Method for getting all the permutations of Resource Terms
    resource_permutation_terms = {}
    # Iterate
    for k, v in resource_terms_revised.items():
        resourceid = v
        resource = k
        if "(" not in resource:
            sampleTokens = word_tokenize(resource.lower())
            # for tkn in sampleTokens:
            if len(sampleTokens) < 7 and "NCBITaxon" not in resourceid :  # NCBI Taxon has 160000 terms - great overhead fo:
                if "NCBITaxon" in resourceid:
                    print("NCBITaxonNCBITaxonNCBITaxon=== ")

                setPerm = allPermutations(resource)
                logger.debug("sssssssssssssss=== " + str(setPerm))
                for perm in setPerm:
                    permString = ' '.join(perm)
                    resource_permutation_terms[permString.strip()] = resourceid.strip()

    # 24-Method for getting all the permutations of Bracketed Resource Terms
    resource_bracketed_permutation_terms={}
    # Iterate
    for k, v in resource_terms_revised.items():
        resourceid = v
        resource1 = k
        sampleTokens = word_tokenize(resource1.lower())
        if len(sampleTokens) < 7 and "NCBITaxon" not in resourceid :  # NCBI Taxon has 160000 terms - great overhead for permutations
            if "(" in resource1:
                part1 = find_left_r(resource1, "(", ")")
                part2 = find_between_r(resource1, "(", ")")
                candidate = ""

                if "," not in part2:
                    candidate = part2 + " " + part1
                    setPerm = allPermutations(candidate)
                    for perm in setPerm:
                        permString = ' '.join(perm)
                        resource_bracketed_permutation_terms[permString.strip()] = resourceid.strip()
                elif "," in part2:
                    lst = part2.split(",")
                    bracketedPart = ""
                    for x in lst:
                        if not bracketedPart:
                            bracketedPart = x.strip()
                        else:
                            bracketedPart = bracketedPart + " " + x.strip()
                    candidate = bracketedPart + " " + part1
                    setPerm = allPermutations(candidate)
                    for perm in setPerm:
                        permString = ' '.join(perm)
                        resource_bracketed_permutation_terms[permString.strip()] = resourceid.strip()
                    
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
        # statusAddendum = ""
        status_addendum = []
        final_status = []
        del final_status [:]
        retained_tokens = []
        remaining_tokens = []
        #Writing in the output file with sampleid and sample to start with
        # output fields:
        #   sample_id:   sampleid
        #   sample_desc: sample
        fw.write('\n' + sampleid + '\t' + sample)

        sample = punctuationTreatment(sample, punctuationsList)  # Sample gets simple punctuation treatment
        sample = re.sub(' +', ' ', sample)  # Extra innner spaces are removed
        sampleTokens = word_tokenize(sample.lower())    #Sample is tokenized into tokenList

        newPhrase = ""  # Phrase that will be used for cleaned sample
        lemma = ""

        for tkn in sampleTokens:
            remaining_tokens.append(tkn.lower())  # To start with all remaining tokens in set

        # ===Few preliminary things- Inflection,spelling mistakes, Abbreviations, acronyms, foreign words, Synonyms taken care of
        for tkn in sampleTokens:

            # Some preprocessing (only limited or controlled) Steps
            tkn = preProcess(tkn)

            # Plurals are converted to singulars with exceptions
            if (tkn.endswith("us") or tkn.endswith("ia") or tkn.endswith("ta")):  # for inflection exception in general-takes into account both lower and upper case (apart from some inflection-exception list used also in next
                lemma = tkn
            elif (tkn not in inflection_exceptions):  # Further Inflection Exception list is taken into account
                lemma = inflection.singularize(tkn)
                if (tkn != lemma):  #Only in case when inflection makes some changes in lemma
                    # statusAddendum = "Inflection (Plural) Treatment"
                    status_addendum.append("Inflection (Plural) Treatment")
            else:
                lemma = tkn

            # Misspellings are dealt with  here
            if (lemma in spelling_mistakes.keys()):  # spelling mistakes taken care of
                lemma = spelling_mistakes[lemma]
                # statusAddendum = statusAddendum + "Spelling Correction Treatment"
                status_addendum.append("Spelling Correction Treatment")
            elif (lemma.lower() in spelling_mistakes_lower.keys()):
                lemma = spelling_mistakes_lower[lemma.lower()]
                # statusAddendum = statusAddendum + "Change Case and Spelling Correction Treatment"
                status_addendum.append("Change Case and Spelling Correction Treatment")
            if (lemma in abbreviations.keys()):  # Abbreviations, acronyms, foreign language words taken care of- need rule for abbreviation e.g. if lemma is Abbreviation
                lemma = abbreviations[lemma]
                # statusAddendum = "Abbreviation-Acronym Treatment"
                status_addendum.append("Abbreviation-Acronym Treatment")
            elif (lemma.lower() in abbreviation_lower.keys()):
                lemma = abbreviation_lower[lemma.lower()]
                # statusAddendum = "Change Case and Abbreviation-Acronym Treatment"
                status_addendum.append("Change Case and Abbreviation-Acronym Treatment")

            if (lemma in non_english_words.keys()):  # Non English language words taken care of
                lemma = non_english_words[lemma]
                # statusAddendum = statusAddendum + "Non English Language Words Treatment"
                status_addendum.append("Non English Language Words Treatment")
            elif (lemma.lower() in non_english_words_lower.keys()):
                lemma = non_english_words_lower[lemma.lower()]
                # statusAddendum = statusAddendum + "Change Case and Non English Language Words Treatment"
                status_addendum.append("Change Case and Non English Language Words Treatment")


            # ===This will create a cleaned sample after above treatments [Here we are making new phrase now in lower case]
            if (not newPhrase and lemma.lower() not in stop_words):  # if newphrase is empty and lemma is in not in stopwordlist (abridged according to domain)
                newPhrase = lemma.lower()
            elif (
                lemma.lower() not in stop_words):  # if newphrase is not empty and lemma is in not in stopwordlist (abridged according to domain)
                newPhrase = newPhrase + " " + lemma.lower()

            newPhrase = re.sub(' +', ' ', newPhrase)  # Extra innner spaces removed from cleaned sample

            if (newPhrase in abbreviations.keys()):  # NEED HERE AGAIN ? Abbreviations, acronyms, non English words taken care of- need rule for abbreviation
                newPhrase = abbreviations[newPhrase]
                # statusAddendum = statusAddendum + "Cleaned Sample and Abbreviation-Acronym Treatment"
                status_addendum.append("Cleaned Sample and Abbreviation-Acronym Treatment")
            elif (newPhrase in abbreviation_lower.keys()):
                newPhrase = abbreviation_lower[newPhrase]
                # statusAddendum = statusAddendum + "Cleaned Sample and Abbreviation-Acronym Treatment"
                status_addendum.append("Cleaned Sample and Abbreviation-Acronym Treatment")

            if (newPhrase in non_english_words.keys()):  # non English words taken care of
                newPhrase = non_english_words[newPhrase]
                # # statusAddendum = statusAddendum + "Non English Language Words Treatment"
                # statusAddendum = statusAddendum + "Cleaned Sample and Non English Language Words Treatment"
                status_addendum.append("Cleaned Sample and Non English Language Words Treatment")
            elif (newPhrase in non_english_words_lower.keys()):
                newPhrase = non_english_words_lower[newPhrase]
                # statusAddendum = statusAddendum + "Cleaned Sample and Non English Language Words Treatment"
                status_addendum.append("Cleaned Sample and Non English Language Words Treatment")

        # Here we are making the tokens of cleaned sample phrase
        newSampleTokens = word_tokenize(newPhrase.lower())
        tokens_pos = pos_tag(newSampleTokens)
        if args.format == "full":
            # output fields:
            #   'cleaned_sample': newPhrase
            #   'phrase_pos_tagged': str(tokens_pos)
            fw.write('\t' + newPhrase + '\t' + str(tokens_pos))
        else:
            # output_fields:
            #   'cleaned_sample': newPhrase
            fw.write('\t' + newPhrase )

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
        def find_full_term_match(sample):
            """Find an annotated, full-term match for a sample.

            TODO:
                * complete function docstring
                * implement function
                * descriptive comments for ret keys
                * move this function out of run
                    * The reason it is currently in run is because we
                        need access to several variables that are local
                        to run
                    * There are two potential solutions:
                        * Pass all local variables to this function
                            * Unreasonable, there are too many
                        * Create a class with the following:
                            * Constructer with all variables relevant
                                to application rules
                            * get_resource_dict
                                * Likely called in constructer
                            * find_full_term_match
                            * MatchNotFoundError
                            * This is the most reasonable solution
                            * Before beginning the design and
                                construction of a class, we may want to
                                do the following:
                                    * Get find_full_term_match working
                                    * Abstract component matching
                                        * May fit in new class
                * simplify change-of-case treatments as follows:
                    * resource dictionaries only contain lower-case
                        words
                    * check if sample.lower() is in a given dictionary
                    * add appropriate status addendum
                    * check if sample != sample.lower()
                        * if true, add change-of-case treatment to
                            status addendum
            """
            # Dictionary to return
            ret = {
                # ...
                "matched_term": "",
                # ...
                "all_match_terms_with_resource_ids": "",
                # ...
                "retained_terms_with_resource_ids": "",
                # TODO: Remove this? Not used in full-term match.
                "number_of_components_for_component_match": "",
                # ...
                "match_status_macro_level": "",
                # ...
                "match_status_micro_level": "",
            }

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
            elif sample in resource_terms:
                # Term with we found a full-term match for
                matched_term = sample
                # Resource ID for matched_term
                resource_id = resource_terms[matched_term]
                # Update retained_tokens
                # TODO: Can this be a local variable?
                retained_tokens.append(matched_term + ":" + resource_id)
                # Update status_addendum
                status_addendum.append("A Direct Match")
            # Full-term match with change-of-case in input data
            elif sample.lower() in resource_terms:
                # Term with we found a full-term match for
                matched_term = sample.lower()
                # Resource ID for matched_term
                resource_id = resource_terms[matched_term]
                # Update retained_tokens
                retained_tokens.append(matched_term + ":" + resource_id)
                # Update status_addendum
                status_addendum.append("Change of Case in Input Data")
            # Full-term match with change-of-case in resource data
            elif sample.lower() in resource_terms_revised:
                # Term with we found a full-term match for
                matched_term = sample.lower()
                # Resource ID for matched_term
                resource_id = resource_terms_revised[matched_term]
                # Update retained_tokens
                retained_tokens.append(matched_term + ":" + resource_id)
                # Update status_addendum
                status_addendum.append("Change of Case in Resource Data")
            # Full-term match with permutation of resource term
            elif sample.lower() in resource_permutation_terms:
                # Term we found a permutation for
                matched_term = sample.lower()
                # Resource ID for matched_term's permutation
                resource_id = resource_permutation_terms[matched_term]
                # Permutation corresponding to matched_term
                matched_permutation = resource_terms_ID_based[resource_id]
                # Update retained_tokens
                retained_tokens.append(matched_permutation + ":"
                    + resource_id)
                # Update status_addendum
                status_addendum.append(
                    "Permutation of Tokens in Resource Term")
            # Full-term match not found
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
            # Tokenize sample
            sample_tokens = word_tokenize(sample.lower())
            # Iterate over tokens
            for token in sample_tokens:
                # Add token to covered_tokens
                covered_tokens.append(token)
                # Remove token from remaining_tokens
                remaining_tokens.remove(token)
            # Return
            return ret

        # Rule1: Annotate all the empty samples
        # Rule2: Annotate all the Full Term Matches of Terms without any treatment
        # Rule3: Annotate all the Full Term Matches of Terms with change of case  -resourceRevisedTermsDict
        try:
            full_term_match = find_full_term_match(sample)
            if args.format == "full":
                fw.write("\t" + full_term_match["matched_term"] + "\t"
                    + full_term_match["all_match_terms_with_resource_ids"]
                    + "\t"
                    + full_term_match["retained_terms_with_resource_ids"]
                    + "\t" + "\t"
                    + full_term_match["match_status_macro_level"] + "\t"
                    + full_term_match["match_status_micro_level"])
            else:
                fw.write("\t" + full_term_match["matched_term"] + "\t"
                    + full_term_match["all_match_terms_with_resource_ids"])
            trigger = True
        except MatchNotFoundError:
            pass

        # Rule3: Annotate all the Full Term Matches of Terms with change of case  -resourceRevisedTermsDict
        if (sample.lower() in resource_bracketed_permutation_terms.keys() and not trigger):
            resourceId = resource_bracketed_permutation_terms[sample.lower()]
            # here need to do the actualResourceTerm=resourceTermsDict.get(resourceId)
            resourceOriginalTerm = resource_terms_ID_based[resourceId]
            status = "Full Term Match"
            # statusAddendum = "[Permutation of Tokens in Bracketed Resource Term]"
            status_addendum.append("Permutation of Tokens in Bracketed Resource Term")
            final_status = set(status_addendum)
            retained_tokens.append(resourceOriginalTerm + ":" + resourceId)
            if args.format == 'full':
                # output fields:
                #   'matched_term':                             sample.lower()
                #   'all_matched_terms_with_resource_ids':      str(list(retained_tokens))
                #   'retained_terms_with_resource_ids'          str(list(retained_tokens))
                #   'number_of_components_for_component_match': 
                #   'match_status_macro_level':                 status
                #   'match_status_micro_level':                 str(list(final_status))
                fw.write('\t' + sample.lower() + '\t' +  str(list(retained_tokens)) + '\t' + str(list(retained_tokens)) + '\t' + '\t' + status + '\t' + str(list(final_status)))
            else:
                # output fields:
                #   'matched_term':                        sample.lower()
                #   'all_matched_terms_with_resource_ids': str(list(retained_tokens))
                fw.write('\t' + sample.lower() + '\t' + str(list(retained_tokens)))
            # To Count the Covered Tokens(words)
            thisSampleTokens = word_tokenize(sample.lower())
            for thisSampleIndvToken in thisSampleTokens:
                covered_tokens.append(thisSampleIndvToken)
                remaining_tokens.remove(thisSampleIndvToken)
            trigger = True

        # Here we check all the suffices that can be applied to input term to make it comparable with resource terms
        suffixList = ["(food source)","(vegetable) food product","vegetable food product", "nut food product","fruit food product","seafood product","meat food product", "plant fruit food product","plant food product", "(food product)","food product","plant (food source)","product","(whole)","(deprecated)"]
        for suff in range(len(suffixList)):
            suffixString=suffixList[suff]
            sampleRevisedWithSuffix = addSuffix(sample, suffixString)
            if (sampleRevisedWithSuffix in resource_terms_revised.keys() and not trigger):
                resourceId = resource_terms_revised[sampleRevisedWithSuffix]
                status = "Full Term Match"
                # statusAddendum = "[Change of Case of Resource and Suffix Addition- "+suffixString+" to the Input]"
                status_addendum.append("[Change of Case of Resource and Suffix Addition- "+suffixString+" to the Input]")
                final_status = set(status_addendum)
                retained_tokens.append(sampleRevisedWithSuffix + ":" + resourceId)
                if args.format == 'full':
                    # output fields:
                    #   'matched_term':                             sample.lower()
                    #   'all_matched_terms_with_resource_ids':      str(list(retained_tokens))
                    #   'retained_terms_with_resource_ids'          str(list(retained_tokens))
                    #   'number_of_components_for_component_match': 
                    #   'match_status_macro_level':                 status
                    #   'match_status_micro_level':                 str(list(final_status))
                    fw.write('\t' + sample.lower() + '\t' + str(list(retained_tokens)) + '\t' + str(list(retained_tokens)) + '\t' + '\t' + status + '\t' + str(list(final_status)))
                else:
                    # output fields:
                    #   'matched_term':                        sample.lower()
                    #   'all_matched_terms_with_resource_ids': str(list(retained_tokens))
                    fw.write('\t' + sample.lower() + '\t' + str(list(retained_tokens)))
                trigger = True
                # To Count the Covered Tokens(words)
                thisSampleTokens = word_tokenize(sample.lower())
                for thisSampleIndvToken in thisSampleTokens:
                    covered_tokens.append(thisSampleIndvToken)
                    remaining_tokens.remove(thisSampleIndvToken)


        # Rule4: This will open now the cleaned sample to the test of Full Term Matching
        if (not trigger):
            logger.debug("We will go further with other rules now on cleaned sample")
            sampleTokens = word_tokenize(sample.lower())
            logger.debug("==============" + sample.lower())
            logger.debug("--------------" + newPhrase.lower())

            if ((newPhrase.lower() in resource_terms.keys() ) and not trigger):
                if (newPhrase.lower() in resource_terms.keys()):
                    resourceId = resource_terms[newPhrase.lower()]  # Gets the id of the resource for matched term
                status = "Full Term Match"  # -Inflection, Synonym, Spelling Correction, Foreign Language Treatment "
                # statusAddendum = statusAddendum + "[A Direct Match with Cleaned Sample]"
                status_addendum.append("A Direct Match with Cleaned Sample")
                final_status = set(status_addendum)
                retained_tokens.append(newPhrase.lower() + ":" + resourceId)
                if args.format == 'full':
                    # output fields:
                    #   '': newPhrase.lower()
                    #   '': str(list(retained_tokens))
                    #   '': str(list(retDet))
                    #   '':
                    #   '': status
                    #   '': str(list(final_status))
                    fw.write('\t' + newPhrase.lower() + '\t' + str(list(retained_tokens)) + '\t' + str(list(retained_tokens)) + '\t' + '\t' + status + '\t' + str(list(final_status)))
                else:
                    # output fields:
                    #   '': newPhrase.lower()
                    #   '': str(retained_tokens)
                    fw.write('\t' + newPhrase.lower() + '\t' + str(list(retained_tokens)))
                # To Count the Covered Tokens(words)
                thisSampleTokens = word_tokenize(sample.lower())
                for thisSampleIndvToken in thisSampleTokens:
                    covered_tokens.append(thisSampleIndvToken)
                    remaining_tokens.remove(thisSampleIndvToken)
                trigger = True


            elif ((newPhrase.lower() in resource_terms_revised.keys() ) and not trigger):
                if (newPhrase.lower() in resource_terms_revised.keys()):
                    resourceId = resource_terms_revised[newPhrase.lower()]  # Gets the id of the resource for matched term
                status = "Full Term Match"
                # statusAddendum = statusAddendum + "[Change of Case of Resource Terms]"
                status_addendum.append("Change of Case of Resource Terms")
                final_status = set(status_addendum)
                retained_tokens.append(newPhrase.lower() + ":" + resourceId)
                if args.format == 'full':
                    fw.write('\t' + newPhrase.lower() + '\t' + str(list(retained_tokens)) + '\t' + str(list(retained_tokens)) + '\t' + '\t' + status + '\t' + str(list(final_status)))
                else:
                    fw.write('\t' + newPhrase.lower() + '\t' + str(list(retained_tokens)))
                # To Count the Covered Tokens(words)
                thisSampleTokens = word_tokenize(sample.lower())
                for thisSampleIndvToken in thisSampleTokens:
                    covered_tokens.append(thisSampleIndvToken)
                    remaining_tokens.remove(thisSampleIndvToken)
                trigger = True

            elif (newPhrase.lower() in resource_permutation_terms.keys() and not trigger):
                resourceId = resource_permutation_terms[newPhrase.lower()]
                status = "Full Term Match"
                # statusAddendum = statusAddendum + "[Permutation of Tokens in Resource Term]"
                status_addendum.append("Permutation of Tokens in Resource Term")
                final_status = set(status_addendum)
                resourceOriginalTerm = resource_terms_ID_based[resourceId]
                retained_tokens.append(resourceOriginalTerm + ":" + resourceId)
                if args.format == 'full':
                    fw.write('\t' + newPhrase.lower() + '\t' + str(list(retained_tokens)) + '\t' + str(list(retained_tokens)) + '\t' + '\t' + status + '\t' + str(list(final_status)))
                else:
                    fw.write('\t' + newPhrase.lower() + '\t' + str(list(retained_tokens)))
                # To Count the Covered Tokens(words)
                thisSampleTokens = word_tokenize(sample.lower())
                for thisSampleIndvToken in thisSampleTokens:
                    covered_tokens.append(thisSampleIndvToken)
                    remaining_tokens.remove(thisSampleIndvToken)
                trigger = True

            elif (newPhrase.lower() in resource_bracketed_permutation_terms.keys() and not trigger):
                resourceId = resource_bracketed_permutation_terms[newPhrase.lower()]
                status = "Full Term Match"
                # statusAddendum = statusAddendum + "[Permutation of Tokens in Bracketed Resource Term]"
                status_addendum.append("Permutation of Tokens in Bracketed Resource Term")
                final_status = set(status_addendum)
                resourceOriginalTerm = resource_terms_ID_based[resourceId]
                retained_tokens.append(resourceOriginalTerm + ":" + resourceId)
                if args.format == 'full':
                    fw.write('\t' + newPhrase.lower() + '\t' + str(list(retained_tokens)) + '\t' + str(list(retained_tokens)) + '\t' + '\t' + status + '\t' + str(list(final_status)))
                else:
                    fw.write('\t' + newPhrase.lower() + '\t' + str(list(retained_tokens)))
                # To Count the Covered Tokens(words)
                thisSampleTokens = word_tokenize(sample.lower())
                for thisSampleIndvToken in thisSampleTokens:
                    covered_tokens.append(thisSampleIndvToken)
                    remaining_tokens.remove(thisSampleIndvToken)
                trigger = True

            for suff in range(len(suffixList)):
                suffixString = suffixList[suff]
                sampleRevisedWithSuffix = addSuffix(newPhrase.lower(), suffixString)
                if (sampleRevisedWithSuffix in resource_terms_revised.keys() and not trigger):
                    resourceId = resource_terms_revised[sampleRevisedWithSuffix]
                    status = "Full Term Match"
                    # statusAddendum = "[CleanedSample-Change of Case of Resource and Suffix Addition- " + suffixString + " to the Input]"
                    status_addendum.append("[CleanedSample-Change of Case of Resource and Suffix Addition- " + suffixString + " to the Input]")
                    final_status = set(status_addendum)
                    retained_tokens.append(sampleRevisedWithSuffix + ":" + resourceId)
                    if args.format == 'full':
                        fw.write('\t' + sample.lower() + '\t' + str(list(retained_tokens)) + '\t' + str(list(retained_tokens)) + '\t' + '\t' + status + '\t' + str(list(final_status)))
                    else:
                        fw.write('\t' + sample.lower() + '\t' + str(list(retained_tokens)))
                    # To Count the Covered Tokens(words)
                    thisSampleTokens = word_tokenize(sample.lower())
                    for thisSampleIndvToken in thisSampleTokens:
                        covered_tokens.append(thisSampleIndvToken)
                        remaining_tokens.remove(thisSampleIndvToken)
                    trigger = True



        # Rule5: Full Term Match if possible from multi-word collocations -e.g. from Wikipedia
        if (not trigger):
            logger.debug("We will go further with other rules")
            sampleTokens = word_tokenize(sample.lower())
            logger.debug("==============" + sample.lower())
            logger.debug("--------------" + newPhrase.lower())
            if (newPhrase.lower() in collocations.keys()):
                resourceId = collocations[newPhrase.lower()]
                status = "Full Term Match"
                # statusAddendum = statusAddendum + "[New Candidadte Terms -validated with Wikipedia Based Collocation Resource]"
                status_addendum.append("New Candidadte Terms -validated with Wikipedia Based Collocation Resource")
                final_status = set(status_addendum)
                retained_tokens.append(newPhrase.lower() + ":" + resourceId)
                if args.format == 'full':
                    fw.write('\t' + newPhrase.lower() + '\t' +str(list(retained_tokens)) + '\t' + str(list(retained_tokens))  + '\t' + '\t' + status + '\t' + str(list(final_status)))
                else:
                    fw.write('\t' + newPhrase.lower() + '\t' + str(list(retained_tokens)))
                # To Count the Covered Tokens(words)
                thisSampleTokens = word_tokenize(sample.lower())
                for thisSampleIndvToken in thisSampleTokens:
                    covered_tokens.append(thisSampleIndvToken)
                    remaining_tokens.remove(thisSampleIndvToken)
                trigger = True

        # Component Matches Section
        if (not trigger):
            logger.debug("We will go further with other rules now targetting components of input data")
            # Some Declarations for component match cases
            partialMatchedList = []
            partialMatchedResourceList = []
            partialMatchedSet = []
            newChunk = newPhrase.lower()
            newChunkTokens = word_tokenize(newChunk.lower())

            # This is the case of making 5-gram chunks and subsequent processing for cleaned samples
            if len(newChunkTokens)<7:
                newChunk5Grams = combi(newChunkTokens, 5)
            else:
                newChunk5Grams = ngrams(newChunk, 5)

            for nc in newChunk5Grams:
                grm1 = ' '.join(nc)
                grmTokens = word_tokenize(grm1.lower())
                localTrigger = False
                setPerm = allPermutations(grm1)  # Gets the set of all possible permutations for this gram type chunks
                for perm in setPerm:
                    grm = ' '.join(perm)
                    if (grm in abbreviations.keys()):  # rule for abbreviation
                        grm = abbreviations[grm]
                        # statusAddendum = statusAddendum + "[Abbreviation-Acronym Treatment]"
                        status_addendum.append("Abbreviation-Acronym Treatment")
                    if (grm in non_english_words.keys()):  # rule for abbreviation
                        grm = non_english_words[grm]
                        # statusAddendum = statusAddendum + "[Non English Language Words Treatment]"
                        status_addendum.append("Non English Language Words Treatment")
                    if (grm in synonyms.keys()):  ## Synonyms taken care of- need more synonyms
                        grm = synonyms[grm]
                        # statusAddendum = statusAddendum + "[Synonym Usage]"
                        status_addendum.append("Synonym Usage")

                    # Matching Test for 5-gram chunk
                    if ((grm in resource_terms.keys() ) and not localTrigger):
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            covered_tokens.append(eachTkn)
                            if eachTkn in remaining_tokens:
                                remaining_tokens.remove(eachTkn)
                        localTrigger = True
                        # statusAddendum="Match with 5-Gram Chunk"+statusAddendum
                    elif ((grm in resource_terms_revised.keys() )and not localTrigger):
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            covered_tokens.append(eachTkn)
                            if eachTkn in remaining_tokens:
                                remaining_tokens.remove(eachTkn)
                            # # statusAddendum = "Match with 5-Gram Chunk"+statusAddendum
                        localTrigger = True
                    elif (grm in resource_bracketed_permutation_terms.keys() and not localTrigger):
                        resourceId = resource_bracketed_permutation_terms[grm]
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            covered_tokens.append(eachTkn)
                            if eachTkn in remaining_tokens:
                                remaining_tokens.remove(eachTkn)
                        # statusAddendum = "[Permutation of Tokens in Bracketed Resource Term]"
                        status_addendum.append("Permutation of Tokens in Bracketed Resource Term")
                        localTrigger = True
                    for suff in range(len(suffixList)):
                        suffixString = suffixList[suff]
                        sampleRevisedWithSuffix = addSuffix(grm, suffixString)
                        if (sampleRevisedWithSuffix in resource_terms_revised.keys() and not localTrigger):  # Not trigger true is used here -reason
                            # resourceId = resourceRevisedTermsDict[sampleRevisedWithSuffix]
                            partialMatchedList.append(sampleRevisedWithSuffix)
                            # statusAddendum = statusAddendum + "[Suffix Addition- " + suffixString + " to the Input]"
                            status_addendum.append("Suffix Addition- " + suffixString + " to the Input")
                            for eachTkn in grmTokens:
                                covered_tokens.append(eachTkn)
                                if eachTkn in remaining_tokens:
                                    remaining_tokens.remove(eachTkn)
                            localTrigger = True


            # This is the case of making 4-gram chunks and subsequent processing for cleaned samples
            if len(newChunkTokens)<7:
                newChunk4Grams = combi(newChunkTokens, 4)
            else:
                newChunk4Grams = ngrams(newChunk, 4)
            for nc in newChunk4Grams:
                grm1 = ' '.join(nc)
                grmTokens = word_tokenize(grm1.lower())
                localTrigger = False
                setPerm = allPermutations(grm1)  # Gets the set of all possible permutations for this gram type chunks
                for perm in setPerm:
                    grm = ' '.join(perm)
                    if (grm in abbreviations.keys()):  # rule for abbreviation
                        grm = abbreviations[grm]
                        # statusAddendum = statusAddendum + "[Abbreviation-Acronym Treatment]"
                        status_addendum.append("Abbreviation-Acronym Treatment")
                    if (grm in non_english_words.keys()):  # rule for abbreviation
                        grm = non_english_words[grm]
                        # statusAddendum = statusAddendum + "[Non English Language Words Treatment]"
                        status_addendum.append("Non English Language Words Treatment")
                    if (grm in synonyms.keys()):  ## Synonyms taken care of- need more synonyms
                        grm = synonyms[grm]
                        # statusAddendum = statusAddendum + "[Synonym Usage]"
                        status_addendum.append("Synonym Usage")

                    # Matching Test for 4-gram chunk
                    if ((grm in resource_terms.keys()) and not localTrigger):
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            covered_tokens.append(eachTkn)
                            if eachTkn in remaining_tokens:
                                remaining_tokens.remove(eachTkn)
                        localTrigger = True
                        # statusAddendum="Match with 5-Gram Chunk"+statusAddendum
                    elif ((  grm in resource_terms_revised.keys() ) and not localTrigger):
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            covered_tokens.append(eachTkn)
                            if eachTkn in remaining_tokens:
                                remaining_tokens.remove(eachTkn)
                        localTrigger = True
                    elif (grm in resource_bracketed_permutation_terms.keys() and not localTrigger):
                        resourceId = resource_bracketed_permutation_terms[grm]
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            covered_tokens.append(eachTkn)
                            if eachTkn in remaining_tokens:
                                remaining_tokens.remove(eachTkn)
                        # statusAddendum = "[Permutation of Tokens in Bracketed Resource Term]"
                        status_addendum.append("Permutation of Tokens in Bracketed Resource Term")
                        localTrigger = True
                    for suff in range(len(suffixList)):
                        suffixString = suffixList[suff]
                        sampleRevisedWithSuffix = addSuffix(grm, suffixString)
                    if (sampleRevisedWithSuffix in resource_terms_revised.keys() and not localTrigger):  # Not trigger true is used here -reason
                        # resourceId = resourceRevisedTermsDict[sampleRevisedWithSuffix]
                        partialMatchedList.append(sampleRevisedWithSuffix)
                        # statusAddendum = statusAddendum + "[Suffix Addition- " + suffixString + " to the Input]"
                        status_addendum.append("Suffix Addition- " + suffixString + " to the Input")
                        for eachTkn in grmTokens:
                            covered_tokens.append(eachTkn)
                            if eachTkn in remaining_tokens:
                                remaining_tokens.remove(eachTkn)
                        localTrigger = True


            # This is the case of making 3-gram (trigram) chunks and subsequent processing for cleaned samples
            if len(newChunkTokens)<7:
                newChunk3Grams = combi(newChunkTokens, 3)
            else:
                newChunk3Grams = ngrams(newChunk, 3)
            for nc in newChunk3Grams:
                grm1 = ' '.join(nc)
                grmTokens = word_tokenize(grm1.lower())
                localTrigger = False
                setPerm = allPermutations(grm1)  # Gets the set of all possible permutations for this gram type chunks
                for perm in setPerm:
                    grm = ' '.join(perm)

                    if (grm in abbreviations.keys()):  # rule for abbreviation
                        grm = abbreviations[grm]
                        # statusAddendum = statusAddendum + "[Abbreviation-Acronym Treatment]"
                        status_addendum.append("Abbreviation-Acronym Treatment")
                    if (grm in non_english_words.keys()):  # rule for abbreviation
                        grm = non_english_words[grm]
                        # statusAddendum = statusAddendum + "[Non English Language Words Treatment]"
                        status_addendum.append("Non English Language Words Treatment")
                    if (grm in synonyms.keys()):  ## Synonyms taken care of- need more synonyms
                        grm = synonyms[grm]
                        # statusAddendum = statusAddendum + "[Synonym Usage]"
                        status_addendum.append("Synonym Usage")

                    # Matching Test for 3-gram chunk
                    if ((grm in resource_terms.keys() ) and not localTrigger):
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            covered_tokens.append(eachTkn)
                            if eachTkn in remaining_tokens:
                                remaining_tokens.remove(eachTkn)
                        localTrigger = True
                        # statusAddendum="Match with 5-Gram Chunk"+statusAddendum
                    elif ((grm in resource_terms_revised.keys() ) and not localTrigger):
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            covered_tokens.append(eachTkn)
                            if eachTkn in remaining_tokens:
                                remaining_tokens.remove(eachTkn)
                            # # statusAddendum = "Match with 5-Gram Chunk"+statusAddendum
                        localTrigger = True
                    elif (grm in resource_bracketed_permutation_terms.keys() and not localTrigger):
                        resourceId = resource_bracketed_permutation_terms[grm]
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            covered_tokens.append(eachTkn)
                            if eachTkn in remaining_tokens:
                                remaining_tokens.remove(eachTkn)
                        # statusAddendum = "[Permutation of Tokens in Bracketed Resource Term]"
                        status_addendum.append("Permutation of Tokens in Bracketed Resource Term")
                        localTrigger = True
                    for suff in range(len(suffixList)):
                        suffixString = suffixList[suff]
                        sampleRevisedWithSuffix = addSuffix(grm, suffixString)
                        if (sampleRevisedWithSuffix in resource_terms_revised.keys() and not localTrigger):  # Not trigger true is used here -reason
                            # resourceId = resourceRevisedTermsDict[sampleRevisedWithSuffix]
                            partialMatchedList.append(sampleRevisedWithSuffix)
                            # statusAddendum = statusAddendum + "[Suffix Addition- " + suffixString + " to the Input]"
                            status_addendum.append("Suffix Addition- " + suffixString + " to the Input")
                            for eachTkn in grmTokens:
                                covered_tokens.append(eachTkn)
                                if eachTkn in remaining_tokens:
                                    remaining_tokens.remove(eachTkn)
                            localTrigger = True

                    # Here the qualities are used for semantic taggings --- change elif to if for qualities in addition to
                    if (grm in qualities_lower.keys() and not localTrigger):
                        quality = qualities_lower[grm]
                        partialMatchedList.append(grm)
                        # statusAddendum = statusAddendum + "[Using Semantic Tagging Resources]"
                        status_addendum.append("Using Semantic Tagging Resources")
                        localTrigger = True
                        for eachTkn in grmTokens:
                            covered_tokens.append(eachTkn)
                            if eachTkn in remaining_tokens:
                                remaining_tokens.remove(eachTkn)
                        localTrigger = True

            # This is the case of making 2-gram (bigram) chunks and subsequent processing for cleaned samples
            if len(newChunkTokens)<7:
                newChunk2Grams = combi(newChunkTokens, 2)
            else:
                newChunk2Grams = ngrams(newChunk, 2)
            for nc in newChunk2Grams:
                grm1 = ' '.join(nc)
                grmTokens = word_tokenize(grm1.lower())
                localTrigger=False
                setPerm = allPermutations(grm1)  # Gets the set of all possible permutations for this gram type chunks
                for perm in setPerm:
                    grm = ' '.join(perm)
                    if (grm in abbreviations.keys()):  # rule for abbreviation
                        grm = abbreviations[grm]
                        # statusAddendum = statusAddendum + "[Abbreviation-Acronym Treatment]"
                        status_addendum.append("Abbreviation-Acronym Treatment")
                    if (grm in non_english_words.keys()):  # rule for abbreviation
                        grm = non_english_words[grm]
                        # statusAddendum = statusAddendum + "[Non English Language Words Treatment]"
                        status_addendum.append("Non English Language Words Treatment")
                    if (grm in synonyms.keys()):  ## Synonyms taken care of- need more synonyms
                        grm = synonyms[grm]
                        # statusAddendum = statusAddendum + "[Synonym Usage]"
                        status_addendum.append("Synonym Usage")

                    # Matching Test for 2-gram chunk
                    if ((grm in resource_terms.keys() ) and not localTrigger):
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            covered_tokens.append(eachTkn)
                            if eachTkn in remaining_tokens:
                                remaining_tokens.remove(eachTkn)
                        localTrigger = True
                    elif (( grm in resource_terms_revised.keys() ) and not localTrigger):
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            covered_tokens.append(eachTkn)
                            if eachTkn in remaining_tokens:
                                remaining_tokens.remove(eachTkn)
                            # # statusAddendum = "Match with 5-Gram Chunk"+statusAddendum
                        localTrigger = True
                    elif (grm in resource_bracketed_permutation_terms.keys() and not localTrigger):
                        resourceId = resource_bracketed_permutation_terms[grm]
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            covered_tokens.append(eachTkn)
                            if eachTkn in remaining_tokens:
                                remaining_tokens.remove(eachTkn)
                        # statusAddendum = "[Permutation of Tokens in Bracketed Resource Term]"
                        status_addendum.append("Permutation of Tokens in Bracketed Resource Term")
                        localTrigger = True
                    for suff in range(len(suffixList)):
                        suffixString = suffixList[suff]
                        sampleRevisedWithSuffix = addSuffix(grm, suffixString)
                    if (sampleRevisedWithSuffix in resource_terms_revised.keys() and not localTrigger):  # Not trigger true is used here -reason
                        # resourceId = resourceRevisedTermsDict[sampleRevisedWithSuffix]
                        partialMatchedList.append(sampleRevisedWithSuffix)
                        # statusAddendum = statusAddendum + "[Suffix Addition- " + suffixString + " to the Input]"
                        status_addendum.append("Suffix Addition- " + suffixString + " to the Input")
                        for eachTkn in grmTokens:
                            covered_tokens.append(eachTkn)
                            if eachTkn in remaining_tokens:
                                remaining_tokens.remove(eachTkn)
                        localTrigger = True

                    # Here the qualities are used for semantic taggings --- change elif to if for qualities in addition to
                    if (grm in qualities_lower.keys() and not localTrigger):
                        quality = qualities_lower[grm]
                        partialMatchedList.append(grm)
                        # statusAddendum = statusAddendum + "[Using Semantic Tagging Resources]"
                        status_addendum.append("Using Semantic Tagging Resources")
                        localTrigger = True
                        for eachTkn in grmTokens:
                            covered_tokens.append(eachTkn)
                            if eachTkn in remaining_tokens:
                                remaining_tokens.remove(eachTkn)
                        localTrigger = True


            # This is the case of making 1-gram (unigram) chunks and subsequent processing for cleaned samples
            if len(newChunkTokens)<7:
                newChunk1Grams = combi(newChunkTokens, 1)
            else:
                newChunk1Grams = ngrams(newChunk, 1)
            for nc in newChunk1Grams:
                grm = ' '.join(nc)
                grmTokens = word_tokenize(grm.lower())
                localTrigger = False

                if (grm in abbreviations.keys()):  # rule for abbreviation
                    grm = abbreviations[grm]
                    # statusAddendum = statusAddendum + "[Abbreviation-Acronym Treatment]"
                    status_addendum.append("Abbreviation-Acronym Treatment")
                if (grm in non_english_words.keys()):  # rule for abbreviation
                    grm = non_english_words[grm]
                    # statusAddendum = statusAddendum + "[Non English Language Words Treatment]"
                    status_addendum.append("Non English Language Words Treatment")
                if (grm in synonyms.keys()):  ## Synonyms taken care of- need more synonyms
                    grm = synonyms[grm]
                    # statusAddendum = statusAddendum + "[Synonym Usage]"
                    status_addendum.append("Synonym Usage")

                # Matching Test for 1-gram chunk
                if ((grm in resource_terms.keys() ) and not localTrigger):
                    partialMatchedList.append(grm)
                    for eachTkn in grmTokens:
                        covered_tokens.append(eachTkn)
                        if eachTkn in remaining_tokens:
                            remaining_tokens.remove(eachTkn)
                    localTrigger = True
                    # statusAddendum="Match with 5-Gram Chunk"+statusAddendum
                elif ((grm in resource_terms_revised.keys() ) and not localTrigger):
                    partialMatchedList.append(grm)
                    for eachTkn in grmTokens:
                        covered_tokens.append(eachTkn)
                        if eachTkn in remaining_tokens:
                            remaining_tokens.remove(eachTkn)
                        # # statusAddendum = "Match with 5-Gram Chunk"+statusAddendum
                    localTrigger = True

                for suff in range(len(suffixList)):
                    suffixString = suffixList[suff]
                    sampleRevisedWithSuffix = addSuffix(grm, suffixString)
                    if (sampleRevisedWithSuffix in resource_terms_revised.keys() and not localTrigger):  # Not trigger true is used here -reason
                        # resourceId = resourceRevisedTermsDict[sampleRevisedWithSuffix]
                        partialMatchedList.append(sampleRevisedWithSuffix)
                        # statusAddendum = statusAddendum + "[Suffix Addition- " + suffixString + " to the Input]"
                        status_addendum.append("Suffix Addition- " + suffixString + " to the Input")
                        for eachTkn in grmTokens:
                            covered_tokens.append(eachTkn)
                            if eachTkn in remaining_tokens:
                                remaining_tokens.remove(eachTkn)
                        localTrigger=True

                # Here the qualities are used for semantic taggings --- change elif to if for qualities in addition to
                if (grm in qualities_lower.keys() and not localTrigger):
                    quality = qualities_lower[grm]
                    partialMatchedList.append(grm)
                    # statusAddendum = statusAddendum + "[Using Semantic Tagging Resources]"
                    status_addendum.append("Using Semantic Tagging Resources")
                    localTrigger = True
                    for eachTkn in grmTokens:
                        covered_tokens.append(eachTkn)
                        if eachTkn in remaining_tokens:
                            remaining_tokens.remove(eachTkn)


                # Here the qualities are used for semantic taggings --- change elif to if for qualities in addition to
                if (grm in processes.keys() and not localTrigger):
                    proc = processes[grm]
                    partialMatchedList.append(grm)
                    # statusAddendum = statusAddendum + "[Using Candidate Processes]"
                    status_addendum.append("Using Candidate Processes")
                    localTrigger = True
                    for eachTkn in grmTokens:
                        covered_tokens.append(eachTkn)
                        if eachTkn in remaining_tokens:
                            remaining_tokens.remove(eachTkn)


            partialMatchedSet = set(partialMatchedList)  # Makes a set of all matched components from the above processing
            status = "GComponent Match"             #Note: GComponent instead of is used as tag to help sorting later in result file

            remSetConv = set(remaining_tokens)
            coveredAllTokensSetConv=set(covered_tokens)
            remSetDiff = remSetConv.difference(coveredAllTokensSetConv)
            # Checking of coverage of tokens for sample as well overall dataset
            coveredTSet = []
            remainingTSet = []
            for tknstr in partialMatchedSet:
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

            #Decoding the partial matched set to get back resource ids
            for matchstring in partialMatchedSet:
                if (matchstring in resource_terms.keys()):
                    resourceId = resource_terms[matchstring]
                    partialMatchedResourceList.append(matchstring + ":" + resourceId)
                elif (matchstring in resource_terms_revised.keys()):
                    resourceId = resource_terms_revised[matchstring]
                    partialMatchedResourceList.append(matchstring + ":" + resourceId)
                elif (matchstring in resource_permutation_terms.keys()):
                    resourceId = resource_permutation_terms[matchstring]
                    resourceOriginalTerm = resource_terms_ID_based[resourceId]
                    partialMatchedResourceList.append(resourceOriginalTerm.lower() + ":" + resourceId)
                elif (matchstring in resource_bracketed_permutation_terms.keys()):
                    resourceId = resource_bracketed_permutation_terms[matchstring]
                    resourceOriginalTerm = resource_terms_ID_based[resourceId]
                    resourceOriginalTerm = resourceOriginalTerm.replace(",", "=")
                    partialMatchedResourceList.append(resourceOriginalTerm.lower() + ":" + resourceId)
                elif (matchstring in processes.keys()):
                    resourceId = processes[matchstring]
                    partialMatchedResourceList.append(matchstring + ":" + resourceId)
                elif (matchstring in qualities.keys()):
                    resourceId = qualities[matchstring]
                    partialMatchedResourceList.append(matchstring + ":" + resourceId)
                elif (matchstring in qualities_lower.keys()):
                    resourceId = qualities_lower[matchstring]
                    partialMatchedResourceList.append(matchstring + ":" + resourceId)
                elif ("==" in matchstring):
                    resList = matchstring.split("==")
                    entityPart = resList[0]
                    entityTag = resList[1]
                    partialMatchedResourceList.append(entityPart + ":" + entityTag)

            partialMatchedResourceListSet = set(partialMatchedResourceList)   # Makes a set from list of all matched components with resource ids
            retainedSet = []

            # If size of set is more than one member, looks for the retained matched terms by defined criteria
            if (len(partialMatchedResourceListSet) > 0):
                retainedSet = retainedPhrase(str(partialMatchedResourceListSet))
                logger.debug("retainedSet " + str(retainedSet))
                # HERE SHOULD HAVE ANOTHER RETAING SET

            final_status = set(status_addendum)

            # In case it is for componet matching and we have at least one component matched
            if (len(partialMatchedSet) > 0):
                if args.format == 'full':
                    fw.write('\t' + str(list(partialMatchedSet)) + '\t' + str(list(partialMatchedResourceListSet)) + '\t' + str(list(retainedSet)) + '\t' + str(len(retainedSet)) + '\t' + status + '\t' + str(list(final_status)) + '\t' + str(list(remSetDiff)))
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
                        fw.write('\t' + str(list(partialMatchedSet)) + '\t' + str(list(partialMatchedResourceList)) + '\t\t' + "\t" + "Sorry No Match" + "\t" + str(list(remaining_tokens)))

    #Output files closed
    if fw is not sys.stdout:
        fw.close()
