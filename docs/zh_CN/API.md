# Python Client API文档 [![Slack](https://slack.min.io/slack?type=svg)](https://slack.min.io)

## 初使化MinIO Client对象。

## MinIO

```py
from newtera import Newtera
from newtera.error import ResponseError

minioClient = Newtera('localhost:8080',
                  access_key='demo1',
                  secret_key='888',
                  secure=True)
```

## AWS S3

```py
from newtera import Newtera
from newtera.error import ResponseError

s3Client = Newtera('s3.amazonaws.com',
                 access_key='YOUR-ACCESSKEYID',
                 secret_key='YOUR-SECRETACCESSKEY',
                 secure=True)
```


## 1. 构造函数

<a name="MinIO"></a>
### Newtera(endpoint, access_key=None, secret_key=None, secure=True, region=None, http_client=None)

|   |
|---|
| `Newtera(endpoint, access_key=None, secret_key=None, secure=True, region=None, http_client=None)`  |
| 初使化一个新的client对象。  |

参数


|参数   | 类型   |描述   |
|:---|:---|:---|
| `endpoint`  | _string_  | S3兼容对象存储服务endpoint。  |
| `access_key`  | _string_  | 对象存储的Access key。（如果是匿名访问则可以为空）。  |
| `secret_key` | _string_  |  对象存储的Secret key。（如果是匿名访问则可以为空）。 |
| `secure`  |_bool_   | 设为`True`代表启用HTTPS。 (默认是`True`)。  |
| `region`  |_string_ | 设置该值以覆盖自动发现存储桶region。 （可选，默认值是`None`）。 |
| `http_client` |_urllib3.poolmanager.PoolManager_ | 设置该值以使用自定义的http client，而不是默认的http client。（可选，默认值是`None`）。 |

__示例__

### MinIO

```py
from newtera import Newtera
from newtera.error import ResponseError

minioClient = Newtera('localhost:8080',
                    access_key='demo1',
                    secret_key='888')
```

```py
from newtera import Newtera
from newtera.error import ResponseError
import urllib3

httpClient = urllib3.ProxyManager(
                'https://proxy_host.sampledomain.com:8119/'
                timeout=urllib3.Timeout.DEFAULT_TIMEOUT,
                cert_reqs='CERT_REQUIRED',
                retries=urllib3.Retry(
                    total=5,
                    backoff_factor=0.2,
                    status_forcelist=[500, 502, 503, 504]
                )
            )
minioClient = Newtera('your_hostname.sampledomain.com:9000',
                    access_key='ACCESS_KEY',
                    secret_key='SECRET_KEY',
                    secure=True,
                    http_client=httpClient)
```

### AWS S3

```py
from newtera import Newtera
from newtera.error import ResponseError

s3Client = Newtera('s3.amazonaws.com',
                 access_key='ACCESS_KEY',
                 secret_key='SECRET_KEY')
```

## 2. 操作存储桶

<a name="list_buckets"></a>
### list_buckets()
列出所有的存储桶。

参数

|返回值   | 类型   |描述   |
|:---|:---|:---|
|``bucketList``   |_function_ |所有存储桶的list。 |
|``bucket.name``   |_string_  |存储桶名称。 |
|``bucket.creation_date`` |_time_   |存储桶的创建时间。 |

__示例__

```py
buckets = minioClient.list_buckets()
for bucket in buckets:
    print(bucket.name, bucket.creation_date)
```

<a name="bucket_exists"></a>
### bucket_exists(bucket_name)
检查存储桶是否存在。

参数

|参数   | 类型   |描述   |
|:---|:---|:---|
|``bucket_name``   |_string_|存储桶名称。 |

__示例__

```py
try:
    print(minioClient.bucket_exists("mybucket"))
except ResponseError as err:
    print(err)
```


<a name="list_objects"></a>
### list_objects(bucket_name, prefix=None, recursive=False)
列出存储桶中所有对象。

参数

| 参数  |  类型 | 描述  |
|:---|:---|:---|
|``bucket_name``   |_string_ | 存储桶名称。  |
|``prefix``   | _string_ |用于过滤的对象名称前缀。可选项，默认为None。 |
|``recursive``   | _bool_ |`True`代表递归查找，`False`代表类似文件夹查找，以'/'分隔，不查子文件夹。（可选，默认值是`False`）。   |

__返回值__

| 参数  |  类型 | 描述  |
|:---|:---|:---|
|``object``   |_Object_ | 该存储桶中所有对象的Iterator，对象的格式如下：  |

| 参数  |  类型 | 描述  |
|:---|:---|:---|
|``object.bucket_name``  | _string_ | 对象所在存储桶的名称。|
|``object.object_name``  | _string_ | 对象的名称。|
|``object.is_dir``       |  _bool_  | `True`代表列举的对象是文件夹（对象前缀）， `False`与之相反。|
|``object.size`` | _int_ | 对象的大小。|
|``object.etag`` | _string_ | 对象的etag值。|
|``object.last_modified`` |_datetime.datetime_ | 最后修改时间。|
|``object.content_type`` | _string_ | 对象的content-type。|
|``object.metadata``     |  _dict_  | 对象的其它元数据。|


__示例__

```py
# List all object paths in bucket that begin with my-prefixname.
objects = minioClient.list_objects('mybucket', prefix='my-prefixname',
                              recursive=True)
for obj in objects:
    print(obj.bucket_name, obj.object_name.encode('utf-8'), obj.last_modified,
          obj.etag, obj.size, obj.content_type)
```

## 3. 操作对象
<a name="get_object"></a>
### get_object(bucket_name, object_name, request_headers=None)
下载一个对象。

参数

|参数   | 类型   |描述   |
|:---|:---|:---|
|``bucket_name``   |_string_   |存储桶名称。   |
|``object_name``   |_string_   |对象名称。  |
|``request_headers`` |_dict_   |额外的请求头信息 （可选，默认为None）。  |

__返回值__

|参数   | 类型   |描述   |
|:---|:---|:---|
|``object``   | _urllib3.response.HTTPResponse_   |http streaming reader。  |

__示例__


```py
# Get a full object.
try:
    data = minioClient.get_object('mybucket', 'myobject')
    with open('my-testfile', 'wb') as file_data:
        for d in data.stream(32*1024):
            file_data.write(d)
except ResponseError as err:
    print(err)
```

<a name="fget_object"></a>
### fget_object(bucket_name, object_name, file_path, request_headers=None)
下载并将文件保存到本地。

参数


|参数   | 类型   |描述   |
|:---|:---|:---|
|``bucket_name``   |_string_   |存储桶名称。   |
|``object_name``   |_string_    |对象名称。   |
|``file_path``   |_dict_ | 对象数据要写入的本地文件路径。 |
|``request_headers`` |_dict_   |额外的请求头信息 （可选，默认为None）。  |

__返回值__

|参数   | 类型   |描述   |
|:---|:---|:---|
|``obj``|_Object_  |对象的统计信息，格式如下： |

|参数   | 类型   |描述   |
|:---|:---|:---|
|``obj.size``|_int_  | 对象的大小。 |
|``obj.etag``|_string_| 对象的etag值。|
|``obj.content_type``|_string_  | 对象的Content-Type。|
|``obj.last_modified``|_time.time_  | 最后修改时间。|
|``obj.metadata`` |_dict_ | 对象的其它元数据。 |

__示例__

```py
# Get a full object and prints the original object stat information.
try:
    print(minioClient.fget_object('mybucket', 'myobject', '/tmp/myobject'))
except ResponseError as err:
    print(err)
```

<a name="put_object"></a>
### put_object(bucket_name, object_name, data, length, content_type='application/octet-stream', metadata=None)
添加一个新的对象到对象存储服务。

注意：本API支持的最大文件大小是5TB。

参数

|参数   | 类型   |描述   |
|:---|:---|:---|
|``bucket_name``   |_string_   |存储桶名称。   |
|``object_name``   |_string_    |对象名称。   |
|``data``   |_io.RawIOBase_   |任何实现了io.RawIOBase的python对象。 |
|``length``   |_int_   |对象的总长度。   |
|``content_type``   |_string_ | 对象的Content type。（可选，默认是“application/octet-stream”）。   |
|``metadata``   |_dict_ | 其它元数据。（可选，默认是None）。 |

__返回值__

|参数   | 类型   |描述   |
|:---|:---|:---|
|``etag``|_string_  |对象的etag值。  |

__示例__

单个对象的最大大小限制在5TB。put_object在对象大于5MiB时，自动使用multiple parts方式上传。这样，当上传失败时，客户端只需要上传未成功的部分即可（类似断点上传）。上传的对象使用MD5SUM签名进行完整性验证。

```py
import os
# Put a file with default content-type, upon success prints the etag identifier computed by server.
try:
    with open('my-testfile', 'rb') as file_data:
        file_stat = os.stat('my-testfile')
        print(minioClient.put_object('mybucket', 'myobject',
                               file_data, file_stat.st_size))
except ResponseError as err:
    print(err)

# Put a file with 'application/csv'.
try:
    with open('my-testfile.csv', 'rb') as file_data:
        file_stat = os.stat('my-testfile.csv')
        minioClient.put_object('mybucket', 'myobject.csv', file_data,
                    file_stat.st_size, content_type='application/csv')
except ResponseError as err:
    print(err)
```

<a name="fput_object"></a>
### fput_object(bucket_name, object_name, file_path, content_type='application/octet-stream', metadata=None)
通过文件上传到对象中。

参数

|参数   | 类型   |描述   |
|:---|:---|:---|
|``bucket_name``   |_string_  |存储桶名称。   |
|``object_name``   |_string_    |对象名称。   |
|``file_path``   |_string_ |本地文件的路径，会将该文件的内容上传到对象存储服务上。 |
|``content_type``   |_string_ | 对象的Content type（可选，默认是“application/octet-stream”）。 |
|``metadata``   |_dict_ | 其它元数据（可选，默认是None）。 |

__返回值__

|参数   | 类型   |描述   |
|:---|:---|:---|
|``etag``|_string_  |对象的etag值。  |

__示例__

单个对象的最大大小限制在5TB。fput_object在对象大于5MiB时，自动使用multiple parts方式上传。这样，当上传失败时，客户端只需要上传未成功的部分即可（类似断点上传）。上传的对象使用MD5SUM签名进行完整性验证。

```py
# Put an object 'myobject' with contents from '/tmp/otherobject', upon success prints the etag identifier computed by server.
try:
    print(minioClient.fput_object('mybucket', 'myobject', '/tmp/otherobject'))
except ResponseError as err:
    print(err)

# Put on object 'myobject.csv' with contents from
# '/tmp/otherobject.csv' as 'application/csv'.
try:
    print(minioClient.fput_object('mybucket', 'myobject.csv',
                             '/tmp/otherobject.csv',
                             content_type='application/csv'))
except ResponseError as err:
    print(err)
```

<a name="stat_object"></a>
### stat_object(bucket_name, object_name)
获取对象的元数据。

参数

|参数   | 类型   |描述   |
|:---|:---|:---|
|``bucket_name``   |_string_  |存储桶名称。   |
|``object_name``   |_string_  |名称名称。  |

__返回值__

|参数   | 类型   |描述   |
|:---|:---|:---|
|``obj``|_Object_  |对象的统计信息，格式如下：  |

|参数   | 类型   |描述   |
|:---|:---|:---|
|``obj.size``|_int_  |对象的大小。 |
|``obj.etag``|_string_|对象的etag值。|
|``obj.content_type``|_string_  | 对象的Content-Type。 |
|``obj.last_modified``|_time.time_  | UTC格式的最后修改时间。|
|``obj.metadata`` |_dict_ | 对象的其它元数据信息。 |


__示例__


```py
# Fetch stats on your object.
try:
    print(minioClient.stat_object('mybucket', 'myobject'))
except ResponseError as err:
    print(err)
```

<a name="remove_object"></a>
### remove_object(bucket_name, object_name)
删除一个对象。

参数

|参数   | 类型   |描述   |
|:---|:---|:---|
|``bucket_name``   |_string_   |存储桶名称。   |
|``object_name``   |_string_    |对象名称。   |

__示例__


```py
# Remove an object.
try:
    minioClient.remove_object('mybucket', 'myobject')
except ResponseError as err:
    print(err)
```

<a name="remove_objects"></a>
### remove_objects(bucket_name, objects_iter)
删除存储桶中的多个对象。

参数

|参数   | 类型   |描述   |
|:---|:---|:---|
|``bucket_name``   | _string_  | 存储桶名称。   |
|``objects_iter``   | _list_ , _tuple_ or _iterator_ | 多个对象名称的列表数据。   |

__返回值__

|参数   | 类型   |描述   |
|:---|:---|:---|
|``delete_error_iterator`` | _iterator_ of _MultiDeleteError_ instances | 删除失败的错误信息iterator,格式如下： |

_注意_

1. 由于上面的方法是延迟计算（lazy evaluation），默认是不计算的，所以上面返回的iterator必须被evaluated（比如：使用循环）。

2. 该iterator只有在执行删除操作出现错误时才不为空，每一项都包含删除报错的对象的错误信息。

该iterator产生的每一个删除错误信息都有如下结构：

|参数 |类型 |描述 |
|:---|:---|:---|
|``MultiDeleteError.object_name`` | _string_ | 删除报错的对象名称。 |
|``MultiDeleteError.error_code`` | _string_ | 错误码。 |
|``MultiDeleteError.error_message`` | _string_ | 错误信息。 |

__示例__


```py
# Remove multiple objects in a single library call.
try:
    objects_to_delete = ['myobject-1', 'myobject-2', 'myobject-3']
    # force evaluation of the remove_objects() call by iterating over
    # the returned value.
    for del_err in minioClient.remove_objects('mybucket', objects_to_delete):
        print("Deletion Error: {}".format(del_err))
except ResponseError as err:
    print(err)
```

<a name="remove_incomplete_upload"></a>
### remove_incomplete_upload(bucket_name, object_name)
删除一个未完整上传的对象。

参数

|参数   | 类型   |描述   |
|:---|:---|:---|
|``bucket_name``   |_string_   |存储桶名称。   |
|``object_name``   |_string_   |对象名称。   |

__示例__


```py
# Remove an partially uploaded object.
try:
    minioClient.remove_incomplete_upload('mybucket', 'myobject')
except ResponseError as err:
    print(err)
```

## 4. Presigned操作

<a name="presigned_get_object"></a>
### presigned_get_object(bucket_name, object_name, expiry=timedelta(days=7))
生成一个用于HTTP GET操作的presigned URL。浏览器/移动客户端可以在即使存储桶为私有的情况下也可以通过这个URL进行下载。这个presigned URL可以有一个过期时间，默认是7天。


参数

|参数   | 类型   |描述   |
|:---|:---|:---|
|``bucket_name``   |_string_   |存储桶名称。   |
|``object_name``   |_string_    |对象名称。   |
|``expiry``   | _datetime.datetime_    |过期时间，单位是秒，默认是7天。    |
|``response_headers``   | _dictionary_    |额外的响应头 （比如：`response-content-type`、`response-content-disposition`）。     |

__示例__


```py
from datetime import timedelta

# presigned get object URL for object name, expires in 2 days.
try:
    print(minioClient.presigned_get_object('mybucket', 'myobject', expires=timedelta(days=2)))
# Response error is still possible since internally presigned does get bucket location.
except ResponseError as err:
    print(err)
```

<a name="presigned_put_object"></a>
### presigned_put_object(bucket_name, object_name, expires=timedelta(days=7))
生成一个用于HTTP PUT操作的presigned URL。浏览器/移动客户端可以在即使存储桶为私有的情况下也可以通过这个URL进行上传。这个presigned URL可以有一个过期时间，默认是7天。

注意：你可以通过只指定对象名称上传到S3。


参数

|参数   | 类型   |描述   |
|:---|:---|:---|
|``bucket_name``   |_string_  |存储桶名称。   |
|``object_name``   |_string_    |对象名称。   |
|``expiry``   | _datetime.datetime_    |过期时间，单位是秒，默认是7天。    |

__示例__

```py
from datetime import timedelta

# presigned Put object URL for an object name, expires in 3 days.
try:
    print(minioClient.presigned_put_object('mybucket',
                                      'myobject',
                                      expires=timedelta(days=3)))
# Response error is still possible since internally presigned does get
# bucket location.
except ResponseError as err:
    print(err)
```

使用`curl`POST你的数据：


```py
curl_str = 'curl -X POST {0}'.format(signed_form_data[0])
curl_cmd = [curl_str]
for field in signed_form_data[1]:
    curl_cmd.append('-F {0}={1}'.format(field, signed_form_data[1][field]))

# print curl command to upload files.
curl_cmd.append('-F file=@<FILE>')
print(' '.join(curl_cmd))
```

## 5. 了解更多

- [MinIO Golang Client SDK快速入门](https://min.io/docs/newtera/linux/developers/go/newtera-go.html)
- [MinIO Java Client SDK快速入门](https://min.io/docs/newtera/linux/developers/java/newtera-java.html)
- [MinIO JavaScript Client SDK快速入门](https://min.io/docs/newtera/linux/developers/javascript/newtera-javascript.html)
