#!/usr/bin/python

""" **************************************************************************
	python ontobucket.py [owl ontology file path or URL]

	Enables creation and cached use of rules based on a given ontology's
	eqivalentTo statements containing 'has member' some/min x/max x/exactly x
	entity or expression.  Applying a rule set to a given set of entities
	(and their ancestor path ids) yields a list of triggered rules/buckets.

	For rule matching, it relies on being given LexMapr search result hits AND
	their entire ancestral list of ids.

 	Author: Damion Dooley

	Ontology() class __main__() reads in given ontology file via path or
	URL and imports all ontology class terms, including labels,
	definitions, and boolean axioms.  Output is produced as json or tabular tsv.

	The focus is on elaborating boolean axioms into their parts.

	REQUIREMENTS
	This script requires python module RDFLib.

	if --cache used, then --output folder is required in order to read where
	cached [ontology].json file is.

	EXAMPLES


	This makes a rule-set for any classes in a local ontology lexmapr.owl file
	under LEXMAPR_0000001 (NARMS reporting bucket) a root term naming a
	particular agency branch of buckets.

		python ontobucket.py ../lexmapr_ontology/lexmapr.owl -r http://genepio.org/ontology/LEXMAPR_0000001

	This makes a rule set as above, and tests rules against FOODON:00001286
	(turkey meat food product)

		python ontobucket.py ../lexmapr_ontology/lexmapr.owl -r http://genepio.org/ontology/LEXMAPR_0000001 -i FOODON:00001286


	As above, but also writes out ruleset to a file called test/lexmapr.json

		python ontobucket.py ../lexmapr_ontology/lexmapr.owl -r http://genepio.org/ontology/LEXMAPR_0000001 -i FOODON:00001286 -o test/

	As above, but also uses that test/lexmapr.json if it exists to run rules,
	rather than generating it from scratch.

		python ontobucket.py ../lexmapr_ontology/lexmapr.owl -r http://genepio.org/ontology/LEXMAPR_0000001 -i FOODON:00001286 -o test/ -c


	TEST CASES
		> python ontobucket.py ../lexmapr_ontology/lexmapr.owl -r http://genepio.org/ontology/LEXMAPR_0000001 -o test/ -c -i FOODON:00001286
	I.e. "turkey meat food product" should yield "Turkey" bucket:
		LEXMAPR:0000073 {FOODON:00001286}

		> python ontobucket.py ../lexmapr_ontology/lexmapr.owl -r http://genepio.org/ontology/LEXMAPR_0000001 -o test/ -c -i FOODON:00002099
	I.e. "peanut food product" should yield "Nuts" bucket
		LEXMAPR:0000073 {FOODON:00002099}

	> python ontobucket.py ../lexmapr_ontology/lexmapr.owl -r http://genepio.org/ontology/LEXMAPR_0000001 -o test/ -c -i FOODON:00002099

	**************************************************************************
"""

import json
import sys
import os
import optparse
import datetime
from copy import deepcopy

# from ontohelper import OntoHelper as oh
import lexmapr.ontohelper as oh

import rdflib
from rdflib.plugins.sparql import prepareQuery

# Do this, otherwise a warning appears on stdout: No handlers could be
# found for logger "rdflib.term"
import logging;

logging.basicConfig(level=logging.ERROR)


def stop_err(msg, exit_code=1):
    sys.stderr.write("%s\n" % msg)
    sys.exit(exit_code)


"""
Allows formatted help info.  From http://stackoverflow.com/questions/1857346/python-optparse-how-to-include-additional-info-in-usage-output.
"""


class MyParser(optparse.OptionParser):

    def format_epilog(self, formatter):
        return self.epilog


"""


"""


class OntologyBuckets(object):
    CODE_VERSION = '0.0.4'
    TEST = 0  # = 1 to test a hardcoded small subset of .owl ontology rules.

    def __init__(self):

        self.onto_helper = oh.OntoHelper()
        self.timestamp = datetime.datetime.now()
        self.comparison_set = None

        self.owl_rules = {

            'owl:someValuesFrom': self.someValuesFrom,

            # Issue: check about recognition of combined min/max cardinality.
            # Issue: returns true/false, not ids of matched items.
            'owl:qualifiedCardinality':
                self.qualifiedCardinality,

            'owl:minQualifiedCardinality':
                self.minQualifiedCardinality,

            'owl:maxQualifiedCardinality':
                self.maxQualifiedCardinality,

            # Unused; 'owl:onProperty' not currently part of the rule syntax.
            # if (rule_fn == 'owl:onProperty'):
            #	return

            'owl:intersectionOf': self.intersectionOf,

            # Matches to expressions like "(a or b or c)". Each can generate a True/
            # False hit on self.comparison_set.
            # RETURN JUST ITEMS THAT ARE COMMON TO BOTH SETS.
            'owl:unionOf': self.someValuesFrom,

            'owl:complementOf': self.complementOf

        }

        self.queries = {

            ##################################################################
            # Membership Rules are boolean expressions or single entities linked
            # via 'has member' relation between a parent_id entity and children.
            #
            # This script returns all triples that immediately compose the
            # owl.subject (aka owl.restriction). Below is simplest case
            #
            #   <owl:Restriction>
            #      <owl:onProperty rdf:resource="obo:RO_0002351"/>
            #      <owl:someValuesFrom rdf:resource="obo:FOODON_00002196"/>
            #   </owl:Restriction>
            #	...

            'report_mapping': rdflib.plugins.sparql.prepareQuery("""

				SELECT DISTINCT ?label ?parent_id ?subject ?predicate ?object
				WHERE {
					BIND (OBO:RO_0002351 as ?has_member).

					?parent_id rdfs:subClassOf* ?root.
					?parent_id owl:equivalentClass ?subject.
					?parent_id rdfs:label ?label.
					{	?subject owl:onProperty ?has_member.
						?subject (owl:someValuesFrom | owl:qualifiedCardinality | owl:minQualifiedCardinality | owl:maxQualifiedCardinality) ?object.
					}
					UNION
					{	?subject (owl:intersectionOf | owl:unionOf |  owl:complementOf) ?object.
					}
					?subject ?predicate ?object.

				 } ORDER BY ?parent_id

			""", initNs=self.onto_helper.namespace),

            # Anything is retrieved here, including annotations
            'triple_by_subject': rdflib.plugins.sparql.prepareQuery("""

				SELECT DISTINCT ?predicate ?object
				WHERE {?subject ?predicate ?object}
				ORDER BY ?predicate

			""", initNs=self.onto_helper.namespace),

            # This query focuses on restriction parts and weeds out unneeded annotations.

            # (owl:onClass | owl:intersectionOf | owl:unionOf | owl:complementOf)
            'triple_by_relation': rdflib.plugins.sparql.prepareQuery("""

				SELECT DISTINCT ?predicate ?object
				WHERE {
					?subject (owl:onClass) ?object.
					?subject ?predicate ?object.
				}
				ORDER BY ?subject

			""", initNs=self.onto_helper.namespace),

            'cardinality_target': rdflib.plugins.sparql.prepareQuery("""

				SELECT DISTINCT ?object
				WHERE {
					?subject owl:onClass ?object.
				}
			""", initNs=self.onto_helper.namespace)
        }

    def log(self, *args):
        """
            Show log messages and differential time between calls
        """
        timestamp = datetime.datetime.now()
        # print("time delta: ", str(timestamp - self.timestamp), "\n", str(args))
        self.timestamp = timestamp

    def __main__(self):
        """
        LexMapr Agency Reporting Module:

        Objective: trigger/activate agency bucket in response to presentation of (a bucket of) a set of lexmapr ontology hits.  Matching is most effective if all lexmapr hits AND THEIR ontology ancestor term ids are presented in a single set.  Each rule needs to be applied to this set in turn.

        """
        (options, args) = self.get_command_line()

        if options.code_version:
            print(self.CODE_VERSION)
            return self.CODE_VERSION

        if not len(args):
            stop_err('Please supply an OWL ontology file (in RDF/XML format)')

        (main_ontology_file, output_file_basename) = self.onto_helper.check_ont_file(args[0],
                                                                                     options)

        cached_rules = False;

        if options.cache:
            # If there is a cached file to use, go for it, otherwise will have to generate it.
            if options.output_folder:
                # Output rule file takes on ontology name + .json
                json_file_path = output_file_basename + '.json'

                if os.path.isfile(json_file_path):
                    with (open(json_file_path)) as input_handle:
                        self.log("Using cached file:", json_file_path)
                        bucket_rules = json.load(input_handle);
                        cached_rules = True;

            else:
                stop_err(
                    'If using the cache flag, you must specify an output folder to read .json file from (or regenerate it to)')

        if not cached_rules:

            # Load main ontology file into RDF graph
            print("Fetching and parsing " + main_ontology_file + " ...")

            try:
                # ISSUE: ontology file taken in as ascii; rdflib doesn't accept
                # utf-8 characters so can experience conversion issues in string
                # conversion stuff like .replace() below
                self.onto_helper.graph.parse(main_ontology_file, format='xml')

            except Exception as e:
                # urllib2.URLError: <urlopen error [Errno 8] nodename nor servname provided, or not known>
                stop_err('WARNING:' + main_ontology_file + " could not be loaded!\n", e)

            # Add each ontology include file (must be in OWL RDF format)
            self.onto_helper.do_ontology_includes(main_ontology_file)

            for term_id in options.root_uri.split(','):
                # THE ONE CALL TO GET REPORT CATEGORY BOOLEAN EXPRESSIONS
                self.log('bucket rule compilation for', term_id)

                # If user has provided a set of comparison ids then actually
                # execute bucket rules on them and return a boolean result for
                # each rule.
                bucket_rules = self.do_membership_rules(term_id)

            # If output folder specified then write out bucket rule file
            if (options.output_folder):
                self.onto_helper.do_output_json(bucket_rules, output_file_basename)

        # FUTURE: ALTERNATELY, INPUT comparison_ids as TSV FILE OR JSON WITH
        # records of hits
        if options.comparison_ids:

            self.log('Bucket reporting')
            # The self.comparison_set of entity ids which rule parts are tested
            # against.
            self.comparison_set = set(options.comparison_ids.split(','))

            ret = []
            for bucket_id, rule in bucket_rules.items():
                output = self.do_bucket_rule(rule)
                if output != {False}:
                    # print("RULE:", bucket_id, output)
                    ret += [bucket_id]
            return ret

    """
    CARDINALITY SPECIFIES NUMBER OF ITEMS THAT CAN MATCH. USUALLY WITH 
    CATEGORY MATCHING RULES one or more supporting (or negated) piece
    of evidence is all we care about, but exact cardinality is also
    enabled below.
    Cardinality rules return boolean True / False, which means that 
    parent term must work on boolean values.

    'member of' some ~= one or more 'member of ' relations to entities.
    """

    def someValuesFrom(self, content):
        output_set = self.do_bucket_rule(content)
        output_set.discard(False)
        # print("atLeastOne", output_set)
        if len(output_set) > 0:
            return output_set
        else:
            return set([False])

    """ 
    Matches to expressions like "(a and b and c)" but these would rarely
    be entity references directly - if they were the constraint would be
    that rule was indicating that member was simultaniously class a, b, c.
    Instead, usually each entity would be an expression of predicate link 
    'has member' to some condition on presence or absense of member 
    elements, i.e. more likely used in form of "(expression a) and 
    (expression b)" where each expression is placing constraints on 
    self.comparison_set elements.

    ISSUE: truthiness. Like the others, IntersectionOf must have its
    components match (or not) as they see fit to the self.comparison_set.
    It must evaluate as both sets returning "True" or an element that was
    matched in self.comparison_set.  So complementOf can return "True".

     "LEXMAPR:0000041": {
            "owl:someValuesFrom": {
                "owl:intersectionOf": {
                    "owl:unionOf": {
                        "FOODON:00001172": null,
                        "FOODON:00002099": null,
                        "FOODON:03306867": null,
                        "FOODON:03411213": null
                    },
                    "owl:complementOf": {
                        "FOODON:03306867": null
                    }
                }
            }
        },

    """

    def intersectionOf(self, content):

        intermediate = self.do_bucket_rule(content);
        if all(intermediate):
            intermediate.discard(True)  # redundant
            return intermediate
        else:
            return set([False])

    """ 
        Matches to expressions like "not (a or b or c) ... " meaning
        none of the target elements should be present in the self.comparison_set.  
        Only returns True or False; never returns elements.
        No element in content can match e in self.comparison_set
    """

    def complementOf(self, content):

        if not any(self.do_bucket_rule(content)):
            return set([True])
        else:
            return set([False])

    def qualifiedCardinality(self, content):
        intermediate = self.do_bucket_rule(content['set'])
        if len(intermediate) == content['limit']:
            return intermediate
        else:
            return set([False])

    def minQualifiedCardinality(self, content):
        intermediate = self.do_bucket_rule(content['set'])
        if len(intermediate) >= content['limit']:
            return intermediate
        else:
            return set([False])

    def maxQualifiedCardinality(self, content):
        intermediate = self.do_bucket_rule(content['set'])
        if len(intermediate) <= content['limit']:
            return intermediate
        else:
            return set([False])

    """
    The first parameter of a rule is one of the predicates. Remaining
    parameters are either cardinality restriction limits, or boolean
    set operators, or entity ids (strings).

    Picture the self.comparison_set as a class or instance having 'has member'
    relations to all its elements.  The rule expression is one or more
    tests of given elements against the self.comparison_set 'has member' items.

    OUTPUT: set() containing matching ids, or None elements.
    """

    def do_bucket_rule(self, rule):

        # print("Doing rule", rule)
        output = set()
        # At top-level a rule dictionary should only have one key, usually owl:someValuesFrom .
        # print ("DOING RULE:", rule )
        for item in rule.keys():

            # print ("Item:", item)
            if item in self.owl_rules:
                # print("RULE ITEM", item, rule[item])
                output.update(self.owl_rules[item](rule[item]))

            # Here we've hit expression that doesn't begin with a function
            # so it is an entity id to compare against comparison set.
            if item in self.comparison_set:
                output.add(item)
        # else:
        #	output.add(False)

        return output

    """ ####################################################################
        Membership Rules are boolean expressions or single entities linked
        via 'has member' relation between a parent_id entity and children.

        This script reports rule label and id (parent_id) and then sends
        triple containing "[member of] [cardinality]

        memberships_by_cardinality query returns just the cardinality part.
        From there we explore the rest of the guts.

        INPUTS
            ?parent_id ?label ?subject ?predicate ?object

    """

    def do_membership_rules(self, term_id):

        specBinding = {'root': rdflib.URIRef(term_id)}
        table = self.onto_helper.do_query_table(self.queries['report_mapping'], specBinding)

        print("Bucket count:", len(table))

        bucket_rules = {}

        # At this level each triple is a bucket-matching rule
        for triple in table:
            # TEST EXAMPLES

            if self.TEST == 1 and not triple['parent_id'] in (['LEXMAPR:0000041']):
                continue  # LEXMAPR:0000002', 'LEXMAPR:0000007', '

            # The 'report_mapping' query triples also have a 'label' and
            # 'parent_id' field. Generally they have predicate: someValuesFrom
            bucket_rules[triple['parent_id']] = self.do_triple(triple)

            if self.TEST == 1:
                print(triple['label'], '(' + triple['parent_id'] + ')',
                      bucket_rules[triple['parent_id']])

        return bucket_rules

    def get_component_BNode(self, node_id):

        result = {}

        # Find subordinate tripples that begin with triple's object.
        # Basically none of these are annotations
        triples = self.onto_helper.do_query_table(
            self.queries['triple_by_subject'], {'subject': node_id}
        )

        for bnode_triple in triples:
            result.update(self.do_triple(bnode_triple))

        return result

    def do_triple(self, triple):

        bnode_predicate = triple['predicate'];
        bnode_object = triple['object'];

        # Add symbol as key.
        if bnode_predicate == 'rdf:first':
            if type(bnode_object) == str:
                return {bnode_object: None};

            # Triples have an apparent list of entity id held in triple.expression.data, but taking this prevents rdf:rest chain which can lead to other things outside the list.  triple e.g.: {'predicate': 'rdf:first', 'expression': {'datatype': 'disjunction', 'data': [... list ..]

            # print("BONODIE1:", bnode_object)
            # Merge dictionary of complex structure:
            return self.get_component_BNode(bnode_object);

        if bnode_predicate == 'rdf:rest':
            if 'bnode_object' == 'rdf:nil':
                # End of list.  Nothing more to do here.
                return None

            return self.get_component_BNode(bnode_object);

        if bnode_predicate == 'rdf:type':
            # and bnode_triple['object'] == 'owl:Class':
            # Currently class simply adds anonymous shell onto contents - because rules (which are anonymous classes) don't/can't hold more than one bracketed expression.
            return self.get_component_BNode(bnode_object);

        if type(bnode_object) == str:
            # At this point, any string object should just be
            # a dictionary predicate key to the string.
            # print ("KONSTANT:", bnode_object)
            return {bnode_predicate: {bnode_object: None}};

        # E.g. QUALIFIED {'label': 'Avian', 'parent_id': 'LEXMAPR:0000004', 'expression': {'datatype': 'disjunction', 'data': []}, 'subject': rdflib.term.BNode('N56404ec196374f5998f05241cf8e7875'), 'predicate': 'owl:minQualifiedCardinality', 'object': {'value': '1', 'datatype': 'xmls:nonNegativeInteger'}}
        if bnode_predicate in ['owl:qualifiedCardinality', 'owl:minQualifiedCardinality',
                               'owl:maxQualifiedCardinality']:
            # print ('QUALIFIED', triple)
            return {bnode_predicate:
                        {'limit': int(bnode_object['value']),
                         'set': self.get_component_cardinality(triple['subject'])
                         }
                    }

        # print("BONODIE2:", bnode_predicate, bnode_object)
        return {bnode_predicate: self.get_component_BNode(bnode_object)};

    def get_component_cardinality(self, subject_id):
        """
        The cardinality cases all require 2nd query to fetch target class
        of restriction.
        """
        objects = self.onto_helper.do_query_table(
            self.queries['cardinality_target'], {'subject': subject_id}
        )
        # print ("DUMP CARD TRIPLES", objects)
        # Should only be one...?!
        for row in objects:
            node_object = row['object']
            if type(node_object) == str:
                return {node_object: None}

            # NOT TESTED:
            return self.get_component_BNode(node_object)

        return {}

    def render_debug(self, triple):
        return ("DEBUG:", json.dumps(triple, sort_keys=False, indent=4, separators=(',', ': ')))

    def get_component_blank(self, triple):
        return None

    def get_command_line(self):
        """
        *************************** Parse Command Line *****************************
        """
        parser = MyParser(
            description='Ontology term fetch to tabular output.  See https://github.com/GenEpiO/genepio',
            usage='ontofetch.py [ontology file path or URL] [options]*',
            epilog="""  """)

        # first (unnamed) parameter is input file or URL
        # output to stdio unless -o provided in which case its to a file.

        # Standard code version identifier.
        parser.add_option('-v', '--version', dest='code_version', default=False,
                          action='store_true', help='Return version of this code.')

        parser.add_option('-c', '--cache', dest='cache', default=False, action="store_true",
                          help='Allow use of cached json rule file?')

        parser.add_option('-o', '--output', dest='output_folder', type='string',
                          help='Path of output file to create')

        parser.add_option('-i', '--input', dest='comparison_ids', type='string',
                          help='Comma separated list of term ids to match rules to.')

        parser.add_option('-r', '--root', dest='root_uri', type='string',
                          help='Comma separated list of full URI root entity ids to fetch underlying terms from. Defaults to owl#Thing.',
                          default='http://www.w3.org/2002/07/owl#Thing')

        return parser.parse_args()


if __name__ == '__main__':
    buckets = OntologyBuckets()
    buckets.__main__()
