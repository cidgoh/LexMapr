# LexMapr
A Lexicon and Rule-Based Tool for Translating Short Biomedical Specimen Descriptions into Semantic Web Ontology Terms

## Build status

[![Build Status](https://travis-ci.org/lexmapr/LexMapr.svg?branch=master)](https://travis-ci.org/lexmapr/LexMapr)
[![Coverage Status](https://coveralls.io/repos/github/lexmapr/LexMapr/badge.svg?branch=master)](https://coveralls.io/github/lexmapr/LexMapr?branch=master)
[![bioconda-badge](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg?style=flat-square)](http://bioconda.github.io)

The main script file for processing is `bin/lexmapr`

## Dependencies

- [nltk](https://pypi.org/project/nltk/)
- [inflection](https://pypi.org/project/inflection/)
- [wikipedia](https://pypi.org/project/wikipedia/)
- [python-dateutil](https://pypi.org/project/python-dateutil/)
- [rdflib](https://pypi.org/project/rdflib/)
- [rdfextras](https://pypi.org/project/rdfextras/)

## Usage

```
usage: lexmapr [-h] [-o [OUTPUT]] [--format FORMAT] input_file [log_file]

positional arguments:
  input_file            Input csv file
  log_file              Log file

optional arguments:
  -h, --help            show this help message and exit
  -o [OUTPUT], --output [OUTPUT]
                        Output file
  --format FORMAT       Output format
```

### Example input files (in `lexmapr/tests/input`)

| Filename                   | Description                      |
|----------------------------|----------------------------------|
| `small_simple.csv`          | A small simple test dataset      |
| `enteroForFreq.csv`        | Dataset from EnteroBase          |
| `genomeTrackerMaster.csv`  | Dataset from GenomeTrakr         |
| `bccdcsample.csv`          | Dataset from BCCDC               |
| `zheminSamples.csv`        | Zhemin's samples from EnteroBase |
| `GRDI-UniqueSamples.csv`   | Dataset from GRDI                |

### Resources Files (in `lexmapr/resources`)

| Filename                      | Description                                                                                          |
|-------------------------------|------------------------------------------------------------------------------------------------------|
| `CombinedResourceTerms.csv`   | All the ontology terms with their ids extracted and combined in a single file                        |
| `SynLex.csv`                  | Synonym Lexicon                                                                                      |
| `AbbLex.csv`                  | Abbreviation/Acronym Lexicon                                                                         |
| `NefLex.csv`                  | Non English FoodNames Lexicon                                                                        |
| `ScorLex.csv`                 | Spellings correction Lexicon                                                                         |
| `SemLex.csv`                  | Semantic Tagging Lexicon                                                                             |
| `inflection-exceptions.csv`   | Exception list for avoiding false positives during inflection treatment                              |
| `candidateProcesses.csv`      | Additional processes which are candidates for inclusion                                              |
| `wikipediaCollocations.csv`   | Additional compound terms (collocations) detected out of datasets which are candidates for inclusion |
| `mining-stopwords.csv`        | Stop Words list for treatment refined for domian under consideration                                 |
