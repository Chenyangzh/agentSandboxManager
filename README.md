
### sandbox: 沙箱实例- 基本信息、执行cmd、（服务请求）


### manager: 沙箱管理器- 环境检查、启动、删除

## 注： 使用localDocker环境时，如果manager执行在容器内，需要启动容器挂载 /var/run/docker.sock:/var/run/docker.sock
## 注： 使用kubernets环境时，需要设置:
    1. 新建账户sandbox-controller，配置在ref/sandbox-controller-rbac.yaml
    2. manager的POD配置spec: serviceAccountName: sandbox-controller
    3.  export KUBERNETES_SERVICE_HOST=10.30.0.1
        export KUBERNETES_SERVICE_PORT=443