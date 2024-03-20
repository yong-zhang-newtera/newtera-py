# 适用于与Amazon S3兼容的云存储的Newtera Python Library [![Slack](https://slack.min.io/slack?type=svg)](https://slack.min.io)

Newtera Python Client SDK提供简单的API来访问任何与Amazon S3兼容的对象存储服务。

本文我们将学习如何安装Newtera client SDK，并运行一个python的示例程序。对于完整的API以及示例，请参考[Python Client API Reference](https://min.io/docs/newtera/linux/developers/python/API.html)。

本文假设你已经有一个可运行的 [Python](https://www.python.org/downloads/)开发环境。

## 最低要求

- Python 3.4或更高版本

## 使用pip安装

```sh
pip install newtera
```

## 使用源码安装

```sh
git clone https://github.com/newtera/newtera-py
cd newtera-py
python setup.py install
```

## 初始化Newtera Client

Newtera client需要以下4个参数来连接Newtera对象存储服务。

| 参数     | 描述  |
| :------- | :---- |
| endpoint | 对象存储服务的URL。 |
| access_key| Access key是唯一标识你的账户的用户ID。  |
| secret_key| Secret key是你账户的密码。   |
|secure| true代表使用HTTPS。 |

```py
from newtera import Newtera
from newtera.error import ResponseError

minioClient = Newtera('localhost:8080',
                  access_key='demo1',
                  secret_key='888',
                  secure=True)
```


## 示例-文件上传
本示例连接到一个Newtera对象存储服务，创建一个存储桶并上传一个文件到存储桶中。

我们在本示例中使用运行在 [https://localhost:8080](https://localhost:8080) 上的Newtera服务，你可以用这个服务来开发和测试。示例中的访问凭据是公开的。

#### file-uploader.py

```py
# 引入Newtera包。
from newtera import Newtera
from newtera.error import (ResponseError, BucketAlreadyOwnedByYou,
                         BucketAlreadyExists)

# 使用endpoint、access key和secret key来初始化minioClient对象。
minioClient = Newtera('localhost:8080',
                    access_key='demo1',
                    secret_key='888',
                    secure=True)

#### Run file-uploader

```bash
python file_uploader.py

mc ls play/maylogs/
[2016-05-27 16:41:37 PDT]  12MiB pumaserver_debug.log
```

## API文档

完整的API文档在这里。
* [完整API文档](https://min.io/docs/newtera/linux/developers/python/API.html)

### API文档 : 操作存储桶

* [`list_buckets`](https://min.io/docs/newtera/linux/developers/python/API.html#list_buckets)
* [`bucket_exists`](https://min.io/docs/newtera/linux/developers/python/API.html#bucket_exists)
* [`remove_bucket`](https://min.io/docs/newtera/linux/developers/python/API.html#remove_bucket)
* [`list_objects`](https://min.io/docs/newtera/linux/developers/python/API.html#list_objects)
* [`list_objects_v2`](https://min.io/docs/newtera/linux/developers/python/API.html#list_objects_v2)
* [`list_incomplete_uploads`](https://min.io/docs/newtera/linux/developers/python/API.html#list_incomplete_uploads)

### API文档 : 操作文件对象

* [`fput_object`](https://min.io/docs/newtera/linux/developers/python/API.html#fput_object)
* [`fget_object`](https://min.io/docs/newtera/linux/developers/python/API.html#fget_object)

### API文档 : 操作对象

* [`get_object`](https://min.io/docs/newtera/linux/developers/python/API.html#get_object)
* [`put_object`](https://min.io/docs/newtera/linux/developers/python/API.html#put_object)
* [`stat_object`](https://min.io/docs/newtera/linux/developers/python/API.html#stat_object)
* [`get_partial_object`](https://min.io/docs/newtera/linux/developers/python/API.html#get_partial_object)
* [`remove_object`](https://min.io/docs/newtera/linux/developers/python/API.html#remove_object)
* [`remove_objects`](https://min.io/docs/newtera/linux/developers/python/API.html#remove_objects)
* [`remove_incomplete_upload`](https://min.io/docs/newtera/linux/developers/python/API.html#remove_incomplete_upload)

### API文档 : Presigned操作

* [`presigned_get_object`](https://min.io/docs/newtera/linux/developers/python/API.html#presigned_get_object)
* [`presigned_put_object`](https://min.io/docs/newtera/linux/developers/python/API.html#presigned_put_object)
* [`presigned_post_policy`](https://min.io/docs/newtera/linux/developers/python/API.html#presigned_post_policy)

## 完整示例

#### 完整示例 : 操作存储桶

* [list_buckets.py](https://github.com/newtera/newtera-py/blob/master/examples/list_buckets.py)
* [bucket_exists.py](https://github.com/newtera/newtera-py/blob/master/examples/bucket_exists.py)
* [list_objects.py](https://github.com/newtera/newtera-py/blob/master/examples/list_objects.py)
* [remove_bucket.py](https://github.com/newtera/newtera-py/blob/master/examples/remove_bucket.py)
* [list_incomplete_uploads.py](https://github.com/newtera/newtera-py/blob/master/examples/list_incomplete_uploads.py)

#### 完整示例 : 操作文件对象

* [fput_object.py](https://github.com/newtera/newtera-py/blob/master/examples/fput_object.py)
* [fget_object.py](https://github.com/newtera/newtera-py/blob/master/examples/fget_object.py)

#### 完整示例 : 操作对象

* [get_object.py](https://github.com/newtera/newtera-py/blob/master/examples/get_object.py)
* [put_object.py](https://github.com/newtera/newtera-py/blob/master/examples/put_object.py)
* [stat_object.py](https://github.com/newtera/newtera-py/blob/master/examples/stat_object.py)
* [get_partial_object.py](https://github.com/newtera/newtera-py/blob/master/examples/get_partial_object.py)
* [remove_object.py](https://github.com/newtera/newtera-py/blob/master/examples/remove_object.py)
* [remove_objects.py](https://github.com/newtera/newtera-py/blob/master/examples/remove_objects.py)
* [remove_incomplete_upload.py](https://github.com/newtera/newtera-py/blob/master/examples/remove_incomplete_upload.py)

#### 完整示例 : Presigned操作

* [presigned_get_object.py](https://github.com/newtera/newtera-py/blob/master/examples/presigned_get_object.py)
* [presigned_put_object.py](https://github.com/newtera/newtera-py/blob/master/examples/presigned_put_object.py)
* [presigned_post_policy.py](https://github.com/newtera/newtera-py/blob/master/examples/presigned_post_policy.py)

## 了解更多

* [完整文档](https://min.io/docs/newtera/kubernetes/upstream/index.html)
* [Newtera Python SDK API文档](https://min.io/docs/newtera/linux/developers/python/API.html)

## 贡献

[贡献指南](https://github.com/newtera/newtera-py/blob/master/docs/zh_CN/CONTRIBUTING.md)

[![PYPI](https://img.shields.io/pypi/v/newtera.svg)](https://pypi.python.org/pypi/newtera)
[![Build Status](https://travis-ci.org/newtera/newtera-py.svg)](https://travis-ci.org/newtera/newtera-py)
[![Build status](https://ci.appveyor.com/api/projects/status/1d05e6nvxcelmrak?svg=true)](https://ci.appveyor.com/project/harshavardhana/newtera-py)
