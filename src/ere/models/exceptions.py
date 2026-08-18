"""Domain exceptions for entity resolution."""


class ConflictError(Exception):
    """Raised when the same mention_id is submitted with different content."""

    def __init__(
        self, mention_id: str, existing_attributes: dict, incoming_attributes: dict
    ):
        super().__init__(
            f"Mention '{mention_id}' was already resolved with different content. "
            f"Existing: {existing_attributes!r}, Incoming: {incoming_attributes!r}"
        )
        self.mention_id = mention_id
        self.existing_attributes = existing_attributes
        self.incoming_attributes = incoming_attributes
