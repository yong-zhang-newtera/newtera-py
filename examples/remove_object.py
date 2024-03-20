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

from newtera import Newtera

client = Newtera(
    "localhost:8080",
    access_key="demo1",
    secret_key="888",
)

# Remove object.
client.remove_object("tdm", "my-object")

# Remove version of an object.
client.remove_object(
    "tdm", "my-object",
    version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
)
