# LexMapr

A Lexicon and Rule-Based Tool for Translating Short Biomedical Specimen Descriptions into Semantic Web Ontology Terms

[![Build Status](https://travis-ci.org/Public-Health-Bioinformatics/LexMapr.svg?branch=master)](https://travis-ci.org/Public-Health-Bioinformatics/LexMapr)
[![Coverage Status](https://coveralls.io/repos/github/Public-Health-Bioinformatics/LexMapr/badge.svg?branch=master)](https://coveralls.io/github/Public-Health-Bioinformatics/LexMapr?branch=master)
[![bioconda-badge](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg?style=flat-square)](http://bioconda.github.io)

![alt text](./logo.png)

## Installation

### With Bioconda

Set up [Bioconda](https://bioconda.github.io/), if you haven't already!

Then:

```
$ conda create -n LexMapr lexmapr
$ conda activate LexMapr
$ python -m nltk.downloader all
```

### Without Bioconda

Install [Conda](https://docs.conda.io/en/latest/miniconda.html).

Create a LexMapr environment:

```
$ conda create --name LexMapr
```

Install LexMapr into your conda environment:
```
$ conda activate LexMapr
$ git clone https://github.com/Public-Health-Bioinformatics/LexMapr.git
$ cd LexMapr
$ pip install .
$ python -m nltk.downloader all
```

## Usage

#### Files

`small_simple.csv`
```
SampleId,Sample
small_simple1,Chicken Breast
small_simple2,Baked Potato
small_simple3,Canned Corn
small_simple4,Frozen Yogurt
small_simple5,Apple Pie
```

`small_simple_config.json`
```javascript
[
  {"http://purl.obolibrary.org/obo/foodon.owl": "http://purl.obolibrary.org/obo/BFO_0000001"}
]
```

#### Command line

```console
(LexMapr) foo@bar:~$ lexmapr small_simple.csv -c small_simple_config.json
Sample_Id       Sample_Desc     Cleaned_Sample  Matched_Components
small_simple1   Chicken Breast  chicken breast  ['chicken breast:foodon_00002703']
small_simple2   Baked Potato    baked potato    ['potato (whole, baked):foodon_03302196']
small_simple3   Canned Corn     canned corn     ['corn (canned):foodon_03302665']
small_simple4   Frozen Yogurt   frozen yogurt   ['frozen yogurt:foodon_03307445']
small_simple5   Apple Pie       apple pie       ['apple pie:foodon_00002475']
```

## More Documentation

[Formal documentation](https://genepio.org/lexmapr-documentation/)

[Tutorial slides for users with little or no experience with command line](./docs/tutorial_slides.pdf)

[Tutorial slides for **IFSAC users** with little or no experience with command line](./docs/ifsac_tutorial_slides.pdf)
