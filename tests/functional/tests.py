#!/usr/bin/env python
# -*- coding: utf-8 -*-
# MinIO Python Library for Amazon S3 Compatible Cloud Storage,
# (C) 2015, 2016, 2017, 2018 MinIO, Inc.
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

# pylint: disable=too-many-lines,broad-exception-raised
"""Functional tests of newtera-py."""

from __future__ import absolute_import, division

import hashlib
import io
import json
import math
import os
import random
import shutil
import sys
import tempfile
import time
import traceback
from binascii import crc32
from datetime import datetime, timedelta, timezone
from inspect import getfullargspec
from threading import Thread
from uuid import uuid4

import certifi
import urllib3

from newtera import Newtera
from newtera.commonconfig import ENABLED, REPLACE, CopySource, SnowballObject
from newtera.datatypes import PostPolicy
from newtera.deleteobjects import DeleteObject
from newtera.error import NewteraError
from newtera.sse import SseCustomerKey
from newtera.time import to_http_header

_CLIENT = None  # initialized in main().
_TEST_FILE = None  # initialized in main().
_LARGE_FILE = None  # initialized in main().
_IS_AWS = None  # initialized in main().
KB = 1024
MB = 1024 * KB
HTTP = urllib3.PoolManager(
    cert_reqs='CERT_REQUIRED',
    ca_certs=os.environ.get('SSL_CERT_FILE') or certifi.where()
)


def _gen_bucket_name():
    """Generate random bucket name."""
    return f"newtera-py-test-{uuid4()}"


def _get_sha256sum(filename):
    """Get SHA-256 checksum of given file."""
    with open(filename, 'rb') as file:
        contents = file.read()
        return hashlib.sha256(contents).hexdigest()


def _get_random_string(size):
    """Get random string of given size."""
    if not size:
        return ""

    chars = "abcdefghijklmnopqrstuvwxyz"
    chars *= int(math.ceil(size / len(chars)))
    chars = list(chars[:size])
    random.shuffle(chars)
    return "".join(chars)


class LimitedRandomReader:  # pylint: disable=too-few-public-methods
    """Random data reader of specified size."""

    def __init__(self, limit):
        self._limit = limit

    def read(self, size=64*KB):
        """Read random data of specified size."""
        if size < 0 or size > self._limit:
            size = self._limit

        data = _get_random_string(size)
        self._limit -= size
        return data.encode()


def _call(log_entry, func, *args, **kwargs):
    """Execute given function."""
    log_entry["method"] = func
    return func(*args, **kwargs)


class TestFailed(Exception):
    """Indicate test failed error."""


def _call_test(func, *args, **kwargs):
    """Execute given test function."""

    log_entry = {
        "name": func.__name__,
        "status": "PASS",
    }

    start_time = time.time()
    try:
        func(log_entry, *args, **kwargs)
    except NewteraError as exc:
        if exc.code == "NotImplemented":
            log_entry["alert"] = "Not Implemented"
            log_entry["status"] = "NA"
        else:
            log_entry["message"] = f"{exc}"
            log_entry["error"] = traceback.format_exc()
            log_entry["status"] = "FAIL"
    except Exception as exc:  # pylint: disable=broad-except
        log_entry["message"] = f"{exc}"
        log_entry["error"] = traceback.format_exc()
        log_entry["status"] = "FAIL"

    if log_entry.get("method"):
        # pylint: disable=deprecated-method
        args_string = ', '.join(getfullargspec(log_entry["method"]).args[1:])
        log_entry["function"] = (
            f"{log_entry['method'].__name__}({args_string})"
        )
    log_entry["args"] = {
        k: v for k, v in log_entry.get("args", {}).items() if v
    }
    log_entry["duration"] = int(
        round((time.time() - start_time) * 1000))
    log_entry["name"] = 'newtera-py:' + log_entry["name"]
    log_entry["method"] = None
    print(json.dumps({k: v for k, v in log_entry.items() if v}))
    if log_entry["status"] == "FAIL":
        raise TestFailed()

def test_list_buckets(log_entry):
    """Test list_buckets()."""

    # Get a unique bucket_name
    bucket_name = _gen_bucket_name()

    try:
        buckets = _CLIENT.list_buckets()
        for bucket in buckets:
            # bucket object should be of a valid value.
            if bucket.name and bucket.creation_date:
                continue
            raise ValueError('list_bucket api failure')
    finally:
        # Remove bucket
        _call(log_entry, _CLIENT.remove_bucket, bucket_name)


def _test_fput_object(bucket_name, object_name, filename, metadata, sse):
    """Test fput_object()."""
    try:
        if _IS_AWS:
            _CLIENT.fput_object(bucket_name, object_name, filename,
                                metadata=metadata, sse=sse)
        else:
            _CLIENT.fput_object(bucket_name, object_name, filename, sse=sse)

        _CLIENT.stat_object(bucket_name, object_name, ssec=sse)
    finally:
        _CLIENT.remove_object(bucket_name, object_name)
        _CLIENT.remove_bucket(bucket_name)


def test_fput_object_small_file(log_entry, sse=None):
    """Test fput_object() with small file."""

    if sse:
        log_entry["name"] += "_with_SSE-C"

    # Get a unique bucket_name and object_name
    bucket_name = _gen_bucket_name()
    object_name = f"{uuid4()}-f"
    metadata = {'x-amz-storage-class': 'STANDARD_IA'}

    log_entry["args"] = {
        "bucket_name": bucket_name,
        "object_name": object_name,
        "file_path": _TEST_FILE,
        "metadata": metadata,
    }

    _test_fput_object(bucket_name, object_name, _TEST_FILE, metadata, sse)


def test_fput_object_large_file(log_entry, sse=None):
    """Test fput_object() with large file."""

    if sse:
        log_entry["name"] += "_with_SSE-C"

    # Get a unique bucket_name and object_name
    bucket_name = _gen_bucket_name()
    object_name = f"{uuid4()}-large"
    metadata = {'x-amz-storage-class': 'STANDARD_IA'}

    log_entry["args"] = {
        "bucket_name": bucket_name,
        "object_name": object_name,
        "file_path": _LARGE_FILE,
        "metadata": metadata,
    }

    # upload local large file through multipart.
    _test_fput_object(bucket_name, object_name, _LARGE_FILE, metadata, sse)


def _validate_stat(st_obj, expected_size, expected_meta, version_id=None):
    """Validate stat information."""

    expected_meta = {
        key.lower(): value for key, value in (expected_meta or {}).items()
    }
    received_etag = st_obj.etag
    received_metadata = {
        key.lower(): value for key, value in (st_obj.metadata or {}).items()
    }
    received_content_type = st_obj.content_type
    received_size = st_obj.size
    received_is_dir = st_obj.is_dir

    if not received_etag:
        raise ValueError('No Etag value is returned.')

    if st_obj.version_id != version_id:
        raise ValueError(
            f"version-id mismatch. expected={version_id}, "
            f"got={st_obj.version_id}"
        )

    # content_type by default can be either application/octet-stream or
    # binary/octet-stream
    if received_content_type not in [
            'application/octet-stream', 'binary/octet-stream']:
        raise ValueError('Incorrect content type. Expected: ',
                         "'application/octet-stream' or 'binary/octet-stream',"
                         " received: ", received_content_type)

    if received_size != expected_size:
        raise ValueError('Incorrect file size. Expected: 11534336',
                         ', received: ', received_size)

    if received_is_dir:
        raise ValueError('Incorrect file type. Expected: is_dir=False',
                         ', received: is_dir=', received_is_dir)

    if not all(i in received_metadata.items() for i in expected_meta.items()):
        raise ValueError("Metadata key 'x-amz-meta-testing' not found")

def test_put_object(log_entry, sse=None):
    """Test put_object()."""

    if sse:
        log_entry["name"] += "_SSE"

    # Get a unique bucket_name and object_name
    bucket_name = _gen_bucket_name()
    object_name = f"{uuid4()}"
    length = 1 * MB

    log_entry["args"] = {
        "bucket_name": bucket_name,
        "object_name": object_name,
        "length": length,
        "data": "LimitedRandomReader(1 * MB)"
    }

    try:
        # Put/Upload a streaming object of 1 MiB
        reader = LimitedRandomReader(length)
        _CLIENT.put_object(bucket_name, object_name, reader, length, sse=sse)
        _CLIENT.stat_object(bucket_name, object_name, ssec=sse)

        # Put/Upload a streaming object of 11 MiB
        log_entry["args"]["length"] = length = 11 * MB
        reader = LimitedRandomReader(length)
        log_entry["args"]["data"] = "LimitedRandomReader(11 * MB)"
        log_entry["args"]["metadata"] = metadata = {
            'x-amz-meta-testing': 'value', 'test-key': 'value2'}
        log_entry["args"]["content_type"] = content_type = (
            "application/octet-stream")
        log_entry["args"]["object_name"] = object_name + "-metadata"
        _CLIENT.put_object(bucket_name, object_name + "-metadata", reader,
                           length, content_type, metadata, sse=sse)
        # Stat on the uploaded object to check if it exists
        # Fetch saved stat metadata on a previously uploaded object with
        # metadata.
        st_obj = _CLIENT.stat_object(bucket_name, object_name + "-metadata",
                                     ssec=sse)
        normalized_meta = {
            key.lower(): value for key, value in (
                st_obj.metadata or {}).items()
        }
        if 'x-amz-meta-testing' not in normalized_meta:
            raise ValueError("Metadata key 'x-amz-meta-testing' not found")
        value = normalized_meta['x-amz-meta-testing']
        if value != 'value':
            raise ValueError(f"Metadata key has unexpected value {value}")
        if 'x-amz-meta-test-key' not in normalized_meta:
            raise ValueError("Metadata key 'x-amz-meta-test-key' not found")
    finally:
        _CLIENT.remove_object(bucket_name, object_name)
        _CLIENT.remove_object(bucket_name, object_name+'-metadata')
        _CLIENT.remove_bucket(bucket_name)


def test_negative_put_object_with_path_segment(  # pylint: disable=invalid-name
        log_entry):
    """Test put_object() failure with path segment."""

    # Get a unique bucket_name and object_name
    bucket_name = _gen_bucket_name()
    object_name = f"/a/b/c/{uuid4()}"
    length = 0

    log_entry["args"] = {
        "bucket_name": bucket_name,
        "object_name": object_name,
        "length": length,
        "data": "",
    }

    try:
        _CLIENT.make_bucket(bucket_name)
        _CLIENT.put_object(bucket_name, object_name, io.BytesIO(b''), 0)
        _CLIENT.remove_object(bucket_name, object_name)
    except NewteraError as err:
        if err.code != 'XNewteraInvalidObjectName':
            raise
    finally:
        _CLIENT.remove_bucket(bucket_name)


def _test_stat_object(log_entry, sse=None, version_check=False):
    """Test stat_object()."""

    if sse:
        log_entry["name"] += "_SSEC"

    # Get a unique bucket_name and object_name
    bucket_name = _gen_bucket_name()
    object_name = f"{uuid4()}"
    length = 1 * MB

    log_entry["args"] = {
        "bucket_name": bucket_name,
        "object_name": object_name,
        "length": length,
        "data": "LimitedRandomReader(1 * MB)"
    }

    version_id1 = None
    version_id2 = None

    try:
        if version_check:
            _CLIENT.set_bucket_versioning(
                bucket_name, VersioningConfig(ENABLED),
            )
        # Put/Upload a streaming object of 1 MiB
        reader = LimitedRandomReader(length)
        result = _CLIENT.put_object(
            bucket_name, object_name, reader, length, sse=sse,
        )
        version_id1 = result.version_id
        _CLIENT.stat_object(
            bucket_name, object_name, ssec=sse, version_id=version_id1,
        )

        # Put/Upload a streaming object of 11 MiB
        log_entry["args"]["length"] = length = 11 * MB
        reader = LimitedRandomReader(length)
        log_entry["args"]["data"] = "LimitedRandomReader(11 * MB)"
        log_entry["args"]["metadata"] = metadata = {
            'X-Amz-Meta-Testing': 'value'}
        log_entry["args"]["content_type"] = content_type = (
            "application/octet-stream")
        log_entry["args"]["object_name"] = object_name + "-metadata"
        result = _CLIENT.put_object(
            bucket_name, object_name + "-metadata", reader,
            length, content_type, metadata, sse=sse,
        )
        version_id2 = result.version_id
        # Stat on the uploaded object to check if it exists
        # Fetch saved stat metadata on a previously uploaded object with
        # metadata.
        st_obj = _CLIENT.stat_object(
            bucket_name, object_name + "-metadata",
            ssec=sse, version_id=version_id2,
        )
        # Verify the collected stat data.
        _validate_stat(
            st_obj, length, metadata, version_id=version_id2,
        )
    finally:
        _CLIENT.remove_object(bucket_name, object_name, version_id=version_id1)
        _CLIENT.remove_object(
            bucket_name, object_name+'-metadata', version_id=version_id2,
        )
        _CLIENT.remove_bucket(bucket_name)


def test_stat_object(log_entry, sse=None):
    """Test stat_object()."""
    _test_stat_object(log_entry, sse)


def test_stat_object_version(log_entry, sse=None):
    """Test stat_object() of versioned object."""
    _test_stat_object(log_entry, sse, version_check=True)


def _test_remove_object(log_entry, version_check=False):
    """Test remove_object()."""

    # Get a unique bucket_name and object_name
    bucket_name = _gen_bucket_name()
    object_name = f"{uuid4()}"
    length = 1 * KB

    log_entry["args"] = {
        "bucket_name": bucket_name,
        "object_name": object_name,
    }

    _CLIENT.make_bucket(bucket_name)
    try:
        if version_check:
            _CLIENT.set_bucket_versioning(
                bucket_name, VersioningConfig(ENABLED),
            )
        result = _CLIENT.put_object(
            bucket_name, object_name, LimitedRandomReader(length), length,
        )
        _CLIENT.remove_object(
            bucket_name, object_name, version_id=result.version_id,
        )
    finally:
        _CLIENT.remove_bucket(bucket_name)


def test_remove_object(log_entry):
    """Test remove_object()."""
    _test_remove_object(log_entry)

def _test_get_object(log_entry, sse=None, version_check=False):
    """Test get_object()."""

    if sse:
        log_entry["name"] += "_SSEC"

    # Get a unique bucket_name and object_name
    bucket_name = _gen_bucket_name()
    object_name = f"{uuid4()}"
    length = 1 * MB

    log_entry["args"] = {
        "bucket_name": bucket_name,
        "object_name": object_name,
    }

    _CLIENT.make_bucket(bucket_name)
    version_id = None
    try:
        if version_check:
            _CLIENT.set_bucket_versioning(
                bucket_name, VersioningConfig(ENABLED),
            )
        result = _CLIENT.put_object(
            bucket_name, object_name, LimitedRandomReader(length),
            length, sse=sse,
        )
        version_id = result.version_id
        # Get/Download a full object, iterate on response to save to disk
        object_data = _CLIENT.get_object(
            bucket_name, object_name, ssec=sse, version_id=version_id,
        )
        newfile = 'newfile جديد'
        with open(newfile, 'wb') as file_data:
            shutil.copyfileobj(object_data, file_data)
        os.remove(newfile)
    finally:
        _CLIENT.remove_object(bucket_name, object_name, version_id=version_id)
        _CLIENT.remove_bucket(bucket_name)


def test_get_object(log_entry, sse=None):
    """Test get_object()."""
    _test_get_object(log_entry, sse)


def _test_fget_object(log_entry, sse=None, version_check=False):
    """Test fget_object()."""

    if sse:
        log_entry["name"] += "_SSEC"

    # Get a unique bucket_name and object_name
    bucket_name = _gen_bucket_name()
    object_name = f"{uuid4()}"
    tmpfd, tmpfile = tempfile.mkstemp()
    os.close(tmpfd)
    length = 1 * MB

    log_entry["args"] = {
        "bucket_name": bucket_name,
        "object_name": object_name,
        "file_path": tmpfile
    }

    _CLIENT.make_bucket(bucket_name)
    version_id = None
    try:
        if version_check:
            _CLIENT.set_bucket_versioning(
                bucket_name, VersioningConfig(ENABLED),
            )
        result = _CLIENT.put_object(
            bucket_name, object_name, LimitedRandomReader(length),
            length, sse=sse,
        )
        version_id = result.version_id
        # Get/Download a full object and save locally at path
        _CLIENT.fget_object(
            bucket_name, object_name, tmpfile, ssec=sse, version_id=version_id,
        )
        os.remove(tmpfile)
    finally:
        _CLIENT.remove_object(bucket_name, object_name, version_id=version_id)
        _CLIENT.remove_bucket(bucket_name)


def test_fget_object(log_entry, sse=None):
    """Test fget_object()."""
    _test_fget_object(log_entry, sse)


def test_get_object_with_default_length(  # pylint: disable=invalid-name
        log_entry, sse=None):
    """Test get_object() with default length."""

    if sse:
        log_entry["name"] += "_SSEC"

    # Get a unique bucket_name and object_name
    bucket_name = _gen_bucket_name()
    object_name = f"{uuid4()}"
    size = 1 * MB
    length = 1000
    offset = size - length

    log_entry["args"] = {
        "bucket_name": bucket_name,
        "object_name": object_name,
        "offset": offset
    }

    _CLIENT.make_bucket(bucket_name)
    try:
        _CLIENT.put_object(bucket_name, object_name,
                           LimitedRandomReader(size), size, sse=sse)
        # Get half of the object
        object_data = _CLIENT.get_object(bucket_name, object_name,
                                         offset=offset, ssec=sse)
        newfile = 'newfile'
        with open(newfile, 'wb') as file_data:
            for data in object_data:
                file_data.write(data)
        # Check if the new file is the right size
        new_file_size = os.path.getsize(newfile)
        os.remove(newfile)
        if new_file_size != length:
            raise ValueError('Unexpected file size after running ')
    finally:
        _CLIENT.remove_object(bucket_name, object_name)
        _CLIENT.remove_bucket(bucket_name)


def _test_list_objects(log_entry, use_api_v1=False, version_check=False):
    """Test list_objects()."""

    # Get a unique bucket_name and object_name
    bucket_name = _gen_bucket_name()
    object_name = f"{uuid4()}"
    is_recursive = True

    log_entry["args"] = {
        "bucket_name": bucket_name,
        "object_name": object_name,
        "recursive": is_recursive,
    }

    _CLIENT.make_bucket(bucket_name)
    version_id1 = None
    version_id2 = None
    try:
        if version_check:
            _CLIENT.set_bucket_versioning(
                bucket_name, VersioningConfig(ENABLED),
            )
        size = 1 * KB
        result = _CLIENT.put_object(
            bucket_name, object_name + "-1", LimitedRandomReader(size), size,
        )
        version_id1 = result.version_id
        result = _CLIENT.put_object(
            bucket_name, object_name + "-2", LimitedRandomReader(size), size,
        )
        version_id2 = result.version_id
        # List all object paths in bucket.
        objects = _CLIENT.list_objects(
            bucket_name, '', is_recursive, include_version=version_check,
            use_api_v1=use_api_v1,
        )
        for obj in objects:
            _ = (obj.bucket_name, obj.object_name, obj.last_modified,
                 obj.etag, obj.size, obj.content_type)
            if obj.version_id not in [version_id1, version_id2]:
                raise ValueError(
                    f"version ID mismatch. "
                    f"expected=any{[version_id1, version_id2]}, "
                    f"got:{obj.version_id}"
                )
    finally:
        _CLIENT.remove_object(
            bucket_name, object_name + "-1", version_id=version_id1,
        )
        _CLIENT.remove_object(
            bucket_name, object_name + "-2", version_id=version_id2,
        )
        _CLIENT.remove_bucket(bucket_name)

def _test_list_objects_api(bucket_name, expected_no, *argv):
    """Test list_objects()."""

    # argv is composed of prefix and recursive arguments of
    # list_objects api. They are both supposed to be passed as strings.
    objects = _CLIENT.list_objects(bucket_name, *argv)

    # expect all objects to be listed
    no_of_files = 0
    for obj in objects:
        _ = (obj.bucket_name, obj.object_name, obj.last_modified, obj.etag,
             obj.size, obj.content_type)
        no_of_files += 1

    if expected_no != no_of_files:
        raise ValueError(
            f"Listed no of objects ({no_of_files}), does not match the "
            f"expected no of objects ({expected_no})"
        )


def test_list_objects_with_prefix(log_entry):
    """Test list_objects() with prefix."""

    # Get a unique bucket_name and object_name
    bucket_name = _gen_bucket_name()
    object_name = f"{uuid4()}"

    log_entry["args"] = {
        "bucket_name": bucket_name,
        "object_name": object_name,
    }

    _CLIENT.make_bucket(bucket_name)
    try:
        size = 1 * KB
        no_of_created_files = 4
        path_prefix = ""
        # Create files and directories
        for i in range(no_of_created_files):
            _CLIENT.put_object(bucket_name, f"{path_prefix}{i}_{object_name}",
                               LimitedRandomReader(size), size)
            path_prefix = f"{path_prefix}{i}/"

        # Created files and directory structure
        # ._<bucket_name>/
        # |___0_<object_name>
        # |___0/
        #     |___1_<object_name>
        #     |___1/
        #         |___2_<object_name>
        #         |___2/
        #             |___3_<object_name>
        #

        # Test and verify list_objects api outputs
        # List objects recursively with NO prefix
        log_entry["args"]["prefix"] = prefix = ""  # no prefix
        log_entry["args"]["recursive"] = recursive = ""
        _test_list_objects_api(bucket_name, no_of_created_files, prefix, True)

        # List objects at the top level with no prefix and no recursive option
        # Expect only the top 2 objects to be listed
        _test_list_objects_api(bucket_name, 2)

        # List objects for '0' directory/prefix without recursive option
        # Expect 2 object (directory '0' and '0_' object) to be listed
        log_entry["args"]["prefix"] = prefix = "0"
        _test_list_objects_api(bucket_name, 2, prefix)

        # List objects for '0/' directory/prefix without recursive option
        # Expect only 2 objects under directory '0/' to be listed,
        # non-recursive
        log_entry["args"]["prefix"] = prefix = "0/"
        _test_list_objects_api(bucket_name, 2, prefix)

        # List objects for '0/' directory/prefix, recursively
        # Expect 2 objects to be listed
        log_entry["args"]["prefix"] = prefix = "0/"
        log_entry["args"]["recursive"] = recursive = "True"
        _test_list_objects_api(bucket_name, 3, prefix, recursive)

        # List object with '0/1/2/' directory/prefix, non-recursive
        # Expect the single object under directory '0/1/2/' to be listed
        log_entry["args"]["prefix"] = prefix = "0/1/2/"
        _test_list_objects_api(bucket_name, 1, prefix)
    finally:
        path_prefix = ""
        for i in range(no_of_created_files):
            _CLIENT.remove_object(
                bucket_name, f"{path_prefix}{i}_{object_name}",
            )
            path_prefix = f"{path_prefix}{i}/"
        _CLIENT.remove_bucket(bucket_name)
    # Test passes
    log_entry["args"]["prefix"] = (
        "Several prefix/recursive combinations are tested")
    log_entry["args"]["recursive"] = (
        'Several prefix/recursive combinations are tested')


def test_list_objects_with_1001_files(  # pylint: disable=invalid-name
        log_entry):
    """Test list_objects() with more 1000 objects."""

    # Get a unique bucket_name and object_name
    bucket_name = _gen_bucket_name()
    object_name = f"{uuid4()}"

    log_entry["args"] = {
        "bucket_name": bucket_name,
        "object_name": f"{object_name}_0 ~ {0}_1000",
    }

    _CLIENT.make_bucket(bucket_name)
    try:
        size = 1 * KB
        no_of_created_files = 2000
        # Create files and directories
        for i in range(no_of_created_files):
            _CLIENT.put_object(bucket_name, f"{object_name}_{i}",
                               LimitedRandomReader(size), size)

        # List objects and check if 1001 files are returned
        _test_list_objects_api(bucket_name, no_of_created_files)
    finally:
        for i in range(no_of_created_files):
            _CLIENT.remove_object(bucket_name, f"{object_name}_{i}")
        _CLIENT.remove_bucket(bucket_name)


def test_list_objects(log_entry):
    """Test list_objects()."""
    _test_list_objects(log_entry)


def _test_remove_objects(log_entry, version_check=False):
    """Test remove_objects()."""

    # Get a unique bucket_name
    bucket_name = _gen_bucket_name()
    log_entry["args"] = {
        "bucket_name": bucket_name,
    }

    _CLIENT.make_bucket(bucket_name)
    object_names = []
    delete_object_list = []
    try:
        if version_check:
            _CLIENT.set_bucket_versioning(
                bucket_name, VersioningConfig(ENABLED),
            )
        size = 1 * KB
        # Upload some new objects to prepare for multi-object delete test.
        for i in range(10):
            object_name = f"prefix-{i}"
            result = _CLIENT.put_object(
                bucket_name, object_name, LimitedRandomReader(size), size,
            )
            object_names.append(
                (object_name, result.version_id) if version_check
                else object_name,
            )
        log_entry["args"]["delete_object_list"] = object_names

        for args in object_names:
            delete_object_list.append(
                DeleteObject(args) if isinstance(args, str)
                else DeleteObject(args[0], args[1])
            )
        # delete the objects in a single library call.
        errs = _CLIENT.remove_objects(bucket_name, delete_object_list)
        for err in errs:
            raise ValueError(f"Remove objects err: {err}")
    finally:
        # Try to clean everything to keep our server intact
        errs = _CLIENT.remove_objects(bucket_name, delete_object_list)
        for err in errs:
            raise ValueError(f"Remove objects err: {err}")
        _CLIENT.remove_bucket(bucket_name)



def main():
    """
    Functional testing of newtera python library.
    """
    # pylint: disable=global-statement
    global _CLIENT, _TEST_FILE, _LARGE_FILE, _IS_AWS

    access_key = os.getenv('ACCESS_KEY')
    secret_key = os.getenv('SECRET_KEY')
    server_endpoint = os.getenv('SERVER_ENDPOINT', 'play.min.io')
    secure = os.getenv('ENABLE_HTTPS', '1') == '1'

    if server_endpoint == 'play.min.io':
        access_key = 'Q3AM3UQ867SPQQA43P2F'
        secret_key = 'zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG'
        secure = True

    _CLIENT = Newtera(server_endpoint, access_key, secret_key, secure=secure)
    _IS_AWS = ".amazonaws.com" in server_endpoint

    # Check if we are running in the mint environment.
    data_dir = os.getenv('DATA_DIR', '/mint/data')

    is_mint_env = (
        os.path.exists(data_dir) and
        os.path.exists(os.path.join(data_dir, 'datafile-1-MB')) and
        os.path.exists(os.path.join(data_dir, 'datafile-11-MB'))
    )

    # Enable trace
    # _CLIENT.trace_on(sys.stderr)

    _TEST_FILE = 'datafile-1-MB'
    _LARGE_FILE = 'datafile-11-MB'
    if is_mint_env:
        # Choose data files
        _TEST_FILE = os.path.join(data_dir, 'datafile-1-MB')
        _LARGE_FILE = os.path.join(data_dir, 'datafile-11-MB')
    else:
        with open(_TEST_FILE, 'wb') as file_data:
            shutil.copyfileobj(LimitedRandomReader(1 * MB), file_data)
        with open(_LARGE_FILE, 'wb') as file_data:
            shutil.copyfileobj(LimitedRandomReader(11 * MB), file_data)

    ssec = None
    if secure:
        # Create a Customer Key of 32 Bytes for Server Side Encryption (SSE-C)
        cust_key = b'AABBCCDDAABBCCDDAABBCCDDAABBCCDD'
        # Create an SSE-C object with provided customer key
        ssec = SseCustomerKey(cust_key)

    if os.getenv("MINT_MODE") == "full":
        tests = {
            test_fput_object_small_file: {"sse": ssec} if ssec else None,
            test_fput_object_large_file: {"sse": ssec} if ssec else None,
            test_put_object: {"sse": ssec} if ssec else None,
            test_negative_put_object_with_path_segment: None,
            test_stat_object: {"sse": ssec} if ssec else None,
            test_stat_object_version: {"sse": ssec} if ssec else None,
            test_get_object: {"sse": ssec} if ssec else None,
            test_get_object_version: {"sse": ssec} if ssec else None,
            test_fget_object: {"sse": ssec} if ssec else None,
            test_fget_object_version: {"sse": ssec} if ssec else None,
            test_get_object_with_default_length: None,
            test_get_partial_object: {"sse": ssec} if ssec else None,
            test_list_objects_v1: None,
            test_list_object_v1_versions: None,
            test_list_objects_with_prefix: None,
            test_list_objects_with_1001_files: None,
            test_list_objects: None,
        }
    else:
        tests = {
            test_put_object: {"sse": ssec} if ssec else None,
            test_stat_object: {"sse": ssec} if ssec else None,
            test_get_object: {"sse": ssec} if ssec else None,
            test_list_objects: None,
        }

    tests.update(
        {
            test_remove_object: None,
            test_remove_object_version: None,
        },
    )

    for test_name, arg_list in tests.items():
        args = ()
        kwargs = {}
        _call_test(test_name, *args, **kwargs)

        if arg_list:
            args = ()
            kwargs = arg_list
            _call_test(
                test_name, *args, **kwargs)  # pylint: disable=not-a-mapping

    # Remove temporary files.
    if not is_mint_env:
        os.remove(_TEST_FILE)
        os.remove(_LARGE_FILE)


if __name__ == "__main__":
    try:
        main()
    except TestFailed:
        sys.exit(1)
    except Exception as excp:  # pylint: disable=broad-except
        print(excp)
        sys.exit(-1)
