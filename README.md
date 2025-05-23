
### sandbox: 沙箱实例- 基本信息、执行cmd、（服务请求）


### manager: 沙箱管理器- 环境检查、启动、删除

## 注： 使用localDocker环境时，如果sandbox执行在容器内，需要启动容器挂载 /var/run/docker.sock:/var/run/docker.sock
## 注： 使用kubernets环境时，需要设置 spec: serviceAccountName: default