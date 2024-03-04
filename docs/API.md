# Python Client API Reference [![Slack](https://slack.min.io/slack?type=svg)](https://slack.min.io)

## 1. Constructor

### Newtera(endpoint, access_key=None, secret_key=None, session_token=None, secure=True, region=None, http_client=None, credentials=None)
Initializes a new client object.

__Parameters__

| Param           | Type                              | Description                                                                      |
|:----------------|:----------------------------------|:---------------------------------------------------------------------------------|
| `endpoint`      | _str_                             | Hostname of a S3 service.                                                        |
| `access_key`    | _str_                             | (Optional) Access key (aka user ID) of your account in S3 service.               |
| `secret_key`    | _str_                             | (Optional) Secret Key (aka password) of your account in S3 service.              |
| `session_token` | _str_                             | (Optional) Session token of your account in S3 service.                          |
| `secure`        | _bool_                            | (Optional) Flag to indicate to use secure (TLS) connection to S3 service or not. |
| `region`        | _str_                             | (Optional) Region name of buckets in S3 service.                                 |
| `http_client`   | _urllib3.poolmanager.PoolManager_ | (Optional) Customized HTTP client.                                               |
| `credentials`   | _minio.credentials.Provider_      | (Optional) Credentials provider of your account in S3 service.                   |
| `cert_check`    | _bool_                            | (Optional) Flag to check on server certificate for HTTPS connection.             |


**NOTE on concurrent usage:** `Newtera` object is thread safe when using the Python `threading` library. Specifically, it is **NOT** safe to share it between multiple processes, for example when using `multiprocessing.Pool`. The solution is simply to create a new `Newtera` object in each process, and not share it between processes.

__Example__

```py
from newtera import Newtera

# Create client with anonymous access.
client = Newtera("play.min.io")

# Create client with access and secret key.
client = Newtera("s3.amazonaws.com", "ACCESS-KEY", "SECRET-KEY")

# Create client with access key and secret key with specific region.
client = Newtera(
    "play.newtera.io:9000",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    region="my-region",
)

# Create client with custom HTTP client using proxy server.
import urllib3
client = Newtera(
    "SERVER:PORT",
    access_key="ACCESS_KEY",
    secret_key="SECRET_KEY",
    secure=True,
    http_client=urllib3.ProxyManager(
        "https://PROXYSERVER:PROXYPORT/",
        timeout=urllib3.Timeout.DEFAULT_TIMEOUT,
        cert_reqs="CERT_REQUIRED",
        retries=urllib3.Retry(
            total=5,
            backoff_factor=0.2,
            status_forcelist=[500, 502, 503, 504],
        ),
    ),
)
```

## 2. Bucket operations

<a name="list_buckets"></a>

### list_buckets()

List information of all accessible buckets.

__Parameters__

| Return           |
|:-----------------|
| List of _Bucket_ |

__Example__

```py
buckets = client.list_buckets()
for bucket in buckets:
    print(bucket.name, bucket.creation_date)
```

<a name="bucket_exists"></a>

### bucket_exists(bucket_name)

Check if a bucket exists.

__Parameters__

| Param         | Type  | Description         |
|:--------------|:------|:--------------------|
| `bucket_name` | _str_ | Name of the bucket. |

__Example__

```py
if client.bucket_exists("my-bucket"):
    print("my-bucket exists")
else:
    print("my-bucket does not exist")
```

<a name="remove_bucket"></a>

### remove_bucket(bucket_name)

Remove an empty bucket.

__Parameters__

| Param         | Type  | Description         |
|:--------------|:------|:--------------------|
| `bucket_name` | _str_ | Name of the bucket. |

__Example__

```py
client.remove_bucket("my-bucket")
```

<a name="list_objects"></a>

### list_objects(bucket_name, prefix=None, recursive=False, start_after=None, include_user_meta=False, include_version=False, use_api_v1=False, use_url_encoding_type=True)

Lists object information of a bucket.

__Parameters__

| Param                   | Type   | Description                                                  |
|:------------------------|:-------|:-------------------------------------------------------------|
| `bucket_name`           | _str_  | Name of the bucket.                                          |
| `prefix`                | _str_  | Object name starts with prefix.                              |
| `recursive`             | _bool_ | List recursively than directory structure emulation.         |
| `start_after`           | _str_  | List objects after this key name.                            |
| `include_user_meta`     | _bool_ | MinIO specific flag to control to include user metadata.     |
| `include_version`       | _bool_ | Flag to control whether include object versions.             |
| `use_api_v1`            | _bool_ | Flag to control to use ListObjectV1 S3 API or not.           |
| `use_url_encoding_type` | _bool_ | Flag to control whether URL encoding type to be used or not. |

__Return Value__

| Return                  |
|:------------------------|
| An iterator of _Object_ |

__Example__

```py
# List objects information.
objects = client.list_objects("my-bucket")
for obj in objects:
    print(obj)

# List objects information whose names starts with "my/prefix/".
objects = client.list_objects("my-bucket", prefix="my/prefix/")
for obj in objects:
    print(obj)

# List objects information recursively.
objects = client.list_objects("my-bucket", recursive=True)
for obj in objects:
    print(obj)

# List objects information recursively whose names starts with
# "my/prefix/".
objects = client.list_objects(
    "my-bucket", prefix="my/prefix/", recursive=True,
)
for obj in objects:
    print(obj)

# List objects information recursively after object name
# "my/prefix/world/1".
objects = client.list_objects(
    "my-bucket", recursive=True, start_after="my/prefix/world/1",
)
for obj in objects:
    print(obj)
```

## 3. Object operations

<a name="get_object"></a>

### get_object(bucket_name, object_name, offset=0, length=0, request_headers=None, ssec=None, version_id=None, extra_query_params=None)

Gets data from offset to length of an object. Returned response should be closed after use to release network resources. To reuse the connection, it's required to call `response.release_conn()` explicitly.

__Parameters__

| Param                | Type             | Description                                          |
|:---------------------|:-----------------|:-----------------------------------------------------|
| `bucket_name`        | _str_            | Name of the bucket.                                  |
| `object_name`        | _str_            | Object name in the bucket.                           |
| `offset`             | _int_            | Start byte position of object data.                  |
| `length`             | _int_            | Number of bytes of object data from offset.          |
| `request_headers`    | _dict_           | Any additional headers to be added with GET request. |
| `ssec`               | _SseCustomerKey_ | Server-side encryption customer key.                 |
| `version_id`         | _str_            | Version-ID of the object.                            |
| `extra_query_params` | _dict_           | Extra query parameters for advanced usage.           |

__Return Value__

| Return                                  |
|:----------------------------------------|
| _urllib3.response.HTTPResponse_ object. |

__Example__

```py
# Get data of an object.
try:
    response = client.get_object("my-bucket", "my-object")
    # Read data from response.
finally:
    response.close()
    response.release_conn()

# Get data of an object of version-ID.
try:
    response = client.get_object(
        "my-bucket", "my-object",
        version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
    )
    # Read data from response.
finally:
    response.close()
    response.release_conn()

# Get data of an object from offset and length.
try:
    response = client.get_object(
        "my-bucket", "my-object", offset=512, length=1024,
    )
    # Read data from response.
finally:
    response.close()
    response.release_conn()

# Get data of an SSE-C encrypted object.
try:
    response = client.get_object(
        "my-bucket", "my-object",
        ssec=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
    )
    # Read data from response.
finally:
    response.close()
    response.release_conn()
```

<a name="fget_object"></a>

### fget_object(bucket_name, object_name, file_path, request_headers=None, ssec=None, version_id=None, extra_query_params=None, tmp_file_path=None)
Downloads data of an object to file.

__Parameters__

| Param                | Type             | Description                                          |
|:---------------------|:-----------------|:-----------------------------------------------------|
| `bucket_name`        | _str_            | Name of the bucket.                                  |
| `object_name`        | _str_            | Object name in the bucket.                           |
| `file_path`          | _str_            | Name of file to download.                            |
| `request_headers`    | _dict_           | Any additional headers to be added with GET request. |
| `ssec`               | _SseCustomerKey_ | Server-side encryption customer key.                 |
| `version_id`         | _str_            | Version-ID of the object.                            |
| `extra_query_params` | _dict_           | Extra query parameters for advanced usage.           |
| `tmp_file_path`      | _str_            | Path to a temporary file.                            |

__Return Value__

| Return                         |
|:-------------------------------|
| Object information as _Object_ |

__Example__

```py
# Download data of an object.
client.fget_object("my-bucket", "my-object", "my-filename")

# Download data of an object of version-ID.
client.fget_object(
    "my-bucket", "my-object", "my-filename",
    version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
)

# Download data of an SSE-C encrypted object.
client.fget_object(
    "my-bucket", "my-object", "my-filename",
    ssec=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
)
```

<a name="put_object"></a>

### put_object(bucket_name, object_name, data, length, content_type="application/octet-stream", metadata=None, sse=None, progress=None, part_size=0, num_parallel_uploads=3, tags=None, retention=None, legal_hold=False)

Uploads data from a stream to an object in a bucket.

__Parameters__

| Param          | Type        | Description                                                         |
|:---------------|:------------|:--------------------------------------------------------------------|
| `bucket_name`  | _str_       | Name of the bucket.                                                 |
| `object_name`  | _str_       | Object name in the bucket.                                          |
| `data`         | _object_    | An object having callable read() returning bytes object.            |
| `length`       | _int_       | Data size; -1 for unknown size and set valid part_size.             |
| `content_type` | _str_       | Content type of the object.                                         |
| `metadata`     | _dict_      | Any additional metadata to be uploaded along with your PUT request. |
| `sse`          | _Sse_       | Server-side encryption.                                             |
| `progress`     | _threading_ | A progress object.                                                  |
| `part_size`    | _int_       | Multipart part size.                                                |

__Return Value__

| Return                      |
|:----------------------------|
| _ObjectWriteResult_ object. |

__Example__
```py
# Upload data.
result = client.put_object(
    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload unknown sized data.
data = urlopen(
    "https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-5.4.81.tar.xz",
)
result = client.put_object(
    "my-bucket", "my-object", data, length=-1, part_size=10*1024*1024,
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with content-type.
result = client.put_object(
    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
    content_type="application/csv",
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with metadata.
result = client.put_object(
    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
    metadata={"My-Project": "one"},
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with customer key type of server-side encryption.
result = client.put_object(
    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
    sse=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with KMS type of server-side encryption.
result = client.put_object(
    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
    sse=SseKMS("KMS-KEY-ID", {"Key1": "Value1", "Key2": "Value2"}),
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with S3 type of server-side encryption.
result = client.put_object(
    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
    sse=SseS3(),
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with tags, retention and legal-hold.
date = datetime.utcnow().replace(
    hour=0, minute=0, second=0, microsecond=0,
) + timedelta(days=30)
tags = Tags(for_object=True)
tags["User"] = "jsmith"
result = client.put_object(
    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with progress bar.
result = client.put_object(
    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
    progress=Progress(),
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)
```

<a name="fput_object"></a>

### fput_object(bucket_name, object_name, file_path, content_type="application/octet-stream", metadata=None, sse=None, progress=None, part_size=0, num_parallel_uploads=3, tags=None, retention=None, legal_hold=False)

Uploads data from a file to an object in a bucket.

| Param          | Type        | Description                                                         |
|:---------------|:------------|:--------------------------------------------------------------------|
| `bucket_name`  | _str_       | Name of the bucket.                                                 |
| `object_name`  | _str_       | Object name in the bucket.                                          |
| `file_path`    | _str_       | Name of file to upload.                                             |
| `content_type` | _str_       | Content type of the object.                                         |
| `metadata`     | _dict_      | Any additional metadata to be uploaded along with your PUT request. |
| `sse`          | _Sse_       | Server-side encryption.                                             |
| `progress`     | _threading_ | A progress object.                                                  |
| `part_size`    | _int_       | Multipart part size.                                                |

__Return Value__

| Return                      |
|:----------------------------|
| _ObjectWriteResult_ object. |

__Example__

```py
# Upload data.
result = client.fput_object(
    "my-bucket", "my-object", "my-filename",
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with content-type.
result = client.fput_object(
    "my-bucket", "my-object", "my-filename",
    content_type="application/csv",
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with metadata.
result = client.fput_object(
    "my-bucket", "my-object", "my-filename",
    metadata={"My-Project": "one"},
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with customer key type of server-side encryption.
result = client.fput_object(
    "my-bucket", "my-object", "my-filename",
    sse=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with KMS type of server-side encryption.
result = client.fput_object(
    "my-bucket", "my-object", "my-filename",
    sse=SseKMS("KMS-KEY-ID", {"Key1": "Value1", "Key2": "Value2"}),
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with S3 type of server-side encryption.
result = client.fput_object(
    "my-bucket", "my-object", "my-filename",
    sse=SseS3(),
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with tags, retention and legal-hold.
date = datetime.utcnow().replace(
    hour=0, minute=0, second=0, microsecond=0,
) + timedelta(days=30)
tags = Tags(for_object=True)
tags["User"] = "jsmith"
result = client.fput_object(
    "my-bucket", "my-object", "my-filename",
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)

# Upload data with progress bar.
result = client.fput_object(
    "my-bucket", "my-object", "my-filename",
    progress=Progress(),
)
print(
    "created {0} object; etag: {1}, version-id: {2}".format(
        result.object_name, result.etag, result.version_id,
    ),
)
```

<a name="stat_object"></a>

### stat_object(bucket_name, object_name, ssec=None, version_id=None, extra_query_params=None)

Get object information and metadata of an object.

__Parameters__

| Param                | Type             | Description                                |
|:---------------------|:-----------------|:-------------------------------------------|
| `bucket_name`        | _str_            | Name of the bucket.                        |
| `object_name`        | _str_            | Object name in the bucket.                 |
| `ssec`               | _SseCustomerKey_ | Server-side encryption customer key.       |
| `version_id`         | _str_            | Version ID of the object.                  |
| `extra_headers`      | _dict_           | Extra HTTP headers for advanced usage.     |
| `extra_query_params` | _dict_           | Extra query parameters for advanced usage. |

__Return Value__

| Return                         |
|:-------------------------------|
| Object information as _Object_ |

__Example__

```py
# Get object information.
result = client.stat_object("my-bucket", "my-object")
print(
    "last-modified: {0}, size: {1}".format(
        result.last_modified, result.size,
    ),
)

# Get object information of version-ID.
result = client.stat_object(
    "my-bucket", "my-object",
    version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
)
print(
    "last-modified: {0}, size: {1}".format(
        result.last_modified, result.size,
    ),
)

# Get SSE-C encrypted object information.
result = client.stat_object(
    "my-bucket", "my-object",
    ssec=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
)
print(
    "last-modified: {0}, size: {1}".format(
        result.last_modified, result.size,
    ),
)
```

<a name="remove_object"></a>

### remove_object(bucket_name, object_name, version_id=None)

Remove an object.

__Parameters__

| Param         | Type  | Description                |
|:--------------|:------|:---------------------------|
| `bucket_name` | _str_ | Name of the bucket.        |
| `object_name` | _str_ | Object name in the bucket. |
| `version_id`  | _str_ | Version ID of the object.  |

__Example__

```py
# Remove object.
client.remove_object("my-bucket", "my-object")

# Remove version of an object.
client.remove_object(
    "my-bucket", "my-object",
    version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
)
```

<a name="remove_objects"></a>

### remove_objects(bucket_name, delete_object_list, bypass_governance_mode=False)

Remove multiple objects.

__Parameters__

| Param                    | Type       | Description                                                         |
|:-------------------------|:-----------|:--------------------------------------------------------------------|
| `bucket_name`            | _str_      | Name of the bucket.                                                 |
| `delete_object_list`     | _iterable_ | An iterable containing :class:`DeleteObject <DeleteObject>` object. |
| `bypass_governance_mode` | _bool_     | Bypass Governance retention mode.                                   |

__Return Value__

| Return                                                           |
|:-----------------------------------------------------------------|
| An iterator containing :class:`DeleteError <DeleteError>` object |

__Example__

```py
# Remove list of objects.
errors = client.remove_objects(
    "my-bucket",
    [
        DeleteObject("my-object1"),
        DeleteObject("my-object2"),
        DeleteObject("my-object3", "13f88b18-8dcd-4c83-88f2-8631fdb6250c"),
    ],
)
for error in errors:
    print("error occurred when deleting object", error)

# Remove a prefix recursively.
delete_object_list = map(
    lambda x: DeleteObject(x.object_name),
    client.list_objects("my-bucket", "my/prefix/", recursive=True),
)
errors = client.remove_objects("my-bucket", delete_object_list)
for error in errors:
    print("error occurred when deleting object", error)
```


## 5. Explore Further

- [MinIO Golang Client SDK Quickstart Guide](https://min.io/docs/newtera/linux/developers/go/newtera-go.html)
- [MinIO Java Client SDK Quickstart Guide](https://min.io/docs/newtera/linux/developers/java/newtera-java.html)
- [MinIO JavaScript Client SDK Quickstart Guide](https://min.io/docs/newtera/linux/developers/javascript/newtera-javascript.html)
