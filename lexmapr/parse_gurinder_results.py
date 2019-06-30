import csv
import re

gurinder_parsed_results = {}

with open("gurinder_unparsed_results.tsv", "r") as fp:
    reader = csv.reader(fp, delimiter="\t")
    next(reader)
    for row in reader:
        gurinder_parsed_results[row[0]] = {
            "sample_desc": row[1],
            "buckets": "[" + row[-2].lower() + "]",
            "result": "[" + row[-1].lower() + "]"
        }
        if gurinder_parsed_results[row[0]]["buckets"] == "[fault classification]":
            gurinder_parsed_results[row[0]]["buckets"] = "[default classification]"
        gurinder_parsed_results[row[0]]["buckets"] = \
            re.sub(r",\s*\d*\s*:\s*", ", ", gurinder_parsed_results[row[0]]["buckets"])
        gurinder_parsed_results[row[0]]["buckets"] = \
            re.sub(r"\[\s*\d*\s*:\s*", "[", gurinder_parsed_results[row[0]]["buckets"])
        for i in range(len(row)):
            if "[" in row[i] or "{" in row[i]:
                matched_components = row[i]
                matched_components = matched_components.replace("'", "")
                matched_components = matched_components.replace("{", "[")
                matched_components = matched_components.replace("}", "]")
                matched_components = matched_components.lower()
                gurinder_parsed_results[row[0]]["matched_components"] = matched_components
                break
        continue

with open("gurinder_parsed_results.tsv", "w") as fp:
    fp.write("Sample_Id\tSample_Desc\tMatched_Components\tThird Party Classification"
             "\tThird Party Bucket\n")
    for key, value in gurinder_parsed_results.items():
        if len(value) <= 3:
            continue
        fp.write(key + "\t" + value["sample_desc"] + "\t" + value["matched_components"] + "\t"
                 + value["result"] + "\t" + value["buckets"] + "\n")
