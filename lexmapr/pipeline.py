#!/usr/bin/env python

"""Point-of-entry script."""

from collections import OrderedDict
import csv
import json
from itertools import permutations
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
    punctuations = ['-', '_', '(', ')', ';', '/', ':', '%']

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
    output_fields = [
        "Sample_Id",
        "Sample_Desc",
        "Cleaned_Sample",
        "Matched_Components"
    ]

    if args.format == 'full':
        output_fields += [
            "Match_Status(Macro Level)",
            "Match_Status(Micro Level)"
        ]

    if args.bucket:
        if args.format == "full":
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
        matched_components = []
        macro_status = "No Match"
        micro_status = []
        lexmapr_classification = []
        lexmapr_bucket = []
        third_party_bucket = []
        third_party_classification = []

        # Standardize sample to lowercase
        sample = original_sample.lower()

        sample = helpers.punctuation_treatment(sample, punctuations)
        sample = re.sub(' +', ' ', sample)
        sample_tokens = word_tokenize(sample)

        # Get ``cleaned_sample``
        for tkn in sample_tokens:
            # Ignore dates
            if helpers.is_date(tkn):
                continue
            # Some preprocessing
            tkn = helpers.preprocess(tkn)

            lemma = helpers.singularize_token(tkn, lookup_table, micro_status)
            lemma = helpers.spelling_correction(lemma, lookup_table, micro_status)
            lemma = helpers.abbreviation_normalization_token(lemma, lookup_table, micro_status)
            lemma = helpers.non_English_normalization_token(lemma, lookup_table, micro_status)

            cleaned_sample = helpers.get_cleaned_sample(cleaned_sample, lemma, lookup_table)
            cleaned_sample = re.sub(' +', ' ', cleaned_sample)
            cleaned_sample = helpers.abbreviation_normalization_phrase(cleaned_sample,
                                                                       lookup_table, micro_status)
            cleaned_sample = helpers.non_English_normalization_phrase(cleaned_sample, lookup_table,
                                                                      micro_status)

        cleaned_sample = helpers.remove_duplicate_tokens(cleaned_sample)

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
                matched_components = helpers.retainedPhrase(matched_components)

            # Finalize micro_status
            # TODO: This is ugly, so revisit after revisiting
            #  ``retainedPhrase``.
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
        fw.write("\n" + sample_id + "\t" + original_sample + "\t" + cleaned_sample + "\t"
                 + str(matched_components))

        if args.format == "full":
            fw.write("\t" + macro_status + "\t" + str(micro_status))

        if args.bucket:
            if args.format == "full":
                fw.write("\t" + str(lexmapr_classification) + "\t" + str(lexmapr_bucket)
                         + "\t" + str(third_party_bucket))
            fw.write("\t" + str(sorted(third_party_classification)))

    fw.write('\n')
    # Output files closed
    if fw is not sys.stdout:
        fw.close()
    # Input file closed
    fr.close()
