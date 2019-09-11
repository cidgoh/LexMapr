#!/usr/bin/env python

"""Point-of-entry script."""

import collections
import csv
import json
import os
import re
import sys

from nltk.tokenize import word_tokenize

from lexmapr.definitions import ROOT
from lexmapr.ontofetch import Ontology
from lexmapr.pipeline_classification import (add_classification_resources_to_lookup_table,
                                             classify_sample)
import lexmapr.pipeline_helpers as helpers


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
    lookup_table_path = os.path.join(ROOT, "cache", "lookup_table.json")
    if os.path.exists(lookup_table_path) and not args.no_cache:
        with open(lookup_table_path) as fp:
            lookup_table = json.load(fp)
    else:
        lookup_table = helpers.create_lookup_table_skeleton()
        lookup_table = helpers.add_predefined_resources_to_lookup_table(lookup_table)
        with open(lookup_table_path, "w") as fp:
            json.dump(lookup_table, fp)

    # Lookup table will also consist of terms fetched from an online
    # ontology.
    if args.config:
        # Make fetched_ontologies folder if it does not already exist
        fetched_ontologies_dir_path = os.path.join(ROOT, "cache", "fetched_ontologies")
        if not os.path.isdir(fetched_ontologies_dir_path):
            os.mkdir(fetched_ontologies_dir_path)
        # Make ontology_lookup_tables folder if it does not already exist
        ontology_lookup_tables_dir_path = os.path.join(ROOT, "cache", "ontology_lookup_tables")
        if not os.path.isdir(ontology_lookup_tables_dir_path):
            os.makedirs(ontology_lookup_tables_dir_path)

        config_file_name = os.path.basename(args.config).rsplit('.', 1)[0]
        ontology_lookup_table_path = os.path.join(ontology_lookup_tables_dir_path,
                                                  "lookup_%s.json" % config_file_name)

        # Retrieve lookup table for fetched ontology from cache
        if os.path.exists(ontology_lookup_table_path) and not args.no_cache:
            with open(ontology_lookup_table_path) as file:
                ontology_lookup_table = json.load(file)
        # Generate new ontology lookup table
        else:
            # Load user-specified config file into an OrderedDict
            with open(args.config) as file:
                config_json = json.load(file)

            # Create empty ontology lookup table
            ontology_lookup_table = helpers.create_lookup_table_skeleton()

            # Iterate over config_json backwards
            for json_object in reversed(config_json):
                (ontology_iri, root_entity_iri), = json_object.items()
                # Arguments for ontofetch.py
                if root_entity_iri == "":
                    sys.argv = ["", ontology_iri, "-o", fetched_ontologies_dir_path + "/"]
                else:
                    sys.argv = ["", ontology_iri, "-o", fetched_ontologies_dir_path + "/", "-r",
                                root_entity_iri]
                # Call ontofetch.py
                ontofetch = Ontology()
                ontofetch.__main__()
                # Load fetched_ontology from JSON, and add the
                # appropriate terms to lookup_table.
                ontology_file_name = os.path.basename(ontology_iri).rsplit('.', 1)[0]
                fetched_ontology_path = os.path.join(fetched_ontologies_dir_path,
                                                     "%s.json" % ontology_file_name)
                with open(fetched_ontology_path) as file:
                    fetched_ontology = json.load(file)
                ontology_lookup_table =\
                    helpers.add_fetched_ontology_to_lookup_table(ontology_lookup_table,
                                                                 fetched_ontology)

            # Add ontology_lookup_table to cache
            with open(ontology_lookup_table_path, "w") as file:
                json.dump(ontology_lookup_table, file)

        # Merge ontology_lookup_table into lookup_table
        lookup_table = helpers.merge_lookup_tables(lookup_table, ontology_lookup_table)

    # Output file Column Headings
    OUTPUT_FIELDS = [
        "Sample_Id",
        "Sample_Desc",
        "Cleaned_Sample"
    ]

    if args.format == 'full':
        OUTPUT_FIELDS += [
            "Final_Refined_Terms_with_Resource_IDs",
            "Match_Status(Macro Level)",
            "Match_Status(Micro Level)"
        ]
    else:
        OUTPUT_FIELDS += [
            "Matched_Components"
        ]

    if args.bucket:
        if args. format == "full":
            OUTPUT_FIELDS += [
                "LexMapr Classification (Full List)",
                "LexMapr Bucket",
                "Third Party Bucket",
                "Third Party Classification"
            ]
        else:
            OUTPUT_FIELDS += [
                "Third Party Classification"
            ]

        # Cache (or get from cache) the lookup table containing pre-defined
        # resources used for **classification**.
        classification_lookup_table_path = os.path.join(ROOT, "cache",
                                                        "classification_lookup_table.json")
        if os.path.exists(classification_lookup_table_path) and not args.no_cache:
            with open(classification_lookup_table_path) as fp:
                classification_lookup_table = json.load(fp)
        else:
            classification_lookup_table = helpers.create_lookup_table_skeleton()
            classification_lookup_table =\
                add_classification_resources_to_lookup_table(classification_lookup_table)
            with open(classification_lookup_table_path, "w") as fp:
                json.dump(classification_lookup_table, fp)

    fw = open(args.output, 'w') if args.output else sys.stdout     # Main output file
    fw.write('\t'.join(OUTPUT_FIELDS))

    # Input file
    fr = open(args.input_file, "r")
    fr_reader = csv.reader(fr, delimiter=",")
    # Skip header
    next(fr_reader)

    # Iterate over samples for matching to ontology terms
    for row in fr_reader:
        sampleid = row[0].strip()
        sample = row[1].strip()
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

        # Standardize sample to lowercase
        sample = sample.lower()

        sample = helpers.punctuationTreatment(sample, punctuations)  # Sample gets simple punctuation treatment
        sample = re.sub(' +', ' ', sample)  # Extra innner spaces are removed
        sampleTokens = word_tokenize(sample)    #Sample is tokenized into tokenList

        cleaned_sample = ""  # Phrase that will be used for cleaned sample
        lemma = ""

        for tkn in sampleTokens:
            remaining_tokens.append(tkn)  # To start with all remaining tokens in set

        # ===Few preliminary things- Inflection,spelling mistakes, Abbreviations, acronyms, foreign words, Synonyms taken care of
        for tkn in sampleTokens:

            # Ignore dates
            if helpers.is_date(tkn):
                continue

            # Some preprocessing (only limited or controlled) Steps
            tkn = helpers.preprocess(tkn)

            # Plurals are converted to singulars with exceptions
            lemma = helpers.singularize_token(tkn, lookup_table, status_addendum)

            # Misspellings are dealt with  here
            lemma = helpers.spelling_correction(lemma, lookup_table, status_addendum)

            # Abbreviations, acronyms, taken care of- need rule for abbreviation e.g. if lemma is Abbreviation
            lemma = helpers.abbreviation_normalization_token(lemma, lookup_table, status_addendum)

            # non-EngLish language words taken care of
            lemma = helpers.non_English_normalization_token(lemma, lookup_table, status_addendum)

            # ===This will create a cleaned sample after above treatments
            cleaned_sample = helpers.get_cleaned_sample(cleaned_sample, lemma, lookup_table)
            cleaned_sample = re.sub(' +', ' ', cleaned_sample)

            # Phrase being cleaned for
            cleaned_sample = helpers.abbreviation_normalization_phrase(cleaned_sample, lookup_table,
                                                                       status_addendum)

            # Phrase being cleaned for
            cleaned_sample = helpers.non_English_normalization_phrase(cleaned_sample, lookup_table,
                                                                      status_addendum)

        cleaned_sample = helpers.remove_duplicate_tokens(cleaned_sample)
        fw.write('\t' + cleaned_sample)

        #---------------------------STARTS APPLICATION OF RULES-----------------------------------------------
        try:
            # Find full-term match for sample
            full_term_match = helpers.find_full_term_match(sample, lookup_table, cleaned_sample,
                                                           status_addendum)

            # Write to all headers
            if args.format == "full":
                fw.write("\t"+ str(full_term_match["retained_terms_with_resource_ids"])
                    + "\t" + full_term_match["match_status_macro_level"] + "\t"
                    + str(full_term_match["match_status_micro_level"]))
            # Write to some headers
            else:
                fw.write("\t" + str(full_term_match["all_match_terms_with_resource_ids"]))
            # Tokenize sample
            sample_tokens = word_tokenize(sample)
            # Add all tokens to covered_tokens
            [covered_tokens.append(token) for token in sample_tokens]
            # Remove all tokens from remaining_tokens
            [remaining_tokens.remove(token) for token in sample_tokens]

            if args.bucket:
                matched_terms_with_ids = full_term_match["retained_terms_with_resource_ids"]
                classification_result = classify_sample(sample, matched_terms_with_ids,
                                                        lookup_table, classification_lookup_table)
                if args.format == "full":
                    fw.write("\t" + str(classification_result["lexmapr_hierarchy_buckets"]) + "\t"
                             + str(classification_result["lexmapr_final_buckets"]) + "\t"
                             + str(classification_result["ifsac_final_buckets"]) + "\t"
                             + str(classification_result["ifsac_final_labels"]))
                else:
                    fw.write("\t" + str(classification_result["ifsac_final_labels"]))

            # Set trigger to True
            trigger = True
        # Full-term match not found
        except helpers.MatchNotFoundError:
            # Continue on
            pass

        # Component Matches Section
        if (not trigger):
            # 1-5 gram component matches for cleaned_sample, and
            # tokens covered by said matches. See find_component_match
            # docstring for details.
            component_and_token_matches = helpers.find_component_matches(cleaned_sample,
                                                                         lookup_table,
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
                strTokens = word_tokenize(tknstr)
                for eachTkn in strTokens:
                    if ("==" in eachTkn):
                        resList = eachTkn.split("==")
                        entity_part = resList[0]
                        entity_tag = resList[1]
                        coveredTSet.append(entity_part)
                        covered_tokens.append(entity_part)
                    else:
                        coveredTSet.append(eachTkn)
                        covered_tokens.append(eachTkn)

            # To find the remaining unmatched token set (Currently has those ones also which otherwise are removed by lexicons such as - synonyms. So need to be removed)
            for chktkn in sampleTokens:
                if (chktkn not in coveredTSet):
                    remainingTSet.append(chktkn)
                if (chktkn not in covered_tokens):
                    remainingTokenSet.append(chktkn)

            partial_matches_with_ids_dict = {}
            for partial_match in partial_matches:
                partial_match_id = helpers.get_resource_id(partial_match, lookup_table)
                if partial_match_id:
                    try:
                        # The partial match may be a permutated term, so we
                        # get the original.
                        true_label = lookup_table["resource_terms_id_based"][partial_match_id]
                    except KeyError:
                        true_label = partial_match

                    partial_matches_with_ids_dict[true_label] = partial_match_id
                elif "==" in partial_match:
                    res_list = partial_match.split("==")
                    entity_part = res_list[0]
                    entity_tag = res_list[1]
                    partial_matches_with_ids_dict[entity_part] = entity_tag

            # We need to eventually remove partial matches that are
            # ancestral to other partial matches.
            ancestors = set()
            for _, partial_match_id in partial_matches_with_ids_dict.items():
                partial_match_hierarchies = helpers.get_term_parent_hierarchies(partial_match_id,
                                                                                lookup_table)

                for partial_match_hierarchy in partial_match_hierarchies:
                    # We do not need the first element
                    partial_match_hierarchy.pop(0)

                    ancestors |= set(partial_match_hierarchy)

            # Add non-ancestral values from
            # partial_matches_with_ids_dict to form required for
            # output.
            partial_matches_with_ids = []
            for partial_match, partial_match_id in partial_matches_with_ids_dict.items():
                if partial_match_id not in ancestors:
                    partial_matches_with_ids.append(partial_match + ":" + partial_match_id)

            partialMatchedResourceListSet = set(partial_matches_with_ids)   # Makes a set from list of all matched components with resource ids
            retainedSet = []

            # If size of set is more than one member, looks for the retained matched terms by defined criteria
            if (len(partialMatchedResourceListSet) > 0):
                retainedSet = helpers.retainedPhrase(list(partialMatchedResourceListSet))
                # HERE SHOULD HAVE ANOTHER RETAING SET

            final_status = set(status_addendum)

            if not partial_matches:
                status = "No Match"
                final_status = set()

            if args.format == 'full':
                fw.write('\t' + str(sorted(list(retainedSet))) + '\t' + status + '\t'
                         + str(sorted(list(final_status))))

            if args.format != 'full':
                fw.write("\t" + str(sorted(list(retainedSet))))

            if args.bucket:
                matched_terms_with_ids = partial_matches_with_ids
                classification_result = classify_sample(sample, matched_terms_with_ids,
                                                        lookup_table,
                                                        classification_lookup_table)
                if args.format == "full":
                    fw.write("\t" + str(classification_result["lexmapr_hierarchy_buckets"])
                             + "\t" + str(classification_result["lexmapr_final_buckets"]) + "\t"
                             + str(classification_result["ifsac_final_buckets"]) + "\t"
                             + str(classification_result["ifsac_final_labels"]))
                else:
                    fw.write("\t" + str(classification_result["ifsac_final_labels"]))

    fw.write('\n')
    #Output files closed
    if fw is not sys.stdout:
        fw.close()
    # Input file closed
    fr.close()
