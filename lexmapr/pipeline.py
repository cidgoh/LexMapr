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

def run(args):
    """
    Main text mining pipeline.
    """
    punctuationsList = ['-', '_', '(', ')', ';', '/', ':', '%']  # Current punctuationsList for basic treatment
    coveredAllTokensSet = []
    remainingAllTokensSet = []
    remainingTokenSet = []
    prioritizedRetainedSet=[]
    samplesDict = collections.OrderedDict()
    samplesList = []
    samplesSet = []
    resourceTermsDict = {}
    resourceRevisedTermsDict = {}
    resourceTermsIDBasedDict = {}

    # 11-Get all synonyms from resource in CSV file format and put in a dictionary to be used further
    synonymsDict = get_resource_dict("SynLex.csv")

    # 12-Get all abbreviation/acronyms from resource in CSV file format and put in a dictionary to be used further
    abbreviationDict = get_resource_dict("AbbLex.csv")
    abbreviationLowerDict = get_resource_dict("AbbLex.csv", True)

    # 13-Get all Non English Language words mappings from resource in CSV file format and put in a dictionary to be used further
    nonEnglishWordsDict = get_resource_dict("NefLex.csv")
    nonEnglishWordsLowerDict = get_resource_dict("NefLex.csv", True)

    # 14-Get all spelling mistake examples from resource in CSV file format and put in a dictionary to be used further
    spellingDict = get_resource_dict("ScorLex.csv")
    spellingLowerDict = get_resource_dict("ScorLex.csv", True)

    # 15-Get candidate processes from resource in a CSV file format and put in a dictionary to be used further
    processDict = get_resource_dict("candidateProcesses.csv")
    
    # 16-Get all semantic tags (e.g.qualities) from resource in a CSV file format and put in a dictionary to be used further
    qualityDict = get_resource_dict("SemLex.csv")
    qualityLowerDict = get_resource_dict("SemLex.csv", True)

    # 17-Get all collocations (Wikipedia) from resource in a CSV file format and put in a dictionary to be used further
    collocationDict = get_resource_dict("wikipediaCollocations.csv")

    # 18-Method to get all inflection exception words from resource in CSV file format -Needed to supercede the general inflection treatment
    inflection_exc_dict = get_resource_dict("inflection-exceptions.csv", True)
    
    # 19-Method to Get all stop words from resource in CSV file format -A very constrained lists of stop words is
    # used as other stop words are assumed to have some useful semantic meaning
    stop_word_dict = get_resource_dict("mining-stopwords.csv", True)
    
    # 21- To get all terms from resources- right now in a CSV file extracted from ontologies using another external script
    resourceTermsIDBasedDict = get_resource_dict("CombinedResourceTerms.csv")
    # Swap keys and values in resourceTermsIDBasedDict
    resourceTermsDict = {v:k for k,v in resourceTermsIDBasedDict.items()}
    # Convert keys in resourceTermsDict to lowercase
    resourceRevisedTermsDict = {k.lower():v
        for k,v in resourceTermsDict.items()}

    # 23-Method for getting all the permutations of Resource Terms
    resourcePermutationTermsDict = {}
    # Iterate
    for k, v in resourceRevisedTermsDict.items():
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
                    resourcePermutationTermsDict[permString.strip()] = resourceid.strip()

    # 24-Method for getting all the permutations of Bracketed Resource Terms
    resourceBracketedPermutationTermsDict={}
    # Iterate
    for k, v in resourceRevisedTermsDict.items():
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
                        resourceBracketedPermutationTermsDict[permString.strip()] = resourceid.strip()
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
                        resourceBracketedPermutationTermsDict[permString.strip()] = resourceid.strip()
                    
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
        statusAddendum = ""
        statusAddendumSet = []
        statusAddendumSetFinal = []
        del statusAddendumSetFinal [:]
        retSet = []
        remSet = []
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
            remSet.append(tkn.lower())  # To start with all remaining tokens in set

        # ===Few preliminary things- Inflection,spelling mistakes, Abbreviations, acronyms, foreign words, Synonyms taken care of
        for tkn in sampleTokens:

            # Some preprocessing (only limited or controlled) Steps
            tkn = preProcess(tkn)

            # Plurals are converted to singulars with exceptions
            if (tkn.endswith("us") or tkn.endswith("ia") or tkn.endswith("ta")):  # for inflection exception in general-takes into account both lower and upper case (apart from some inflection-exception list used also in next
                lemma = tkn
            elif (tkn not in inflection_exc_dict):  # Further Inflection Exception list is taken into account
                lemma = inflection.singularize(tkn)
                if (tkn != lemma):  #Only in case when inflection makes some changes in lemma
                    statusAddendum = "Inflection (Plural) Treatment"
                    statusAddendumSet.append("Inflection (Plural) Treatment")
            else:
                lemma = tkn

            # Misspellings are dealt with  here
            if (lemma in spellingDict.keys()):  # spelling mistakes taken care of
                lemma = spellingDict[lemma]
                statusAddendum = statusAddendum + "Spelling Correction Treatment"
                statusAddendumSet.append("Spelling Correction Treatment")
            elif (lemma.lower() in spellingLowerDict.keys()):
                lemma = spellingLowerDict[lemma.lower()]
                statusAddendum = statusAddendum + "Change Case and Spelling Correction Treatment"
                statusAddendumSet.append("Change Case and Spelling Correction Treatment")
            if (lemma in abbreviationDict.keys()):  # Abbreviations, acronyms, foreign language words taken care of- need rule for abbreviation e.g. if lemma is Abbreviation
                lemma = abbreviationDict[lemma]
                statusAddendum = "Abbreviation-Acronym Treatment"
                statusAddendumSet.append("Abbreviation-Acronym Treatment")
            elif (lemma.lower() in abbreviationLowerDict.keys()):
                lemma = abbreviationLowerDict[lemma.lower()]
                statusAddendum = "Change Case and Abbreviation-Acronym Treatment"
                statusAddendumSet.append("Change Case and Abbreviation-Acronym Treatment")

            if (lemma in nonEnglishWordsDict.keys()):  # Non English language words taken care of
                lemma = nonEnglishWordsDict[lemma]
                statusAddendum = statusAddendum + "Non English Language Words Treatment"
                statusAddendumSet.append("Non English Language Words Treatment")
            elif (lemma.lower() in nonEnglishWordsLowerDict.keys()):
                lemma = nonEnglishWordsLowerDict[lemma.lower()]
                statusAddendum = statusAddendum + "Change Case and Non English Language Words Treatment"
                statusAddendumSet.append("Change Case and Non English Language Words Treatment")


            # ===This will create a cleaned sample after above treatments [Here we are making new phrase now in lower case]
            if (not newPhrase and lemma.lower() not in stop_word_dict):  # if newphrase is empty and lemma is in not in stopwordlist (abridged according to domain)
                newPhrase = lemma.lower()
            elif (
                lemma.lower() not in stop_word_dict):  # if newphrase is not empty and lemma is in not in stopwordlist (abridged according to domain)
                newPhrase = newPhrase + " " + lemma.lower()

            newPhrase = re.sub(' +', ' ', newPhrase)  # Extra innner spaces removed from cleaned sample

            if (newPhrase in abbreviationDict.keys()):  # NEED HERE AGAIN ? Abbreviations, acronyms, non English words taken care of- need rule for abbreviation
                newPhrase = abbreviationDict[newPhrase]
                statusAddendum = statusAddendum + "Cleaned Sample and Abbreviation-Acronym Treatment"
                statusAddendumSet.append("Cleaned Sample and Abbreviation-Acronym Treatment")
            elif (newPhrase in abbreviationLowerDict.keys()):
                newPhrase = abbreviationLowerDict[newPhrase]
                statusAddendum = statusAddendum + "Cleaned Sample and Abbreviation-Acronym Treatment"
                statusAddendumSet.append("Cleaned Sample and Abbreviation-Acronym Treatment")

            if (newPhrase in nonEnglishWordsDict.keys()):  # non English words taken care of
                newPhrase = nonEnglishWordsDict[newPhrase]
                # statusAddendum = statusAddendum + "Non English Language Words Treatment"
                statusAddendum = statusAddendum + "Cleaned Sample and Non English Language Words Treatment"
                statusAddendumSet.append("Cleaned Sample and Non English Language Words Treatment")
            elif (newPhrase in nonEnglishWordsLowerDict.keys()):
                newPhrase = nonEnglishWordsLowerDict[newPhrase]
                statusAddendum = statusAddendum + "Cleaned Sample and Non English Language Words Treatment"
                statusAddendumSet.append("Cleaned Sample and Non English Language Words Treatment")

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
        # Rule1: Annotate all the empty samples
        if not sample:
            status = "Empty Sample"
            if args.format == 'full':
                # output fields: 'matched_term' ... 'different_components_for_component_match'
                fw.write("\t--" + "\t--" + "\t" + "\t" + "\t" + status)
            trigger = True

        # Rule2: Annotate all the Full Term Matches of Terms without any treatment
        if ((sample in resourceTermsDict.keys() ) and not trigger):
            if(sample in resourceTermsDict.keys()):
                resourceId = resourceTermsDict[sample]  # Gets the id of the resource for matched term
            status = "Full Term Match"
            statusAddendum = "[A DirectMatch]"
            statusAddendumSet.append("A Direct Match")
            statusAddendumSetFinal = set(statusAddendumSet)
            retSet.append(sample + ":" + resourceId)
            if args.format == 'full':
                # output fields:
                #   'matched_term':                             sample,
                #   'all_matched_terms_with_resource_ids':      "[" + (sample + ":" + resourceId) + "]"
                #   'retained_terms_with_resource_ids':         str(retSet)
                #   'number_of_components_for_component_match': 
                #   'match_status_macro_level':                 status
                #   'match_status_micro_level':                 str(list(statusAddendumSetFinal))
                fw.write('\t' + sample + '\t' + "[" + (sample + ":" + resourceId) + "]" + '\t' + str(retSet) + '\t' + '\t' + status + '\t' + str(list(statusAddendumSetFinal)))
            else:
                # output fields:
                #   'matched_term':                        sample
                #   'all_matched_terms_with_resource_ids': "[" + (sample + ":" + resourceId) + "]"
                fw.write('\t' + sample + '\t' + "[" + (sample + ":" + resourceId) + "]" )
            # To Count the Covered Tokens(words)
            thisSampleTokens = word_tokenize(sample.lower())
            for thisSampleIndvToken in thisSampleTokens:
                coveredAllTokensSet.append(thisSampleIndvToken)
                remSet.remove(thisSampleIndvToken)
            trigger = True


        # Rule3: Annotate all the Full Term Matches of Terms with change of case  -resourceRevisedTermsDict
        if ((sample.lower() in resourceTermsDict.keys()) and not trigger):
            if(sample.lower() in resourceTermsDict.keys()):
                resourceId = resourceTermsDict[sample.lower()]  # Gets the id of the resource for matched term
            status = "Full Term Match"
            statusAddendum = "[Change of Case in Input Data]"
            statusAddendumSet.append("Change of Case in Input Data")
            statusAddendumSetFinal = set(statusAddendumSet)
            retSet.append(sample.lower() + ":" + resourceId)
            if args.format == "full":
                # output fields:
                #   'matched_term':                             sample.lower()
                #   'all_matched_terms_with_resource_ids':      str(retSet)
                #   'retained_terms_with_resource_ids'          str(retSet)
                #   'number_of_components_for_component_match': 
                #   'match_status_macro_level':                 status
                #   'match_status_micro_level':                 str(list(statusAddendumSetFinal))
                fw.write('\t' + sample.lower() + '\t' + str(list(retSet)) + '\t' + str(list(retSet)) + '\t' + '\t' + status + '\t' + str(list(statusAddendumSetFinal)))
            else:
                # output fields:
                #   'matched_term':                        sample.lower()
                #   'all_matched_terms_with_resource_ids': str(list(retSet))
                fw.write('\t' + sample.lower() + '\t' + str(list(retSet)))
            # To Count the Covered Tokens(words)
            thisSampleTokens = word_tokenize(sample.lower())
            for thisSampleIndvToken in thisSampleTokens:
                coveredAllTokensSet.append(thisSampleIndvToken)
                remSet.remove(thisSampleIndvToken)
            trigger = True  # resourcePermutationTermsDict

        elif ((sample.lower() in resourceRevisedTermsDict.keys() ) and not trigger):
            if (sample.lower() in resourceRevisedTermsDict.keys()):
                resourceId = resourceRevisedTermsDict[sample.lower()]  # Gets the id of the resource for matched term
            status = "Full Term Match"
            statusAddendum = "[Change of Case in Input or Resource Data]"
            statusAddendumSet.append("Change of Case in Resource Data")
            statusAddendumSetFinal = set(statusAddendumSet)
            retSet.append(sample.lower() + ":" + resourceId)
            if args.format == 'full':
                # output fields:
                #   'matched_term':                             sample.lower()
                #   'all_matched_terms_with_resource_ids':      str(list(retSet))
                #   'retained_terms_with_resource_ids'          str(list(retSet))
                #   'number_of_components_for_component_match': 
                #   'match_status_macro_level':                 status
                #   'match_status_micro_level':                 str(list(statusAddendumSetFinal))
                fw.write('\t' + sample.lower() + '\t' + str(list(retSet)) + '\t' + str(list(retSet)) + '\t' + '\t' + status + "\t" + str(list(statusAddendumSetFinal)))
            else:
                # output fields:
                #   'matched_term':                        sample.lower()
                #   'all_matched_terms_with_resource_ids': str(retSet)
                fw.write('\t' + sample.lower() + '\t' + str(list(retSet)))
            # To Count the Covered Tokens(words)
            thisSampleTokens = word_tokenize(sample.lower())
            for thisSampleIndvToken in thisSampleTokens:
                coveredAllTokensSet.append(thisSampleIndvToken)
                remSet.remove(thisSampleIndvToken)
            trigger = True

        elif (sample.lower() in resourcePermutationTermsDict.keys() and not trigger):
            resourceId = resourcePermutationTermsDict[sample.lower()]
            # here need to do the actualResourceTerm=resourceTermsDict.get(resourceId)
            resourceOriginalTerm = resourceTermsIDBasedDict[resourceId]
            status = "Full Term Match"
            statusAddendum = "[Permutation of Tokens in Resource Term]"
            statusAddendumSet.append("Permutation of Tokens in Resource Term")
            statusAddendumSetFinal = set(statusAddendumSet)
            retSet.append(resourceOriginalTerm + ":" + resourceId)
            if args.format == 'full':
                # output fields:
                #   'matched_term':                             sample.lower()
                #   'all_matched_terms_with_resource_ids':      str(list(retSet))
                #   'retained_terms_with_resource_ids'          str(list(retSet))
                #   'number_of_components_for_component_match': 
                #   'match_status_macro_level':                 status
                #   'match_status_micro_level':                 str(list(statusAddendumSetFinal))
                fw.write('\t' + sample.lower() + '\t' + str(list(retSet)) + '\t' + str(list(retSet)) + '\t' + '\t' + status + '\t' + str(list(statusAddendumSetFinal)))
            else:
                # output fields:
                #   'matched_term':                        sample.lower()
                #   'all_matched_terms_with_resource_ids': str(list(retSet))
                fw.write('\t' + sample.lower() + '\t' + str(list(retSet)))
            # To Count the Covered Tokens(words)
            thisSampleTokens = word_tokenize(sample.lower())
            for thisSampleIndvToken in thisSampleTokens:
                coveredAllTokensSet.append(thisSampleIndvToken)
                remSet.remove(thisSampleIndvToken)
            trigger = True


        elif (sample.lower() in resourceBracketedPermutationTermsDict.keys() and not trigger):
            resourceId = resourceBracketedPermutationTermsDict[sample.lower()]
            # here need to do the actualResourceTerm=resourceTermsDict.get(resourceId)
            resourceOriginalTerm = resourceTermsIDBasedDict[resourceId]
            status = "Full Term Match"
            statusAddendum = "[Permutation of Tokens in Bracketed Resource Term]"
            statusAddendumSet.append("Permutation of Tokens in Bracketed Resource Term")
            statusAddendumSetFinal = set(statusAddendumSet)
            retSet.append(resourceOriginalTerm + ":" + resourceId)
            if args.format == 'full':
                # output fields:
                #   'matched_term':                             sample.lower()
                #   'all_matched_terms_with_resource_ids':      str(list(retSet))
                #   'retained_terms_with_resource_ids'          str(list(retSet))
                #   'number_of_components_for_component_match': 
                #   'match_status_macro_level':                 status
                #   'match_status_micro_level':                 str(list(statusAddendumSetFinal))
                fw.write('\t' + sample.lower() + '\t' +  str(list(retSet)) + '\t' + str(list(retSet)) + '\t' + '\t' + status + '\t' + str(list(statusAddendumSetFinal)))
            else:
                # output fields:
                #   'matched_term':                        sample.lower()
                #   'all_matched_terms_with_resource_ids': str(list(retSet))
                fw.write('\t' + sample.lower() + '\t' + str(list(retSet)))
            # To Count the Covered Tokens(words)
            thisSampleTokens = word_tokenize(sample.lower())
            for thisSampleIndvToken in thisSampleTokens:
                coveredAllTokensSet.append(thisSampleIndvToken)
                remSet.remove(thisSampleIndvToken)
            trigger = True

        # Here we check all the suffices that can be applied to input term to make it comparable with resource terms
        suffixList=["(plant) as food source","plant as food source","as food source","(vegetable) food product","vegetable food product", "nut food product","fruit food product","seafood product","meat food product", "plant fruit food product","plant food product",  "(food product)","food product","product"]
        for suff in range(len(suffixList)):
            suffixString=suffixList[suff]
            sampleRevisedWithSuffix = addSuffix(sample, suffixString)
            if (sampleRevisedWithSuffix in resourceRevisedTermsDict.keys() and not trigger):
                resourceId = resourceRevisedTermsDict[sampleRevisedWithSuffix]
                status = "Full Term Match"
                statusAddendum = "[Change of Case of Resource and Suffix Addition- "+suffixString+" to the Input]"
                statusAddendumSet.append("[Change of Case of Resource and Suffix Addition- "+suffixString+" to the Input]")
                statusAddendumSetFinal = set(statusAddendumSet)
                retSet.append(sampleRevisedWithSuffix + ":" + resourceId)
                if args.format == 'full':
                    # output fields:
                    #   'matched_term':                             sample.lower()
                    #   'all_matched_terms_with_resource_ids':      str(list(retSet))
                    #   'retained_terms_with_resource_ids'          str(list(retSet))
                    #   'number_of_components_for_component_match': 
                    #   'match_status_macro_level':                 status
                    #   'match_status_micro_level':                 str(list(statusAddendumSetFinal))
                    fw.write('\t' + sample.lower() + '\t' + str(list(retSet)) + '\t' + str(list(retSet)) + '\t' + '\t' + status + '\t' + str(list(statusAddendumSetFinal)))
                else:
                    # output fields:
                    #   'matched_term':                        sample.lower()
                    #   'all_matched_terms_with_resource_ids': str(list(retSet))
                    fw.write('\t' + sample.lower() + '\t' + str(list(retSet)))
                trigger = True
                # To Count the Covered Tokens(words)
                thisSampleTokens = word_tokenize(sample.lower())
                for thisSampleIndvToken in thisSampleTokens:
                    coveredAllTokensSet.append(thisSampleIndvToken)
                    remSet.remove(thisSampleIndvToken)


        # Rule4: This will open now the cleaned sample to the test of Full Term Matching
        if (not trigger):
            logger.debug("We will go further with other rules now on cleaned sample")
            sampleTokens = word_tokenize(sample.lower())
            logger.debug("==============" + sample.lower())
            logger.debug("--------------" + newPhrase.lower())

            if ((newPhrase.lower() in resourceTermsDict.keys() ) and not trigger):
                if (newPhrase.lower() in resourceTermsDict.keys()):
                    resourceId = resourceTermsDict[newPhrase.lower()]  # Gets the id of the resource for matched term
                status = "Full Term Match"  # -Inflection, Synonym, Spelling Correction, Foreign Language Treatment "
                statusAddendum = statusAddendum + "[A Direct Match with Cleaned Sample]"
                statusAddendumSet.append("A Direct Match with Cleaned Sample")
                statusAddendumSetFinal = set(statusAddendumSet)
                retSet.append(newPhrase.lower() + ":" + resourceId)
                if args.format == 'full':
                    # output fields:
                    #   '': newPhrase.lower()
                    #   '': str(list(retSet))
                    #   '': str(list(retDet))
                    #   '':
                    #   '': status
                    #   '': str(list(statusAddendumSetFinal))
                    fw.write('\t' + newPhrase.lower() + '\t' + str(list(retSet)) + '\t' + str(list(retSet)) + '\t' + '\t' + status + '\t' + str(list(statusAddendumSetFinal)))
                else:
                    # output fields:
                    #   '': newPhrase.lower()
                    #   '': str(retSet)
                    fw.write('\t' + newPhrase.lower() + '\t' + str(list(retSet)))
                # To Count the Covered Tokens(words)
                thisSampleTokens = word_tokenize(sample.lower())
                for thisSampleIndvToken in thisSampleTokens:
                    coveredAllTokensSet.append(thisSampleIndvToken)
                    remSet.remove(thisSampleIndvToken)
                trigger = True


            elif ((newPhrase.lower() in resourceRevisedTermsDict.keys() ) and not trigger):
                if (newPhrase.lower() in resourceRevisedTermsDict.keys()):
                    resourceId = resourceRevisedTermsDict[newPhrase.lower()]  # Gets the id of the resource for matched term
                status = "Full Term Match"
                statusAddendum = statusAddendum + "[Change of Case of Resource Terms]"
                statusAddendumSet.append("Change of Case of Resource Terms")
                statusAddendumSetFinal = set(statusAddendumSet)
                retSet.append(newPhrase.lower() + ":" + resourceId)
                if args.format == 'full':
                    fw.write('\t' + newPhrase.lower() + '\t' + str(list(retSet)) + '\t' + str(list(retSet)) + '\t' + '\t' + status + '\t' + str(list(statusAddendumSetFinal)))
                else:
                    fw.write('\t' + newPhrase.lower() + '\t' + str(list(retSet)))
                # To Count the Covered Tokens(words)
                thisSampleTokens = word_tokenize(sample.lower())
                for thisSampleIndvToken in thisSampleTokens:
                    coveredAllTokensSet.append(thisSampleIndvToken)
                    remSet.remove(thisSampleIndvToken)
                trigger = True

            elif (newPhrase.lower() in resourcePermutationTermsDict.keys() and not trigger):
                resourceId = resourcePermutationTermsDict[newPhrase.lower()]
                status = "Full Term Match"
                statusAddendum = statusAddendum + "[Permutation of Tokens in Resource Term]"
                statusAddendumSet.append("Permutation of Tokens in Resource Term")
                statusAddendumSetFinal = set(statusAddendumSet)
                resourceOriginalTerm = resourceTermsIDBasedDict[resourceId]
                retSet.append(resourceOriginalTerm + ":" + resourceId)
                if args.format == 'full':
                    fw.write('\t' + newPhrase.lower() + '\t' + str(list(retSet)) + '\t' + str(list(retSet)) + '\t' + '\t' + status + '\t' + str(list(statusAddendumSetFinal)))
                else:
                    fw.write('\t' + newPhrase.lower() + '\t' + str(list(retSet)))
                # To Count the Covered Tokens(words)
                thisSampleTokens = word_tokenize(sample.lower())
                for thisSampleIndvToken in thisSampleTokens:
                    coveredAllTokensSet.append(thisSampleIndvToken)
                    remSet.remove(thisSampleIndvToken)
                trigger = True

            elif (newPhrase.lower() in resourceBracketedPermutationTermsDict.keys() and not trigger):
                resourceId = resourceBracketedPermutationTermsDict[newPhrase.lower()]
                status = "Full Term Match"
                statusAddendum = statusAddendum + "[Permutation of Tokens in Bracketed Resource Term]"
                statusAddendumSet.append("Permutation of Tokens in Bracketed Resource Term")
                statusAddendumSetFinal = set(statusAddendumSet)
                resourceOriginalTerm = resourceTermsIDBasedDict[resourceId]
                retSet.append(resourceOriginalTerm + ":" + resourceId)
                if args.format == 'full':
                    fw.write('\t' + newPhrase.lower() + '\t' + str(list(retSet)) + '\t' + str(list(retSet)) + '\t' + '\t' + status + '\t' + str(list(statusAddendumSetFinal)))
                else:
                    fw.write('\t' + newPhrase.lower() + '\t' + str(list(retSet)))
                # To Count the Covered Tokens(words)
                thisSampleTokens = word_tokenize(sample.lower())
                for thisSampleIndvToken in thisSampleTokens:
                    coveredAllTokensSet.append(thisSampleIndvToken)
                    remSet.remove(thisSampleIndvToken)
                trigger = True

            for suff in range(len(suffixList)):
                suffixString = suffixList[suff]
                sampleRevisedWithSuffix = addSuffix(newPhrase.lower(), suffixString)
                if (sampleRevisedWithSuffix in resourceRevisedTermsDict.keys() and not trigger):
                    resourceId = resourceRevisedTermsDict[sampleRevisedWithSuffix]
                    status = "Full Term Match"
                    statusAddendum = "[CleanedSample-Change of Case of Resource and Suffix Addition- " + suffixString + " to the Input]"
                    statusAddendumSet.append("[CleanedSample-Change of Case of Resource and Suffix Addition- " + suffixString + " to the Input]")
                    statusAddendumSetFinal = set(statusAddendumSet)
                    retSet.append(sampleRevisedWithSuffix + ":" + resourceId)
                    if args.format == 'full':
                        fw.write('\t' + sample.lower() + '\t' + str(list(retSet)) + '\t' + str(list(retSet)) + '\t' + '\t' + status + '\t' + str(list(statusAddendumSetFinal)))
                    else:
                        fw.write('\t' + sample.lower() + '\t' + str(list(retSet)))
                    # To Count the Covered Tokens(words)
                    thisSampleTokens = word_tokenize(sample.lower())
                    for thisSampleIndvToken in thisSampleTokens:
                        coveredAllTokensSet.append(thisSampleIndvToken)
                        remSet.remove(thisSampleIndvToken)
                    trigger = True



        # Rule5: Full Term Match if possible from multi-word collocations -e.g. from Wikipedia
        if (not trigger):
            logger.debug("We will go further with other rules")
            sampleTokens = word_tokenize(sample.lower())
            logger.debug("==============" + sample.lower())
            logger.debug("--------------" + newPhrase.lower())
            if (newPhrase.lower() in collocationDict.keys()):
                resourceId = collocationDict[newPhrase.lower()]
                status = "Full Term Match"
                statusAddendum = statusAddendum + "[New Candidadte Terms -validated with Wikipedia Based Collocation Resource]"
                statusAddendumSet.append("New Candidadte Terms -validated with Wikipedia Based Collocation Resource")
                statusAddendumSetFinal = set(statusAddendumSet)
                retSet.append(newPhrase.lower() + ":" + resourceId)
                if args.format == 'full':
                    fw.write('\t' + newPhrase.lower() + '\t' +str(list(retSet)) + '\t' + str(list(retSet))  + '\t' + '\t' + status + '\t' + str(list(statusAddendumSetFinal)))
                else:
                    fw.write('\t' + newPhrase.lower() + '\t' + str(list(retSet)))
                # To Count the Covered Tokens(words)
                thisSampleTokens = word_tokenize(sample.lower())
                for thisSampleIndvToken in thisSampleTokens:
                    coveredAllTokensSet.append(thisSampleIndvToken)
                    remSet.remove(thisSampleIndvToken)
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
                    if (grm in abbreviationDict.keys()):  # rule for abbreviation
                        grm = abbreviationDict[grm]
                        statusAddendum = statusAddendum + "[Abbreviation-Acronym Treatment]"
                        statusAddendumSet.append("Abbreviation-Acronym Treatment")
                    if (grm in nonEnglishWordsDict.keys()):  # rule for abbreviation
                        grm = nonEnglishWordsDict[grm]
                        statusAddendum = statusAddendum + "[Non English Language Words Treatment]"
                        statusAddendumSet.append("Non English Language Words Treatment")
                    if (grm in synonymsDict.keys()):  ## Synonyms taken care of- need more synonyms
                        grm = synonymsDict[grm]
                        statusAddendum = statusAddendum + "[Synonym Usage]"
                        statusAddendumSet.append("Synonym Usage")

                    # Matching Test for 5-gram chunk
                    if ((grm in resourceTermsDict.keys() ) and not localTrigger):
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            coveredAllTokensSet.append(eachTkn)
                            if eachTkn in remSet:
                                remSet.remove(eachTkn)
                        localTrigger = True
                        # statusAddendum="Match with 5-Gram Chunk"+statusAddendum
                    elif ((grm in resourceRevisedTermsDict.keys() )and not localTrigger):
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            coveredAllTokensSet.append(eachTkn)
                            if eachTkn in remSet:
                                remSet.remove(eachTkn)
                            # statusAddendum = "Match with 5-Gram Chunk"+statusAddendum
                        localTrigger = True
                    elif (grm in resourceBracketedPermutationTermsDict.keys() and not localTrigger):
                        resourceId = resourceBracketedPermutationTermsDict[grm]
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            coveredAllTokensSet.append(eachTkn)
                            if eachTkn in remSet:
                                remSet.remove(eachTkn)
                        statusAddendum = "[Permutation of Tokens in Bracketed Resource Term]"
                        statusAddendumSet.append("Permutation of Tokens in Bracketed Resource Term")
                        localTrigger = True
                    for suff in range(len(suffixList)):
                        suffixString = suffixList[suff]
                        sampleRevisedWithSuffix = addSuffix(grm, suffixString)
                        if (sampleRevisedWithSuffix in resourceRevisedTermsDict.keys() and not localTrigger):  # Not trigger true is used here -reason
                            # resourceId = resourceRevisedTermsDict[sampleRevisedWithSuffix]
                            partialMatchedList.append(sampleRevisedWithSuffix)
                            statusAddendum = statusAddendum + "[Suffix Addition- " + suffixString + " to the Input]"
                            statusAddendumSet.append("Suffix Addition- " + suffixString + " to the Input")
                            for eachTkn in grmTokens:
                                coveredAllTokensSet.append(eachTkn)
                                if eachTkn in remSet:
                                    remSet.remove(eachTkn)
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
                    if (grm in abbreviationDict.keys()):  # rule for abbreviation
                        grm = abbreviationDict[grm]
                        statusAddendum = statusAddendum + "[Abbreviation-Acronym Treatment]"
                        statusAddendumSet.append("Abbreviation-Acronym Treatment")
                    if (grm in nonEnglishWordsDict.keys()):  # rule for abbreviation
                        grm = nonEnglishWordsDict[grm]
                        statusAddendum = statusAddendum + "[Non English Language Words Treatment]"
                        statusAddendumSet.append("Non English Language Words Treatment")
                    if (grm in synonymsDict.keys()):  ## Synonyms taken care of- need more synonyms
                        grm = synonymsDict[grm]
                        statusAddendum = statusAddendum + "[Synonym Usage]"
                        statusAddendumSet.append("Synonym Usage")

                    # Matching Test for 4-gram chunk
                    if ((grm in resourceTermsDict.keys()) and not localTrigger):
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            coveredAllTokensSet.append(eachTkn)
                            if eachTkn in remSet:
                                remSet.remove(eachTkn)
                        localTrigger = True
                        # statusAddendum="Match with 5-Gram Chunk"+statusAddendum
                    elif ((  grm in resourceRevisedTermsDict.keys() ) and not localTrigger):
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            coveredAllTokensSet.append(eachTkn)
                            if eachTkn in remSet:
                                remSet.remove(eachTkn)
                        localTrigger = True
                    elif (grm in resourceBracketedPermutationTermsDict.keys() and not localTrigger):
                        resourceId = resourceBracketedPermutationTermsDict[grm]
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            coveredAllTokensSet.append(eachTkn)
                            if eachTkn in remSet:
                                remSet.remove(eachTkn)
                        statusAddendum = "[Permutation of Tokens in Bracketed Resource Term]"
                        statusAddendumSet.append("Permutation of Tokens in Bracketed Resource Term")
                        localTrigger = True
                    for suff in range(len(suffixList)):
                        suffixString = suffixList[suff]
                        sampleRevisedWithSuffix = addSuffix(grm, suffixString)
                    if (sampleRevisedWithSuffix in resourceRevisedTermsDict.keys() and not localTrigger):  # Not trigger true is used here -reason
                        # resourceId = resourceRevisedTermsDict[sampleRevisedWithSuffix]
                        partialMatchedList.append(sampleRevisedWithSuffix)
                        statusAddendum = statusAddendum + "[Suffix Addition- " + suffixString + " to the Input]"
                        statusAddendumSet.append("Suffix Addition- " + suffixString + " to the Input")
                        for eachTkn in grmTokens:
                            coveredAllTokensSet.append(eachTkn)
                            if eachTkn in remSet:
                                remSet.remove(eachTkn)
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

                    if (grm in abbreviationDict.keys()):  # rule for abbreviation
                        grm = abbreviationDict[grm]
                        statusAddendum = statusAddendum + "[Abbreviation-Acronym Treatment]"
                        statusAddendumSet.append("Abbreviation-Acronym Treatment")
                    if (grm in nonEnglishWordsDict.keys()):  # rule for abbreviation
                        grm = nonEnglishWordsDict[grm]
                        statusAddendum = statusAddendum + "[Non English Language Words Treatment]"
                        statusAddendumSet.append("Non English Language Words Treatment")
                    if (grm in synonymsDict.keys()):  ## Synonyms taken care of- need more synonyms
                        grm = synonymsDict[grm]
                        statusAddendum = statusAddendum + "[Synonym Usage]"
                        statusAddendumSet.append("Synonym Usage")

                    # Matching Test for 3-gram chunk
                    if ((grm in resourceTermsDict.keys() ) and not localTrigger):
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            coveredAllTokensSet.append(eachTkn)
                            if eachTkn in remSet:
                                remSet.remove(eachTkn)
                        localTrigger = True
                        # statusAddendum="Match with 5-Gram Chunk"+statusAddendum
                    elif ((grm in resourceRevisedTermsDict.keys() ) and not localTrigger):
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            coveredAllTokensSet.append(eachTkn)
                            if eachTkn in remSet:
                                remSet.remove(eachTkn)
                            # statusAddendum = "Match with 5-Gram Chunk"+statusAddendum
                        localTrigger = True
                    elif (grm in resourceBracketedPermutationTermsDict.keys() and not localTrigger):
                        resourceId = resourceBracketedPermutationTermsDict[grm]
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            coveredAllTokensSet.append(eachTkn)
                            if eachTkn in remSet:
                                remSet.remove(eachTkn)
                        statusAddendum = "[Permutation of Tokens in Bracketed Resource Term]"
                        statusAddendumSet.append("Permutation of Tokens in Bracketed Resource Term")
                        localTrigger = True
                    for suff in range(len(suffixList)):
                        suffixString = suffixList[suff]
                        sampleRevisedWithSuffix = addSuffix(grm, suffixString)
                        if (sampleRevisedWithSuffix in resourceRevisedTermsDict.keys() and not localTrigger):  # Not trigger true is used here -reason
                            # resourceId = resourceRevisedTermsDict[sampleRevisedWithSuffix]
                            partialMatchedList.append(sampleRevisedWithSuffix)
                            statusAddendum = statusAddendum + "[Suffix Addition- " + suffixString + " to the Input]"
                            statusAddendumSet.append("Suffix Addition- " + suffixString + " to the Input")
                            for eachTkn in grmTokens:
                                coveredAllTokensSet.append(eachTkn)
                                if eachTkn in remSet:
                                    remSet.remove(eachTkn)
                            localTrigger = True

                    # Here the qualities are used for semantic taggings --- change elif to if for qualities in addition to
                    if (grm in qualityLowerDict.keys() and not localTrigger):
                        quality = qualityLowerDict[grm]
                        partialMatchedList.append(grm)
                        statusAddendum = statusAddendum + "[Using Semantic Tagging Resources]"
                        statusAddendumSet.append("Using Semantic Tagging Resources")
                        localTrigger = True
                        for eachTkn in grmTokens:
                            coveredAllTokensSet.append(eachTkn)
                            if eachTkn in remSet:
                                remSet.remove(eachTkn)
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
                    if (grm in abbreviationDict.keys()):  # rule for abbreviation
                        grm = abbreviationDict[grm]
                        statusAddendum = statusAddendum + "[Abbreviation-Acronym Treatment]"
                        statusAddendumSet.append("Abbreviation-Acronym Treatment")
                    if (grm in nonEnglishWordsDict.keys()):  # rule for abbreviation
                        grm = nonEnglishWordsDict[grm]
                        statusAddendum = statusAddendum + "[Non English Language Words Treatment]"
                        statusAddendumSet.append("Non English Language Words Treatment")
                    if (grm in synonymsDict.keys()):  ## Synonyms taken care of- need more synonyms
                        grm = synonymsDict[grm]
                        statusAddendum = statusAddendum + "[Synonym Usage]"
                        statusAddendumSet.append("Synonym Usage")

                    # Matching Test for 2-gram chunk
                    if ((grm in resourceTermsDict.keys() ) and not localTrigger):
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            coveredAllTokensSet.append(eachTkn)
                            if eachTkn in remSet:
                                remSet.remove(eachTkn)
                        localTrigger = True
                    elif (( grm in resourceRevisedTermsDict.keys() ) and not localTrigger):
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            coveredAllTokensSet.append(eachTkn)
                            if eachTkn in remSet:
                                remSet.remove(eachTkn)
                            # statusAddendum = "Match with 5-Gram Chunk"+statusAddendum
                        localTrigger = True
                    elif (grm in resourceBracketedPermutationTermsDict.keys() and not localTrigger):
                        resourceId = resourceBracketedPermutationTermsDict[grm]
                        partialMatchedList.append(grm)
                        for eachTkn in grmTokens:
                            coveredAllTokensSet.append(eachTkn)
                            if eachTkn in remSet:
                                remSet.remove(eachTkn)
                        statusAddendum = "[Permutation of Tokens in Bracketed Resource Term]"
                        statusAddendumSet.append("Permutation of Tokens in Bracketed Resource Term")
                        localTrigger = True
                    for suff in range(len(suffixList)):
                        suffixString = suffixList[suff]
                        sampleRevisedWithSuffix = addSuffix(grm, suffixString)
                    if (sampleRevisedWithSuffix in resourceRevisedTermsDict.keys() and not localTrigger):  # Not trigger true is used here -reason
                        # resourceId = resourceRevisedTermsDict[sampleRevisedWithSuffix]
                        partialMatchedList.append(sampleRevisedWithSuffix)
                        statusAddendum = statusAddendum + "[Suffix Addition- " + suffixString + " to the Input]"
                        statusAddendumSet.append("Suffix Addition- " + suffixString + " to the Input")
                        for eachTkn in grmTokens:
                            coveredAllTokensSet.append(eachTkn)
                            if eachTkn in remSet:
                                remSet.remove(eachTkn)
                        localTrigger = True

                    # Here the qualities are used for semantic taggings --- change elif to if for qualities in addition to
                    if (grm in qualityLowerDict.keys() and not localTrigger):
                        quality = qualityLowerDict[grm]
                        partialMatchedList.append(grm)
                        statusAddendum = statusAddendum + "[Using Semantic Tagging Resources]"
                        statusAddendumSet.append("Using Semantic Tagging Resources")
                        localTrigger = True
                        for eachTkn in grmTokens:
                            coveredAllTokensSet.append(eachTkn)
                            if eachTkn in remSet:
                                remSet.remove(eachTkn)
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

                if (grm in abbreviationDict.keys()):  # rule for abbreviation
                    grm = abbreviationDict[grm]
                    statusAddendum = statusAddendum + "[Abbreviation-Acronym Treatment]"
                    statusAddendumSet.append("Abbreviation-Acronym Treatment")
                if (grm in nonEnglishWordsDict.keys()):  # rule for abbreviation
                    grm = nonEnglishWordsDict[grm]
                    statusAddendum = statusAddendum + "[Non English Language Words Treatment]"
                    statusAddendumSet.append("Non English Language Words Treatment")
                if (grm in synonymsDict.keys()):  ## Synonyms taken care of- need more synonyms
                    grm = synonymsDict[grm]
                    statusAddendum = statusAddendum + "[Synonym Usage]"
                    statusAddendumSet.append("Synonym Usage")

                # Matching Test for 1-gram chunk
                if ((grm in resourceTermsDict.keys() ) and not localTrigger):
                    partialMatchedList.append(grm)
                    for eachTkn in grmTokens:
                        coveredAllTokensSet.append(eachTkn)
                        if eachTkn in remSet:
                            remSet.remove(eachTkn)
                    localTrigger = True
                    # statusAddendum="Match with 5-Gram Chunk"+statusAddendum
                elif ((grm in resourceRevisedTermsDict.keys() ) and not localTrigger):
                    partialMatchedList.append(grm)
                    for eachTkn in grmTokens:
                        coveredAllTokensSet.append(eachTkn)
                        if eachTkn in remSet:
                            remSet.remove(eachTkn)
                        # statusAddendum = "Match with 5-Gram Chunk"+statusAddendum
                    localTrigger = True

                for suff in range(len(suffixList)):
                    suffixString = suffixList[suff]
                    sampleRevisedWithSuffix = addSuffix(grm, suffixString)
                    if (sampleRevisedWithSuffix in resourceRevisedTermsDict.keys() and not localTrigger):  # Not trigger true is used here -reason
                        # resourceId = resourceRevisedTermsDict[sampleRevisedWithSuffix]
                        partialMatchedList.append(sampleRevisedWithSuffix)
                        statusAddendum = statusAddendum + "[Suffix Addition- " + suffixString + " to the Input]"
                        statusAddendumSet.append("Suffix Addition- " + suffixString + " to the Input")
                        for eachTkn in grmTokens:
                            coveredAllTokensSet.append(eachTkn)
                            if eachTkn in remSet:
                                remSet.remove(eachTkn)
                        localTrigger=True

                # Here the qualities are used for semantic taggings --- change elif to if for qualities in addition to
                if (grm in qualityLowerDict.keys() and not localTrigger):
                    quality = qualityLowerDict[grm]
                    partialMatchedList.append(grm)
                    statusAddendum = statusAddendum + "[Using Semantic Tagging Resources]"
                    statusAddendumSet.append("Using Semantic Tagging Resources")
                    localTrigger = True
                    for eachTkn in grmTokens:
                        coveredAllTokensSet.append(eachTkn)
                        if eachTkn in remSet:
                            remSet.remove(eachTkn)


                # Here the qualities are used for semantic taggings --- change elif to if for qualities in addition to
                if (grm in processDict.keys() and not localTrigger):
                    proc = processDict[grm]
                    partialMatchedList.append(grm)
                    statusAddendum = statusAddendum + "[Using Candidate Processes]"
                    statusAddendumSet.append("Using Candidate Processes")
                    localTrigger = True
                    for eachTkn in grmTokens:
                        coveredAllTokensSet.append(eachTkn)
                        if eachTkn in remSet:
                            remSet.remove(eachTkn)


            partialMatchedSet = set(partialMatchedList)  # Makes a set of all matched components from the above processing
            status = "GComponent Match"             #Note: GComponent instead of is used as tag to help sorting later in result file

            remSetConv = set(remSet)
            coveredAllTokensSetConv=set(coveredAllTokensSet)
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
                        coveredAllTokensSet.append(entityPart)
                    else:
                        coveredTSet.append(eachTkn)
                        coveredAllTokensSet.append(eachTkn)

            # To find the remaining unmatched token set (Currently has those ones also which otherwise are removed by lexicons such as - synonyms. So need to be removed)
            for chktkn in sampleTokens:
                if (chktkn not in coveredTSet):
                    remainingTSet.append(chktkn)
                if (chktkn not in coveredAllTokensSet):
                    remainingTokenSet.append(chktkn)

            #Decoding the partial matched set to get back resource ids
            for matchstring in partialMatchedSet:
                if (matchstring in resourceTermsDict.keys()):
                    resourceId = resourceTermsDict[matchstring]
                    partialMatchedResourceList.append(matchstring + ":" + resourceId)
                elif (matchstring in resourceRevisedTermsDict.keys()):
                    resourceId = resourceRevisedTermsDict[matchstring]
                    partialMatchedResourceList.append(matchstring + ":" + resourceId)
                elif (matchstring in resourcePermutationTermsDict.keys()):
                    resourceId = resourcePermutationTermsDict[matchstring]
                    resourceOriginalTerm = resourceTermsIDBasedDict[resourceId]
                    partialMatchedResourceList.append(resourceOriginalTerm.lower() + ":" + resourceId)
                elif (matchstring in resourceBracketedPermutationTermsDict.keys()):
                    resourceId = resourceBracketedPermutationTermsDict[matchstring]
                    resourceOriginalTerm = resourceTermsIDBasedDict[resourceId]
                    resourceOriginalTerm = resourceOriginalTerm.replace(",", "=")
                    partialMatchedResourceList.append(resourceOriginalTerm.lower() + ":" + resourceId)
                elif (matchstring in processDict.keys()):
                    resourceId = processDict[matchstring]
                    partialMatchedResourceList.append(matchstring + ":" + resourceId)
                elif (matchstring in qualityDict.keys()):
                    resourceId = qualityDict[matchstring]
                    partialMatchedResourceList.append(matchstring + ":" + resourceId)
                elif (matchstring in qualityLowerDict.keys()):
                    resourceId = qualityLowerDict[matchstring]
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

            statusAddendumSetFinal = set(statusAddendumSet)

            # In case it is for componet matching and we have at least one component matched
            if (len(partialMatchedSet) > 0):
                if args.format == 'full':
                    fw.write('\t' + str(list(partialMatchedSet)) + '\t' + str(list(partialMatchedResourceListSet)) + '\t' + str(list(retainedSet)) + '\t' + str(len(retainedSet)) + '\t' + status + '\t' + str(list(statusAddendumSetFinal)) + '\t' + str(list(remSetDiff)))
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
                        fw.write('\t' + str(list(partialMatchedSet)) + '\t' + str(list(partialMatchedResourceList)) + '\t\t' + "\t" + "Sorry No Match" + "\t" + str(list(remSet)))

    #Output files closed
    if fw is not sys.stdout:
        fw.close()
