README:

The main script file for processing is "LexMaprPipeline.py"

Packages Imported (or to be imported):
import csv  
import nltk
import re
import inflection
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk import pos_tag, ne_chunk
import wikipedia
import itertools
from itertools import combinations
from dateutil.parser import parse


INPUTS:

Input (samples) files:
enteroForFreq.csv	#If dataset from EnteroBase has to be used
genomeTrackerMaster.csv	#If dataset from GenomeTrakr has to be used
bccdcsample.csv		#If dataset from BCCDC has to be used
zheminSamples.csv	#If Zhemin's samples from EnteroBase has to be used
GRDI-UniqueSamples.csv	#If dataset from GRDI has to be used


Input Resources:
CombinedResourceTerms.csv	#All the ontology terms with their ids extracted and combined in a single file
SynLex.csv			#Synonym Lexicon
AbbLex.csv			#Abbreviation/Acronym Lexicon
NefLex.csv			#Non English FoodNames Lexicon
ScorLex.csv   			#Spellings correction Lexicon
SemLex.csv			#Semantic Tagging Lexicon

inflection-exceptions.csv	#Exception list for avoiding false positives during inflection treatment
candidateProcesses.csv		#Additional processes which are candidates for inclusion
wikipediaCollocations.csv	#Additional compound terms (collocations) detected out of datasets which are candidates for inclusion
mining-stopwords.csv		#Stop Words list for treatment refined for domian under consideration


OUTPUTS:
Output-OutputFileName.tsv	#Annotated Output  - could be named as required