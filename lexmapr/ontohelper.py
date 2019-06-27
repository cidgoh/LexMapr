#!/usr/bin/python
# 

""" **************************************************************************
	This collects a set of commonly used python functions into the OntoHelper class
	
	Call from another class init routine. 

	import python.ontohelper as oh

	class Ontology(object):

		self.onto_helper = oh.OntoHelper()
		...

	Instance of onto_helper has:

		self.graph: holds a triple store graph

		self.struct: an OrderedDict() of
			.@context: OrderedDict() of prefix:url key values.
			.metadata: Holds metadata (dc:title etc) for loaded ontology
			.specifications Holds term details or other derived datastructures

"""

import os
import json
import sys
import rdflib
from rdflib.plugins.sparql import prepareQuery

# Do this, otherwise a warning appears on stdout: No handlers could be 
#found for logger "rdflib.term"
import logging; logging.basicConfig(level=logging.ERROR) 

try: #Python 2.7
	from collections import OrderedDict
except ImportError: # Python 2.6
	from ordereddict import OrderedDict

def stop_err(msg, exit_code = 1):
	sys.stderr.write("%s\n" % msg)
	sys.exit(exit_code)


class OntoHelper(object):

	CODE_VERSION = '0.0.3'

	def __init__(self):

		self.graph = rdflib.Graph()

		self.struct = OrderedDict()
		"""
		JSON-LD @context enables output .json file to have shorter URI's
		using namespace prefixes.  Generally this is an auto-generated table
		based on finding prefixes in input .owl file URI references. However,
		a prefix can be hardcoded below when there is a preferred or eccentric
		prefix.

		Note: if ontologies use different URI's for a given ontology term,
		that will be problematic!
		"""
		self.struct['@context'] = OrderedDict({
			'owl': 'http://www.w3.org/2002/07/owl#',
			'rdfs': 'http://www.w3.org/2000/01/rdf-schema#', 
			'oboInOwl': 'http://www.geneontology.org/formats/oboInOwl#',
			'xmls': 'http://www.w3.org/2001/XMLSchema#',
			'vcard': 'http://www.w3.org/2006/vcard/ns#',
			'vcf': 'http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#',
			'dc': 'http://purl.org/dc/elements/1.1/',
			'terms': "http://purl.org/dc/terms/",
			'NDF-RT':'http://evs.nci.nih.gov/ftp1/NDF-RT/NDF-RT.owl#',
		})

		# Holds metadata (dc:title etc) for loaded ontology
		self.struct['metadata'] = {}

		# Holds term details or other derived datastructures
		self.struct['specifications'] = {}

		# Namespace is for rdflib sparql querries
		# FUTURE: DEPRECATE?.  QUERY ENGINE SHOULD USE @CONTEXT.
		self.namespace = { 
			'owl': rdflib.URIRef('http://www.w3.org/2002/07/owl#'),
			'rdfs': rdflib.URIRef('http://www.w3.org/2000/01/rdf-schema#'),
			'rdf':	rdflib.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#'),
			'xmls': rdflib.URIRef('http://www.w3.org/2001/XMLSchema#'),
			'dc': rdflib.URIRef('http://purl.org/dc/elements/1.1/'),
			'terms': rdflib.URIRef('http://purl.org/dc/terms/'),
			'oboInOwl': rdflib.URIRef('http://www.geneontology.org/formats/oboInOwl#'),
			'OBO': rdflib.URIRef('http://purl.obolibrary.org/obo/'), # shortcut for all OBOFoundry purls
			'IAO':	rdflib.URIRef('http://purl.obolibrary.org/obo/IAO_'),
			'GENEPIO':rdflib.URIRef('http://purl.obolibrary.org/obo/GENEPIO_'), # Still needed for a few GEEM relations
			'RO':	rdflib.URIRef('http://purl.obolibrary.org/obo/RO_'),
			'OBI':	rdflib.URIRef('http://purl.obolibrary.org/obo/OBI_')
		}

		self.queries = {

			##################################################################
			# Fetch ontology metadata fields
			#
			# Example ontology header:
			#	<owl:Ontology rdf:about="http://purl.obolibrary.org/obo/genepio.owl">
		    #	    <owl:versionIRI rdf:resource="http://purl.obolibrary.org/obo/genepio/releases/2018-02-28/genepio.owl"/>
		    #		<oboInOwl:default-namespace rdf:datatype="http://www.w3.org/2001/XMLSchema#string">GENEPIO</oboInOwl:default-namespace>
		    #		<dc:title xml:lang="en">Genomic Epidemiology Ontology</dc:title>
		    #		<dc:description xml:lang="en">The Ontology for Biomedical Investigations (OBI) is build in a ...</dc:description>
		    #		<dc:license rdf:resource="http://creativecommons.org/licenses/by/3.0/"/>
		    #		<dc:date rdf:datatype="http://www.w3.org/2001/XMLSchema#date">2018-02-28</dc:date>

			'ontology_metadata': prepareQuery("""
			SELECT DISTINCT ?resource ?title ?description ?versionIRI ?prefix ?license ?date 
			WHERE {
				?resource rdf:type owl:Ontology.
				OPTIONAL {?resource (dc:title|terms:title) ?title.}
				OPTIONAL {?resource (dc:description|terms:description) ?description.}
				OPTIONAL {?resource owl:versionIRI ?versionIRI.}
				OPTIONAL {?resource oboInOwl:default-namespace ?prefix.}
				OPTIONAL {?resource (dc:license|terms:license) ?license.}
				OPTIONAL {?resource (dc:date|terms:date) ?date.}
			}
			""", initNs = self.namespace)

		}

	def __main__(self):
		pass


	############################## UTILITIES ###########################

	def get_bindings(self, myDict):
		obj = {}
		for entity in myDict:
			obj[entity] = myDict[entity]

		return obj


	def set_struct(self, focus,*args):
		# Create a recursive dictionary path from focus ... to n-1 args, and 
		# set it to value provided in last argument
		value = args[-1]
		for ptr, arg in enumerate(args[0:-1]):
			if not arg in focus: focus[arg]={}
			if ptr == len(args)-2:
				focus[arg] = value 
			else:
				focus = focus[arg]


	def get_struct(self, focus, *args):
		"""
			Navigate from focus object dictionary hierarchy down through 
			textual keys, returning value of last key.
		"""
		try:
			for arg in args:
				focus = focus[arg]
		except:
			print ("ERROR: in get_struct(), couldn't find '%s' key or struct in %s" % (str(arg), str(args) ) )
			return None
		return focus


	def get_parent_id(self, myDict):
		if 'parent_id' in myDict: 
			# Note sometimes binary nodes are returned
			return str(myDict['parent_id']) 
		return None


	def set_entity_default(self, focus,*args):
		""" 
		Same as set_struct() but won't create path; it will only use existing
		path.
		"""
		if not focus:
			print ( "ERROR: in set_entity_default(), no focus for setting: %s" % str(args[0:-1]) )
			return None

		value = args[-1]
		for ptr, arg in enumerate(args[0:-1]):
			#arg = str(arg) # binary nodes are objects
			if not arg: stop_err( "ERROR: in set_entity_default(), an argument isn't set: %s" % str(args[0:-1]) ) 
			if ptr == len(args)-2:
				if not arg in focus:
					focus[arg] = value
				return focus[arg]

			elif not arg in focus: 
				print ( "ERROR: in set_entity_default(), couldn't find %s" % str(args[0:-1]) )
				return False
			else:
				focus = focus[arg]


	def get_entity_id(self, myURI):
		"""
		 If given text is an http URI, look up its substitution prefix
		 in @context.  This avoids having to hardcode all prefixes that 
		 might be encountered in some ontology one is downloading.

		 If not found, add prefix to @context. Return
		 shortened namespace version, e.g.
		 
		 	URI: http://purl.obolibrary.org/obo/GENEPIO_0001234
		 	@context item: "GENEPIO": "http://purl.obolibrary.org/obo/GENEPIO_",

		 returns GENEPIO:0001234

		 INPUT
		 	URI:string
		 OUTPUT
		 	:string
		 """
		if myURI[0:4] == 'http':

			if '_' in myURI:
				(path, fragment) = myURI.rsplit('_',1)
				separator = '_'

			elif '#' in myURI: # Need '#' test first!    path#fragment
				(path, fragment) = myURI.rsplit('#',1)
				separator = '#'

			else:

				(path, fragment) = myURI.rsplit('/',1)
				separator = '/'
			
			full_path = path + separator

			for prefix, context_prefix in self.struct['@context'].items():
				# Snips last separation character 
				if full_path == context_prefix: 
					return prefix + ":" + fragment
			
			# At this point path not recognized in @context lookup
			# table, so add it to @context 
			prefix = path.rsplit('/',1)[1]

			# At least 2 characters in @context prefix required to avoid
			# exception to rule below, as no namespace begins with number
			# and following is a URI but not an ontology term reference.
			#	<owl:versionIRI rdf:resource="http://purl.obolibrary.org/obo/obi/2018-05-23/obi.owl"/>

			if prefix[0:2].isalpha(): 
				self.struct['@context'][prefix] = full_path
				return prefix + ":" + fragment


		return myURI 		# Returns untouched string


	def get_expanded_id(self, myURI):
		# If a URI has a recognized prefix, create full version
		if ':' in myURI: 
			(prefix, myid) = myURI.rsplit(':',1)

			if prefix in self.struct['@context']:
				return self.struct['@context'][prefix] + myid
			else:
				print ('ERROR in get_expanded_id(): No @context prefix for: ', myURI, ">" + prefix + "<")

		return myURI 


	def reorder(self, entity, part, orderedKeys = None):
			""" Order given entity part dictionary by given order array of ids, or alphabetically if none.
				# components, models, choices are all orderedDict already.
			"""
			if part in entity:
				if orderedKeys:
					# Each entity[part] item is given a rank by the index location of its id in given orderedKeys list
					entity[part] = OrderedDict(sorted(entity[part].items(), key=lambda item: orderedKeys.index(item[0]) if item[0] in orderedKeys else False))
				else:
					entity[part] = OrderedDict(sorted(entity[part].items(), key=attrgetter('ui_label')) )


	def do_ontology_includes(self, main_ontology_file):
		"""
		Detects all the import files in a loaded OWL ontology graph and adds
		them to the graph. If main ontology file is given as a file path, then
		imports are checked as resources located in possible './imports" 
		folder relative to that file.  Otherwise they are fetched by URL.

		INPUT

		"""
		imports = self.graph.query("""
			SELECT distinct ?import_file
			WHERE {?s owl:imports ?import_file.}
			ORDER BY (?import_file)
		""")		

		print ("It has %s import files ..." % len(imports))

		for result_row in imports:

			import_file = result_row.import_file
			print (import_file)
			# If main file supplied as a URI, then process imports likewise
			if main_ontology_file[0:4] == 'http':
				try:
					self.graph.parse(import_file, format='xml')	
				#except rdflib.exceptions.ParserError as e:
				except Exception as e:
					print ('WARNING:' + import_file + " could not be loaded!\n", e)		

			# Ontology given as file path, so only check its ./imports/ folder
			# since, as a local resource, its imports should be local too.
			else:

				file_path = os.path.dirname(main_ontology_file) + '/imports/' + import_file.rsplit('/',1)[1]

				try:
					if os.path.isfile( file_path):
						self.graph.parse(file_path)	
					else:
						print ('WARNING:' + file_path + " could not be loaded!  Does its ontology include purl have a corresponding local file? \n")

				except rdflib.exceptions.ParserError as e:
					print (file_path + " needs to be in RDF OWL format!")			


	def set_ontology_metadata(self, query):
		""" 
		Create a self.struct.metadata dictionary holding metadata for 
		incomming ontology, if any.	Query adjusts for one issue that
		some ontologies are using wrong Dublin Core URI.

		Fields directly from sparql: 
			dc:title -> title 					// e.g. Genomic Epidemiology Ontology
			dc:description -> description
			owl:versionIRI -> versionIRI  		// e.g. http://purl.obolibrary.org/obo/genepio/releases/2018-04-24/genepio.owl
			oboInOwl:default-namespace -> prefix  // e.g. GENEPIO
			dc:license -> license 				// e.g. http://creativecommons.org/licenses/by/3.0/
			dc:date -> date 						// have to get value component , self.struct['metadata']['date']['value']
        	resource = "http://purl.obolibrary.org/obo/genepio.owl",
		"""
		
		metadata = self.graph.query(query)

		for myDict in metadata: # Should only be 1 row containing a dictionary.
			myDict2 = myDict.asdict()
			# Default values
			myDict2['type'] = 'ontology'
			myDict2['status'] = 'release'
			# In some ontologies date comes in directly as string if it has no xml datatype
			if isinstance(myDict['date'], dict):
				myDict2['date'] = myDict['date']['value']

			self.struct['metadata'] = myDict2


	def do_query_table(self, query, initBinds = {}):
		"""
		Given a sparql 1.1 query, returns a list of objects, one for each row.
		For each object key/value, simplifies any URI reference (http://...) 
		into namespace prefix:identifier as in @context. 

		INPUT
		initBinds:	To provide parameters to the query, supply it with initBindings 
					containing a dictionary of bindings in format "term: value".

		"""

		#query = self.queries[query_name]

		try:
			result = self.graph.query(query, initBindings=initBinds)
		except Exception as e:
			print ("\nSparql query [%s] parsing problem: %s \n" % (query, str(e) ))
			return None

		# Can't get columns by row.asdict().keys() because columns with null results won't be included in a row.
		# Handles "... SELECT DISTINCT (?something as ?somethingelse) ?this ?and ?that WHERE ....""
		#columns = re.search(r"(?mi)\s*SELECT(\s+DISTINCT)?\s+((\?\w+\s+|\(\??\w+\s+as\s+\?\w+\)\s*)+)\s*WHERE", query)
		#columns = re.findall(r"\s+\?(?P<name>\w+)\)?", columns.group(2))

		STRING_DATATYPE = rdflib.term.URIRef('http://www.w3.org/2001/XMLSchema#string')
		table = []
		for ptr, row in enumerate(result):
			rowdict = row.asdict()
			newrowdict = {}

			for column in rowdict:

				# Each value has a datatype defined by RDF Parser: URIRef, Literal, BNode
				value = rowdict[column]
				valType = type(value) 
				if valType is rdflib.term.URIRef : 
					newrowdict[column] = self.get_entity_id(value)  # a plain string

				elif valType is rdflib.term.Literal :
					# Text may include carriage returns; escape to json
					literal = {'value': value.replace('\n', r'\n')} 
					#_invalid_uri_chars = '<>" {}|\\^`'

					if hasattr(value, 'datatype'): #rdf:datatype
						#Convert literal back to straight string if its datatype is simply xmls:string
						if value.datatype == None or value.datatype == STRING_DATATYPE:
							literal = literal['value']
						else:
							literal['datatype'] = self.get_entity_id(value.datatype)															

					elif hasattr(value, 'language'): # e.g.  xml:lang="en"
						#A query Literal won't have a language if its the result of str(?whatever) !
						literal['language'] = self.get_entity_id(value.language)
					
					else: # WHAT OTHER OPTIONS?
						literal = literal['value']

					newrowdict[column] = literal

				elif valType is rdflib.term.BNode:
					"""
					Convert a variety of BNode structures into something simple.
					E.g. "(province or state or territory)" is a BNode structure coded like
					 	<owl:someValuesFrom> 
							<owl:Class>
								<owl:unionOf rdf:parseType="Collection">
                    			   <rdf:Description rdf:about="&resource;SIO_000661"/> 
                    			   <rdf:Description rdf:about="&resource;SIO_000662"/>
                    			   ...
                    """
                    # Here we fetch list of items in disjunction
					disjunction = self.graph.query(
						"SELECT ?id WHERE {?datum owl:unionOf/rdf:rest*/rdf:first ?id}", 
						initBindings={'datum': value} )		
					results = [self.get_entity_id(item[0]) for item in disjunction] 
					newrowdict['expression'] = {'datatype':'disjunction', 'data':results}

					newrowdict[column] = value

				else:

					newrowdict[column] = {'value': 'unrecognized column [%s] type %s for value %s' % (column, type(value), value)}

			table.append(newrowdict)

		return table


	def check_folder(self, file_path, message = "Directory for "):
		"""
		Ensures file folder path for a file exists.
		It can be a relative path.
		"""
		if file_path != None:

			path = os.path.normpath(file_path)
			if not os.path.isdir(os.path.dirname(path)): 
				# Not an absolute path, so try default folder where script launched from:
				path = os.path.normpath(os.path.join(os.getcwd(), path) )
				if not os.path.isdir(os.path.dirname(path)):
					stop_err(message + "[" + path + "] does not exist!")			
					
			return path
		return None


	def check_ont_file(self, main_ontology_file, options):
		# Input is either a file or URL
		# e.g. https://raw.githubusercontent.com/obi-ontology/obi/master/obi.owl

		if main_ontology_file[0:4].lower() != 'http':
			main_ontology_file = self.check_folder(main_ontology_file, "Ontology file")
			if not os.path.isfile(main_ontology_file):
				stop_err('Please check the OWL ontology file path')			

		# Ontology core filename (minus .owl suffix) used in output file name
		ontology_filename = os.path.basename(main_ontology_file).rsplit('.',1)[0]

		# Output folder can be relative to current folder
		if options.output_folder:
			output_folder = options.output_folder 
		else:
			output_folder = os.path.dirname(os.path.realpath(sys.argv[0]))
		output_file_basename = output_folder + '/' + ontology_filename

		return (main_ontology_file, output_file_basename)


	def do_output_json(self, struct, output_file_basename):
		with (open(output_file_basename + '.json', 'w')) as output_handle:
			# DO NOT USE sort_keys=True on piclists etc. because this overrides
			# OrderedDict() sort order.
			output_handle.write(json.dumps(struct, sort_keys = False, indent = 4, separators = (',', ': ')))


	def do_output_tsv(self, struct, output_file_basename, fields):
		"""
		Tab separated output based on given field names

		INPUT
			fields: list
			self.struct['specifications']
		"""
		output = []

		# Header:			
		output.append('\t'.join(fields))

		for (key, entity) in struct['specifications'].items():
			row = []
			for field in fields:
				value = entity[field] if field in entity else ''
				if isinstance(value, list): # Constructed parent_id list.
					value = ','.join(value)
				row.append(value.replace('\t',' ')) # str() handles other_parents array

			output.append('\t'.join(row))

		with (open(output_file_basename + '.tsv', 'w')) as output_handle:
			output_handle.write('\n'.join(output))


