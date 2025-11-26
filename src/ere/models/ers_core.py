# TODO: WARNING: this is temporarily copied here from the er-system repo.
# We need to setup proper packaging and dependency management
#

from __future__ import annotations

import re
import sys
from datetime import (
    date,
    datetime,
    time
)
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional,
    Union
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer
)


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


class EntityResolution(Response):
    """
    An entity resolution response sent by the ERE.

    This contains a reference to the canonical entity that the ERE has associated to the original 
    entity in the request. It also reports a confidence score for the established association.

    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'examples': [{'value': '{\n'
                                '  "type": "EntityResolution",\n'
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
""", json_schema_extra = { "linkml_meta": {'domain_of': ['EntityResolution']} })
    sourceEntityId: str = Field(default=..., description="""The ID or URI of the original entity that has been resolved.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['EntityResolution']} })
    confidenceLevel: Optional[float] = Field(default=None, description="""A 0-1 value of how confident the ERE is about associating the original entity
with the canonical entity's cluster.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['EntityResolution']} })
    requestId: str = Field(default=..., description="""A string representing the unique ID of the request this response is about.
""", json_schema_extra = { "linkml_meta": {'domain_of': ['Request', 'Response']} })
    type: Literal["EntityResolution"] = Field(default="EntityResolution", description="""The type of the request or result.

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

    id: str = Field(default=..., description="""A string containing the entity ID or URI (set by the ERS or, for canonical entities, by the ERE).
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

    id: Optional[str] = Field(default=None, description="""The (canonical) URI of the canonical entity. This restricts the parent range to URIs only.
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
EntityResolution.model_rebuild()
Entity.model_rebuild()
CanonicalEntity.model_rebuild()
RebuildRequest.model_rebuild()
RebuildResponse.model_rebuild()
