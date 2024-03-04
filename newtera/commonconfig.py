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

"""Common request/response configuration of S3 APIs."""
# pylint: disable=invalid-name

from __future__ import absolute_import, annotations

from abc import ABCMeta
from datetime import datetime
from typing import Type, TypeVar, cast
from xml.etree import ElementTree as ET

from .error import NewteraException
from .helpers import quote
from .sse import SseCustomerKey
from .time import to_http_header
from .xml import SubElement, find, findall, findtext

COPY = "COPY"
REPLACE = "REPLACE"
DISABLED = "Disabled"
ENABLED = "Enabled"
GOVERNANCE = "GOVERNANCE"
COMPLIANCE = "COMPLIANCE"
_MAX_KEY_LENGTH = 128
_MAX_VALUE_LENGTH = 256
_MAX_OBJECT_TAG_COUNT = 10
_MAX_TAG_COUNT = 50

A = TypeVar("A", bound="Tags")


class Tags(dict):
    """dict extended to bucket/object tags."""

    def __init__(self, for_object: bool = False):
        self._for_object = for_object
        super().__init__()

    def __setitem__(self, key: str, value: str):
        limit = _MAX_OBJECT_TAG_COUNT if self._for_object else _MAX_TAG_COUNT
        if len(self) == limit:
            tag_type = "object" if self._for_object else "bucket"
            raise ValueError(f"only {limit} {tag_type} tags are allowed")
        if not key or len(key) > _MAX_KEY_LENGTH or "&" in key:
            raise ValueError(f"invalid tag key '{key}'")
        if value is None or len(value) > _MAX_VALUE_LENGTH or "&" in value:
            raise ValueError(f"invalid tag value '{value}'")
        super().__setitem__(key, value)

    @classmethod
    def new_bucket_tags(cls: Type[A]) -> A:
        """Create new bucket tags."""
        return cls()

    @classmethod
    def new_object_tags(cls: Type[A]) -> A:
        """Create new object tags."""
        return cls(True)

    @classmethod
    def fromxml(cls: Type[A], element: ET.Element) -> A:
        """Create new object with values from XML element."""
        elements = findall(element, "Tag")
        obj = cls()
        for tag in elements:
            key = cast(str, findtext(tag, "Key", True))
            value = cast(str, findtext(tag, "Value", True))
            obj[key] = value
        return obj

    def toxml(self, element: ET.Element | None) -> ET.Element:
        """Convert to XML."""
        if element is None:
            raise ValueError("element must be provided")
        for key, value in self.items():
            tag = SubElement(element, "Tag")
            SubElement(tag, "Key", key)
            SubElement(tag, "Value", value)
        return element


B = TypeVar("B", bound="Tag")


class Tag:
    """Tag."""

    def __init__(self, key: str, value: str):
        if not key:
            raise ValueError("key must be provided")
        if value is None:
            raise ValueError("value must be provided")
        self._key = key
        self._value = value

    @property
    def key(self) -> str:
        """Get key."""
        return self._key

    @property
    def value(self) -> str:
        """Get value."""
        return self._value

    @classmethod
    def fromxml(cls: Type[B], element: ET.Element) -> B:
        """Create new object with values from XML element."""
        element = cast(ET.Element, find(element, "Tag", True))
        key = cast(str, findtext(element, "Key", True))
        value = cast(str, findtext(element, "Value", True))
        return cls(key, value)

    def toxml(self, element: ET.Element | None) -> ET.Element:
        """Convert to XML."""
        if element is None:
            raise ValueError("element must be provided")
        element = SubElement(element, "Tag")
        SubElement(element, "Key", self._key)
        SubElement(element, "Value", self._value)
        return element


C = TypeVar("C", bound="AndOperator")


class AndOperator:
    """AND operator."""

    def __init__(self, prefix: str | None = None, tags: Tags | None = None):
        if prefix is None and not tags:
            raise ValueError("at least prefix or tags must be provided")
        self._prefix = prefix
        self._tags = tags

    @property
    def prefix(self) -> str | None:
        """Get prefix."""
        return self._prefix

    @property
    def tags(self) -> Tags | None:
        """Get tags."""
        return self._tags

    @classmethod
    def fromxml(cls: Type[C], element: ET.Element) -> C:
        """Create new object with values from XML element."""
        element = cast(ET.Element, find(element, "And", True))
        prefix = findtext(element, "Prefix")
        tags = (
            None if find(element, "Tag") is None
            else Tags.fromxml(element)
        )
        return cls(prefix, tags)

    def toxml(self, element: ET.Element | None) -> ET.Element:
        """Convert to XML."""
        if element is None:
            raise ValueError("element must be provided")
        element = SubElement(element, "And")
        if self._prefix is not None:
            SubElement(element, "Prefix", self._prefix)
        if self._tags is not None:
            self._tags.toxml(element)
        return element


D = TypeVar("D", bound="Filter")


class Filter:
    """Lifecycle rule filter."""

    def __init__(
            self,
            and_operator: AndOperator | None = None,
            prefix: str | None = None,
            tag: Tag | None = None,
    ):
        valid = (
            (and_operator is not None) ^
            (prefix is not None) ^
            (tag is not None)
        )
        if not valid:
            raise ValueError("only one of and, prefix or tag must be provided")
        self._and_operator = and_operator
        self._prefix = prefix
        self._tag = tag

    @property
    def and_operator(self) -> AndOperator | None:
        """Get AND operator."""
        return self._and_operator

    @property
    def prefix(self) -> str | None:
        """Get prefix."""
        return self._prefix

    @property
    def tag(self) -> Tag | None:
        """Get tag."""
        return self._tag

    @classmethod
    def fromxml(cls: Type[D], element: ET.Element) -> D:
        """Create new object with values from XML element."""
        element = cast(ET.Element, find(element, "Filter", True))
        and_operator = (
            None if find(element, "And") is None
            else AndOperator.fromxml(element)
        )
        prefix = findtext(element, "Prefix")
        tag = None if find(element, "Tag") is None else Tag.fromxml(element)
        return cls(and_operator, prefix, tag)

    def toxml(self, element: ET.Element | None) -> ET.Element:
        """Convert to XML."""
        if element is None:
            raise ValueError("element must be provided")
        element = SubElement(element, "Filter")
        if self._and_operator:
            self._and_operator.toxml(element)
        if self._prefix is not None:
            SubElement(element, "Prefix", self._prefix)
        if self._tag is not None:
            self._tag.toxml(element)
        return element


class BaseRule:
    """Base rule class for Replication and Lifecycle."""
    __metaclass__ = ABCMeta

    def __init__(
            self,
            rule_filter: Filter | None = None,
            rule_id: str | None = None,
    ):
        if rule_id is not None:
            rule_id = rule_id.strip()
            if not rule_id:
                raise ValueError("rule ID must be non-empty string")
            if len(rule_id) > 255:
                raise ValueError("rule ID must not exceed 255 characters")
        self._rule_filter = rule_filter
        self._rule_id = rule_id

    @property
    def rule_filter(self) -> Filter | None:
        """Get replication rule filter."""
        return self._rule_filter

    @property
    def rule_id(self) -> str | None:
        """Get rule ID."""
        return self._rule_id

    @staticmethod
    def parsexml(element: ET.Element) -> tuple[Filter | None, str | None]:
        """Parse XML and return filter and ID."""
        return (
            None if find(element, "Filter") is None
            else Filter.fromxml(element)
        ), findtext(element, "ID")

    def toxml(self, element: ET.Element | None) -> ET.Element:
        """Convert to XML."""
        if element is None:
            raise ValueError("element must be provided")
        if self._rule_filter:
            self._rule_filter.toxml(element)
        if self._rule_id is not None:
            SubElement(element, "ID", self._rule_id)
        return element


def check_status(status: str):
    """Validate status."""
    if status not in [ENABLED, DISABLED]:
        raise ValueError("status must be 'Enabled' or 'Disabled'")


class ObjectConditionalReadArgs:
    """Base argument class holds condition properties for reading object."""
    __metaclass__ = ABCMeta

    def __init__(
            self,
            bucket_name: str,
            object_name: str,
            region: str | None = None,
            version_id: str | None = None,
            ssec: SseCustomerKey | None = None,
            offset: int | None = None,
            length: int | None = None,
            match_etag: str | None = None,
            not_match_etag: str | None = None,
            modified_since: str | None = None,
            unmodified_since: str | None = None,
    ):
        if ssec is not None and not isinstance(ssec, SseCustomerKey):
            raise ValueError("ssec must be SseCustomerKey type")
        if offset is not None and offset < 0:
            raise ValueError("offset should be zero or greater")
        if length is not None and length <= 0:
            raise ValueError("length should be greater than zero")
        if match_etag is not None and match_etag == "":
            raise ValueError("match_etag must not be empty")
        if not_match_etag is not None and not_match_etag == "":
            raise ValueError("not_match_etag must not be empty")
        if (
                modified_since is not None and
                not isinstance(modified_since, datetime)
        ):
            raise ValueError("modified_since must be datetime type")
        if (
                unmodified_since is not None and
                not isinstance(unmodified_since, datetime)
        ):
            raise ValueError("unmodified_since must be datetime type")

        self._bucket_name = bucket_name
        self._object_name = object_name
        self._region = region
        self._version_id = version_id
        self._ssec = ssec
        self._offset = offset
        self._length = length
        self._match_etag = match_etag
        self._not_match_etag = not_match_etag
        self._modified_since = modified_since
        self._unmodified_since = unmodified_since

    @property
    def bucket_name(self) -> str:
        """Get bucket name."""
        return self._bucket_name

    @property
    def object_name(self) -> str:
        """Get object name."""
        return self._object_name

    @property
    def region(self) -> str | None:
        """Get region."""
        return self._region

    @property
    def version_id(self) -> str | None:
        """Get version ID."""
        return self._version_id

    @property
    def ssec(self) -> SseCustomerKey | None:
        """Get SSE-C."""
        return self._ssec

    @property
    def offset(self) -> int | None:
        """Get offset."""
        return self._offset

    @property
    def length(self) -> int | None:
        """Get length."""
        return self._length

    @property
    def match_etag(self) -> str | None:
        """Get match ETag condition."""
        return self._match_etag

    @property
    def not_match_etag(self) -> str | None:
        """Get not-match ETag condition."""
        return self._not_match_etag

    @property
    def modified_since(self) -> str | None:
        """Get modified since condition."""
        return self._modified_since

    @property
    def unmodified_since(self) -> str | None:
        """Get unmodified since condition."""
        return self._unmodified_since

    def gen_copy_headers(self) -> dict[str, str]:
        """Generate copy source headers."""
        copy_source = quote("/" + self._bucket_name + "/" + self._object_name)
        if self._version_id:
            copy_source += "?versionId=" + quote(self._version_id)

        headers = {"x-amz-copy-source": copy_source}
        if self._ssec:
            headers.update(self._ssec.copy_headers())
        if self._match_etag:
            headers["x-amz-copy-source-if-match"] = self._match_etag
        if self._not_match_etag:
            headers["x-amz-copy-source-if-none-match"] = self._not_match_etag
        if self._modified_since:
            headers["x-amz-copy-source-if-modified-since"] = (
                to_http_header(self._modified_since)
            )
        if self._unmodified_since:
            headers["x-amz-copy-source-if-unmodified-since"] = (
                to_http_header(self._unmodified_since)
            )
        return headers


E = TypeVar("E", bound="CopySource")


class CopySource(ObjectConditionalReadArgs):
    @classmethod
    def of(cls: Type[E], src: ObjectConditionalReadArgs) -> E:
        """Create CopySource from another source."""
        return cls(
            src.bucket_name, src.object_name, src.region, src.version_id,
            src.ssec, src.offset, src.length, src.match_etag,
            src.not_match_etag, src.modified_since, src.unmodified_since,
        )


F = TypeVar("F", bound="ComposeSource")
