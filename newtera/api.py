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

import itertools
import os
from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import BinaryIO, Iterator, TextIO, Union, cast
from urllib.parse import urlunsplit
from xml.etree import ElementTree as ET

import certifi
import urllib3
from urllib3 import Retry
from urllib3._collections import HTTPHeaderDict

try:
    from urllib3.response import BaseHTTPResponse  # type: ignore[attr-defined]
except ImportError:
    from urllib3.response import HTTPResponse as BaseHTTPResponse

from urllib3.util import Timeout

from . import __title__, __version__, time
from .commonconfig import (Tags)
from .credentials import Credentials, StaticProvider
from .credentials.providers import Provider
from .datatypes import (Bucket, CompleteMultipartUploadResult,
                        ListAllMyBucketsResult,
                        Object, Part,
                        parse_list_objects)
from .deleteobjects import (DeleteError, DeleteObject, DeleteRequest,
                            DeleteResult)
from .error import InvalidResponseError, NewteraError, ServerError
from .helpers import (_DEFAULT_USER_AGENT,
                      BaseURL, DictType, ObjectWriteResult, ProgressType,
                      ThreadPool, check_bucket_name, check_non_empty_string,
                      check_sse, check_ssec, genheaders, get_part_info,
                      headers_to_strings, makedirs,
                      md5sum_hash, queryencode, read_part_data, sha256_hash)
from .select import SelectObjectReader, SelectRequest
from .sse import Sse, SseCustomerKey
from .xml import Element, SubElement, findtext, getbytes, marshal, unmarshal


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
    _user_agent: str
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
            credentials: Provider | None = None,
    ):
        # Validate http client has correct base class.
        if http_client and not isinstance(http_client, urllib3.PoolManager):
            raise ValueError(
                "HTTP client should be instance of `urllib3.PoolManager`"
            )

        self._base_url = BaseURL(
            ("https://" if secure else "http://") + endpoint,
        )
        self._user_agent = _DEFAULT_USER_AGENT
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

    def _handle_redirect_response(
            self,
            method: str,
            bucket_name: str | None,
            response: BaseHTTPResponse,
            retry: bool = False,
    ) -> tuple[str | None, str | None]:
        """
        Handle redirect response indicates whether retry HEAD request
        on failure.
        """
        code, message = {
            301: ("PermanentRedirect", "Moved Permanently"),
            307: ("Redirect", "Temporary redirect"),
            400: ("BadRequest", "Bad request"),
        }.get(response.status, (None, None))
        region = response.headers.get("x-amz-bucket-region")
        if message and region:
            message += "; use region " + region

        if (
                retry and region and method == "HEAD" and bucket_name and
                self._region_map.get(bucket_name)
        ):
            code, message = ("RetryHead", None)

        return code, message

    def _build_headers(
            self,
            host: str,
            headers: DictType | None,
            body: bytes | None,
            creds: Credentials | None,
    ) -> tuple[DictType, datetime]:
        """Build headers with given parameters."""
        headers = headers or {}
        md5sum_added = headers.get("Content-MD5")
        headers["Host"] = host
        headers["User-Agent"] = self._user_agent
        sha256 = None
        md5sum = None

        if body:
            headers["Content-Length"] = str(len(body))
        if creds:
            if self._base_url.is_https:
                sha256 = "UNSIGNED-PAYLOAD"
                md5sum = None if md5sum_added else md5sum_hash(body)
            else:
                sha256 = sha256_hash(body)
        else:
            md5sum = None if md5sum_added else md5sum_hash(body)
        if md5sum:
            headers["Content-MD5"] = md5sum
        if sha256:
            headers["x-amz-content-sha256"] = sha256
        if creds and creds.session_token:
            headers["X-Amz-Security-Token"] = creds.session_token
        date = time.utcnow()
        headers["x-amz-date"] = time.to_amz_date(date)
        return headers, date

    def _url_open(
            self,
            method: str,
            bucket_name: str | None = None,
            object_name: str | None = None,
            body: bytes | None = None,
            headers: DictType | None = None,
            query_params: DictType | None = None,
            preload_content: bool = True,
            no_body_trace: bool = False,
    ) -> BaseHTTPResponse:
        """Execute HTTP request."""
        creds = self._provider.retrieve() if self._provider else None
        url = self._base_url.build(
            method,
            bucket_name=bucket_name,
            object_name=object_name,
            query_params=query_params,
        )
        headers = self._build_headers(url.netloc, headers, body, creds)

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
            301: lambda: self._handle_redirect_response(
                method, bucket_name, response, True,
            ),
            307: lambda: self._handle_redirect_response(
                method, bucket_name, response, True,
            ),
            400: lambda: self._handle_redirect_response(
                method, bucket_name, response, True,
            ),
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

        if response_error.code in ["NoSuchBucket", "RetryHead"]:
            if bucket_name is not None:
                self._region_map.pop(bucket_name, None)

        raise response_error

    def _execute(
            self,
            method: str,
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

            code, message = self._handle_redirect_response(
                method, bucket_name, exc.response,
            )
            raise exc.copy(cast(str, code), cast(str, message))

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

    def list_buckets(self) -> list[Bucket]:
        """
        List information of all accessible buckets.

        :return: List of :class:`Bucket <Bucket>` object.

        Example::
            buckets = client.list_buckets()
            for bucket in buckets:
                print(bucket.name, bucket.creation_date)
        """

        response = self._execute("GET")
        result = unmarshal(ListAllMyBucketsResult, response.data.decode())
        return result.buckets

    def bucket_exists(self, bucket_name: str) -> bool:
        """
        Check if a bucket exists.

        :param bucket_name: Name of the bucket.
        :return: True if the bucket exists.

        Example::
            if client.bucket_exists("my-bucket"):
                print("my-bucket exists")
            else:
                print("my-bucket does not exist")
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        try:
            self._execute("HEAD", bucket_name)
            return True
        except NewteraError as exc:
            if exc.code != "NoSuchBucket":
                raise
        return False

    def fput_object(
            self,
            bucket_name: str,
            object_name: str,
            file_path: str,
            content_type: str = "application/octet-stream",
            metadata: DictType | None = None,
            sse: Sse | None = None,
            progress: ProgressType | None = None,
            part_size: int = 0,
            num_parallel_uploads: int = 3,
    ) -> ObjectWriteResult:
        """
        Uploads data from a file to an object in a bucket.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param file_path: Name of file to upload.
        :param content_type: Content type of the object.
        :param metadata: Any additional metadata to be uploaded along
            with your PUT request.
        :param sse: Server-side encryption.
        :param progress: A progress object
        :param part_size: Multipart part size
        :param num_parallel_uploads: Number of parallel uploads.
        :return: :class:`ObjectWriteResult` object.

        Example::
            # Upload data.
            result = client.fput_object(
                "my-bucket", "my-object", "my-filename",
            )

            # Upload data with metadata.
            result = client.fput_object(
                "my-bucket", "my-object", "my-filename",
                metadata={"My-Project": "one"},
            )

            # Upload data with tags, retention and legal-hold.
            date = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0,
            ) + timedelta(days=30)
            tags = Tags(for_object=True)
            tags["User"] = "jsmith"
            result = client.fput_object(
                "my-bucket", "my-object", "my-filename",
            )
        """

        file_size = os.stat(file_path).st_size
        with open(file_path, "rb") as file_data:
            return self.put_object(
                bucket_name,
                object_name,
                file_data,
                file_size,
                content_type=content_type,
                metadata=cast(Union[DictType, None], metadata),
                sse=sse,
                progress=progress,
                part_size=part_size,
                num_parallel_uploads=num_parallel_uploads,
                tags=tags,
                retention=retention,
                legal_hold=legal_hold,
            )

    def fget_object(
            self,
            bucket_name: str,
            object_name: str,
            file_path: str,
            request_headers: DictType | None = None,
            ssec: SseCustomerKey | None = None,
            version_id: str | None = None,
            extra_query_params: DictType | None = None,
            tmp_file_path: str | None = None,
            progress: ProgressType | None = None,
    ):
        """
        Downloads data of an object to file.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param file_path: Name of file to download.
        :param request_headers: Any additional headers to be added with GET
                                request.
        :param ssec: Server-side encryption customer key.
        :param version_id: Version-ID of the object.
        :param extra_query_params: Extra query parameters for advanced usage.
        :param tmp_file_path: Path to a temporary file.
        :param progress: A progress object
        :return: Object information.

        Example::
            # Download data of an object.
            client.fget_object("my-bucket", "my-object", "my-filename")

            # Download data of an object of version-ID.
            client.fget_object(
                "my-bucket", "my-object", "my-filename",
                version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
            )

            # Download data of an SSE-C encrypted object.
            client.fget_object(
                "my-bucket", "my-object", "my-filename",
                ssec=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
            )
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_non_empty_string(object_name)

        if os.path.isdir(file_path):
            raise ValueError(f"file {file_path} is a directory")

        # Create top level directory if needed.
        makedirs(os.path.dirname(file_path))

        stat = self.stat_object(
            bucket_name,
            object_name,
            ssec,
            version_id=version_id,
        )

        etag = queryencode(cast(str, stat.etag))
        # Write to a temporary file "file_path.part.newtera" before saving.
        tmp_file_path = (
            tmp_file_path or f"{file_path}.{etag}.part.newtera"
        )

        response = None
        try:
            response = self.get_object(
                bucket_name,
                object_name,
                request_headers=request_headers,
                ssec=ssec,
                version_id=version_id,
                extra_query_params=extra_query_params,
            )

            if progress:
                # Set progress bar length and object name before upload
                length = int(response.headers.get('content-length', 0))
                progress.set_meta(object_name=object_name, total_length=length)

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
            object_name: str,
            offset: int = 0,
            length: int = 0,
            request_headers: DictType | None = None,
            ssec: SseCustomerKey | None = None,
            version_id: str | None = None,
            extra_query_params: DictType | None = None,
    ) -> BaseHTTPResponse:
        """
        Get data of an object. Returned response should be closed after use to
        release network resources. To reuse the connection, it's required to
        call `response.release_conn()` explicitly.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param offset: Start byte position of object data.
        :param length: Number of bytes of object data from offset.
        :param request_headers: Any additional headers to be added with GET
                                request.
        :param ssec: Server-side encryption customer key.
        :param version_id: Version-ID of the object.
        :param extra_query_params: Extra query parameters for advanced usage.
        :return: :class:`urllib3.response.BaseHTTPResponse` object.

        Example::
            # Get data of an object.
            try:
                response = client.get_object("my-bucket", "my-object")
                # Read data from response.
            finally:
                response.close()
                response.release_conn()

            # Get data of an object of version-ID.
            try:
                response = client.get_object(
                    "my-bucket", "my-object",
                    version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
                )
                # Read data from response.
            finally:
                response.close()
                response.release_conn()

            # Get data of an object from offset and length.
            try:
                response = client.get_object(
                    "my-bucket", "my-object", offset=512, length=1024,
                )
                # Read data from response.
            finally:
                response.close()
                response.release_conn()

            # Get data of an SSE-C encrypted object.
            try:
                response = client.get_object(
                    "my-bucket", "my-object",
                    ssec=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
                )
                # Read data from response.
            finally:
                response.close()
                response.release_conn()
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_non_empty_string(object_name)
        check_ssec(ssec)

        headers = cast(DictType, ssec.headers() if ssec else {})
        headers.update(request_headers or {})

        if offset or length:
            end = (offset + length - 1) if length else ""
            headers['Range'] = f"bytes={offset}-{end}"

        if version_id:
            extra_query_params = extra_query_params or {}
            extra_query_params["versionId"] = version_id

        return self._execute(
            "GET",
            bucket_name,
            object_name,
            headers=cast(DictType, headers),
            query_params=extra_query_params,
            preload_content=False,
        )

    def _put_object(
            self,
            bucket_name: str,
            object_name: str,
            data: bytes,
            headers: DictType | None,
            query_params: DictType | None = None,
    ) -> ObjectWriteResult:
        """Execute PutObject Newtera TDM API."""
        response = self._execute(
            "PUT",
            bucket_name,
            object_name,
            body=data,
            headers=headers,
            query_params=query_params,
            no_body_trace=True,
        )
        return ObjectWriteResult(
            bucket_name,
            object_name,
            response.headers.get("x-amz-version-id"),
            response.headers.get("etag", "").replace('"', ""),
            response.headers,
        )

    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream",
        metadata: DictType | None = None,
        sse: Sse | None = None,
        progress: ProgressType | None = None,
        part_size: int = 0,
        num_parallel_uploads: int = 3,
    ) -> ObjectWriteResult:
        """
        Uploads data from a stream to an object in a bucket.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param data: An object having callable read() returning bytes object.
        :param length: Data size; -1 for unknown size and set valid part_size.
        :param content_type: Content type of the object.
        :param metadata: Any additional metadata to be uploaded along
            with your PUT request.
        :param sse: Server-side encryption.
        :param progress: A progress object;
        :param part_size: Multipart part size.
        :param num_parallel_uploads: Number of parallel uploads.
        :return: :class:`ObjectWriteResult` object.

        Example::
            # Upload data.
            result = client.put_object(
                "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
            )

            # Upload data with metadata.
            result = client.put_object(
                "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
                metadata={"My-Project": "one"},
            )

            # Upload data with tags, retention and legal-hold.
            date = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0,
            ) + timedelta(days=30)
            tags = Tags(for_object=True)
            tags["User"] = "jsmith"
            result = client.put_object(
                "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
            )
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_non_empty_string(object_name)
        check_sse(sse)
        if tags is not None and not isinstance(tags, Tags):
            raise ValueError("tags must be Tags type")
        if not callable(getattr(data, "read")):
            raise ValueError("input data must have callable read()")
        part_size, part_count = get_part_info(length, part_size)
        if progress:
            # Set progress bar length and object name before upload
            progress.set_meta(object_name=object_name, total_length=length)

        headers = genheaders(metadata, sse, tags, retention, legal_hold)
        headers["Content-Type"] = content_type or "application/octet-stream"

        object_size = length
        uploaded_size = 0
        part_number = 0
        one_byte = b""
        stop = False
        upload_id = None
        parts: list[Part] = []
        pool: ThreadPool | None = None

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
                        bucket_name, object_name, part_data, headers,
                    )

                if not upload_id:
                    upload_id = self._create_multipart_upload(
                        bucket_name, object_name, headers,
                    )
                    if num_parallel_uploads and num_parallel_uploads > 1:
                        pool = ThreadPool(num_parallel_uploads)
                        pool.start_parallel()

                args = (
                    bucket_name,
                    object_name,
                    part_data,
                    (
                        cast(DictType, sse.headers())
                        if isinstance(sse, SseCustomerKey) else None
                    ),
                    upload_id,
                    part_number,
                )
                if num_parallel_uploads > 1:
                    cast(ThreadPool, pool).add_task(
                        self._upload_part_task, args,
                    )
                else:
                    etag = self._upload_part(*args)
                    parts.append(Part(part_number, etag))

            if pool:
                result = pool.result()
                parts = [Part(0, "")] * part_count
                while not result.empty():
                    part_number, etag = result.get()
                    parts[part_number-1] = Part(part_number, etag)

            upload_result = self._complete_multipart_upload(
                bucket_name, object_name, cast(str, upload_id), parts,
            )
            return ObjectWriteResult(
                cast(str, upload_result.bucket_name),
                cast(str, upload_result.object_name),
                upload_result.version_id,
                upload_result.etag,
                upload_result.http_headers,
                location=upload_result.location,
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
            recursive: bool = False,
            start_after: str | None = None,
            include_user_meta: bool = False,
            include_version: bool = False,
            use_api_v1: bool = False,
            use_url_encoding_type: bool = True,
            fetch_owner: bool = False,
    ):
        """
        Lists object information of a bucket.

        :param bucket_name: Name of the bucket.
        :param prefix: Object name starts with prefix.
        :param recursive: List recursively than directory structure emulation.
        :param start_after: List objects after this key name.
        :param include_user_meta: MinIO specific flag to control to include
                                 user metadata.
        :param include_version: Flag to control whether include object
                                versions.
        :param use_api_v1: Flag to control to use ListObjectV1 Newtera TDM API or not.
        :param use_url_encoding_type: Flag to control whether URL encoding type
                                      to be used or not.
        :return: Iterator of :class:`Object <Object>`.

        Example::
            # List objects information.
            objects = client.list_objects("my-bucket")
            for obj in objects:
                print(obj)

            # List objects information whose names starts with "my/prefix/".
            objects = client.list_objects("my-bucket", prefix="my/prefix/")
            for obj in objects:
                print(obj)

            # List objects information recursively.
            objects = client.list_objects("my-bucket", recursive=True)
            for obj in objects:
                print(obj)

            # List objects information recursively whose names starts with
            # "my/prefix/".
            objects = client.list_objects(
                "my-bucket", prefix="my/prefix/", recursive=True,
            )
            for obj in objects:
                print(obj)

            # List objects information recursively after object name
            # "my/prefix/world/1".
            objects = client.list_objects(
                "my-bucket", recursive=True, start_after="my/prefix/world/1",
            )
            for obj in objects:
                print(obj)
        """
        return self._list_objects(
            bucket_name,
            delimiter=None if recursive else "/",
            include_user_meta=include_user_meta,
            prefix=prefix,
            start_after=start_after,
            use_api_v1=use_api_v1,
            include_version=include_version,
            encoding_type="url" if use_url_encoding_type else None,
            fetch_owner=fetch_owner,
        )

    def stat_object(
            self,
            bucket_name: str,
            object_name: str,
            ssec: SseCustomerKey | None = None,
            version_id: str | None = None,
            extra_headers: DictType | None = None,
            extra_query_params: DictType | None = None,
    ) -> Object:
        """
        Get object information and metadata of an object.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param ssec: Server-side encryption customer key.
        :param version_id: Version ID of the object.
        :param extra_headers: Extra HTTP headers for advanced usage.
        :param extra_query_params: Extra query parameters for advanced usage.
        :return: :class:`Object <Object>`.

        Example::
            # Get object information.
            result = client.stat_object("my-bucket", "my-object")

            # Get object information of version-ID.
            result = client.stat_object(
                "my-bucket", "my-object",
                version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
            )

            # Get SSE-C encrypted object information.
            result = client.stat_object(
                "my-bucket", "my-object",
                ssec=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
            )
        """

        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_non_empty_string(object_name)
        check_ssec(ssec)

        headers = cast(DictType, ssec.headers() if ssec else {})
        if extra_headers:
            headers.update(extra_headers)

        query_params = extra_query_params or {}
        query_params.update({"versionId": version_id} if version_id else {})
        response = self._execute(
            "HEAD",
            bucket_name,
            object_name,
            headers=headers,
            query_params=query_params,
        )

        value = response.headers.get("last-modified")
        if value is not None:
            last_modified = time.from_http_header(value)
        else:
            last_modified = None

        return Object(
            bucket_name,
            object_name,
            last_modified=last_modified,
            etag=response.headers.get("etag", "").replace('"', ""),
            size=int(response.headers.get("content-length", "0")),
            content_type=response.headers.get("content-type"),
            metadata=response.headers,
            version_id=response.headers.get("x-amz-version-id"),
        )

    def remove_object(
        self,
        bucket_name: str,
        object_name: str,
        version_id: str | None = None
    ):
        """
        Remove an object.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param version_id: Version ID of the object.

        Example::
            # Remove object.
            client.remove_object("my-bucket", "my-object")

            # Remove version of an object.
            client.remove_object(
                "my-bucket", "my-object",
                version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
            )
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_non_empty_string(object_name)
        self._execute(
            "DELETE",
            bucket_name,
            object_name,
            query_params={"versionId": version_id} if version_id else None,
        )

    def _list_objects(
            self,
            bucket_name: str,
            continuation_token: str | None = None,  # listV2 only
            delimiter: str | None = None,  # all
            encoding_type: str | None = None,  # all
            fetch_owner: bool | None = None,  # listV2 only
            include_user_meta: bool = False,  # MinIO specific listV2.
            max_keys: int | None = None,  # all
            prefix: str | None = None,  # all
            start_after: str | None = None,
        # all: v1:marker, versioned:key_marker
            version_id_marker: str | None = None,  # versioned
            use_api_v1: bool = False,
            include_version: bool = False,
    ) -> Iterator[Object]:
        """
        List objects optionally including versions.
        Note: Its required to send empty values to delimiter/prefix and 1000 to
        max-keys when not provided for server-side bucket policy evaluation to
        succeed; otherwise AccessDenied error will be returned for such
        policies.
        """

        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)

        if version_id_marker:
            include_version = True

        is_truncated = True
        while is_truncated:
            query = {}
            if include_version:
                query["versions"] = ""
            elif not use_api_v1:
                query["list-type"] = "2"

            if not include_version and not use_api_v1:
                if continuation_token:
                    query["continuation-token"] = continuation_token
                if fetch_owner:
                    query["fetch-owner"] = "true"
                if include_user_meta:
                    query["metadata"] = "true"
            query["delimiter"] = delimiter or ""
            if encoding_type:
                query["encoding-type"] = encoding_type
            query["max-keys"] = str(max_keys or 1000)
            query["prefix"] = prefix or ""
            if start_after:
                if include_version:
                    query["key-marker"] = start_after
                elif use_api_v1:
                    query["marker"] = start_after
                else:
                    query["start-after"] = start_after
            if version_id_marker:
                query["version-id-marker"] = version_id_marker

            response = self._execute(
                "GET",
                bucket_name,
                query_params=cast(DictType, query),
            )

            objects, is_truncated, start_after, version_id_marker = (
                parse_list_objects(response)
            )

            if not include_version:
                version_id_marker = None
                if not use_api_v1:
                    continuation_token = start_after

            for obj in objects:
                yield obj
