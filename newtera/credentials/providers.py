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

"""Credential providers."""

from __future__ import annotations

from abc import ABCMeta, abstractmethod


from .credentials import Credentials


class Provider:  # pylint: disable=too-few-public-methods
    """Credential retriever."""
    __metaclass__ = ABCMeta

    @abstractmethod
    def retrieve(self) -> Credentials:
        """Retrieve credentials and its expiry if available."""


class StaticProvider(Provider):
    """Fixed credential provider."""

    def __init__(
            self,
            access_key: str,
            secret_key: str,
    ):
        self._credentials = Credentials(access_key, secret_key)

    def retrieve(self) -> Credentials:
        """Return passed credentials."""
        return self._credentials








