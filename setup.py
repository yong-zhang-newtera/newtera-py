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

import codecs
import re
import sys

from setuptools import setup

if sys.argv[-1] == "publish":
    sys.argv = sys.argv[:-1] + ["sdist", "upload"]

with codecs.open("newtera/__init__.py") as file:
    version = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
        file.read(),
        re.MULTILINE,
    ).group(1)

with codecs.open("README.md", encoding="utf-8") as file:
    readme = file.read()

setup(
    name="newtera",
    description="Newtera Python SDK for Newtera TDM",
    author="Newtera",
    url="https://github.com/yong-zhang-newtera/newtera-py",
    author_email="info@newtera.com",
    version=version,
    long_description_content_type="text/markdown",
    package_dir={"newtera": "newtera"},
    packages=["newtera", "newtera.credentials"],
    install_requires=["urllib3", "typing-extensions"],
    tests_require=[],
    license="Apache-2.0",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    long_description=readme,
    package_data={"": ["LICENSE", "README.md"]},
    include_package_data=True,
)
