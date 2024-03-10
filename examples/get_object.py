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

from newtera import Newtera

client = Newtera(
    "localhost:8080",
    access_key="demo1",
    secret_key="888",
)

# Get data of an object.
response = None
try:
    response = client.get_object("tdm", "my-object")
    # Read data from response.
finally:
    response.close()
    response.release_conn()

# Get data of an object from offset and length.
try:
    response = client.get_object(
        "tdm", "my-object", offset=512, length=1024,
    )
    # Read data from response.
finally:
    response.close()
    response.release_conn()

# Get data of an SSE-C encrypted object.
try:
    response = client.get_object(
        "tdm", "my-object",
    )
    # Read data from response.
finally:
    response.close()
    response.release_conn()
