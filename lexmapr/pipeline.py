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
    OUTPUT_FIELDS = [
        "Sample_Id",
        "Sample_Desc",
        "Cleaned_Sample",
        "Matched_Components"
    ]

    if args.format == 'full':
        OUTPUT_FIELDS += [
            "Match_Status(Macro Level)",
            "Match_Status(Micro Level)"
        ]

    if args.bucket:
        if args.format == "full":
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

        # Preliminary treatments
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
            cleaned_sample = helpers.abbreviation_normalization_phrase(cleaned_sample, lookup_table,
                                                                       micro_status)
            cleaned_sample = helpers.non_English_normalization_phrase(cleaned_sample, lookup_table,
                                                                      micro_status)

        cleaned_sample = helpers.remove_duplicate_tokens(cleaned_sample)

        #---------------------------STARTS APPLICATION OF RULES-----------------------------------------------
        try:
            # full_term_match = helpers.map_term(sample, lookup_table)
            # if not full_term_match and sample in lookup_table["synonyms"]:
            #     full_term_match = helpers.map_term(lookup_table["synonyms"][sample], lookup_table)


            # Find full-term match for sample
            full_term_match = helpers.find_full_term_match(sample, lookup_table, cleaned_sample,
                                                           micro_status)

            if full_term_match["retained_terms_with_resource_ids"]:
                matched_components = full_term_match["retained_terms_with_resource_ids"]
                macro_status = "Full Term Match"
                micro_status = full_term_match["match_status_micro_level"]

                if args.bucket:
                    classification_result = classify_sample(
                        sample, matched_components, lookup_table, classification_lookup_table
                    )
                    lexmapr_classification = classification_result["lexmapr_hierarchy_buckets"]
                    lexmapr_bucket = classification_result["lexmapr_final_buckets"]
                    third_party_bucket = classification_result["ifsac_final_buckets"]
                    third_party_classification = classification_result["ifsac_final_labels"]

            trigger = True
        # Full-term match not found
        except helpers.MatchNotFoundError:
            trigger = False

        # Component Matches Section
        if not trigger:
            # 1-5 gram component matches for cleaned_sample, and
            # tokens covered by said matches. See find_component_match
            # docstring for details.
            component_and_token_matches = helpers.find_component_matches(cleaned_sample,
                                                                         lookup_table,
                                                                         micro_status)

            partial_matches = set(component_and_token_matches["component_matches"])  # Makes a set of all matched components from the above processing

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

            # Makes a set from list of all matched components with
            # resource ids.
            partialMatchedResourceListSet = set(partial_matches_with_ids)
            retainedSet = []

            # If size of set is more than one member, looks for the retained matched terms by defined criteria
            if (len(partialMatchedResourceListSet) > 0):
                retainedSet = helpers.retainedPhrase(list(partialMatchedResourceListSet))
                # HERE SHOULD HAVE ANOTHER RETAING SET

            matched_components = sorted(list(retainedSet))

            if retainedSet:
                matched_components = sorted(list(retainedSet))
                macro_status = "Component Match"
                # https://stackoverflow.com/a/7961390/11472358
                micro_status = list(collections.OrderedDict.fromkeys(micro_status))
            else:
                # TODO: remove the need for this
                micro_status = []

            if args.bucket:
                classification_result = classify_sample(sample, partial_matches_with_ids,
                                                        lookup_table,
                                                        classification_lookup_table)
                lexmapr_classification = classification_result["lexmapr_hierarchy_buckets"]
                lexmapr_bucket = classification_result["lexmapr_final_buckets"]
                third_party_bucket = classification_result["ifsac_final_buckets"]
                third_party_classification = classification_result["ifsac_final_labels"]

        fw.write("\n" + sample_id + "\t" + original_sample + "\t" + cleaned_sample + "\t"
                 + str(matched_components))
        if args.format == "full":
            fw.write("\t" + macro_status + "\t" + str(micro_status))
        if args.bucket:
            if args.format == "full":
                fw.write("\t" + str(lexmapr_classification) + "\t" + str(lexmapr_bucket) + "\t"
                         + str(third_party_bucket))
            fw.write("\t" + str(third_party_classification))

    fw.write('\n')
    #Output files closed
    if fw is not sys.stdout:
        fw.close()
    # Input file closed
    fr.close()
