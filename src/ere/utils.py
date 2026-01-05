# These are used by get_message_object() to map 'type' fields in JSON representations to
# domain model (LinkML) classes.
#
# TODO: open-closed principle. For now, we don't see much need to extend these
# TODO: move to a utils module
#
import json
from linkml_runtime.dumpers import JSONDumper
from linkml_runtime.loaders import JSONLoader
from ere.models.ers_core import EntityResolutionRequest, EntityResolutionResponse, ErrorResponse, RebuildRequest, RebuildResponse, Request, RequestOrResponseMixin, Response

SUPPORTED_REQUEST_CLASSES = {
	cls.__name__: cls for cls in [ EntityResolutionRequest, RebuildRequest ]
}
"""
Explicit list of supported Request classes, used in utilities like :meth:`get_request_from_message`.

TODO: Refactor according to the open-closed principle. For now, we don't expect many extensions to these
types, so, we keep it simple.
"""

SUPPORTED_RESPONSE_CLASSES = {
	cls.__name__: cls for cls in [ EntityResolutionResponse, RebuildResponse, ErrorResponse ]
}
"""
Explicit list of supported Response classes, used in utilities like :meth:`get_response_from_message`.

TODO: open-closed principle, see above.
"""

_linkml_loader = JSONLoader () # Just to cache it


def get_message_object (
	raw_msg: bytes,
	supported_classes: dict [str, RequestOrResponseMixin],
	character_encoding: str = 'utf-8'
) -> RequestOrResponseMixin:
	"""
	Helper to parse a raw message (bytes) coming from places like a Redis queue into a Request/Response object.

	This parses the initial input into JSON, then it uses the LinkML facilities to create domain model
	instances from the JSON. This requires the :param:`supported_classes` dict to map the 'type' field
	in the JSON to the corresponding class.
	"""

	msg_str = raw_msg.decode ( character_encoding )
	msg_json = json.loads ( msg_str )

	message_type = msg_json.get ( 'type' )
	if not message_type:
		raise ValueError ( "ERE: message without 'type' field" )

	cls = supported_classes.get ( message_type )
	if not cls:
		raise ValueError ( f"ERE: unsupported message class: \"{message_type}\"" )

	return _linkml_loader.load_any (
		source = msg_json, target_class = cls
	)


def get_response_from_message (
	raw_msg: bytes,
	character_encoding: str = 'utf-8'
) -> Response :
	"""
	Helper to parse a raw message (bytes) coming from places like a Redis queue into a Response object.

	This is a simple wrapper around :meth:`get_message_object`.
	"""
	return get_message_object ( raw_msg, SUPPORTED_RESPONSE_CLASSES, character_encoding )


def get_request_from_message (
	raw_msg: bytes,
	character_encoding: str = 'utf-8'
) -> Request :
	"""
	Helper to parse a raw message (bytes) coming from places like a Redis queue into a Request object.

	This is a simple wrapper around :meth:`get_message_object`.
	"""

	return get_message_object ( raw_msg, SUPPORTED_REQUEST_CLASSES, character_encoding )