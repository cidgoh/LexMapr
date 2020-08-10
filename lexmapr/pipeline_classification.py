"""3rd-party classification functions using ontology-based buckets."""

from inflection import singularize
from nltk import word_tokenize
import re

import lexmapr.pipeline_helpers as helpers


def customize_order_of_labels(ifsac_final_labels):
    """Get the final labels in a customized order.

    :param set ifsac_final_labels: the final labels set to be ordered
    :return: returned list of labels in cutomized order
    :rtype: list
    """

    ret = set(ifsac_final_labels)
    priority_listing_categories = {"multi-ingredient", "veterinary clinical/research",
                                   "environmental", "environmental-water", "environmental-farm",
                                   "environmental-restaurant", "environmental-retail",
                                   "environmental-abattoir", "environmental-warehouse",
                                   "environmental-researchfacility",
                                   "environmental-pasture", "environmental-animal housing",
                                   "environmental-factory/production facility",
                                   "environmental-vehicle", "environmental-construction"}

    revised_final_labels_list = []
    ifsac_final_labels_list = list(ifsac_final_labels)
    if ret.intersection(priority_listing_categories):
        priority_category = (ret.intersection(priority_listing_categories)).pop()
        revised_final_labels_list.insert(0, str(priority_category))
        ifsac_final_labels_list.remove(str(priority_category))
    for item in sorted(ifsac_final_labels_list):
        revised_final_labels_list.append(item)

    return revised_final_labels_list


def decode_multi_class_labels(ifsac_final_labels):
    """Decodes the multi class label values in bucket labels.

    :param set ifsac_final_labels: the final labels set to be decoded
    :return: returned list of labels after decoding
    :rtype: list
    """

    revised_final_labels = set()
    for label in ifsac_final_labels:
        if ";" in label:
            multi_labels = label.split(";")
            for multi_label in multi_labels:
                revised_final_labels.add(multi_label)
        else:
            revised_final_labels.add(label)
    revised_final_labels_list = list(revised_final_labels)
    return revised_final_labels_list


def refine_ifsac_final_labels(sample, ifsac_final_labels,
                              label_refinements):
    """Gets refined final labels after application of customized rules.

    :param str sample: sample
    :param set ifsac_final_labels: the final labels set
    :param dict label_refinements: the dictionary of label refinement 
        resource
    :return set of refined final labels
    :rtype: set
    """

    # Caution: Rules are sequential - changing the order might change 
    # results.
    ret = set(ifsac_final_labels)
    sample = helpers.punctuation_treatment(sample)
    sample_tokens = word_tokenize(sample)
    sample_tokens_set = set(sample_tokens)

    for label, refined_label in label_refinements.items():
        label_tokens = word_tokenize(label)
        if not (set(label_tokens) - set(sample_tokens)) or re.search(r"\b"+label+r"\b", sample):
            ret.add(refined_label)
            break

    # Defines different groups/ categories of classes
    specific_meat_categories = {"pork", "chicken", "beef", "fish", "game", "poultry", "turkey"}
    mollusk_categories = {"mollusks (non-bi-valve)", "mollusks (bi-valve)"}
    shellfish_categories = {"crustaceans", "mollusks"} | mollusk_categories
    aquatic_animal_categories = {"fish", "other aquatic animals"} | shellfish_categories
    poultry_categories = {"other poultry", "chicken", "turkey"}
    avian_categories = {"other poultry", "game", "poultry"} | poultry_categories
    animal_categories = {"human",  "companion animal", "aquatic animals", "wild animal",
                         "beef", "pork", "other meat", "cow", "pig"}
    animal_categories |= avian_categories | aquatic_animal_categories | {"other animal"}
    veterinary_categories = avian_categories | aquatic_animal_categories | {"other animal"}
    veterinary_categories |= {"animal", "avian", "companion animal", "aquatic animals", 
                              "wild animal", "beef", "pork", "other meat", "cow", "pig"}
    environmental_categories = {"environmental-water", "environmental-farm",
                                "environmental-restaurant", "environmental-retail",
                                "environmental-abattoir", "environmental-warehouse",
                                "environmental-researchfacility",
                                "environmental-pasture", "environmental-animal housing",
                                "environmental-factory/production facility",
                                "environmental-vehicle", "environmental-construction"}
    root_underground_categories = {"root/underground (roots)", "root/underground (tubers)",
                                   "root/underground (bulbs)", "root/underground (other)"}
    seeded_vegetable_categories = {"seeded vegetables (vine-grown)",
                                   "seeded vegetables (solanaceous)", 
                                   "seeded vegetables (legumes)",
                                   "seeded vegetables (other)"}
    vegetable_categories = {"fungi", "sprouts", "root/underground", "seeded vegetables", "herbs",
                            "vegetable row crops (flower)", "vegetable row crops (stem)",
                            "vegetable row crops (leafy)"}
    vegetable_categories |= root_underground_categories | seeded_vegetable_categories
    fruit_categories = {"melon fruit", "pome fruit", "stone fruit", "sub-tropical fruit",
                        "small fruit", "tropical fruit"}
    plant_categories = {"oils", "vegetables", "fruits", "grains", "beans", "nuts",
                        "seeds"}
    plant_categories |= vegetable_categories | fruit_categories
    other_plant_food_category = {"other (food additive)", "dietary supplement", 
                                 "other (sweetener)", "other (flavoring and seasoning", 
                                 "other (confectionary)"}
    other_animal_food_category = {"meat", "other meat", "beef", "pork"}

    # Customized rules for refinement of class labels
    # Deals with "animal feed" class
    if "animal feed" in ret and "by" in sample and "by product" not in sample:
        ret.remove("animal feed")

    # Deals with "clinical/research" class
    if "clinical/research" in ret \
            and ret.intersection(plant_categories | other_plant_food_category) \
            and not ("swab" in sample or "clinical" in sample):
        ret.remove("clinical/research")
    if "clinical/research" in ret and "swab sub" in sample:
        ret.clear()
        ret.add("environmental")
    if "clinical/research" in ret and "scat" in sample:
        ret.remove("clinical/research")
        ret.add("environmental")
    if "clinical/research" in ret and "environmental" in ret \
            and not ("tissue" in sample or "biological" in sample):
        ret.remove("clinical/research")
    if "clinical/research" in ret and ret.intersection(environmental_categories):
        ret.remove("clinical/research")
    if "clinical/research" in ret and (ret.intersection(plant_categories)
                                       or ret.intersection(animal_categories)):
        if "shell" in sample or "shell on" in sample or "shellon" in sample:
            ret.remove("clinical/research")
    if "clinical/research" in ret and ret.intersection(veterinary_categories):
        ret.remove("clinical/research")
        ret.add("veterinary clinical/research")
    if "veterinary clinical/research" in ret and "animal" in ret:
        ret.remove("animal")

    # Converts animal not defined to other animal, if not general 
    # animal class.
    if "animal" in ret and sample != "animal":
        ret.remove("animal")
        ret.add("other animal")

    # Deals with "dairy", "cow" and "beef" cases
    if "dairy" in ret and "cow" in ret:
        ret.remove("cow")
    if "beef" in ret and "dairy" in ret and "milk" in sample:
        ret.remove("beef")
    beef_keywords = ["raw cow", "raw veal", "raw calf", "meat", "beef",
                     "cow lung", "cow liver", "cow heart"]
    for entry in beef_keywords:
        if entry in sample and "cow" in ret:
            ret.remove("cow")
            ret.add("beef")
    pork_keywords = ["raw pig", "raw swine", "meat", "pork", "porcine"]
    for entry in pork_keywords:
        if entry in sample and "pig" in ret:
            ret.remove("pig")
            ret.add("pork")
    if "cow" in ret and "beef" in ret:
        ret.remove("cow")
    if "beef" in ret and "fish" in ret and ("fillet" in sample or "filet" in sample):
        ret.remove("beef")
    if "beef" in ret and ("veterinary clinical/research" in ret):
        ret.remove("beef")
        ret.add("cow")
    if "oils" in ret and "in oil" in sample:
        ret.remove("oils")
    if "other (sweetener)" in ret and "sugar free" in sample:
        ret.remove("other (sweetener)")

    # Deals with "fish", "shellfish" and "eggs" cases
    if "shellfish" in ret and "fish" in ret:
        ret.remove("fish")
    if "fish" in ret and "eggs" in ret:
        ret.remove("eggs")
    if "fish eggs" in ret and "eggs" in ret:
        ret.remove("fish eggs")
    if "fish" in ret and "poultry" in ret:
        ret.remove("poultry")
    if "fish" in ret and "other poultry" in ret:
        ret.remove("other poultry")
    if "poultry" in ret and "eggs" in ret:
        ret.remove("poultry")

    # Deals with "pig", "pork" and "meat" cases
    if ("pork" in ret or "pork" in sample) and ("pig" in ret):
        ret.remove("pig")
        ret.add("pork")
    if ("pork" in ret or "pork" in sample) and ("meat" in ret):
        ret.remove("meat")
        ret.add("pork")
    if "pork" in ret and "veterinary clinical/research" in ret:
        ret.remove("pork")
        ret.add("pig")
    if "meat" in ret and ("veterinary clinical/research" in ret or "engineering  seafood" in ret):
        ret.remove("meat")
    if ret.intersection(specific_meat_categories) and "meat" in ret:
        ret.remove("meat")

    # Deals with cases when clinical/research is there and meats are 
    # there.
    if not ret.intersection(animal_categories) and "other meat" in ret \
            and ("veterinary clinical/research" in ret or "clinical/research" in ret):
        ret.remove("other meat")
        ret.add("other animal")
    if not ret.intersection(animal_categories) and "meat" in ret \
            and ("veterinary clinical/research" in ret or "clinical/research" in ret):
        ret.remove("meat")
        if "liver" not in sample:
            ret.add("other animal")
    if not ret.intersection(animal_categories) and ("veterinary clinical/research" in ret):
        ret.add("other animal")

    # Retains the specific (more granular) animal classes
    if "mollusks" in ret and ret.intersection(mollusk_categories):
        ret.remove("mollusks")
    if "shellfish" in ret and ret.intersection(shellfish_categories):
        ret.remove("shellfish")
    if "aquatic animals" in ret and ret.intersection(aquatic_animal_categories):
        ret.remove("aquatic animals")
    if "poultry" in ret and ret.intersection(poultry_categories):
        ret.remove("poultry")
    if "other animal" in ret and ret.intersection(avian_categories):
        ret.remove("other animal")
    if "animal" in ret and ret.intersection(animal_categories):
        ret.remove("animal")
    if "engineered seafood" in ret and ret.intersection(aquatic_animal_categories):
        ret = ret - ret.intersection(aquatic_animal_categories)
    if "engineered seafood" in ret and "aquatic animals" in ret:
        ret.remove("aquatic animals")
    if ("engineered seafood" in ret or "companion animal" in ret) and "other animal" in ret:
        ret.remove("other animal")

    # Retains the specific (more granular) plant classes
    if "root/underground" in ret and ret.intersection(root_underground_categories):
        ret.remove("root/underground")
    if "seeded vegetables" in ret and ret.intersection(seeded_vegetable_categories):
        ret.remove("seeded vegetables")
    if "vegetables" in ret and ret.intersection(vegetable_categories):
        ret.remove("vegetables")
    if "fruits" in ret and ret.intersection(fruit_categories):
        ret.remove("fruits")
    if "plant" in ret and ret.intersection(plant_categories):
        ret.remove("plant")

    # Deals with "nut", and "seeds", and "environment-water" and "fish" 
    # case.
    if "nut" in ret and "seeds" in ret and len(ret) == 2:
        ret.remove("seeds")
    if "environment-water" in ret and "fish" in ret and len(ret) == 2:
        ret.remove("environment-water")

    # Retains the specific (more granular) environmental classes
    if "environmental" in ret and ret.intersection(environmental_categories):
        ret.remove("environmental")
    if ("environmental-animal housing" in ret or "environmental-abattoir" in ret
            or "environmental-farm" in ret) \
            and "environmental-factory/production facility" in ret:
        ret.remove("environmental-factory/production facility")
    if "environmental-abattoir" in ret and "environmental-factory/production facility" in ret:
        ret.remove("environmental-factory/production facility")
    exclusions = {
        'clinical/research', 'veterinary clinical/research', 'animal feed', 'human',
        'environmental'
    }

    # Assigns multi-ingredient to the cases where multiple food 
    # ingredients have been tagged.
    if not (ret.intersection(exclusions) or ret.intersection(environmental_categories)) \
            and len(ret) >= 3:
        ret.add("multi-ingredient")   # To be revisted and revised as per evaluation

    # Deals with some specific cases
    if "other meat" in ret and "other animal" in ret:
        ret.remove("other animal")
    if "meat" in ret and ret.intersection(animal_categories):
        if len(ret) == 3 and "multi-ingredient" in ret:
            ret.remove("multi-ingredient")
            ret.remove("meat")
        else:
            ret.remove("meat")

    # Retains the specific (more granular) classes and removing the 
    # general "food" class.
    if "food" in ret and ret.intersection(animal_categories | plant_categories 
                                          | other_animal_food_category | other_plant_food_category 
                                          | {"plant", "animal"}):
        ret.remove("food")
    if "food" in ret and ("dairy" in ret or "environmental" in ret or "clinical/research" in ret 
                          or "veterinary clinical/research" in ret):
        ret.remove("food")

    # Deals with addtional/unique cases
    if "food" in ret and "environmental" in ret and "leaf" in sample:
        ret.remove("environmental")
    if "environmental-animal housing" in ret and "finished" in sample:
        ret.remove("environmental-animal housing")
    if ("chicken" in ret or "poultry" in ret or "other poultry" in ret or "cow" in ret) \
            and "environmental-factory/production facility" in ret:
        ret.remove("environmental-factory/production facility")
        ret.add("environmental-farm")
    if "eggs" in ret and "veterinary clinical/research" in ret:
        ret.remove("veterinary clinical/research")
    if "environmental" in ret \
            and ("multi-ingredient" in ret or ret.intersection(plant_categories)) \
            and not ("swab" in sample or "environmental" in sample):
        ret.remove("environmental")

    # Deals with body parts that are food for specific animal 
    # categories and not clinical/research.
    food_anatomical_parts = {'heart', 'liver', 'lung', 'leg', 'shell-on', 'shell', 'soft shell',
                             'tail', 'hlso', 'shellon', 'beef', 'pork', 'meat', 'porcine',
                             'shell on'}
    body_part_for_food_animal_categories = \
        aquatic_animal_categories | shellfish_categories | poultry_categories | {"cow"}
    if "veterinary clinical/research" in ret \
            and ret.intersection(body_part_for_food_animal_categories) \
            and sample_tokens_set.intersection(food_anatomical_parts) and "swab" not in sample:
        ret.remove("veterinary clinical/research")

    # Deals with very specific disambiguation tokens
    disambiguation_words = {'ground', 'scraps', 'cut', 'smoke', 'moon', 'plain'}
    if "environmental" in ret \
            and (ret.intersection(animal_categories) or ret.intersection(plant_categories) 
                 or "dairy" in ret) \
            and sample_tokens_set.intersection(disambiguation_words):
        ret.remove("environmental")

    # Retains the general class (only animal feed)
    if "animal feed" in ret:
        ret.clear()
        ret.add("animal feed")

    # Deals with multi-ingredient case
    if ("multi-ingredient" in ret or "food supplement" in ret) and "food" in ret:
        ret.remove("food")
    if "food" in ret and len(ret) < 2:
        ret.remove("food")
        ret.add("multi-ingredient")

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
            matched_term_hierarchies = helpers.get_term_parent_hierarchies(term_id, lookup_table)

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

    if ifsac_final_labels:
        ifsac_final_labels = sorted(decode_multi_class_labels(ifsac_final_labels))

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
    ifsac_final_labels = customize_order_of_labels(ifsac_final_labels)

    return {
        "lexmapr_hierarchy_buckets": lexmapr_hierarchy_buckets,
        "lexmapr_final_buckets": lexmapr_final_buckets,
        "ifsac_final_buckets": ifsac_final_buckets,
        "ifsac_final_labels": ifsac_final_labels
    }
