"""Functions used for bucket classification."""

from lexmapr.pipeline_helpers import get_resource_dict, get_term_parent_hierarchies, word_tokenize


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
    # Buckets made with IFSAC in mind
    classification_lookup_table["buckets_ifsactop"] = get_resource_dict("buckets-ifsactop.csv")
    # IFSAC labels corresponding to IFSAC buckets
    classification_lookup_table["ifsac_labels"] = get_resource_dict("ifsac-labels.csv")

    # Default labels to consider with IFSAC in mind
    classification_lookup_table["ifsac_default"] = get_resource_dict("ifsac-default.csv")
    classification_lookup_table["ifsac_refinement"] = get_resource_dict("ifsac-refinement.csv")

    return classification_lookup_table


def refine_ifsac_final_labels(sample, ifsac_final_labels, label_refinements):
    """TODO..."""
    ret = set(ifsac_final_labels)

    sample_tokens = word_tokenize(sample)
    for label, refined_label in label_refinements.items():
        if label in sample_tokens:
            ret.add(refined_label)
            break

    if "equipment" in ret or "structure" in ret:
        ret.add("environmental")
    if "poultry" in ret and ("other poultry" in ret or "chicken" in ret):
        ret.remove("poultry")
    if "dairy" in ret and "cow" in ret and not "milk" in sample:
        ret.remove("dairy")
    if "beef" in ret and "dairy" in ret and "milk" in sample:
        ret.remove("beef")
    if "dairy" in ret and ("calf" in ret or "environmental-farm" in ret):
        ret.remove("dairy")
    if "beef" in ret and ("cow" in ret or "calf" in ret):
        ret.remove("beef")
    if "meat" in ret and ("chicken" in ret or "crustaceans" in ret or "pork" in ret or "beef" in ret
                          or "fish" in ret):
        ret.remove("meat")
    if ("shellfish" in ret or "siluriformes" in ret) and "fish" in ret:
        ret.remove("fish")
    if "poultry" in ret and "chicken" in sample:
        ret.remove("poultry")
        ret.add("chicken")
    if "environmental" in ret and ("environmental-water" in ret
                                   or "environmental-factory/production facility/abattoir" in ret):
        ret.remove("environmental")
    if "environmental" in ret and ("feces" in sample or "fecal" in sample or "stool" in sample):
        ret.remove("environmental")
        ret.add("clinical/research")  # "clinical-fecal"
    if "environmental-animal housing" in ret and "finished" in sample:
        ret.remove("environmental-animal housing")
    if "pork" in ret and "clinical/research" in ret:
        ret.remove("pork")
        ret.add("pig")
    if "clinical/research" in ret and ("environmental" in ret or "environmental-water" in ret
                                       or "environmental-factory/production facility/abattoir"
                                       in ret):
        ret.remove("clinical/research")

    if "herbs" in ret and "organism" in ret:
        ret.remove("organism")
    if "organism" in ret and ("homo sapiens" in sample or "human" in sample):
        ret.remove("organism")
        ret.add("human")

    if ("other poultry" in ret or "game" in ret ) and "avian" in ret:
        ret.remove("avian")
    if "poultry" in ret and "avian" in ret:
        ret.remove("poultry")
    if ("human" in ret or "cattle" in ret or "crustaceans" in ret or "pig" in ret or "sheep" in ret
        or "calf" in ret or "fish" in ret or "chicken" in ret or "beef" in ret or "pork" in ret
        or "turkey" in ret or "calf" in ret or "cow" in ret or "pig" in ret):
        if "organism" in ret:
            ret.remove("organism")
        if "poultry" in ret:
            ret.remove("poultry")
        if "other poultry" in ret:
            ret.remove("other poultry")
        if "avian" in ret:
            ret.remove("avian")

    if "clinical/research" in ret and "organism" in ret and not ("human" in ret or "fish" in ret
                                                                 or "chicken" in ret or "beef"
                                                                 in ret or "pork" in ret or "turkey"
                                                                 in ret or "crustaceans" in ret
                                                                 or "calf" in ret or "pig" in ret
                                                                 or "cattle" in ret or "sheep"
                                                                 in ret or "cow" in ret):
        ret.clear()
        ret.add("animal")
        ret.add("clinical/research")
    if "clinical/research" in ret and "environmental" in ret and "biological" in sample:
        ret.remove("environmental")

    if "beef" in ret and not "liver" in sample and ("clinical/research" in ret or "environmental"
                                                    in ret or "dairy" in ret):
        ret.remove("beef")
        ret.add("cow")

    if "clinical/research" in ret and "liver" in sample and len(ret) > 1:
        ret.remove("clinical/research")
    if "cow" in ret and "calf" in ret:
        ret.remove("cow")
    if "calf" in ret:
        ret.remove("calf")
        ret.add("cattle")

    if "pig" in ret and "liver" in sample:
        ret.remove("pig")
        ret.add("pork")
    if "cow" in ret and "liver" in sample:
        ret.remove("cow")
        ret.add("beef")

    # Should be checked at the end
    if "animal feed" in ret:
        ret.clear()
        ret.add("animal feed")
    if "multi ingredient" in ret:
        ret.clear()
        ret.add("multi ingredient")

    return list(ret)


def classify_sample_helper(sample_hierarchy, buckets):
    """TODO..."""
    sample_hierarchy_classification = {}

    for i in range(len(sample_hierarchy)):
        parent_id = sample_hierarchy[i]
        # 1-based indexing of parent hierarchy
        parent_level = i+1

        for bucket_label, bucket_id in buckets.items():
            if bucket_id == parent_id:
                sample_hierarchy_classification[parent_level] = {bucket_id: bucket_label}

    return sample_hierarchy_classification


def classify_sample(sample, matched_terms_with_ids, lookup_table, classification_lookup_table):
    """TODO..."""

    # LexMapr and IFSAC buckets mapped to the parental hierarchies of
    # each element in ``matched_term_with_ids``.
    lexmapr_hierarchy_buckets = []
    ifsac_hierarchy_buckets = []
    # Lowest-level mapping for each element in ``matched_terms_with_ids``.
    lexmapr_final_buckets = []
    ifsac_final_buckets = []
    # IFSAC labels corresponding to the buckets in
    # ``ifsac_final_buckets``.
    ifsac_final_labels = []

    if matched_terms_with_ids:
        for matched_term_with_id in matched_terms_with_ids:
            [_, term_id] = matched_term_with_id.split(":", 1)
            matched_term_hierarchies = get_term_parent_hierarchies(term_id, lookup_table)

            for matched_term_hierarchy in matched_term_hierarchies:
                lexmapr_hierarchy_bucket = \
                    classify_sample_helper(matched_term_hierarchy,
                                           classification_lookup_table["buckets_lexmapr"])

                if lexmapr_hierarchy_bucket:
                    lexmapr_hierarchy_buckets.append(lexmapr_hierarchy_bucket)

                    lexmapr_final_bucket_level = min(lexmapr_hierarchy_bucket.keys())
                    lexmapr_final_bucket = lexmapr_hierarchy_bucket[lexmapr_final_bucket_level]
                    lexmapr_final_buckets.append(lexmapr_final_bucket)

                ifsac_hierarchy_bucket = \
                    classify_sample_helper(matched_term_hierarchy,
                                           classification_lookup_table["buckets_ifsactop"])

                if ifsac_hierarchy_bucket:
                    ifsac_hierarchy_buckets.append(ifsac_hierarchy_bucket)

                    ifsac_final_bucket_level = min(ifsac_hierarchy_bucket.keys())
                    ifsac_final_bucket = \
                        ifsac_hierarchy_bucket[ifsac_final_bucket_level]
                    ifsac_final_buckets.append(ifsac_final_bucket)

                    # ``ifsac_final_bucket`` has is a one-item
                    # dictionary of the following format:
                    # ``{bucket_id:bucket_label}``.
                    ifsac_final_bucket_id = list(ifsac_final_bucket.keys())[0]

                    ifsac_final_label = \
                        classification_lookup_table["ifsac_labels"][ifsac_final_bucket_id]
                    ifsac_final_labels.append(ifsac_final_label)

        if not ifsac_final_buckets:
            # Attempt to find a classification using ifsac_default
            default_classification = ""
            for bucket, label in classification_lookup_table["ifsac_default"].items():
                if bucket in sample:
                    default_classification = label

            if default_classification:
                ifsac_final_buckets.append("Default classification")
                ifsac_final_labels.append(default_classification)

        ifsac_final_labels = \
            refine_ifsac_final_labels(sample, ifsac_final_labels,
                                      classification_lookup_table["ifsac_refinement"])

    return {
        "lexmapr_hierarchy_buckets": lexmapr_hierarchy_buckets,
        "lexmapr_final_buckets": lexmapr_final_buckets,
        "ifsac_final_buckets": ifsac_final_buckets,
        "ifsac_final_labels": ifsac_final_labels
    }
