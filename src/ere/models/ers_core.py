from __future__ import annotations

from typing import Any, ClassVar, Literal, Optional

from pydantic import (BaseModel, ConfigDict, Field, RootModel,
                      SerializationInfo, SerializerFunctionWrapHandler,
                      model_serializer)

metamodel_version = "None"
version = "1.0-SNAPSHOT"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias = True,
        validate_by_name = True,
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )

    @model_serializer(mode='wrap', when_used='unless-none')
    def treat_empty_lists_as_none(
            self, handler: SerializerFunctionWrapHandler,
            info: SerializationInfo) -> dict[str, Any]:
        if info.exclude_none:
            _instance = self.model_copy()
            for field, field_info in type(_instance).model_fields.items():
                if getattr(_instance, field) == [] and not(
                        field_info.is_required()):
                    setattr(_instance, field, None)
        else:
            _instance = self
        return handler(_instance, info)



class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key:str):
        return getattr(self.root, key)

    def __getitem__(self, key:str):
        return self.root[key]

    def __setitem__(self, key:str, value):
        self.root[key] = value

    def __contains__(self, key:str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta({'default_prefix': 'ers',
     'default_range': 'string',
     'description': 'A LinkML schema for the ERS Services.',
     'id': 'https://data.europa.eu/ers/schema',
     'imports': ['linkml:types'],
     'name': 'ersServiceDataSchema',
     'prefixes': {'ers': {'prefix_prefix': 'ers',
                          'prefix_reference': 'https://data.europa.eu/ers/schema/'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'}},
     'source_file': 'resources/schema/ers-core_v1.0.yaml'} )


class RequestOrResponseMixin(ConfiguredBaseModel):
    """
    Root mixin to represent attributes common to both requests and results.

    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True,
         'from_schema': 'https://data.europa.eu/ers/schema',
         'mixin': True})

    type: Literal["RequestOrResponseMixin"] = Field(default="RequestOrResponseMixin", description="""The type of the request or result.

As per LinkML specification, `designates_type` is used here in order to allow for this
slot to tell the concrete subclass that an instance (such as a JSON object) belongs to.

In other words, a particular request will have `type` set with values like 
`EntityResolutionRequest` or `EntityResolutionResult`
""", json_schema_extra = { "linkml_meta": {'designates_type': True, 'domain_of': ['RequestOrResponseMixin', 'Entity']} })
    metadata: Optional[str] = Field(default=None, description="""An optional arbitrary dictionary of further request metadata.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['RequestOrResponseMixin']} })


class Request(RequestOrResponseMixin):
    """
    Root class to represent all the requests sent to the ERE.

    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True,
         'from_schema': 'https://data.europa.eu/ers/schema',
         'mixins': ['RequestOrResponseMixin']})

    requestId: str = Field(default=..., description="""A string representing the unique ID of this request.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['Request', 'Response']} })
    originator: str = Field(default=..., description="""The ID or URI of the request originator.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['Request']} })
    type: Literal["Request"] = Field(default="Request", description="""The type of the request or result.

As per LinkML specification, `designates_type` is used here in order to allow for this
slot to tell the concrete subclass that an instance (such as a JSON object) belongs to.

In other words, a particular request will have `type` set with values like 
`EntityResolutionRequest` or `EntityResolutionResult`
""", json_schema_extra = { "linkml_meta": {'designates_type': True, 'domain_of': ['RequestOrResponseMixin', 'Entity']} })
    metadata: Optional[str] = Field(default=None, description="""An optional arbitrary dictionary of further request metadata.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['RequestOrResponseMixin']} })


class Response(RequestOrResponseMixin):
    """
    Root class to represent all the responses sent by the ERE.

    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True,
         'from_schema': 'https://data.europa.eu/ers/schema',
         'mixins': ['RequestOrResponseMixin']})

    requestId: str = Field(default=..., description="""A string representing the unique ID of the request this response is about.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['Request', 'Response']} })
    type: Literal["Response"] = Field(default="Response", description="""The type of the request or result.

As per LinkML specification, `designates_type` is used here in order to allow for this
slot to tell the concrete subclass that an instance (such as a JSON object) belongs to.

In other words, a particular request will have `type` set with values like 
`EntityResolutionRequest` or `EntityResolutionResult`
""", json_schema_extra = { "linkml_meta": {'designates_type': True, 'domain_of': ['RequestOrResponseMixin', 'Entity']} })
    metadata: Optional[str] = Field(default=None, description="""An optional arbitrary dictionary of further request metadata.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['RequestOrResponseMixin']} })


class EntityResolutionRequest(Request):
    """
    An entity resolution request sent to the ERE, containing the entity to be resolved.

    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'examples': [{'value': '{\n'
                                '  "type": "EntityResolutionRequest",            \n'
                                '  "entity": \n'
                                '  { \n'
                                '    "type": "http://www.w3.org/ns/org#Organization",\n'
                                '    "id": '
                                '"http://data.europa.eu/ers/id/324fs3r345vx-aa32wa",\n'
                                '    "entityData": "epd:ent005 a org:Organization; '
                                '...   cccev:telephone \\"+44 1924306780\\" .",\n'
                                '    "entityDataFormat": "text/turtle"\n'
                                '  },\n'
                                '  "requestId": "324fs3r345vx",\n'
                                '  "originator": "TED SWS pipeline",\n'
                                '  "metadata": {\n'
                                '    "originator system": "VocBench editor",\n'
                                '    "originator timestamp": "23748737643"\n'
                                '  }\n'
                                '}\n'}],
         'from_schema': 'https://data.europa.eu/ers/schema'})

    entity: Entity = Field(default=..., description="""The data about the entity to be resolved.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['EntityResolutionRequest']} })
    requestId: str = Field(default=..., description="""A string representing the unique ID of this request.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['Request', 'Response']} })
    originator: str = Field(default=..., description="""The ID or URI of the request originator.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['Request']} })
    type: Literal["EntityResolutionRequest"] = Field(default="EntityResolutionRequest", description="""The type of the request or result.

As per LinkML specification, `designates_type` is used here in order to allow for this
slot to tell the concrete subclass that an instance (such as a JSON object) belongs to.

In other words, a particular request will have `type` set with values like 
`EntityResolutionRequest` or `EntityResolutionResult`
""", json_schema_extra = { "linkml_meta": {'designates_type': True, 'domain_of': ['RequestOrResponseMixin', 'Entity']} })
    metadata: Optional[str] = Field(default=None, description="""An optional arbitrary dictionary of further request metadata.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['RequestOrResponseMixin']} })


class EntityResolutionResponse(Response):
    """
    An entity resolution response sent by the ERE.

    This contains a reference to the canonical entity that the ERE has associated to the original 
    entity in the request. It also reports a confidence score for the established association.

    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'examples': [{'value': '{\n'
                                '  "type": "EntityResolutionResponse",\n'
                                '  "sourceEntityId": '
                                '"http://data.europa.eu/ers/id/324fs3r345vx-q11rea",\n'
                                '  "confidenceLevel": 0.91,\n'
                                '  "requestId": "324fs3r345vx"\n'
                                '  "canonicalEntity": \n'
                                '  { \n'
                                '    "type": "http://www.w3.org/ns/org#Organization",\n'
                                '    "id": '
                                '"http://data.europa.eu/ers/id/324fs3r345vx-aa32wa",\n'
                                '    "entityData": "epd:ent001 a org:Organization; '
                                '...   cccev:telephone \\"+441924306780\\" .",\n'
                                '    "entityDataFormat": "text/turtle"\n'
                                '  }\n'
                                '}\n'}],
         'from_schema': 'https://data.europa.eu/ers/schema'})

    canonicalEntity: CanonicalEntity = Field(default=..., description="""The canonical entity that the ERE has associated to the original entity.
This includes the canonical entity URI and its type.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['EntityResolutionResponse']} })
    sourceEntityId: str = Field(default=..., description="""The ID or URI of the original entity that has been resolved.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['EntityResolutionResponse']} })
    confidenceLevel: Optional[float] = Field(default=None, description="""A 0-1 value of how confident the ERE is about associating the original entity
with the canonical entity's cluster.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['EntityResolutionResponse']} })
    requestId: str = Field(default=..., description="""A string representing the unique ID of the request this response is about.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['Request', 'Response']} })
    type: Literal["EntityResolutionResponse"] = Field(default="EntityResolutionResponse", description="""The type of the request or result.

As per LinkML specification, `designates_type` is used here in order to allow for this
slot to tell the concrete subclass that an instance (such as a JSON object) belongs to.

In other words, a particular request will have `type` set with values like 
`EntityResolutionRequest` or `EntityResolutionResult`
""", json_schema_extra = { "linkml_meta": {'designates_type': True, 'domain_of': ['RequestOrResponseMixin', 'Entity']} })
    metadata: Optional[str] = Field(default=None, description="""An optional arbitrary dictionary of further request metadata.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['RequestOrResponseMixin']} })


class ErrorResponse(Response):
    """
    Response sent by the ERE when some error/exception occurs while processing a request.
    For instance, this may happen if the request is malformed or some internal error happens.

    The attributes of this class are based on [RFC-9457](https://datatracker.ietf.org/doc/html/rfc9457).

    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'examples': [{'value': '{\n'
                                '  "type": "ErrorResponse",\n'
                                '  "requestId": "324fs3r345vx",\n'
                                '  "errorType": '
                                '"ere.exceptions.MalformedRequestError",\n'
                                '  "errorTitle": "The entity data is missing in the '
                                'request",\n'
                                '  "errorDetail": "The \'entity\' attribute is '
                                'required in EntityResolutionRequest message",\n'
                                '  // Optional and not recommended for production use\n'
                                '  "errorTrace": "Traceback (most recent call '
                                'last):\\n  File \\"/app/ere/service.py\\", line 45, '
                                'in process_request\\n..."\n'
                                '}\n'}],
         'from_schema': 'https://data.europa.eu/ers/schema'})

    errorType: str = Field(default=..., description="""A string representing the error type, eg, the FQN of the raised exception.

This corresponds to RFC-9457's `type`.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['ErrorResponse']} })
    errorTitle: Optional[str] = Field(default=None, description="""A human readable brief message about the error that occurred.

This corresponds to RFC-9457's `title`.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['ErrorResponse']} })
    errorDetail: Optional[str] = Field(default=None, description="""A human readable detailed message about the error that occurred.

This corresponds to RFC-9457's `detail`.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['ErrorResponse']} })
    errorTrace: Optional[str] = Field(default=None, description="""A string representing a (stack) trace of the error that occurred.

This is optional and typically used for debugging purposes only, since
exposing this kind of server-side information is a security risk.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['ErrorResponse']} })
    requestId: str = Field(default=..., description="""A string representing the unique ID of the request this response is about.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['Request', 'Response']} })
    type: Literal["ErrorResponse"] = Field(default="ErrorResponse", description="""The type of the request or result.

As per LinkML specification, `designates_type` is used here in order to allow for this
slot to tell the concrete subclass that an instance (such as a JSON object) belongs to.

In other words, a particular request will have `type` set with values like 
`EntityResolutionRequest` or `EntityResolutionResult`
""", json_schema_extra = { "linkml_meta": {'designates_type': True, 'domain_of': ['RequestOrResponseMixin', 'Entity']} })
    metadata: Optional[str] = Field(default=None, description="""An optional arbitrary dictionary of further request metadata.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['RequestOrResponseMixin']} })


class Entity(ConfiguredBaseModel):
    """
    An entity is a representation of a real-world entity, as provided by the ERS.
    It contains the entity data (e.g. RDF description) along with metadata about
    the entity, such as its type and the data format used to represent it.

    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://data.europa.eu/ers/schema'})

    id: Optional[str] = Field(default=None, description="""A string containing the entity ID or URI (set by the ERS or, for canonical entities, by the ERE).

Note that the ID isn't mandatory when an entity is submitted for resolution, since the initial input
might be something like unstructured text, where the entity and its ID is to be recognised.        
""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'CanonicalEntity']} })
    type: str = Field(default=..., description="""A string representing the entity type URI (based on CET).

Note that we don't use the `designates_type` thing here, since entities or canonical entities 
are always used in clearly distinct contexts.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['RequestOrResponseMixin', 'Entity']} })
    entityDataFormat: Optional[str] = Field(default=None, description="""A string about the MIME format of `entityData` (e.g. text/turtle, application/ld+json)
""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity']} })
    entityData: Optional[str] = Field(default=None, description="""A code string representing the entity details (eg, RDF description).
""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity']} })


class CanonicalEntity(Entity):
    """
    A canonical entity is an entity that the ERE has created during the resolution process
    of ERS entities.

    TODO: we don't support lineage for the moment, see the ERE contract document.

    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://data.europa.eu/ers/schema'})

    id: str = Field(default=..., description="""The (canonical) URI of the canonical entity. This restricts the parent range to URIs only.

Contrary to `Entity.id`, this is always known/required for canonical entities.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity', 'CanonicalEntity']} })
    type: str = Field(default=..., description="""A string representing the entity type URI (based on CET).

Note that we don't use the `designates_type` thing here, since entities or canonical entities 
are always used in clearly distinct contexts.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['RequestOrResponseMixin', 'Entity']} })
    entityDataFormat: Optional[str] = Field(default=None, description="""A string about the MIME format of `entityData` (e.g. text/turtle, application/ld+json)
""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity']} })
    entityData: Optional[str] = Field(default=None, description="""A code string representing the entity details (eg, RDF description).
""", json_schema_extra = { "linkml_meta": {'domain_of': ['Entity']} })


class RebuildRequest(Request):
    """
    A request to reset all the resolutions computed so far and rebuild them as 
    requests about old entities arrive again (and build new entities from scratch).

    It is expected that the ERE client re-sends all the entities to be resolved again,
    using `EntityResolutionRequest` messages exactly as the first time the resolutions 
    were built. This implies the a client like the ERS logs/persists the entities it receives
    to resolve and also saves manual overriding of ERE results.

    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://data.europa.eu/ers/schema'})

    requestId: str = Field(default=..., description="""A string representing the unique ID of this request.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['Request', 'Response']} })
    originator: str = Field(default=..., description="""The ID or URI of the request originator.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['Request']} })
    type: Literal["RebuildRequest"] = Field(default="RebuildRequest", description="""The type of the request or result.

As per LinkML specification, `designates_type` is used here in order to allow for this
slot to tell the concrete subclass that an instance (such as a JSON object) belongs to.

In other words, a particular request will have `type` set with values like 
`EntityResolutionRequest` or `EntityResolutionResult`
""", json_schema_extra = { "linkml_meta": {'designates_type': True, 'domain_of': ['RequestOrResponseMixin', 'Entity']} })
    metadata: Optional[str] = Field(default=None, description="""An optional arbitrary dictionary of further request metadata.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['RequestOrResponseMixin']} })


class RebuildResponse(Response):
    """
    A response to a `RebuildRequest`, confirming that the rebuild process has started.

    This should carry the `requestId` attribute.

    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://data.europa.eu/ers/schema'})

    requestId: str = Field(default=..., description="""A string representing the unique ID of the request this response is about.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['Request', 'Response']} })
    type: Literal["RebuildResponse"] = Field(default="RebuildResponse", description="""The type of the request or result.

As per LinkML specification, `designates_type` is used here in order to allow for this
slot to tell the concrete subclass that an instance (such as a JSON object) belongs to.

In other words, a particular request will have `type` set with values like 
`EntityResolutionRequest` or `EntityResolutionResult`
""", json_schema_extra = { "linkml_meta": {'designates_type': True, 'domain_of': ['RequestOrResponseMixin', 'Entity']} })
    metadata: Optional[str] = Field(default=None, description="""An optional arbitrary dictionary of further request metadata.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['RequestOrResponseMixin']} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
RequestOrResponseMixin.model_rebuild()
Request.model_rebuild()
Response.model_rebuild()
EntityResolutionRequest.model_rebuild()
EntityResolutionResponse.model_rebuild()
ErrorResponse.model_rebuild()
Entity.model_rebuild()
CanonicalEntity.model_rebuild()
RebuildRequest.model_rebuild()
RebuildResponse.model_rebuild()
