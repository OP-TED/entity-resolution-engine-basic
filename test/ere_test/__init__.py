"""
Helpers and mockups for ERE tests.

"""
import hashlib
from pathlib import Path
from typing import Dict, Iterable

from assertpy import assert_that
from rdflib import Graph

from ere.models.ers_core import (CanonicalEntity, EntityResolutionRequest,
                                 EntityResolutionResponse, ErrorResponse,
                                 RebuildRequest, RebuildResponse, Request,
                                 Response, linkml_meta)
from ere.service import AbstractEREClient, AbstractResolver

ERS_TEST_DATA_NS = "https://data.europa.eu/ers/resource/"
ERS_SCHEMA_NS = linkml_meta.root [ "id" ] + "/"

EPD_NS = "http://data.europa.eu/a4g/resource/"
EPO_NS = "http://data.europa.eu/a4g/ontology#"
ORG_NS = "http://www.w3.org/ns/org#"


class MockEREClient ( AbstractEREClient ):
	"""
	A Mockup ERE client, based on an internal in-memory store loaded with test data.
	"""
	def __init__ ( self ):
		self._init_test_data ()
		self._response_queue = []
	
	def _init_test_data ( self ):
		self._resolver = MockResolver ()

	def push_request ( self, request: Request ):
		result = self._resolver.process_request ( request )
		self._response_queue.append ( result )

	def subscribe_responses ( self ) -> Iterable [ Response ]:
		while self._response_queue:
			yield self._response_queue.pop ( 0 )


def hash_uri ( uri: str ) -> str:
	"""
	Generates a simple hash for URIs to be used for tasks like generating a cluster URI

	TODO: utils module
	"""
	return hashlib.md5 ( uri.encode ( 'utf-8' ) ).hexdigest ()


# TODO: will become an internal class for the implementation
class _ERECluster:
	def __init__ ( 
		self,
		uri: str, 
		canonical_entity_uri: str, 
		canonical_entity_rdf: Graph | str = None,
		members: Dict [str, float] = {}
	):
		self.uri = uri
		self.canonical_entity_uri = canonical_entity_uri
		self.members = members

		if not canonical_entity_rdf: raise ValueError ( 'ERECluster needs an RDF representation for its canonical entity' )
		if isinstance ( canonical_entity_rdf, Graph ):
			self.canonical_entity_rdf = canonical_entity_rdf
			return
	
		self.canonical_entity_rdf = Graph ()
		self.canonical_entity_rdf.parse ( data = canonical_entity_rdf, format = "turtle" )
	def get_canonical_entity_type ( self ) -> str:
		sparql = """
		SELECT ?type WHERE {
			<%s> a ?type .
		}
		"""
		sparql = sparql % self.canonical_entity_uri
		types = []
		for row in self.canonical_entity_rdf.query ( sparql ):
			types.append ( str ( row['type'] ) )
		if not types:
			raise ValueError ( f'No type found for entity { self.canonical_entity_uri }' )
		if len ( types ) > 1:
			raise ValueError ( f'Multiple types found for entity { self.canonical_entity_uri }: { types }' )
		return types[0]


class MockResolver ( AbstractResolver ):
	"""
	A mockup in-memory resolver for entity resolution, based on test data.
	"""
	def __init__ ( self ):
		self._load_test_data ()
		self._extract_all_clusters ()

	def get_cluster_by_canonical_entity ( self, canonical_entity_uri: str ) -> _ERECluster:
		return self._canonical_entity_index.get ( canonical_entity_uri )
	
	def get_cluster_by_member ( self, member_uri: str ) -> _ERECluster:
		return self._member_index.get ( member_uri )
	
	def get_cluster_by_entity ( self, entity_uri: str ) -> _ERECluster:
		cluster = self._canonical_entity_index.get ( entity_uri )
		if cluster: return cluster
		return self._member_index.get ( entity_uri )
	
	def process_request ( self, request: Request ) -> Response:
		"""
		Dispatches a request to the appropriate handler.

		This is also responsible for wrapping any exception into an ErrorResponse.
		"""

		try:
			# TODO: this is an intial silly implementation, which violates the Open/Closed principle, move
			# it to an abstract method for a resolution service and have a default implementation 
			# based on a registry
			if isinstance ( request, EntityResolutionRequest ):
				return self.resolve_entity ( request )
			elif isinstance ( request, RebuildRequest ):
				return self.process_rebuild_request ( request )
			else:
				raise ValueError ( f'Unsupported request type: { type ( request ) }' )
			
		except Exception as ex:
			ex_type = type ( ex )
			ex_name = ex_type.__name__
			
			ex_fqn_name = ex_type.__module__
			if ex_fqn_name == 'builtins': ex_fqn_name = ''
			if ex_fqn_name: ex_fqn_name += "."
			ex_fqn_name += ex_name
			
			req_type = type ( request ).__name__
			error_response = ErrorResponse (
				requestId = request.requestId,
				errorTitle = f"Request processing error: { str ( ex ) }",
				errorDetail = f"{ex_name} Error while processing request of type { req_type }: { str ( ex ) }",
				errorType = ex_fqn_name
			)
			return error_response


	def resolve_entity ( self, request: EntityResolutionRequest ) -> EntityResolutionResponse:
		"""
		Mocks up an entity resolution, that is:

		- if the uri is a canonical entity, it returns itself with a confidence of 1.0
		- else tries to find a cluster of which this entity is a member, and returns the canonical entity
		  of that cluster with the confidence associated to that member
		- else creates a new cluster with this entity as canonical entity and returns itself with confidence 1.0
		"""
		can_entity = None
		confidence = None

		entity_uri = request.entity.id

		cluster = self.get_cluster_by_canonical_entity ( entity_uri )
		if cluster:
			confidence = 1.0 # The entity is the canonical entity of this cluster
		else:
			cluster = self.get_cluster_by_member ( entity_uri )
			if cluster: 
				confidence = cluster.members.get ( entity_uri ) # The entity is a member of this cluster
			else:
				# We don't have this entity, create a new cluster with it as canonical entity
				canonical_rdf = request.entity.entityData

				if not canonical_rdf:
					# TODO: manage error messages in the system channel
					raise ValueError ( f"Cannot create new cluster for entity { entity_uri } without entity data/RDF" )

				cluster = self._create_new_cluster ( entity_uri, canonical_rdf, members = {} )
				confidence = 1.0

		if not cluster:
			raise RuntimeError ( f'Internal error during mockup entity resolution for entity { entity_uri }: cluster not found or created' )
		if not confidence:
			raise RuntimeError ( f'Internal error during mockup entity resolution for entity { entity_uri }: confidence score not found or not created' )

		can_entity = CanonicalEntity (
			type = cluster.get_canonical_entity_type (),
			id = cluster.canonical_entity_uri
		)

		can_entity.entityData = cluster.canonical_entity_rdf.serialize ( format = 'turtle' )
		can_entity.entityDataFormat = 'text/turtle'

		result = EntityResolutionResponse (
			requestId = request.requestId,
			canonicalEntity = can_entity,
			sourceEntityId = entity_uri,
		)
		result.confidenceLevel = confidence
		return result


	def process_rebuild_request ( self, request ) -> RebuildResponse:
		"""
		Mocks up the processing of a rebuild request by reloading the test data.
		"""
		self.__init__ ()
		response = RebuildResponse (
			requestId = request.requestId
		)
		return response


	def _load_test_data ( self ):
		"""
		Populates the internal RDF graph with data from test files.
		"""

		self.graph = Graph ()
		test_dir = Path ( __file__ ).parent.parent / 'resources'

		for ttl_file in test_dir.glob ( 'example*.ttl' ):
			# TODO: logging
			print ( f'Loading test data from { ttl_file }' )
			self.graph.parse ( str ( ttl_file ), format = 'turtle' )

	def _create_new_cluster (
		self, 
		canonical_entity_uri: str, 
		canonical_entity_rdf: Graph | str,
		cluster_uri: str = None,
		members: Dict [ str, float ] = {}
	) -> _ERECluster:
		"""
		Creates a new cluster for the given entity and updates the internal data with it.

		Returns: the created ERECluster instance, which can be used to add members.
		"""
		if canonical_entity_uri in self._canonical_entity_index:
			raise ValueError ( f'Cluster for canonical entity { canonical_entity_uri } already exists' )
		if not cluster_uri:
			cluster_uri = f'{ERS_TEST_DATA_NS}cluster_' + hash_uri ( canonical_entity_uri )

		cluster = _ERECluster ( cluster_uri, canonical_entity_uri, canonical_entity_rdf, members )
		self._clusters [ cluster.uri ] = cluster
		self._canonical_entity_index [ canonical_entity_uri ] = cluster
		# We also need an index from member URIs to clusters
		for member_uri in members.keys ():
			self._member_index [ member_uri ] = cluster

		return cluster


	def _extract_all_clusters ( self ) -> Dict [ str, _ERECluster ]:
		"""
		Extracts cluster info from test data like:

		epd:id_2023-S-210-662860_ReviewerOrganisation_LLhJHMi9mby8ixbkfyGoWj_Cluster
			a ers:Cluster;
			ers:canonicalEntity epd:id_2023-S-210-662860_ReviewerOrganisation_LLhJHMi9mby8ixbkfyGoWj;
			ers:membership [
				ers:member epd:id_2023-S-210-661238_ReviewerOrganisation_LLhJHMi9mby8ixbkfyGoWj;
				ers:confidence 0.98
			]
		.

		Returns: an index from member URIs to ERECluster instances.
		"""
		def extract_canonical_entity_uri ( cluster_uri: str ) -> str:
			query = f"""
			PREFIX ers:		<{ERS_SCHEMA_NS}>

			SELECT ?canonicalEntity where {{
				<{ cluster_uri }> ers:canonicalEntity ?canonicalEntity .
			}}
			"""
			for row in self.graph.query ( query ):
				return str ( row['canonicalEntity'] )
			raise ValueError ( f'No canonical entity found for cluster { cluster_uri }' )


		def extract_members ( cluster_uri: str ) -> Dict:
			members = {}
			query = f"""
			PREFIX ers:		<{ERS_SCHEMA_NS}>
			SELECT ?member ?confidence WHERE {{
				<{ cluster_uri }> ers:membership ?membership .
				?membership ers:member ?member ;
										ers:confidence ?confidence .
			}}
			"""
			for row in self.graph.query ( query ):
				member_uri = str ( row['member'] )
				score = float ( row['confidence'] )
				members [ member_uri ] = score

			return members
		

		self._clusters: Dict [ str, _ERECluster ] = {}
		self._canonical_entity_index: Dict [ str, _ERECluster ] = {}
		self._member_index: Dict [ str, _ERECluster ] = {}

		query = f"""
		PREFIX ers:		<{ERS_SCHEMA_NS}>

		SELECT ?cluster WHERE {{
			?cluster a ers:Cluster .
		}}
		"""

		for row in self.graph.query ( query ):
			cluster_uri = str ( row [ 'cluster' ] )
			print ( f"Loading cluster { cluster_uri }" )
			canonical_entity_uri = extract_canonical_entity_uri ( cluster_uri )
			canonical_entity_rdf = extract_resource_rdf ( self.graph, canonical_entity_uri )
			members = extract_members ( cluster_uri )

			self._create_new_cluster ( canonical_entity_uri, canonical_entity_rdf, cluster_uri, members	)

		if not self._clusters:
			raise ValueError ( 'No clusters found in the test data' )
		
	# /end: _extract_all_clusters ()
	

def extract_resource_rdf ( graph: Graph, resource_uri: str ) -> Graph:
	"""
	Fetches subject-centric triples from the test data, up to a couple of levels deep.
	"""
	
	sparql = """
	CONSTRUCT {
		?myent ?p ?o.
		?o ?p1 ?o1.
		?o1 ?p2 ?o2
	}
	WHERE {
		bind ( <%s> AS ?myent )
		?myent ?p ?o.

		OPTIONAL { 
			?o ?p1 ?o1. 
			OPTIONAL { ?o1 ?p2 ?o2. }
		}
	}
	"""
	sparql = sparql % resource_uri
	entity_graph = graph.query ( sparql ).graph
	if len ( entity_graph ) == 0:
		raise ValueError ( f'No RDF found for entity { resource_uri }' )
	return entity_graph
# /end: _extract_entity_rdf ()

def catch_response ( ere_cli: AbstractEREClient, request_id: str, type_to_check: type[Response] = None ) -> Response:
	"""
	Subscribes to to ERE responses and keeps getting responses until one with the given
	request ID is found.

	If the response flow stops (eg, channel closed, system went down), raises a :class:`RuntimeError`
	
	If type_to_check isn't None, asserts that the response is an instance of the given type.	
	"""
	for response in ere_cli.subscribe_responses ():
		if response.requestId == request_id:
			if type_to_check:
				assert_that ( response, f"Response for request ID '{request_id}' is of the expected type" )\
					.is_instance_of ( type_to_check )			
			return response
	raise RuntimeError ( f"No response found for request ID '{request_id}'" )


def prefix_common_namespaces ( rdf_or_sparql_body: str ) -> str:
	"""
	Simple helper to have your Turtle or SPARQL string prefixed with common namespace prefixes.
	"""
	return """
		PREFIX cccev: <http://data.europa.eu/m8g/>
		PREFIX dct:   <http://purl.org/dc/terms/>
		PREFIX ep:    <http://eprints.org/ontology/>
		PREFIX epd:   <http://data.europa.eu/a4g/resource/>
		PREFIX epo:   <http://data.europa.eu/a4g/ontology#>
		PREFIX locn:  <http://www.w3.org/ns/locn#>
		PREFIX org:   <http://www.w3.org/ns/org#>
		PREFIX owl:   <http://www.w3.org/2002/07/owl#>
		PREFIX ql:    <http://semweb.mmlab.be/ns/ql#>
		PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
		PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
		PREFIX rml:   <http://semweb.mmlab.be/ns/rml#>
		PREFIX rr:    <http://www.w3.org/ns/r2rml#>
		PREFIX skos:  <http://www.w3.org/2004/02/skos/core#>
		PREFIX tedm:  <http://data.europa.eu/a4g/mapping/sf-rml/>
		PREFIX time:  <http://www.w3.org/2006/time#>
		PREFIX xsd:   <http://www.w3.org/2001/XMLSchema#>

	""" + rdf_or_sparql_body