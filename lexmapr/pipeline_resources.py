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
    """Add elements from lexmapr.predefined_resources to lookup table.

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


def get_resource_permutation_terms(resource_label):
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
