
Newtera Python Client SDK提供简单的API来访问Newtera TDM存储的数据。

本文我们将学习如何安装Newtera client SDK，并运行一个python的示例程序。对于完整的API以及示例，请参考[Python Client API Reference](http://newtera.net/docs/newtera/linux/developers/python/API.html)。

本文假设你已经有一个可运行的 [Python](https://www.python.org/downloads/)开发环境。

## 最低要求

- Python 3.4或更高版本

## 使用pip安装

```sh
pip install newtera
```

## 使用源码安装

```sh
git clone https://github.com/yong-zhang-newtera/newtera-py
cd newtera-py
python setup.py install
```

## 初始化Newtera Client

Newtera client需要以下3个参数来连接Newtera TDM服务。

| 参数     | 描述  |
| :------- | :---- |
| endpoint | Newtera TDM服务的URL。 |
| access_key| Access key是唯一标识你的账户的用户ID。  |
| secret_key| Secret key是你账户的密码。   |

```py
from newtera import Newtera
from newtera.error import ResponseError

newteraClient = Newtera('localhost:8080',
                  access_key='demo1',
                  secret_key='888')
```


## 示例-文件上传
本示例连接到一个Newtera TDM服务，上传一个文件到存储桶中。

我们在本示例中使用运行在 [https://localhost:8080](https://localhost:8080) 上的Newtera TDM服务，你可以用这个服务来开发和测试。

#### file-uploader.py

```py
# 引入Newtera包。
from newtera import Newtera
from newtera.error import (ResponseError, BucketAlreadyOwnedByYou,
                         BucketAlreadyExists)

# 使用endpoint、access key和secret key来初始化newteraClient对象。
newteraClient = Newtera('localhost:8080',
                    access_key='demo1',
                    secret_key='888')
```

## API文档

完整的API文档在这里。
* [完整API文档](http://newtera.net/docs/newtera/linux/developers/python/API.html)

