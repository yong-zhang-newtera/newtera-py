# -*- coding: utf-8 -*-
# Newtera Python Library for Newtera TDM,
# (C) 2020 Newtera, Inc.
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

"""Credential definitions to access S3 service."""
from __future__ import annotations


class Credentials:
    """
    Represents credentials access key, secret key and session token.
    """

    _access_key: str
    _secret_key: str

    def __init__(
        self,
        access_key: str,
        secret_key: str,
    ):
        if not access_key:
            raise ValueError("Access key must not be empty")

        if not secret_key:
            raise ValueError("Secret key must not be empty")

        self._access_key = access_key
        self._secret_key = secret_key

    @property
    def access_key(self) -> str:
        """Get access key."""
        return self._access_key

    @property
    def secret_key(self) -> str:
        """Get secret key."""
        return self._secret_key
