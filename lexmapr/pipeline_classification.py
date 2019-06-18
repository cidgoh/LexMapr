"""Functions used for bucket classification."""

from lexmapr.pipeline_helpers import get_resource_dict, get_term_parent_hierarchy


def add_classification_resources_to_lookup_table(classification_lookup_table):
    """Add classification elements from ``resources/`` to lookup table.

    :param classification_lookup_table: See
        create_lookup_table_skeleton for the expected format of this
        parameter
    :type classification_lookup_table: dict
    :return: Modified ``lookup_table``
    :rtype: dict
    """
    # Some default buckets pre-defined by LexMapr
    classification_lookup_table["buckets_lexmapr"] = get_resource_dict("buckets-lexmapr.csv")
    # Buckets made with IFSAC in mind, and their corresponding ontology
    # IDs.
    classification_lookup_table["buckets_ifsactop"] = get_resource_dict("buckets-ifsactop.csv")
    # Ontology IDs for buckets made with IFSAC in mind, and their
    # corresponding IFSAC labels.
    classification_lookup_table["ifsac_labels"] = get_resource_dict("ifsac-labels.csv")
    # Better maps for certain terms, with IFSAC in mind?
    classification_lookup_table["ifsac_refinement"] = get_resource_dict("ifsac-refinement.csv")
    # ???
    classification_lookup_table["ifsac_default"] = get_resource_dict("ifsac-default.csv")

    return classification_lookup_table


def classify_sample(sample, matched_terms_with_ids, lookup_table, classification_lookup_table):
    """TODO..."""

    # Attempt to find a classification using ifsac_default
    default_classification = ""
    for bucket, ifsac_label in classification_lookup_table["ifsac_default"].items():
        if bucket in sample:
            default_classification = ifsac_label
            break

    if matched_terms_with_ids:
        for matched_term_with_id in matched_terms_with_ids:
            [_, term_id] = matched_term_with_id.split(":", 1)
            matched_term_hierarchy = get_term_parent_hierarchy(term_id, lookup_table)
            pass

    # Stub
    return False
