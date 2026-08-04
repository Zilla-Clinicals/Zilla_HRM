from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

DocumentKind = Literal[
    "degree",
    "id_document",
    "offer_letter",
    "employment_letter",
    "promotion_letter",
    "other",
]

# What a filed document may be (photos use a separate endpoint).
DOCUMENT_KINDS = {
    "degree",
    "id_document",
    "offer_letter",
    "employment_letter",
    "promotion_letter",
    "other",
}

PHOTO_KIND = "photo"

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_DOCUMENT_TYPES = ALLOWED_IMAGE_TYPES | {
    "application/pdf",
    "image/gif",
    "text/plain",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    kind: str
    title: str
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
