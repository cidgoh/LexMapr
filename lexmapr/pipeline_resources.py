"""Cache and load binary resources."""

from collections import OrderedDict
import csv
from itertools import permutations
import json
import os
import sys

from nltk import word_tokenize

from lexmapr.definitions import ROOT
from lexmapr.ontofetch import Ontology
from lexmapr.pipeline_helpers import punctuation_treatment


def get_profile_args(args):
    """Get args specified by ``args.profile``.

    :rtype: argparse.Namespace
    """
    profile_args_path =\
        os.path.join(ROOT, "resources", "profiles", args.profile, args.profile + "_args.json")

    with open(profile_args_path) as fp:
        profile_args_dict = json.load(fp)

    args_dict = vars(args)
    for key, val in profile_args_dict.items():
        # TODO: How do we allow user to overwrite bucket==True and
        #  --no-cache==True?
        if not args_dict[key]:
            args_dict[key] = val

    return args


def get_profile_resources(profile):
    """Get lookup table of resources specified by ``profile``.

    :rtype:  dict[str, dict]
    """
    ontology_lookup_table_path =\
        os.path.join(ROOT, "resources", "profiles", profile, profile + "_table.json")

    with open(ontology_lookup_table_path) as fp:
        ontology_lookup_table = json.load(fp)

    return ontology_lookup_table


def get_predefined_resources():
    """Get lookup table of ``lexmapr.predefined_resources``.

    Retrieves from disk if possible. Otherwise, creates from scratch
    and adds to disk.

    :rtype: dict[str, dict]
    """
    lookup_table_path = os.path.join(ROOT, "resources", "lookup_table.json")

    if os.path.exists(lookup_table_path):
        with open(lookup_table_path) as fp:
            lookup_table = json.load(fp)
    else:
        lookup_table = create_lookup_table_skeleton()
        lookup_table = add_predefined_resources_to_lookup_table(lookup_table)
        with open(lookup_table_path, "w") as fp:
            json.dump(lookup_table, fp)

    return lookup_table


def get_config_resources(path, no_cache):
    """Get lookup table with resources specified by config file.

    These are resources fetched from online ontologies.

    Retrieves from cache if possible. Otherwise, creates from scratch
    and adds to cache.

    :param str path: Config file path
    :param bool no_cache: If ``True``, does not attempt to retrieve
        from cache
    :rtype: dict[str, dict]
    """
    # Make fetched_ontologies folder if it does not already exist
    fetched_ontologies_dir_path = os.path.join(ROOT, "resources", "fetched_ontologies")
    if not os.path.isdir(fetched_ontologies_dir_path):
        os.mkdir(fetched_ontologies_dir_path)

    # Make ontology_lookup_tables folder if it does not already exist
    ontology_lookup_tables_dir_path = os.path.join(ROOT, "resources", "ontology_lookup_tables")
    if not os.path.isdir(ontology_lookup_tables_dir_path):
        os.makedirs(ontology_lookup_tables_dir_path)

    config_file_name = os.path.splitext(os.path.basename(path))[0]
    ontology_lookup_table_path = os.path.join(ontology_lookup_tables_dir_path,
                                              "lookup_%s.json" % config_file_name)

    if os.path.exists(ontology_lookup_table_path) and not no_cache:
        # Retrieve lookup table for fetched ontology from cache
        with open(ontology_lookup_table_path) as file:
            ontology_lookup_table = json.load(file)
    else:
        # Generate new ontology lookup table
        with open(path) as file:
            config_json = json.load(file)

        ontology_lookup_table = create_lookup_table_skeleton()

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

            # Load fetched_ontology from JSON, and add the appropriate
            # terms to ``ontology_lookup_table.``
            ontology_file_name = os.path.basename(ontology_iri).rsplit('.', 1)[0]
            fetched_ontology_path = os.path.join(fetched_ontologies_dir_path,
                                                 "%s.json" % ontology_file_name)
            with open(fetched_ontology_path) as file:
                fetched_ontology = json.load(file)
            ontology_lookup_table =\
                add_fetched_ontology_to_lookup_table(ontology_lookup_table, fetched_ontology)

        # Add ontology_lookup_table to cache
        with open(ontology_lookup_table_path, "w") as file:
            json.dump(ontology_lookup_table, file)

    return ontology_lookup_table


def get_classification_resources():
    """Get lookup table with resources used in bucket classification.

    Retrieves from disk if possible. Otherwise, creates from scratch
    and adds to disk.

    :rtype: dict[str, dict]
    """
    classification_lookup_table_path =\
        os.path.join(ROOT, "resources", "classification_lookup_table.json")

    if os.path.exists(classification_lookup_table_path):
        with open(classification_lookup_table_path) as fp:
            classification_lookup_table = json.load(fp)
    else:
        classification_lookup_table = create_lookup_table_skeleton()
        classification_lookup_table = \
            add_classification_resources_to_lookup_table(classification_lookup_table)
        with open(classification_lookup_table_path, "w") as fp:
            json.dump(classification_lookup_table, fp)

    return classification_lookup_table


def create_lookup_table_skeleton():
    """Generate an empty lookup table.

    :return: Empty lookup table
    :rtype: dict
    """
    return {
        # ontology_resource_id:ontology_resource_label
        "non_standard_resource_ids": {},
        # standardized_ontology_resource_label:ontology_resource_id
        "standard_resource_labels": {},
        # Keys are some permutation of a standardized ontology resource
        # label, and values are the corresponding ontology resource id.
        "standard_resource_label_permutations": {},
        # Keys are some synonym of an ontology resource, and values are
        # the corresponding standardized ontology resource label.
        "synonyms": {},
        # Keys are some ontology resource id, and values are an array
        # of immediate ontology parent ids.
        "parents": {},
        "abbreviations": {},
        "non_english_words": {},
        "spelling_mistakes": {},
        "inflection_exceptions": {},
        "stop_words": {},
        "suffixes": {},
        "buckets_ifsactop": {},
        "buckets_lexmapr": {},
        "ifsac_labels": {},
        "ifsac_refinement": {},
        "ifsac_default": {}
        }


def add_predefined_resources_to_lookup_table(lookup_table):
    """Add elements from lexmapr.predefined_resources to lookup table.

    :param lookup_table: See create_lookup_table_skeleton for the
                         expected format of this parameter
    :type lookup_table: dict
    :return: Modified ``lookup_table``
    :rtype: dict
    """
    # Abbreviations of resource terms
    lookup_table["abbreviations"] = get_resource_dict("AbbLex.csv")
    # Non-english translations of resource terms
    lookup_table["non_english_words"] = get_resource_dict("NefLex.csv")
    # Common misspellings of resource terms
    lookup_table["spelling_mistakes"] = get_resource_dict("ScorLex.csv")
    # Terms excluded from inflection treatment
    lookup_table["inflection_exceptions"] = get_resource_dict("inflection-exceptions.csv")
    # Constrained list of stop words considered to be meaningless
    lookup_table["stop_words"] = get_resource_dict("mining-stopwords.csv")
    # Suffixes to consider appending to terms when mining ontologies
    lookup_table["suffixes"] = get_resource_dict("suffixes.csv")

    lookup_table["synonyms"] = get_resource_dict("SynLex.csv")
    lookup_table["synonyms"] = {
        punctuation_treatment(k): punctuation_treatment(v)
        for k, v in lookup_table["synonyms"].items()
    }

    lookup_table["non_standard_resource_ids"] = get_resource_dict("CombinedResourceTerms.csv")

    lookup_table["standard_resource_labels"] = {
        punctuation_treatment(v): k
        for k, v in lookup_table["non_standard_resource_ids"].items()
    }

    for label in lookup_table["standard_resource_labels"]:
        resource_id = lookup_table["standard_resource_labels"][label]
        label_tokens = word_tokenize(label)
        # To limit performance overhead, we ignore resource labels with
        # more than 7 tokens, as permutating too many tokens can be
        # costly. We also ignore NCBI taxon terms, as there are
        # ~160000 such terms.
        if len(label_tokens) <7 and "ncbitaxon" not in resource_id:
            label_permutations = get_resource_label_permutations(label)
            for permutation in label_permutations:
                lookup_table["standard_resource_label_permutations"][permutation] = resource_id
    return lookup_table


def get_resource_dict(resource_file_name):
    """Get dictionary of data from ``predefined_resources/`` csv file.

    The data is standardized to lowercase.

    :param resource_file_name: Name of file (with extension) in
        ``predefined_resources/``
    :type resource_file_name: str
    :return: data in ``resource_file_name``
    :rtype: dict
    """
    # Return value
    ret = {}
    # Open file_name
    with open(os.path.join(ROOT, "predefined_resources", resource_file_name)) as fp:
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


def get_resource_label_permutations(resource_label):
    """Get permutations of some term.

    :param resource_label: Name of some resource
    :type resource_label: str
    :return: All permutations of resource_label
    :rtype: list
    """
    # List of tuples, where each tuple is a different permutation of
    # tokens from label
    permutations_set = list(OrderedDict.fromkeys(permutations(resource_label.split())))
    # Return value
    ret = []
    # Generate a string from each tuple, and add it to ret
    for permutation_tuple in permutations_set:
        permutation_string = " ".join(permutation_tuple)
        ret = ret + [permutation_string]

    return ret


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
            resource_id = resource["id"].lower()
            resource_label = resource["label"].lower()

            # ID value should match format of pre-defined resources
            resource_id = resource_id.replace(":", "_")
            lookup_table["non_standard_resource_ids"][resource_id] = resource_label

            # Standardize label
            resource_label = punctuation_treatment(resource_label)
            lookup_table["standard_resource_labels"][resource_label] = resource_id

            # List of tokens in resource_label
            resource_tokens = word_tokenize(resource_label)
            # Add permutations if there are less than seven tokens.
            # Permutating more tokens than this can lead to performance
            # issues.
            if len(resource_tokens) < 7:
                permutations = get_resource_label_permutations(resource_label)
                for permutation in permutations:
                    lookup_table["standard_resource_label_permutations"][permutation] = resource_id

            if "oboInOwl:hasSynonym" in resource:
                synonyms = resource["oboInOwl:hasSynonym"]
                for synonym in synonyms:
                    # Standardize synonym
                    synonym = punctuation_treatment(synonym.lower())

                    lookup_table["synonyms"][synonym] = resource_label

            if "oboInOwl:hasNarrowSynonym" in resource:
                synonyms = resource["oboInOwl:hasNarrowSynonym"]
                for synonym in synonyms:
                    # Standardize synonym
                    synonym = punctuation_treatment(synonym.lower())

                    lookup_table["synonyms"][synonym] = resource_label

            if "oboInOwl:hasExactSynonym" in resource:
                synonyms = resource["oboInOwl:hasExactSynonym"]
                for synonym in synonyms:
                    # Standardize synonym
                    synonym = punctuation_treatment(synonym.lower())

                    lookup_table["synonyms"][synonym] = resource_label

            if "parent_id" in resource:
                # Standardize parent_id
                parent_id = resource["parent_id"].replace(":", "_")
                parent_id = parent_id.lower()

                # Bug in ``ontofetch.py``--sometimes a resource is
                # parent to itself. Remove when fixed.
                if resource_id == parent_id:
                    continue
                # Instead of overwriting parents like we do with
                # synonyms, we will concatenate parents from different
                # fetches.
                elif resource_id in lookup_table["parents"]:
                    # Prevent duplicates
                    if parent_id not in lookup_table["parents"][resource_id]:
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

                    # Bug in ``ontofetch.py``--sometimes a resource is
                    # parent to itself. Remove when fixed.
                    other_parents = list(filter(lambda x: x != resource_id, other_parents))

                    lookup_table["parents"][resource_id] += other_parents

    return lookup_table


def add_classification_resources_to_lookup_table(classification_lookup_table):
    """Add classification elements to lookup table.

    :param classification_lookup_table: See
        create_lookup_table_skeleton for the expected format of this
        parameter
    :type classification_lookup_table: dict
    :return: Modified ``lookup_table``
    :rtype: dict
    """
    # Some default buckets pre-defined by LexMapr
    classification_lookup_table["buckets_lexmapr"] = get_resource_dict("buckets-lexmapr.csv")
    # Buckets made with IFSAC in mind
    classification_lookup_table["buckets_ifsactop"] = get_resource_dict("buckets-ifsactop.csv")
    # IFSAC labels corresponding to IFSAC buckets
    classification_lookup_table["ifsac_labels"] = get_resource_dict("ifsac-labels.csv")

    # Default labels to consider with IFSAC in mind
    classification_lookup_table["ifsac_default"] = get_resource_dict("ifsac-default.csv")
    classification_lookup_table["ifsac_refinement"] = get_resource_dict("ifsac-refinement.csv")

    return classification_lookup_table
