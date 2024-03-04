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

from .minio_mocks import MockConnection, MockResponse


class BucketExists(TestCase):
    def test_bucket_is_string(self):
        client = Newtera('localhost:8080')
        self.assertRaises(TypeError, client.bucket_exists, 1234)

    def test_bucket_is_not_empty_string(self):
        client = Newtera('localhost:8080')
        self.assertRaises(ValueError, client.bucket_exists, '  \t \n  ')

    def test_bucket_exists_invalid_name(self):
        client = Newtera('localhost:8080')
        self.assertRaises(ValueError, client.bucket_exists, 'AB*CD')

    @mock.patch('urllib3.PoolManager')
    def test_bucket_exists_bad_request(self, mock_connection):
        mock_server = MockConnection()
        mock_connection.return_value = mock_server
        mock_server.mock_add_request(
            MockResponse('HEAD',
                         'https://localhost:8080/hello',
                         {'User-Agent': _DEFAULT_USER_AGENT},
                         400)
        )
        client = Newtera('localhost:8080')
        self.assertRaises(NewteraError, client.bucket_exists, 'hello')

    @mock.patch('urllib3.PoolManager')
    def test_bucket_exists_works(self, mock_connection):
        mock_server = MockConnection()
        mock_connection.return_value = mock_server
        mock_server.mock_add_request(
            MockResponse('HEAD',
                         'https://localhost:8080/hello',
                         {'User-Agent': _DEFAULT_USER_AGENT},
                         200)
        )
        client = Newtera('localhost:8080')
        result = client.bucket_exists('hello')
        self.assertTrue(result)
        mock_server.mock_add_request(
            MockResponse('HEAD',
                         'https://localhost:8080/goodbye',
                         {'User-Agent': _DEFAULT_USER_AGENT},
                         404)
        )
        false_result = client.bucket_exists('goodbye')
        self.assertFalse(false_result)
