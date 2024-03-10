# -*- coding: utf-8 -*-
# MinIO Python Library for Amazon S3 Compatible Cloud Storage, (C)
# 2020 MinIO, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=too-many-lines

"""
Response of ListBuckets, ListObjects, ListObjectsV2 and ListObjectVersions API.
"""

from __future__ import absolute_import, annotations

from datetime import datetime
from typing import Type, TypeVar, cast
from urllib.parse import unquote_plus
from xml.etree import ElementTree as ET

from urllib3._collections import HTTPHeaderDict

try:
    from urllib3.response import BaseHTTPResponse  # type: ignore[attr-defined]
except ImportError:
    from urllib3.response import HTTPResponse as BaseHTTPResponse

from .time import from_iso8601utc
from .xml import find, findall, findtext


class Bucket:
    """Bucket information."""

    def __init__(self, name: str, creation_date: datetime | None):
        self._name = name
        self._creation_date = creation_date

    @property
    def name(self) -> str:
        """Get name."""
        return self._name

    @property
    def creation_date(self) -> datetime | None:
        """Get creation date."""
        return self._creation_date

    def __repr__(self):
        return f"{type(self).__name__}('{self.name}')"

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, Bucket):
            return self.name == other.name
        if isinstance(other, str):
            return self.name == other
        return NotImplemented

    def __hash__(self):
        return hash(self.name)


B = TypeVar("B", bound="Object")


class Object:
    """Object information."""

    def __init__(  # pylint: disable=too-many-arguments
            self,
            bucket_name: str,
            object_name: str | None,
            last_modified: datetime | None = None,
            etag: str | None = None,
            size: int | None = None,
            metadata: dict[str, str] | HTTPHeaderDict | None = None,
            version_id: str | None = None,
            is_latest: str | None = None,
            storage_class: str | None = None,
            owner_id: str | None = None,
            owner_name: str | None = None,
            content_type: str | None = None,
            is_delete_marker: bool = False,
    ):
        self._bucket_name = bucket_name
        self._object_name = object_name
        self._last_modified = last_modified
        self._etag = etag
        self._size = size
        self._metadata = metadata
        self._version_id = version_id
        self._is_latest = is_latest
        self._storage_class = storage_class
        self._owner_id = owner_id
        self._owner_name = owner_name
        self._content_type = content_type
        self._is_delete_marker = is_delete_marker

    @property
    def bucket_name(self) -> str:
        """Get bucket name."""
        return self._bucket_name

    @property
    def object_name(self) -> str | None:
        """Get object name."""
        return self._object_name

    @property
    def is_dir(self) -> bool:
        """Get whether this key is a directory."""
        return (
            self._object_name is not None and self._object_name.endswith("/")
        )

    @property
    def last_modified(self) -> datetime | None:
        """Get last modified time."""
        return self._last_modified

    @property
    def etag(self) -> str | None:
        """Get etag."""
        return self._etag

    @property
    def size(self) -> int | None:
        """Get size."""
        return self._size

    @property
    def metadata(self) -> dict[str, str] | HTTPHeaderDict | None:
        """Get metadata."""
        return self._metadata

    @property
    def version_id(self) -> str | None:
        """Get version ID."""
        return self._version_id

    @property
    def is_latest(self) -> str | None:
        """Get is-latest flag."""
        return self._is_latest

    @property
    def storage_class(self) -> str | None:
        """Get storage class."""
        return self._storage_class

    @property
    def owner_id(self) -> str | None:
        """Get owner ID."""
        return self._owner_id

    @property
    def owner_name(self) -> str | None:
        """Get owner name."""
        return self._owner_name

    @property
    def is_delete_marker(self) -> bool:
        """Get whether this key is a delete marker."""
        return self._is_delete_marker

    @property
    def content_type(self) -> str | None:
        """Get content type."""
        return self._content_type

    @classmethod
    def fromxml(
            cls: Type[B],
            element: ET.Element,
            bucket_name: str,
            is_delete_marker: bool = False,
            encoding_type: str | None = None,
    ) -> B:
        """Create new object with values from XML element."""
        tag = findtext(element, "LastModified")
        last_modified = None if tag is None else from_iso8601utc(tag)

        tag = findtext(element, "ETag")
        etag = None if tag is None else tag.replace('"', "")

        tag = findtext(element, "Size")
        size = None if tag is None else int(tag)

        elem = find(element, "Owner")
        owner_id, owner_name = (
            (None, None) if elem is None
            else (findtext(elem, "ID"), findtext(elem, "DisplayName"))
        )

        elems: ET.Element | list = find(element, "UserMetadata") or []
        metadata: dict[str, str] = {}
        for child in elems:
            key = child.tag.split("}")[1] if "}" in child.tag else child.tag
            metadata[key] = child.text or ""

        object_name = cast(str, findtext(element, "Key", True))
        if encoding_type == "url":
            object_name = unquote_plus(object_name)

        return cls(
            bucket_name,
            object_name,
            last_modified=last_modified,
            etag=etag,
            size=size,
            version_id=findtext(element, "VersionId"),
            is_latest=findtext(element, "IsLatest"),
            storage_class=findtext(element, "StorageClass"),
            owner_id=owner_id,
            owner_name=owner_name,
            metadata=metadata,
            is_delete_marker=is_delete_marker,
        )


def parse_list_objects(
        response: BaseHTTPResponse,
        bucket_name: str | None = None,
) -> tuple[list[Object], bool, str | None, str | None]:
    """Parse ListObjects/ListObjectsV2/ListObjectVersions response."""
    element = ET.fromstring(response.data.decode())
    bucket_name = cast(str, findtext(element, "Name", True))
    encoding_type = findtext(element, "EncodingType")
    elements = findall(element, "Contents")
    objects = [
        Object.fromxml(tag, bucket_name, encoding_type=encoding_type)
        for tag in elements
    ]
    marker = objects[-1].object_name if objects else None

    elements = findall(element, "Version")
    objects += [
        Object.fromxml(tag, bucket_name, encoding_type=encoding_type)
        for tag in elements
    ]

    elements = findall(element, "CommonPrefixes")
    objects += [
        Object(
            bucket_name, unquote_plus(findtext(tag, "Prefix", True) or "")
            if encoding_type == "url" else findtext(tag, "Prefix", True)
        ) for tag in elements
    ]

    elements = findall(element, "DeleteMarker")
    objects += [
        Object.fromxml(tag, bucket_name, is_delete_marker=True,
                       encoding_type=encoding_type)
        for tag in elements
    ]

    is_truncated = (findtext(element, "IsTruncated") or "").lower() == "true"
    key_marker = findtext(element, "NextKeyMarker")
    if key_marker and encoding_type == "url":
        key_marker = unquote_plus(key_marker)
    version_id_marker = findtext(element, "NextVersionIdMarker")
    continuation_token = findtext(element, "NextContinuationToken")
    if key_marker is not None:
        continuation_token = key_marker
    if continuation_token is None:
        continuation_token = findtext(element, "NextMarker")
        if continuation_token and encoding_type == "url":
            continuation_token = unquote_plus(continuation_token)
    if continuation_token is None and is_truncated:
        continuation_token = marker
    return objects, is_truncated, continuation_token, version_id_marker


