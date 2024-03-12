# -*- coding: utf-8 -*-
# MinIO Python Library for Amazon S3 Compatible Cloud Storage, (C)
# 2015, 2016, 2017 MinIO, Inc.
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

"""Helper functions."""

from __future__ import absolute_import, annotations, division, unicode_literals

import errno
import math
import os
import re
import urllib.parse
from datetime import datetime
from typing import BinaryIO, Dict, List, Mapping, Tuple, Union

from urllib3._collections import HTTPHeaderDict

from . import __title__, __version__

MAX_MULTIPART_COUNT = 10000  # 10000 parts
MAX_MULTIPART_OBJECT_SIZE = 5 * 1024 * 1024 * 1024 * 1024  # 5TiB
MAX_PART_SIZE = 5 * 1024 * 1024 * 1024  # 5GiB
MIN_PART_SIZE = 5 * 1024 * 1024  # 5MiB

_BUCKET_NAME_REGEX = re.compile(r'^[a-z0-9][a-z0-9\.\-]{1,61}[a-z0-9]$')
_OLD_BUCKET_NAME_REGEX = re.compile(r'^[a-z0-9][a-z0-9_\.\-\:]{1,61}[a-z0-9]$',
                                    re.IGNORECASE)
_IPV4_REGEX = re.compile(
    r'^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])\.){3}'
    r'(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])$')

DictType = Dict[str, Union[str, List[str], Tuple[str]]]


def quote(
        resource: str,
        safe: str = "/",
        encoding: str | None = None,
        errors: str | None = None,
) -> str:
    """
    Wrapper to urllib.parse.quote() replacing back to '~' for older python
    versions.
    """
    return urllib.parse.quote(
        resource,
        safe=safe,
        encoding=encoding,
        errors=errors,
    ).replace("%7E", "~")


def queryencode(
        query: str,
        safe: str = "",
        encoding: str | None = None,
        errors: str | None = None,
) -> str:
    """Encode query parameter value."""
    return quote(query, safe, encoding, errors)


def headers_to_strings(
        headers: Mapping[str, str | list[str] | tuple[str]],
        titled_key: bool = False,
) -> str:
    """Convert HTTP headers to multi-line string."""
    values = []
    for key, value in headers.items():
        key = key.title() if titled_key else key
        for item in value if isinstance(value, (list, tuple)) else [value]:
            item = re.sub(
                r"Credential=([^/]+)",
                "Credential=*REDACTED*",
                re.sub(r"Signature=([0-9a-f]+)", "Signature=*REDACTED*", item),
            ) if titled_key else item
            values.append(f"{key}: {item}")
    return "\n".join(values)


def _validate_sizes(object_size: int, part_size: int):
    """Validate object and part size."""
    if part_size > 0:
        if part_size < MIN_PART_SIZE:
            raise ValueError(
                f"part size {part_size} is not supported; minimum allowed 5MiB"
            )
        if part_size > MAX_PART_SIZE:
            raise ValueError(
                f"part size {part_size} is not supported; maximum allowed 5GiB"
            )

    if object_size >= 0:
        if object_size > MAX_MULTIPART_OBJECT_SIZE:
            raise ValueError(
                f"object size {object_size} is not supported; "
                f"maximum allowed 5TiB"
            )
    elif part_size <= 0:
        raise ValueError(
            "valid part size must be provided when object size is unknown",
        )


def _get_part_info(object_size: int, part_size: int):
    """Compute part information for object and part size."""
    _validate_sizes(object_size, part_size)

    if object_size < 0:
        return part_size, -1

    if part_size > 0:
        part_size = min(part_size, object_size)
        return part_size, math.ceil(object_size / part_size) if part_size else 1

    part_size = math.ceil(
        math.ceil(object_size / MAX_MULTIPART_COUNT) / MIN_PART_SIZE,
    ) * MIN_PART_SIZE
    return part_size, math.ceil(object_size / part_size) if part_size else 1


def get_part_info(object_size: int, part_size: int) -> tuple[int, int]:
    """Compute part information for object and part size."""
    part_size, part_count = _get_part_info(object_size, part_size)
    if part_count > MAX_MULTIPART_COUNT:
        raise ValueError(
            f"object size {object_size} and part size {part_size} "
            f"make more than {MAX_MULTIPART_COUNT} parts for upload"
        )
    return part_size, part_count


class ProgressType():
    """typing stub for Put/Get object progress."""

    def set_meta(self, object_name: str, total_length: int):
        """Set process meta information."""

    def update(self, length: int):
        """Set current progress length."""


def read_part_data(
        stream: BinaryIO,
        size: int,
        part_data: bytes = b"",
        progress: ProgressType | None = None,
) -> bytes:
    """Read part data of given size from stream."""
    size -= len(part_data)
    while size:
        data = stream.read(size)
        if not data:
            break  # EOF reached
        if not isinstance(data, bytes):
            raise ValueError("read() must return 'bytes' object")
        part_data += data
        size -= len(data)
        if progress:
            progress.update(len(data))
    return part_data


def makedirs(path: str):
    """Wrapper of os.makedirs() ignores errno.EEXIST."""
    try:
        if path:
            os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno != errno.EEXIST:
            raise

        if not os.path.isdir(path):
            raise ValueError(f"path {path} is not a directory") from exc


def check_bucket_name(
        bucket_name: str,
        strict: bool = False,
):
    """Check whether bucket name is valid optional with strict check or not."""

    if strict:
        if not _BUCKET_NAME_REGEX.match(bucket_name):
            raise ValueError(f'invalid bucket name {bucket_name}')
    else:
        if not _OLD_BUCKET_NAME_REGEX.match(bucket_name):
            raise ValueError(f'invalid bucket name {bucket_name}')

    if _IPV4_REGEX.match(bucket_name):
        raise ValueError(f'bucket name {bucket_name} must not be formatted '
                         'as an IP address')

    unallowed_successive_chars = ['..', '.-', '-.']
    if any(x in bucket_name for x in unallowed_successive_chars):
        raise ValueError(f'bucket name {bucket_name} contains invalid '
                         'successive characters')


def check_non_empty_string(string: str | bytes):
    """Check whether given string is not empty."""
    try:
        if not string.strip():
            raise ValueError()
    except AttributeError as exc:
        raise TypeError() from exc


def is_valid_policy_type(policy: str | bytes):
    """
    Validate if policy is type str

    :param policy: S3 style Bucket policy.
    :return: True if policy parameter is of a valid type, 'string'.
    Raise :exc:`TypeError` otherwise.
    """
    if not isinstance(policy, (str, bytes)):
        raise TypeError("policy must be str or bytes type")

    check_non_empty_string(policy)

    return True


def url_replace(
        url: urllib.parse.SplitResult,
        scheme: str | None = None,
        netloc: str | None = None,
        path: str | None = None,
        query: str | None = None,
        fragment: str | None = None,
) -> urllib.parse.SplitResult:
    """Return new URL with replaced properties in given URL."""
    return urllib.parse.SplitResult(
        scheme if scheme is not None else url.scheme,
        netloc if netloc is not None else url.netloc,
        path if path is not None else url.path,
        query if query is not None else url.query,
        fragment if fragment is not None else url.fragment,
    )


def _metadata_to_headers(metadata: DictType) -> dict[str, list[str]]:
    """Convert user metadata to headers."""
    def normalize_key(key: str) -> str:
        if not key.lower().startswith("x-amz-meta-"):
            key = "X-Amz-Meta-" + key
        return key

    def to_string(value) -> str:
        value = str(value)
        try:
            value.encode("us-ascii")
        except UnicodeEncodeError as exc:
            raise ValueError(
                f"unsupported metadata value {value}; "
                f"only US-ASCII encoded characters are supported"
            ) from exc
        return value

    def normalize_value(values: str | list[str] | tuple[str]) -> list[str]:
        if not isinstance(values, (list, tuple)):
            values = [values]
        return [to_string(value) for value in values]

    return {
        normalize_key(key): normalize_value(value)
        for key, value in (metadata or {}).items()
    }


def normalize_headers(headers: DictType | None) -> DictType:
    """Normalize headers by prefixing 'X-Amz-Meta-' for user metadata."""
    headers = {str(key): value for key, value in (headers or {}).items()}

    def guess_user_metadata(key: str) -> bool:
        key = key.lower()
        return not (
            key.startswith("x-amz-") or
            key in [
                "cache-control",
                "content-encoding",
                "content-type",
                "content-disposition",
                "content-language",
            ]
        )

    user_metadata = {
        key: value for key, value in headers.items()
        if guess_user_metadata(key)
    }

    # Remove guessed user metadata.
    _ = [headers.pop(key) for key in user_metadata]

    headers.update(_metadata_to_headers(user_metadata))
    return headers


def genheaders(
        headers: DictType | None,
) -> DictType:
    """Generate headers for given parameters."""
    headers = normalize_headers(headers)
    return headers


def _parse_url(endpoint: str) -> urllib.parse.SplitResult:
    """Parse url string."""

    url = urllib.parse.urlsplit(endpoint)
    host = url.hostname

    if url.scheme.lower() not in ["http", "https"]:
        raise ValueError("scheme in endpoint must be http or https")

    url = url_replace(url, scheme=url.scheme.lower())

    if url.path and url.path != "/":
        raise ValueError("path in endpoint is not allowed")

    url = url_replace(url, path="")

    if url.query:
        raise ValueError("query in endpoint is not allowed")

    if url.fragment:
        raise ValueError("fragment in endpoint is not allowed")

    try:
        url.port
    except ValueError as exc:
        raise ValueError("invalid port") from exc

    if url.username:
        raise ValueError("username in endpoint is not allowed")

    if url.password:
        raise ValueError("password in endpoint is not allowed")

    if (
            (url.scheme == "http" and url.port == 80) or
            (url.scheme == "https" and url.port == 443)
    ):
        url = url_replace(url, netloc=host)

    return url


class BaseURL:
    """Base URL of S3 endpoint."""
    _aws_info: dict | None
    _virtual_style_flag: bool
    _url: urllib.parse.SplitResult
    _accelerate_host_flag: bool

    def __init__(self, endpoint: str):
        url = _parse_url(endpoint)

        self._url = url
        self._accelerate_host_flag = False

    @property
    def is_https(self) -> bool:
        """Check if scheme is HTTPS."""
        return self._url.scheme == "https"

    @property
    def host(self) -> str:
        """Get hostname."""
        return self._url.netloc

    @property
    def accelerate_host_flag(self) -> bool:
        """Get AWS accelerate host flag."""
        return self._accelerate_host_flag

    @accelerate_host_flag.setter
    def accelerate_host_flag(self, flag: bool):
        """Set AWS accelerate host flag."""
        self._accelerate_host_flag = flag

    @property
    def dualstack_host_flag(self) -> bool:
        """Check if URL points to AWS dualstack host."""
        return self._aws_info["dualstack"] if self._aws_info else False

    @dualstack_host_flag.setter
    def dualstack_host_flag(self, flag: bool):
        """Set AWS dualstack host."""
        if self._aws_info:
            self._aws_info["dualstack"] = flag

    @property
    def virtual_style_flag(self) -> bool:
        """Check to use virtual style or not."""
        return self._virtual_style_flag

    @virtual_style_flag.setter
    def virtual_style_flag(self, flag: bool):
        """Check to use virtual style or not."""
        self._virtual_style_flag = flag

    def _build_list_buckets_url(
            self,
            url: urllib.parse.SplitResult,
    ) -> urllib.parse.SplitResult:
        """Build URL for ListBuckets API."""
        if not self._aws_info:
            return url

    def build(
            self,
            method: str,
            request_path: str,
            bucket_name: str | None = None,
            object_name: str | None = None,
            query_params: DictType | None = None,
    ) -> urllib.parse.SplitResult:
        """Build URL for given information."""
        if not bucket_name and object_name:
            raise ValueError(
                f"empty bucket name for object name {object_name}",
            )

        path = f"{request_path}{bucket_name}"
        url = url_replace(self._url, path=path)

        query = []
        for key, values in sorted((query_params or {}).items()):
            values = values if isinstance(values, (list, tuple)) else [values]
            query += [
                f"{queryencode(key)}={queryencode(value)}"
                for value in sorted(values)
            ]
        url = url_replace(url, query="&".join(query))

        netloc = url.netloc

        if object_name:
            path += ("" if path.endswith("/") else "/") + quote(object_name)

        return url_replace(url, netloc=netloc, path=path)


class ObjectWriteResult:
    """Result class of any APIs doing object creation."""

    def __init__(
            self,
            bucket_name: str,
            object_name: str,
            version_id: str | None,
            etag: str | None,
            http_headers: HTTPHeaderDict,
            last_modified: datetime | None = None,
            location: str | None = None,
    ):
        self._bucket_name = bucket_name
        self._object_name = object_name
        self._version_id = version_id
        self._etag = etag
        self._http_headers = http_headers
        self._last_modified = last_modified
        self._location = location

    @property
    def bucket_name(self) -> str:
        """Get bucket name."""
        return self._bucket_name

    @property
    def object_name(self) -> str:
        """Get object name."""
        return self._object_name

    @property
    def version_id(self) -> str | None:
        """Get version ID."""
        return self._version_id

    @property
    def etag(self) -> str | None:
        """Get etag."""
        return self._etag

    @property
    def http_headers(self) -> HTTPHeaderDict:
        """Get HTTP headers."""
        return self._http_headers

    @property
    def last_modified(self) -> datetime | None:
        """Get last-modified time."""
        return self._last_modified

    @property
    def location(self) -> str | None:
        """Get location."""
        return self._location
