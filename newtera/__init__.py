# -*- coding: utf-8 -*-
# Newtera Python Library for Newtera TDM,
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

"""
newtera - Newtera Python SDK for Newtera TDM

    >>> from newtera import Newtera
    >>> client = Newtera(
    ...     "localhost:8080",
    ...     access_key="demo1",
    ...     secret_key="888",
    ... )
    >>> buckets = client.list_buckets()
    >>> for bucket in buckets:
    ...     print(bucket.name, bucket.creation_date)

:copyright: (C) 2015-2020 Newtera, Inc.
:license: Apache 2.0, see LICENSE for more details.
"""

__title__ = "newtera-py"
__author__ = "Newtera, Inc."
__version__ = "1.0.0"
__license__ = "Apache 2.0"
__copyright__ = "Copyright 2024 Newtera, Inc."

# pylint: disable=unused-import,useless-import-alias
from .api import Newtera as Newtera
from .error import InvalidResponseError as InvalidResponseError
from .error import NewteraError as NewteraError
from .error import ServerError as ServerError
