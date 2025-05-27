# Sandbox container
## 结构
1. sandbox沙箱实例： 基本信息、执行cmd、（服务请求）
2. manager沙箱管理器： 环境检查、启动、删除

## 使用
1. localDocker环境，如果manager执行在容器内，启动时容器挂载宿主机docker.sock
    ```bash
    docker run -d --name sandbox-manager \
            ... \
            -v /var/run/docker.sock:/var/run/docker.sock \
            ...
    ```

2. kubernets环境时，需要配置:

    a. 新建账户sandbox-controller，参考在ref/sandbox-controller-rbac.yaml

    b. manager的POD配置spec: serviceAccountName: sandbox-controller

    c. 执行manager的pod配置环境变量：
    ```bash
    export KUBERNETES_SERVICE_HOST=10.30.0.1
    export KUBERNETES_SERVICE_PORT=443
    ```