# -*- coding: utf-8 -*-
# Newtera Python Library for Newtera TDM,
# (C) 2024 Newtera, Inc.
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

import io
from newtera import Newtera

client = Newtera(
    "localhost:8080",
    access_key="demo1",
    secret_key="888",
)

# Upload data.
bucketName = "tdm"
prefix = "Task-20230930-0023\慢充功能测试\电池循环充放电数据"
object_name = "test-data.txt"

result = client.put_object(
    bucketName, prefix, object_name, io.BytesIO(b"hello"), 5,
)
print(
    "created {0} object".format(
        result.object_name,
    ),
)
