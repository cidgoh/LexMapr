"""Functions used for bucket classification."""

import os
import sys

from inflection import singularize
from nltk import word_tokenize

from lexmapr.definitions import ROOT
from lexmapr.ontobucket import OntologyBuckets
from lexmapr.pipeline_helpers import get_term_parent_hierarchies


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
    if "shellfish" in ret and "fish" in ret:
        ret.remove("fish")
    if "environmental" in ret and ("feces" in sample or "fecal" in sample or "stool" in sample):
        ret.remove("environmental")
        ret.add("clinical/research")  # "clinical-fecal"
    if "environmental-animal housing" in ret and "finished" in sample:
        ret.remove("environmental-animal housing")

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

    mollusk_categories = {"mollusks (non-bi-valve)", "mollusks (bi-valve)"}
    shellfish_categories = {"crustaceans", "mollusks"} | mollusk_categories
    aquatic_animal_categories = {"fish", "other aquatic animals"} | shellfish_categories

    poultry_categories = {"other poultry", "chicken", "turkey"}
    avian_categories = {"game", "poultry"} | poultry_categories

    animal_categories = {"human", "avian", "companion animal", "aquatic animals", "wild animal",
                         "beef", "pork", "other meat", "cow", "pig", "other animal"}
    animal_categories |= avian_categories | aquatic_animal_categories

    if "mollusks" in ret and ret.intersection(mollusk_categories):
        ret.remove("mollusks")
    if "shellfish" in ret and ret.intersection(shellfish_categories):
        ret.remove("shellfish")
    if "aquatic animals" in ret and ret.intersection(aquatic_animal_categories):
        ret.remove("aquatic animals")
    if "poultry" in ret and ret.intersection(poultry_categories):
        ret.remove("poultry")
    if "avian" in ret and ret.intersection(avian_categories):
        ret.remove("avian")
    if "animal" in ret and ret.intersection(animal_categories):
        ret.remove("animal")
    if "meat" in ret and ret.intersection(animal_categories):
        ret.remove("meat")

    environmental_categories = {"environmental-water", "environmental-farm",
                                "environmental-restaurant", "environmental-store",
                                "environmental-abbatoir", "environmental-warehouse",
                                "environmental-factory", "environmental-researchfacility",
                                "environmental-pasture", "environmental-animal housing",
                                "environmental-factory/production facility/abattoir",
                                "environmental-vehicle", "environmental-construction"}
    if "environmental" in ret and ret.intersection(environmental_categories):
        ret.remove("environmental")

    root_underground_categories = {"root/underground (roots)", "root/underground (tubers)",
                                   "root/underground (bulbs)", "root/underground (other)"}
    seeded_vegetable_categories = {"seeded vegetables (vine-grown)",
                                   "seeded vegetables (solanaceous)", "seeded vegetables (legumes)",
                                   "seeded vegetables (other)"}
    vegetable_categories = {"fungi", "sprouts", "root/underground", "seeded vegetables", "herbs",
                            "vegetable row crops (flower)", "vegetable row crops (stem)",
                            "vegetable row crops (leafy)"}
    vegetable_categories |= root_underground_categories | seeded_vegetable_categories

    fruit_categories = {"melon fruit", "pome fruit", "stone fruit", "sub-tropical fruit",
                        "small fruit", "tropical fruit"}

    plant_categories = {"oils", "sugars", "vegetables", "fruits", "grains", "beans", "nuts",
                        "seeds"}
    plant_categories |= vegetable_categories | fruit_categories

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

    if "food" in ret and ret.intersection(animal_categories | plant_categories | {"meat"}):
            ret.remove("food")

    if "animal feed" in ret:
        ret.clear()
        ret.add("animal feed")
    if "multi-ingredient" in ret:
        ret.clear()
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


def classify_term(matched_component, scheme, lookup_table):
    """TODO: document function"""
    ret = []
    matched_component_id = matched_component.split(":")[1].upper().replace("_", ":")
    lexmapr_ontology_path = os.path.join(ROOT, "resources", "classification", "lexmapr.owl")

    if scheme == "narms":
        root = "http://genepio.org/ontology/LEXMAPR_0000001"
    scheme_dir_path = os.path.join(ROOT, "resources", "classification", scheme)


    ontobucket = OntologyBuckets()
    sys.argv = ["", lexmapr_ontology_path, "-o", scheme_dir_path + "/", "-r", root, "-c", "-i", matched_component_id]
    ret += [lookup_table["bucket_labels"][x] for x in ontobucket.__main__()]

    return ret
