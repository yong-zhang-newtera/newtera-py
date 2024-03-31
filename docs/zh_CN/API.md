# Python Client API文档 [![Slack](https://slack.min.io/slack?type=svg)](https://slack.min.io)

## 初使化Newtera Client对象。

## Newtera

```py
from newtera import Newtera
from newtera.error import ResponseError

minioClient = Newtera('localhost:8080',
                  access_key='demo1',
                  secret_key='888')
```

