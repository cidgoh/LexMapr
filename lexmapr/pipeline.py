#!/usr/bin/env python

"""Point-of-entry script."""

from collections import OrderedDict
import csv
from itertools import permutations
import os
import re
import sys

from nltk.tokenize import word_tokenize

import lexmapr.pipeline_resources as pipeline_resources
from lexmapr.pipeline_classification import classify_sample
import lexmapr.pipeline_helpers as helpers


def run(args):
    """
    Main text mining pipeline.
    """
    # If the user specified a profile, we must retrieve args specified
    # by the profile, unless they were explicitly overridden.
    if args.profile:
        args = pipeline_resources.get_profile_args(args)

    # To contain all resources, and their variations, that samples are
    # matched to.  Start by adding pre-defined resources from
    # lexmapr.predefined_resources.
    # TODO: These pre-defined resources are the remnants of early
    #  LexMapr development.  We should eventually move to only adding
    #  terms from online ontologies to lookup tables.
    lookup_table = pipeline_resources.get_predefined_resources()

    # Scientific names dictionary fetched from lookup tables.
    # Todo: Move to ontology_lookup_table later
    scientific_names_dict = pipeline_resources.get_resource_dict(
        "foodon_ncbi_synonyms.csv")

    # To contain resources fetched from online ontologies, if any.
    # Will eventually be added to ``lookup_table``.
    ontology_lookup_table = None

    if args.config:
        # Fetch online ontology terms specified in config file.
        ontology_lookup_table = pipeline_resources.get_config_resources(args.config, args.no_cache)
    elif args.profile:
        # Fetch online ontology terms specified in profile.
        ontology_lookup_table = pipeline_resources.get_profile_resources(args.profile)

    if ontology_lookup_table:
        # Merge ``ontology_lookup_table`` into ``lookup_table``
        lookup_table = helpers.merge_lookup_tables(lookup_table, ontology_lookup_table)

    # To contain resources used in classification.
    classification_lookup_table = None
    if args.bucket:
        classification_lookup_table = pipeline_resources.get_classification_resources()

    # Output file Column Headings
    output_fields = [
        "Sample_Id",
        "Sample_Desc",
        "Processed_Sample",
        "Processed_Sample (With Scientific Name)",
        "Matched_Components"
    ]

    if args.full:
        output_fields += [
            "Match_Status(Macro Level)",
            "Match_Status(Micro Level)",
            "Sample_Transformations"
        ]
    else:
        output_fields += [
                "Match_Status(Macro Level)"
        ]

    if args.bucket:
        if args.full:
            output_fields += [
                "LexMapr Classification (Full List)",
                "LexMapr Bucket",
                "Third Party Bucket",
                "Third Party Classification"
            ]
        else:
            output_fields += [
                "Third Party Classification"
            ]

    fw = open(args.output, 'w') if args.output else sys.stdout     # Main output file
    fw.write('\t'.join(output_fields))

    # Input file
    fr = open(args.input_file, "r")
    _, ext = os.path.splitext(args.input_file)
    if ext == ".csv":
        fr_reader = csv.reader(fr, delimiter=",")
    elif ext == ".tsv":
        fr_reader = csv.reader(fr, delimiter="\t")
    else:
        raise ValueError("Should not reach here")
    # Skip header
    next(fr_reader)

    # Iterate over samples for matching to ontology terms
    for row in fr_reader:
        sample_id = row[0].strip()
        original_sample = " ".join(row[1:]).strip()
        cleaned_sample = ""
        cleaned_sample_scientific_name = ""
        matched_components = []
        macro_status = "No Match"
        micro_status = []
        lexmapr_classification = []
        lexmapr_bucket = []
        third_party_bucket = []
        third_party_classification = []
        sample_conversion_status = {}

        # Standardize sample to lowercase and with punctuation
        # treatment.
        sample = original_sample.lower()
        sample = helpers.punctuation_treatment(sample)

        sample_tokens = word_tokenize(sample)

        # Get ``cleaned_sample``
        for token in sample_tokens:
            # Ignore dates
            if helpers.is_date(token) or helpers.is_number(token):
                continue
            # Some preprocessing
            token = helpers.preprocess(token)

            lemma = helpers.singularize_token(token, lookup_table, micro_status)
            lemma = helpers.spelling_correction(lemma, lookup_table, micro_status)
            lemma = helpers.abbreviation_normalization_token(lemma, lookup_table, micro_status)
            lemma = helpers.non_English_normalization_token(lemma, lookup_table, micro_status)
            if not token == lemma:
                sample_conversion_status[token] = lemma
            cleaned_sample = helpers.get_cleaned_sample(cleaned_sample, lemma, lookup_table)
            cleaned_sample = re.sub(' +', ' ', cleaned_sample)
            cleaned_sample = helpers.abbreviation_normalization_phrase(cleaned_sample,
                                                                       lookup_table, micro_status)
            cleaned_sample = helpers.non_English_normalization_phrase(cleaned_sample, lookup_table,
                                                                      micro_status)
            cleaned_sample_scientific_name = helpers.get_annotated_sample(
                cleaned_sample_scientific_name, lemma, scientific_names_dict)
            cleaned_sample_scientific_name = re.sub(' +', ' ', cleaned_sample_scientific_name)

        cleaned_sample = helpers.remove_duplicate_tokens(cleaned_sample)
        cleaned_sample_scientific_name = helpers.remove_duplicate_tokens(
            cleaned_sample_scientific_name)

        # Attempt full term match
        full_term_match = helpers.map_term(sample, lookup_table)

        if not full_term_match:
            # Attempt full term match with cleaned sample
            full_term_match = helpers.map_term(cleaned_sample, lookup_table)
            if full_term_match:
                micro_status.insert(0, "Used Cleaned Sample")

        if not full_term_match:
            # Attempt full term match using suffixes
            full_term_match = helpers.map_term(sample, lookup_table, consider_suffixes=True)

        if not full_term_match:
            # Attempt full term match with cleaned sample using suffixes
            full_term_match =\
                helpers.map_term(cleaned_sample, lookup_table, consider_suffixes=True)
            if full_term_match:
                micro_status.insert(0, "Used Cleaned Sample")

        if full_term_match:
            matched_components.append(full_term_match["term"] + ":" + full_term_match["id"])
            macro_status = "Full Term Match"
            micro_status += full_term_match["status"]

            if args.bucket:
                classification_result = classify_sample(
                    sample, matched_components, lookup_table, classification_lookup_table
                )
                lexmapr_classification = classification_result["lexmapr_hierarchy_buckets"]
                lexmapr_bucket = classification_result["lexmapr_final_buckets"]
                third_party_bucket = classification_result["ifsac_final_buckets"]
                third_party_classification = classification_result["ifsac_final_labels"]
        else:
            # Attempt various component matches
            component_matches = []
            covered_tokens = set()

            for i in range(5, 0, -1):
                for gram_chunk in helpers.get_gram_chunks(cleaned_sample, i):
                    concat_gram_chunk = " ".join(gram_chunk)
                    gram_tokens = word_tokenize(concat_gram_chunk)
                    gram_permutations =\
                        list(OrderedDict.fromkeys(permutations(concat_gram_chunk.split())))

                    # gram_tokens covered in prior component match
                    if set(gram_tokens) <= covered_tokens:
                        continue

                    for gram_permutation in gram_permutations:
                        gram_permutation_str = " ".join(gram_permutation)
                        component_match = helpers.map_term(gram_permutation_str, lookup_table)

                        if not component_match:
                            # Try again with suffixes
                            component_match = helpers.map_term(gram_permutation_str, lookup_table,
                                                               consider_suffixes=True)

                        if component_match:
                            component_matches.append(component_match)
                            covered_tokens.update(gram_tokens)
                            break

            # We need should not consider component matches that are
            # ancestral to other component matches.
            ancestors = set()
            for component_match in component_matches:
                component_match_hierarchies =\
                    helpers.get_term_parent_hierarchies(component_match["id"], lookup_table)

                for component_match_hierarchy in component_match_hierarchies:
                    # We do not need the first element
                    component_match_hierarchy.pop(0)

                    ancestors |= set(component_match_hierarchy)

            for component_match in component_matches:
                if component_match["id"] not in ancestors:
                    matched_component = component_match["term"] + ":" + component_match["id"]
                    matched_components.append(matched_component)

            # TODO: revisit this step.
            # We do need it, but perhaps the function could be
            #  simplified?
            if len(matched_components):
                matched_components = helpers.retain_phrase(matched_components)

            # Finalize micro_status
            # TODO: This is ugly, so revisit after revisiting
            #  ``retain_phrase``.
            micro_status_covered_matches = set()
            for component_match in component_matches:
                possible_matched_component = component_match["term"] + ":" + component_match["id"]
                if possible_matched_component in matched_components:
                    if possible_matched_component not in micro_status_covered_matches:
                        micro_status_covered_matches.add(possible_matched_component)
                        micro_status.append("{%s: %s}"
                                            % (component_match["term"], component_match["status"]))

            if matched_components:
                macro_status = "Component Match"

            if args.bucket:
                classification_result = classify_sample(
                    sample, matched_components, lookup_table, classification_lookup_table
                )
                lexmapr_classification = classification_result["lexmapr_hierarchy_buckets"]
                lexmapr_bucket = classification_result["lexmapr_final_buckets"]
                third_party_bucket = classification_result["ifsac_final_buckets"]
                third_party_classification = classification_result["ifsac_final_labels"]

        # Write to row
        matched_components = helpers.get_matched_component_standardized(matched_components)

        # Get post-processed cleaned sample with embedded scientific 
        # name.
        cleaned_sample_scientific_name = helpers.refine_sample_sc_name(
            sample, cleaned_sample, cleaned_sample_scientific_name,
            third_party_classification)

        fw.write("\n" + sample_id + "\t" + original_sample + "\t" + cleaned_sample + "\t"
                 + cleaned_sample_scientific_name + "\t" + str(matched_components) + "\t" 
                 + macro_status)

        if args.full:
            fw.write("\t" + str(micro_status)+"\t" + str(sample_conversion_status))

        if args.bucket:
            if args.full:
                fw.write("\t" + str(lexmapr_classification) + "\t" + str(lexmapr_bucket)
                         + "\t" + str(third_party_bucket))
            fw.write("\t" + str(third_party_classification))

    fw.write('\n')
    # Output files closed
    if fw is not sys.stdout:
        fw.close()
    # Input file closed
    fr.close()
