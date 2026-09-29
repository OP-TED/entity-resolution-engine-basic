# These are used by get_message_object() to map 'type' fields in JSON representations to
# domain model (LinkML) classes.
#
# TODO: open-closed principle. For now, we don't see much need to extend these
# TODO: move to a utils module
# pylint: disable=C0104
#
import json

from linkml_runtime.loaders import JSONLoader

from erspec.models.ere import (
    EntityMentionResolutionRequest,
    EntityMentionResolutionResponse,
    EREErrorResponse,
    # FullRebuildRequest,  # TODO: Not yet implemented in erspec.models.ere
    # FullRebuildResponse,  # TODO: Not yet implemented in erspec.models.ere
    ERERequest,
    EREMessage,
    EREResponse,
)

SUPPORTED_REQUEST_CLASSES = {
    cls.__name__: cls
    for cls in [
        EntityMentionResolutionRequest
    ]
}
"""
Explicit list of supported Request classes, used in utilities like :meth:`get_request_from_message`.

TODO: Refactor according to the open-closed principle. For now, we don't expect many extensions to these
types, so, we keep it simple.

Note: FullRebuildRequest not yet implemented in erspec; add when available.
"""

SUPPORTED_RESPONSE_CLASSES = {
    cls.__name__: cls
    for cls in [
        EntityMentionResolutionResponse,
        EREErrorResponse,
    ]
}
"""
Explicit list of supported Response classes, used in utilities like :meth:`get_response_from_message`.

TODO: open-closed principle, see above.

Note: FullRebuildResponse not yet implemented in erspec; add when available.
"""

_linkml_loader = JSONLoader()  # Just to cache it


def get_message_object(
    raw_msg: bytes,
    supported_classes: dict[str, EREMessage],
    character_encoding: str = "utf-8",
) -> EREMessage:
    """
    Helper to parse a raw message (bytes) coming from places like a Redis queue into a Request/Response object.

    This parses the initial input into JSON, then it uses the LinkML facilities to create domain model
    instances from the JSON. This requires the :param:`supported_classes` dict to map the 'type' field
    in the JSON to the corresponding class.
    """

    msg_str = raw_msg.decode(character_encoding)
    msg_json = json.loads(msg_str)

    message_type = msg_json.get("type")
    if not message_type:
        raise ValueError("ERE: message without 'type' field")

    cls = supported_classes.get(message_type)
    if not cls:
        raise ValueError(f'ERE: unsupported message class: "{message_type}"')

    return _linkml_loader.load_any(source=msg_json, target_class=cls)


def get_response_from_message(
    raw_msg: bytes, character_encoding: str = "utf-8"
) -> EREResponse:
    """
    Helper to parse a raw message (bytes) coming from places like a Redis queue into a Response object.

    This is a simple wrapper around :meth:`get_message_object`.
    """
    return get_message_object(raw_msg, SUPPORTED_RESPONSE_CLASSES, character_encoding)


def get_request_from_message(
    raw_msg: bytes, character_encoding: str = "utf-8"
) -> ERERequest:
    """
    Helper to parse a raw message (bytes) coming from places like a Redis queue into a Request object.

    This is a simple wrapper around :meth:`get_message_object`.
    """

    return get_message_object(raw_msg, SUPPORTED_REQUEST_CLASSES, character_encoding)
