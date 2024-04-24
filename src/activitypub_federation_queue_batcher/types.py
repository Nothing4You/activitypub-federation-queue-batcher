from dataclasses import dataclass, field
from datetime import datetime

from dataclasses_json import DataClassJsonMixin, config
from marshmallow import fields


@dataclass
class SerializableActivitySubmission(DataClassJsonMixin):
    time: datetime = field(
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format="iso"),
        ),
    )
    activity_id: str
    host: str
    path: str
    headers: list[list[str]]
    b64_body: str


@dataclass
class UpstreamSubmissionResponse(DataClassJsonMixin):
    time: datetime = field(
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format="iso"),
        ),
    )
    activity_id: str
    status: int
    headers: list[list[str]]
    content_type: str | None
    body: str | None
