# LexMapr
A Lexicon and Rule-Based Tool for Translating Short Biomedical Specimen Descriptions into Semantic Web Ontology Terms

The main script file for processing is `lexmapr/lexmapr.py`

## Dependencies

- [nltk](https://pypi.org/project/nltk/)
- [inflection](https://pypi.org/project/inflection/)
- [wikipedia](https://pypi.org/project/wikipedia/)
- [python-dateutil](https://pypi.org/project/python-dateutil/)

## Usage

```
usage: lexmapr.py [-h] [-o [OUTPUT]] [--format FORMAT] input_file [log_file]

positional arguments:
  input_file            Input csv file
  log_file              Log file

optional arguments:
  -h, --help            show this help message and exit
  -o [OUTPUT], --output [OUTPUT]
                        Output file
  --format FORMAT       Output format
```

### Example input files

| Filename                   | Description                      |
|----------------------------|----------------------------------|
| `enteroForFreq.csv`        | Dataset from EnteroBase          |
| `genomeTrackerMaster.csv`	 | Dataset from GenomeTrakr         |
| `bccdcsample.csv`          | Dataset from BCCDC               |
| `zheminSamples.csv`        | Zhemin's samples from EnteroBase |
| `GRDI-UniqueSamples.csv`	 | Dataset from GRDI                |

### Resources Files

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
