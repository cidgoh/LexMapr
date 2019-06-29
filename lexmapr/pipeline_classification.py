"""Functions used for bucket classification."""

from inflection import singularize

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
    sample_tokens = list(map(lambda token: singularize(token), sample_tokens))
    for label, refined_label in label_refinements.items():
        label_tokens = word_tokenize(label)
        label_tokens = list(map(lambda token: singularize(token), label_tokens))
        if not (set(label_tokens) - set(sample_tokens)):
            ret.add(refined_label)
            break

    if "equipment" in ret or "structure" in ret:
        ret.add("environmental")
    if "dairy" in ret and "cow" in ret:
        ret.remove("cow")
    if "beef" in ret and "dairy" in ret and "milk" in sample:
        ret.remove("beef")
    if "beef" in ret and ("cow" in ret or "calf" in ret):
        ret.remove("beef")
    if ("shellfish" in ret or "siluriformes" in ret) and "fish" in ret:
        ret.remove("fish")
    if "environmental" in ret and ("feces" in sample or "fecal" in sample or "stool" in sample):
        ret.remove("environmental")
        ret.add("clinical/research")  # "clinical-fecal"
    if "environmental-animal housing" in ret and "finished" in sample:
        ret.remove("environmental-animal housing")

    if "herbs" in ret and "organism" in ret:
        ret.remove("organism")
    if "animal" in ret and ("homo sapiens" in sample or "human" in sample):
        ret.remove("organism")
        ret.add("human")

    if "clinical/research" in ret and "environmental" in ret and "biological" in sample:
        ret.remove("environmental")

    # # #

    if "pig" in ret and "meat" in ret:
        ret.remove("pig")
        ret.add("pork")
    if "cow" in ret and "meat" in ret:
        ret.remove("cow")
        ret.add("beef")
    if "other animal" in ret and "meat" in ret:
        ret.remove("other animal")
        ret.add("other meat")

    if "beef" in ret and "cow" in ret:
        ret.remove("beef")
    if "pork" in ret and "pig" in ret:
        ret.remove("pork")
    if "other meat" in ret and "other animal" in ret:
        ret.remove("other meat")

    if "pork" in ret and "clinical/research" in ret:
        ret.remove("pork")
        ret.add("pig")
    if "beef" in ret and ("clinical/research" in ret or "dairy" in ret):
        ret.remove("beef")
        ret.add("cow")
    if "other meat" in ret and "clinical/research" in ret:
        ret.remove("other meat")
        ret.add("other animal")
    if "meat" in ret and "clinical/research" in ret:
        ret.remove("meat")

    animal_categories = {"human", "fish", "chicken", "turkey", "crustaceans", "pig", "sheep", "cow",
                         "avian", "companion animal", "shellfish", "mollusks (non-bi-valve)",
                         "mollusks (bi-valve)", "aquatic animals", "other aquatic animals",
                         "wild animal", "other poultry", "poultry", "pork", "beef", "other meat"}
    if "animal" in ret and ret.intersection(animal_categories):
        ret.remove("animal")
    if "meat" in ret and ret.intersection(animal_categories):
        ret.remove("meat")

    avian_categories = {"poultry", "other poultry", "chicken", "turkey", "game"}
    if "avian" in ret and ret.intersection(avian_categories):
        ret.remove("avian")

    poultry_categories = {"other poultry", "chicken", "turkey"}
    if "poultry" in ret and ret.intersection(poultry_categories):
        ret.remove("poultry")

    environmental_categories = {"environmental-water", "environmental-farm",
                                "environmental-restaurant", "environmental-store",
                                "environmental-abbatoir", "environmental-warehouse",
                                "environmental-factory", "environmental-researchfacility",
                                "environmental-pasture",
                                "environmental-factory/production facility/abattoir",
                                "environmental-vehicle"}
    if "environmental" in ret and ret.intersection(environmental_categories):
        ret.remove("environmental")

    plant_categories = {"vegetables", "fungi", "sprouts", "root/underground",
                        "root/underground (roots)", "root/underground (tubers)",
                        "root/underground (bulbs)", "root/underground (other)",
                        "seeded vegetables", "seeded vegetables (vine-grown)",
                        "seeded vegetables (solanaceous)", "seeded vegetables (legumes)",
                        "seeded vegetables (other)", "herbs", "vegetable row crops (flower)",
                        "vegetable row crops (stem)", "vegetable row crops (leafy)", "fruits",
                        "melon fruit", "pome fruit", "stone fruit", "small fruit", "tropical fruit",
                        "sub-tropical fruit", "grains", "beans", "nuts", "seeds"}
    if "plant" in ret and ret.intersection(plant_categories):
        ret.remove("plant")

    fruit_categories = {"melon fruit", "pome fruit", "stone fruit", "sub-tropical fruit",
                        "small fruit", "tropical fruit"}
    if "fruits" in ret and ret.intersection(fruit_categories):
        ret.remove("fruits")

    if "animal feed" in ret:
        ret.clear()
        ret.add("animal feed")
    if "multi-ingredient" in ret:
        ret.clear()
        ret.add("multi-ingredient")

    if "food" in ret:
        ret.remove("food")
    if "organism" in ret:
        ret.remove("organism")

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
                    if lexmapr_final_bucket not in lexmapr_final_buckets:
                        lexmapr_final_buckets.append(lexmapr_final_bucket)

                ifsac_hierarchy_bucket = \
                    classify_sample_helper(matched_term_hierarchy,
                                           classification_lookup_table["buckets_ifsactop"])

                if ifsac_hierarchy_bucket:
                    ifsac_hierarchy_buckets.append(ifsac_hierarchy_bucket)

                    ifsac_final_bucket_level = min(ifsac_hierarchy_bucket.keys())
                    ifsac_final_bucket = \
                        ifsac_hierarchy_bucket[ifsac_final_bucket_level]
                    if ifsac_final_bucket not in ifsac_final_buckets:
                        ifsac_final_buckets.append(ifsac_final_bucket)

                        # ``ifsac_final_bucket`` has is a one-item
                        # dictionary of the following format:
                        # ``{bucket_id:bucket_label}``.
                        ifsac_final_bucket_id = list(ifsac_final_bucket.keys())[0]

                        ifsac_final_label = \
                            classification_lookup_table["ifsac_labels"][ifsac_final_bucket_id]
                        ifsac_final_labels.append(ifsac_final_label)

        if not ifsac_final_labels or set(ifsac_final_labels) == {"food"}:
            # Attempt to find a classification using ifsac_default
            default_classification = ""
            sample_tokens = word_tokenize(sample)
            sample_tokens = list(map(lambda token: singularize(token), sample_tokens))
            for bucket, label in classification_lookup_table["ifsac_default"].items():
                bucket_tokens = word_tokenize(bucket)
                bucket_tokens = list(map(lambda token: singularize(token), bucket_tokens))
                if not (set(bucket_tokens) - set(sample_tokens)):
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
