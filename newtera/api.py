# -*- coding: utf-8 -*-
# Newtera Python Library for Newtera TDM, (C)
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

# pylint: disable=too-many-arguments
# pylint: disable=too-many-branches
# pylint: disable=too-many-function-args
# pylint: disable=too-many-lines
# pylint: disable=too-many-public-methods
# pylint: disable=too-many-statements


from __future__ import absolute_import, annotations

import os
from datetime import datetime, timedelta
from typing import BinaryIO, TextIO, Union, cast
from urllib.parse import urlunsplit

import urllib3
from urllib3 import Retry
from urllib3._collections import HTTPHeaderDict

try:
    from urllib3.response import BaseHTTPResponse  # type: ignore[attr-defined]
except ImportError:
    from urllib3.response import HTTPResponse as BaseHTTPResponse

from urllib3.util import Timeout

from . import __title__, __version__
from .credentials import StaticProvider
from .credentials.providers import Provider
from .datatypes import (Object, ObjectModel,
                        parse_list_objects)
from .error import InvalidResponseError, NewteraError, ServerError
from .helpers import (BaseURL, DictType, ObjectWriteResult, ProgressType,
                      check_bucket_name, check_non_empty_string,
                      get_part_info,
                      headers_to_strings, makedirs,
                      read_part_data)


class Newtera:
    """
    Newtera TDM client to perform bucket and object
    operations.

    :param endpoint: Hostname of a Newtera TDM service.
    :param access_key: Access key (aka user ID) of your account in Newtera TDM service.
    :param secret_key: Secret Key (aka password) of your account in Newtera TDM service.
    :param secure: Flag to indicate to use secure (TLS) connection to Newtera TDM
        service or not.
    :param http_client: Customized HTTP client.
    :param credentials: Credentials provider of your account in Newtera TDM service.
    :return: :class:`Newtera <Newtera>` object

    Example::
        # Create client with access and secret key.
        client = Newtera("localhost:8080", "ACCESS-KEY", "SECRET-KEY")

    **NOTE on concurrent usage:** `Newtera` object is thread safe when using
    the Python `threading` library. Specifically, it is **NOT** safe to share
    it between multiple processes, for example when using
    `multiprocessing.Pool`. The solution is simply to create a new `Newtera`
    object in each process, and not share it between processes.

    """
    _base_url: BaseURL
    _trace_stream: TextIO | None
    _provider: Provider | None
    _http: urllib3.PoolManager

    def __init__(
            self,
            endpoint: str,
            access_key: str | None = None,
            secret_key: str | None = None,
            secure: bool = False,
            http_client: urllib3.PoolManager | None = None,
    ):
        # Validate http client has correct base class.
        if http_client and not isinstance(http_client, urllib3.PoolManager):
            raise ValueError(
                "HTTP client should be instance of `urllib3.PoolManager`"
            )

        self._base_url = BaseURL(
            ("https://" if secure else "http://") + endpoint,
        )
        self._trace_stream = None
        if access_key:
            if secret_key is None:
                raise ValueError("secret key must be provided with access key")
            credentials = StaticProvider(access_key, secret_key)
        self._provider = credentials

        # Load CA certificates from SSL_CERT_FILE file if set
        timeout = timedelta(minutes=5).seconds
        self._http = http_client or urllib3.PoolManager(
            timeout=Timeout(connect=timeout, read=timeout),
            maxsize=10,
            cert_reqs='CERT_NONE',
            retries=Retry(
                total=5,
                backoff_factor=0.2,
                status_forcelist=[500, 502, 503, 504]
            )
        )

    def __del__(self):
        if hasattr(self, "_http"):  # Only required for unit test run
            self._http.clear()

    def _build_headers(
            self,
            host: str,
            headers: DictType | None,
            body: bytes | None,
    ) -> tuple[DictType, datetime]:
        """Build headers with given parameters."""
        headers = headers or {}
        headers["Host"] = host

        if body:
            headers["Content-Length"] = str(len(body))
        return headers

    def _url_open(
            self,
            method: str,
            request_path: str,
            bucket_name: str | None = None,
            object_name: str | None = None,
            body: bytes | None = None,
            headers: DictType | None = None,
            query_params: DictType | None = None,
            preload_content: bool = True,
            no_body_trace: bool = False,
    ) -> BaseHTTPResponse:
        """Execute HTTP request."""
        url = self._base_url.build(
            method,
            request_path,
            bucket_name=bucket_name,
            object_name=object_name,
            query_params=query_params,
        )
        headers = self._build_headers(url.netloc, headers, body)

        if self._trace_stream:
            self._trace_stream.write("---------START-HTTP---------\n")
            query = ("?" + url.query) if url.query else ""
            self._trace_stream.write(f"{method} {url.path}{query} HTTP/1.1\n")
            self._trace_stream.write(
                headers_to_strings(headers, titled_key=True),
            )
            self._trace_stream.write("\n")
            if not no_body_trace and body is not None:
                self._trace_stream.write("\n")
                self._trace_stream.write(
                    body.decode() if isinstance(body, bytes) else str(body),
                )
                self._trace_stream.write("\n")
            self._trace_stream.write("\n")

        http_headers = HTTPHeaderDict()
        for key, value in (headers or {}).items():
            if isinstance(value, (list, tuple)):
                for val in value:
                    http_headers.add(key, val)
            else:
                http_headers.add(key, value)

        http_headers.add("AccessKey", self._provider.retrieve().access_key)
        http_headers.add("SecretKey", self._provider.retrieve().secret_key)

        response = self._http.urlopen(
            method,
            urlunsplit(url),
            body=body,
            headers=http_headers,
            preload_content=preload_content,
        )

        if self._trace_stream:
            self._trace_stream.write(f"HTTP/1.1 {response.status}\n")
            self._trace_stream.write(
                headers_to_strings(response.headers),
            )
            self._trace_stream.write("\n")

        if response.status in [200, 204, 206]:
            if self._trace_stream:
                if preload_content:
                    self._trace_stream.write("\n")
                    self._trace_stream.write(response.data.decode())
                    self._trace_stream.write("\n")
                self._trace_stream.write("----------END-HTTP----------\n")
            return response

        response.read(cache_content=True)
        if not preload_content:
            response.release_conn()

        if self._trace_stream and method != "HEAD" and response.data:
            self._trace_stream.write(response.data.decode())
            self._trace_stream.write("\n")

        if (
                method != "HEAD" and
                "application/xml" not in response.headers.get(
                    "content-type", "",
                ).split(";")
        ):
            if self._trace_stream:
                self._trace_stream.write("----------END-HTTP----------\n")
            if response.status == 304 and not response.data:
                raise ServerError(
                    f"server failed with HTTP status code {response.status}",
                    response.status,
                )
            raise InvalidResponseError(
                response.status,
                cast(str, response.headers.get("content-type")),
                response.data.decode() if response.data else None,
            )

        if not response.data and method != "HEAD":
            if self._trace_stream:
                self._trace_stream.write("----------END-HTTP----------\n")
            raise InvalidResponseError(
                response.status,
                response.headers.get("content-type"),
                None,
            )

        response_error = NewteraError.fromxml(response) if response.data else None

        if self._trace_stream:
            self._trace_stream.write("----------END-HTTP----------\n")

        error_map = {
            403: lambda: ("AccessDenied", "Access denied"),
            404: lambda: (
                ("NoSuchKey", "Object does not exist")
                if object_name
                else ("NoSuchBucket", "Bucket does not exist")
                if bucket_name
                else ("ResourceNotFound", "Request resource not found")
            ),
            405: lambda: (
                "MethodNotAllowed",
                "The specified method is not allowed against this resource",
            ),
            409: lambda: (
                ("NoSuchBucket", "Bucket does not exist")
                if bucket_name
                else ("ResourceConflict", "Request resource conflicts"),
            ),
            501: lambda: (
                "MethodNotAllowed",
                "The specified method is not allowed against this resource",
            ),
        }

        if not response_error:
            func = error_map.get(response.status)
            code, message = func() if func else (None, None)
            if not code:
                raise ServerError(
                    f"server failed with HTTP status code {response.status}",
                    response.status,
                )
            response_error = NewteraError(
                cast(str, code),
                cast(Union[str, None], message),
                url.path,
                response.headers.get("x-amz-request-id"),
                response.headers.get("x-amz-id-2"),
                response,
                bucket_name=bucket_name,
                object_name=object_name,
            )

        raise response_error

    def _execute(
            self,
            method: str,
            request_path: str,
            bucket_name: str | None = None,
            object_name: str | None = None,
            body: bytes | None = None,
            headers: DictType | None = None,
            query_params: DictType | None = None,
            preload_content: bool = True,
            no_body_trace: bool = False,
    ) -> BaseHTTPResponse:
        """Execute HTTP request."""
 
        try:
            return self._url_open(
                method,
                request_path=request_path,
                bucket_name=bucket_name,
                object_name=object_name,
                body=body,
                headers=headers,
                query_params=query_params,
                preload_content=preload_content,
                no_body_trace=no_body_trace,
            )
        except NewteraError as exc:
            if exc.code != "RetryHead":
                raise

        # Retry only once on RetryHead error.
        try:
            return self._url_open(
                method,
                request_path=request_path,
                bucket_name=bucket_name,
                object_name=object_name,
                body=body,
                headers=headers,
                query_params=query_params,
                preload_content=preload_content,
                no_body_trace=no_body_trace,
            )
        except NewteraError as exc:
            if exc.code != "RetryHead":
                raise

    def trace_on(self, stream: TextIO):
        """
        Enable http trace.

        :param stream: Stream for writing HTTP call tracing.
        """
        if not stream:
            raise ValueError('Input stream for trace output is invalid.')
        # Save new output stream.
        self._trace_stream = stream

    def trace_off(self):
        """
        Disable HTTP trace.
        """
        self._trace_stream = None

    def bucket_exists(self, bucket_name: str) -> bool:
        """
        Check if a bucket exists.

        :param bucket_name: Name of the bucket.
        :return: True if the bucket exists.

        Example::
            if client.bucket_exists("tdm"):
                print("tdm exists")
            else:
                print("tdm does not exist")
        """
        check_bucket_name(bucket_name)
        try:
            self._execute("HEAD", "/api/blob/buckets/", bucket_name)
            return True
        except NewteraError as exc:
            if exc.code != "NoSuchBucket":
                raise
        return False

    def fput_object(
            self,
            bucket_name: str,
            prefix: str,
            object_name: str,
            file_path: str,
            content_type: str = "application/octet-stream",
            progress: ProgressType | None = None,
    ) -> ObjectWriteResult:
        """
        Uploads data from a file to an object in a bucket.

        :param bucket_name: Name of the bucket.
        :param prefix: Prefix of the object.
        :param object_name: Object name in the bucket.
        :param file_path: Name of file to upload.
        :param content_type: Content type of the object.
        :param progress: A progress object
        :return: :class:`ObjectWriteResult` object.

        Example::
            # Upload data.
            result = client.fput_object(
                "tdm", "my-prefix", "my-object", "my-filename",
            )
        """

        file_size = os.stat(file_path).st_size
        with open(file_path, "rb") as file_data:
            return self.put_object(
                bucket_name,
                prefix,
                object_name,
                file_data,
                file_size,
                content_type=content_type,
                progress=progress,
            )

    def fget_object(
            self,
            bucket_name: str,
            prefix: str,
            object_name: str,
            file_path: str,
            request_headers: DictType | None = None,
            tmp_file_path: str | None = None,
            progress: ProgressType | None = None,
    ):
        """
        Downloads data of an object to file.

        :param bucket_name: Name of the bucket.
        :param prefix: Prefix of the object.
        :param object_name: Object name in the bucket.
        :param file_path: Name of file to download.
        :param request_headers: Any additional headers to be added with GET
                                request.
        :param tmp_file_path: Path to a temporary file.
        :param progress: A progress object
        :return: Object information.

        Example::
            # Download data of an object.
            client.fget_object("tdm", "my-prefix", "my-object", "my-filename")
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        check_non_empty_string(prefix)

        if os.path.isdir(file_path):
            raise ValueError(f"file {file_path} is a directory")

        # Create top level directory if needed.
        makedirs(os.path.dirname(file_path))

        stat = self.stat_object(
            bucket_name,
            prefix,
            object_name,
        )

        response = None
        try:
            response = self.get_object(
                bucket_name,
                prefix,
                object_name,
                request_headers=request_headers,
            )

            if progress:
                # Set progress bar length and object name before upload
                length = int(response.headers.get('content-length', 0))
                progress.set_meta(object_name=object_name, total_length=length)

             # Write to a temporary file "file_path.part.newtera" before saving.
            tmp_file_path = (
                tmp_file_path or f"{file_path}.part.newtera"
            )

            with open(tmp_file_path, "wb") as tmp_file:
                for data in response.stream(amt=1024*1024):
                    size = tmp_file.write(data)
                    if progress:
                        progress.update(size)
            if os.path.exists(file_path):
                os.remove(file_path)  # For windows compatibility.
            os.rename(tmp_file_path, file_path)
            return stat
        finally:
            if response:
                response.close()
                response.release_conn()

    def get_object(
            self,
            bucket_name: str,
            prefix: str,
            object_name: str,
            offset: int = 0,
            length: int = 0,
            request_headers: DictType | None = None,
    ) -> BaseHTTPResponse:
        """
        Get data of an object. Returned response should be closed after use to
        release network resources. To reuse the connection, it's required to
        call `response.release_conn()` explicitly.

        :param bucket_name: Name of the bucket.
        :param prefix: Prefix of the object.
        :param object_name: Object name in the bucket.
        :param offset: Start byte position of object data.
        :param length: Number of bytes of object data from offset.
        :param request_headers: Any additional headers to be added with GET
                                request.
        :return: :class:`urllib3.response.BaseHTTPResponse` object.

        Example::
            # Get data of an object.
            try:
                response = client.get_object("tdm", "my-object")
                # Read data from response.
            finally:
                response.close()
                response.release_conn()
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        check_non_empty_string(prefix)

        headers = cast(DictType, {})
        headers.update(request_headers or {})

        if offset or length:
            end = (offset + length - 1) if length else ""
            headers['Range'] = f"bytes={offset}-{end}"

        query_params = {}
        query_params["prefix"] = prefix or ""

        return self._execute(
            "GET",
            "/api/blob/objects/",
            bucket_name,
            object_name,
            headers=cast(DictType, headers),
            query_params=query_params,
            preload_content=False,
        )

    def _put_object(
            self,
            bucket_name: str,
            prefix: str,
            object_name: str,
            data: bytes,
            headers: DictType | None,
            query_params: DictType | None = None,
    ) -> ObjectWriteResult:
        """Execute PutObject Newtera TDM API."""
        query_params = {}
        query_params["prefix"] = prefix or ""
        response = self._execute(
            "PUT",
            "/api/blob/objects/",
            bucket_name,
            object_name,
            body=data,
            headers=headers,
            query_params=query_params,
            no_body_trace=True,
        )
        return ObjectWriteResult(
            bucket_name,
            prefix,
            object_name,
            response.headers,
        )

    def put_object(
        self,
        bucket_name: str,
        prefix: str,
        object_name: str,
        data: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream",
        progress: ProgressType | None = None,
        part_size: int = 0,
    ) -> ObjectWriteResult:
        """
        Uploads data from a stream to an object in a bucket.

        :param bucket_name: Name of the bucket.
        :param prefix: Prefix of the object.
        :param object_name: Object name in the bucket.
        :param data: An object having callable read() returning bytes object.
        :param length: Data size; -1 for unknown size and set valid part_size.
        :param content_type: Content type of the object.
        :param progress: A progress object;
        :return: :class:`ObjectWriteResult` object.

        Example::
            # Upload data.
            result = client.put_object(
                "tdm", "my-prefix", "my-object", io.BytesIO(b"hello"), 5,
            )
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        check_non_empty_string(prefix)

        if not callable(getattr(data, "read")):
            raise ValueError("input data must have callable read()")
        part_size, part_count = get_part_info(length, part_size)
        if progress:
            # Set progress bar length and object name before upload
            progress.set_meta(object_name=object_name, total_length=length)

        headers = {}
        headers["Content-Type"] = content_type or "application/octet-stream"
        headers["newtera-meta-user"] = self._provider.retrieve().access_key

        object_size = length
        uploaded_size = 0
        part_number = 0
        one_byte = b""
        stop = False
        upload_id = None

        try:
            while not stop:
                part_number += 1
                if part_count > 0:
                    if part_number == part_count:
                        part_size = object_size - uploaded_size
                        stop = True
                    part_data = read_part_data(
                        data, part_size, progress=progress,
                    )
                    if len(part_data) != part_size:
                        raise IOError(
                            f"stream having not enough data;"
                            f"expected: {part_size}, "
                            f"got: {len(part_data)} bytes"
                        )
                else:
                    part_data = read_part_data(
                        data, part_size + 1, one_byte, progress=progress,
                    )
                    # If part_data_size is less or equal to part_size,
                    # then we have reached last part.
                    if len(part_data) <= part_size:
                        part_count = part_number
                        stop = True
                    else:
                        one_byte = part_data[-1:]
                        part_data = part_data[:-1]

                uploaded_size += len(part_data)

                if part_count == 1:
                    return self._put_object(
                        bucket_name, prefix, object_name, part_data, headers,
                    )
        except Exception as exc:
            if upload_id:
                self._abort_multipart_upload(
                    bucket_name, object_name, upload_id,
                )
            raise exc

    def list_objects(
            self,
            bucket_name: str,
            prefix: str | None = None,
    ) -> list[ObjectModel]:
        """
        Lists object information of a bucket.

        :param bucket_name: Name of the bucket.
        :param prefix: Object name starts with prefix.
        :return: Iterator of :class:`Object <Object>`.

        Example::
            # List objects information whose names starts with "my/prefix/".
            objects = client.list_objects("tdm", prefix="my/prefix/")
            for obj in objects:
                print(obj)
        """
        return self._list_objects(
            bucket_name,
            prefix=prefix,
        )

    def stat_object(
            self,
            bucket_name: str,
            prefix: str,
            object_name: str,
            extra_headers: DictType | None = None,
    ) -> Object:
        """
        Get object information of an object.

        :param bucket_name: Name of the bucket.
        :param prefix: Object name starts with prefix.
        :param object_name: Object name in the bucket.
        :param extra_headers: Extra HTTP headers for advanced usage.
        :return: :class:`ObjectModel <ObjectModel>`.

        Example::
            # Get object information.
            result = client.stat_object("tdm", "prefix", "my-object")
        """

        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        check_non_empty_string(prefix)

        headers = cast(DictType, {})
        if extra_headers:
            headers.update(extra_headers)

        response = self._execute(
            "HEAD",
            "/api/blob/objects/",
            bucket_name,
            object_name,
            headers=headers,
            query_params={"prefix": prefix},
        )

        return Object(
            bucket_name,
            object_name,
            size=int(response.headers.get("Length", "0")),
            content_type=response.headers.get("ContentType"),
            metadata=response.headers,
        )

    def remove_object(
        self,
        bucket_name: str,
        prefix: str,
        object_name: str,
    ):
        """
        Remove an object.

        :param bucket_name: Name of the bucket.
        :param prefix: Object name starts with prefix.
        :param object_name: Object name in the bucket.
        :param version_id: Version ID of the object.

        Example::
            # Remove object.
            client.remove_object("tdm", "my-prefix", "my-object")
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        check_non_empty_string(prefix)

        self._execute(
            "DELETE",
            "/api/blob/objects/",
            bucket_name,
            object_name,
            query_params={"prefix": prefix},
        )

    def _list_objects(
            self,
            bucket_name: str,
            prefix: str | None = None,
    ) -> list[ObjectModel]:

        check_bucket_name(bucket_name)

        query = {}
        query["prefix"] = prefix or ""

        response = self._execute(
            "GET",
            "/api/blob/objects/",
            bucket_name,
            query_params=cast(DictType, query),
        )

        objects = parse_list_objects(response)

        return objects
