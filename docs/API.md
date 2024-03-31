## 1. Constructor

### Newtera(endpoint, access_key=None, secret_key=None)
Initializes a new client object.

__Parameters__

| Param           | Type                              | Description                                                                      |
|:----------------|:----------------------------------|:---------------------------------------------------------------------------------|
| `endpoint`      | _str_                             | Hostname of a S3 service.                                                        |
| `access_key`    | _str_                             | (Optional) Access key (aka user ID) of your account in S3 service.               |
| `secret_key`    | _str_                             | (Optional) Secret Key (aka password) of your account in S3 service.              |

**NOTE on concurrent usage:** `Newtera` object is thread safe when using the Python `threading` library. Specifically, it is **NOT** safe to share it between multiple processes, for example when using `multiprocessing.Pool`. The solution is simply to create a new `Newtera` object in each process, and not share it between processes.

__Example__

```py
from newtera import Newtera

# Create client with access and secret key.
client = Newtera("localhost:8080", "ACCESS-KEY", "SECRET-KEY")
```

## 2. Bucket operations

<a name="bucket_exists"></a>

### bucket_exists(bucket_name)

Check if a bucket exists.

__Parameters__

| Param         | Type  | Description         |
|:--------------|:------|:--------------------|
| `bucket_name` | _str_ | Name of the bucket. |

__Example__

```py
if client.bucket_exists("tdm"):
    print("tdm exists")
else:
    print("tdm does not exist")
```

<a name="list_objects"></a>

### list_objects(bucket_name, prefix)

Lists object information of a bucket.

__Parameters__

| Param                   | Type   | Description                                                  |
|:------------------------|:-------|:-------------------------------------------------------------|
| `bucket_name`           | _str_  | Name of the bucket.                                          |
| `prefix`                | _str_  | Object name starts with prefix.                              |

__Return Value__

| Return                  |
|:------------------------|
| An iterator of _ObjectModel_ |

__Example__

```py
# List objects information whose names starts with "my/prefix/".
objects = client.list_objects("tdm", prefix="my/prefix/")
for obj in objects:
    print(obj)
```

## 3. Object operations

<a name="get_object"></a>

### get_object(bucket_name, prefix, object_name)

Gets data an object. Returned response should be closed after use to release network resources. To reuse the connection, it's required to call `response.release_conn()` explicitly.

__Parameters__

| Param                | Type             | Description                                          |
|:---------------------|:-----------------|:-----------------------------------------------------|
| `bucket_name`        | _str_            | Name of the bucket.                                  |
| `prefix`             | _str_            | Prefix of the bucket.                                |
| `object_name`        | _str_            | Object name in the bucket.                           |

__Return Value__

| Return                                  |
|:----------------------------------------|
| _urllib3.response.HTTPResponse_ object. |

__Example__

```py
# Get data of an object.
try:
    response = client.get_object("tdm", "my/prefix/", "my-object")
    # Read data from response.
finally:
    response.close()
    response.release_conn()
```

<a name="fget_object"></a>

### fget_object(bucket_name, prefix, object_name, file_path)
Downloads data of an object to file.

__Parameters__

| Param                | Type             | Description                                          |
|:---------------------|:-----------------|:-----------------------------------------------------|
| `bucket_name`        | _str_            | Name of the bucket.                                  |
| `prefix`             | _str_            | Prefix of the bucket.                                |
| `object_name`        | _str_            | Object name in the bucket.                           |
| `file_path`          | _str_            | Name of file to download.                            |

__Return Value__

| Return                         |
|:-------------------------------|
| Object information as _Object_ |

__Example__

```py
# Download data of an object.
client.fget_object("tdm", "my/prefix/", "my-object", "my-filename")

```

<a name="put_object"></a>

### put_object(bucket_name, prefix, object_name, data, length, content_type="application/octet-stream")

Uploads data from a stream to an object in a bucket.

__Parameters__

| Param          | Type        | Description                                                         |
|:---------------|:------------|:--------------------------------------------------------------------|
| `bucket_name`  | _str_       | Name of the bucket.                                                 |
| `prefix`       | _str_       | Prefix of the bucket.                                               |
| `object_name`  | _str_       | Object name in the bucket.                                          |
| `data`         | _object_    | An object having callable read() returning bytes object.            |
| `length`       | _int_       | Data size; -1 for unknown size and set valid part_size.             |
| `content_type` | _str_       | Content type of the object.                                         |

__Return Value__

| Return                      |
|:----------------------------|
| _ObjectWriteResult_ object. |

__Example__
```py
# Upload data.
result = client.put_object(
    "tdm", "my/prefix/", "my-object", io.BytesIO(b"hello"), 5,
)
print(
    "created {0} object".format(
        result.object_name,
    ),
)
```

<a name="fput_object"></a>

### fput_object(bucket_name, prefix, object_name, file_path, content_type="application/octet-stream")

Uploads data from a file to an object in a bucket.

| Param          | Type        | Description                                                         |
|:---------------|:------------|:--------------------------------------------------------------------|
| `bucket_name`  | _str_       | Name of the bucket.                                                 |
| `prefix`       | _str_       | Prefix of the bucket.                                               |
| `object_name`  | _str_       | Object name in the bucket.                                          |
| `file_path`    | _str_       | Name of file to upload.                                             |
| `content_type` | _str_       | Content type of the object.                                         |

__Return Value__

| Return                      |
|:----------------------------|
| _ObjectWriteResult_ object. |

__Example__

```py
# Upload data.
result = client.fput_object(
    "tdm", "my/prefix/", "my-object", "my-filename",
)
print(
    "created {0} object".format(
        result.object_name,
    ),
)
```

<a name="stat_object"></a>

### stat_object(bucket_name, prefix, object_name)

Get object information and metadata of an object.

__Parameters__

| Param                | Type             | Description                                |
|:---------------------|:-----------------|:-------------------------------------------|
| `bucket_name`        | _str_            | Name of the bucket.                        |
| `prefix`             | _str_            | Prefix of the bucket.                      |
| `object_name`        | _str_            | Object name in the bucket.                 |

__Return Value__

| Return                         |
|:-------------------------------|
| Object information as _Object_ |

__Example__

```py
# Get object information.
result = client.stat_object("tdm", "my/prefix/", "my-object")
print(
    "last-modified: {0}, size: {1}".format(
        result.last_modified, result.size,
    ),
)
```

<a name="remove_object"></a>

### remove_object(bucket_name, prefix, object_name)

Remove an object.

__Parameters__

| Param         | Type  | Description                |
|:--------------|:------|:---------------------------|
| `bucket_name` | _str_ | Name of the bucket.        |
| `prefix`      | _str_ | Prefix of the bucket.      |
| `object_name` | _str_ | Object name in the bucket. |

__Example__

```py
# Remove object.
client.remove_object("tdm", "my/prefix/", "my-object")
```

