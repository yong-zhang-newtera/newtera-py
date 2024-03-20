# -*- coding: utf-8 -*-
# Newtera Python Library for Newtera TDM, (C)
# 2020 Newtera, Inc.
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
Response of ListBuckets, ListObjects, API.
"""

from __future__ import absolute_import, annotations

from datetime import datetime
from typing import TypeVar
from xml.etree import ElementTree as ET

from urllib3._collections import HTTPHeaderDict

try:
    from urllib3.response import BaseHTTPResponse  # type: ignore[attr-defined]
except ImportError:
    from urllib3.response import HTTPResponse as BaseHTTPResponse

import json
from types import SimpleNamespace

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

class ObjectModel:
    """Object model."""

    def __init__(  # pylint: disable=too-many-arguments
            self,
            id: str,
            name: str,
            description: str |None,
            created: datetime | None,
            modified: datetime | None,
            size: str | None,
            type: str | None,
            suffix: str | None,
            instanceId: str | None,
            className: str | None,
            creator: str | None,
    ):
        self._id = id
        self._name = name
        self._description = description
        self._created = created
        self._modified = modified
        self._size = size
        self._type = type
        self._suffix = suffix
        self._instanceId = instanceId
        self._className = className
        self._creator = creator

    @property
    def id(self) -> str:
        """Get id."""
        return self._id

    @property
    def name(self) -> str | None:
        """Get object name."""
        return self._name

    @property
    def created(self) -> datetime | None:
        """Get created time."""
        return self._created

    @property
    def modified(self) -> datetime | None:
        """Get created time."""
        return self._modified

    @property
    def size(self) -> str | None:
        """Get size."""
        return self._size

    @property
    def type(self) -> str | None:
        """Get is-latest flag."""
        return self._type

    @property
    def suffix(self) -> str | None:
        """Get object suffix."""
        return self._suffix

    @property
    def className(self) -> str | None:
        """Get class name."""
        return self._className

    @property
    def creator(self) -> str | None:
        """Get creator name."""
        return self._creator


def parse_list_objects(
        response: BaseHTTPResponse,
        bucket_name: str | None = None,
) -> list[Object]:

    objectList = []
    jsonData = json.loads(response.data, object_hook=lambda d: SimpleNamespace(**d))

    for o in jsonData.files:
        obj = ObjectModel(o.id, o.name, o.description, o.created, o.modified, o.size, o.type, o.suffix, o.instanceId, o.className, o.creator)
        objectList.append(obj)

    return objectList


