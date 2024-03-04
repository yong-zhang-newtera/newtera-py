# -*- coding: utf-8 -*-
# MinIO Python Library for Amazon S3 Compatible Cloud Storage,
# (C) 2015 MinIO, Inc.
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

import unittest.mock as mock
from unittest import TestCase

from newtera import Newtera
from newtera.api import _DEFAULT_USER_AGENT
from newtera.error import NewteraError

from .helpers import generate_error
from .minio_mocks import MockConnection, MockResponse


class GetObjectTest(TestCase):
    def test_object_is_string(self):
        client = Newtera('localhost:8080')
        self.assertRaises(TypeError, client.get_object, 'hello', 1234)

    def test_object_is_not_empty_string(self):
        client = Newtera('localhost:8080')
        self.assertRaises(ValueError, client.get_object, 'hello', ' \t \n ')

    @mock.patch('urllib3.PoolManager')
    def test_get_object_throws_fail(self, mock_connection):
        error_xml = generate_error('code', 'message', 'request_id',
                                   'host_id', 'resource', 'bucket',
                                   'object')
        mock_server = MockConnection()
        mock_connection.return_value = mock_server
        mock_server.mock_add_request(
            MockResponse('GET',
                         'https://localhost:8080/hello/key',
                         {'User-Agent': _DEFAULT_USER_AGENT},
                         404,
                         response_headers={"Content-Type": "application/xml"},
                         content=error_xml.encode())
        )
        client = Newtera('localhost:8080')
        self.assertRaises(NewteraError, client.get_object, 'hello', 'key')
