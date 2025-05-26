
from abc import ABC, abstractmethod
from typing import Any, Optional

from client import LocalDockerClient, KubernetesClient, get_client


class Sandbox(ABC):
    def __init__(self, obj: Any, name: str):
        self.obj = obj
        self.name = name

    @abstractmethod
    def exec_command(self, command: str) -> str:
        pass

    @abstractmethod
    def exec_command(self, command: str, workdir: Optional[str] = None) -> str:
        pass

class LocalContainerSandbox(Sandbox):
    def __init__(self, obj: Any, name: str):
        super().__init__(obj, name)
    
    def exec_command(self, command):
        return LocalDockerClient.exec_command(
            self.obj, 
            command
        )
    
class KubernetesSandbox(Sandbox):
    def __init__(self, obj: Any, name: str):
        super().__init__(obj, name)
    
    def exec_command(self, command):
        return KubernetesClient.exec_command(
            self.obj, 
            command
        )

sandbox_mapping = {
    "local_container": LocalContainerSandbox,
    "kubernetes": KubernetesSandbox,
}

class sandboxManager(object):
    def __init__(self, ):
        self.client, self.env_type = get_client()

    def create_sandbox(self, image: str, name: str, command: str = None) -> Sandbox:
        if not name.startswith("sandbox-"):
            name = "sandbox-" + name
        if command:
            obj = self.client.create(image, name, command)
        else:
            obj = self.client.create(image, name)
        sandbox_class = sandbox_mapping.get(self.env_type)
        if not sandbox_class:
            raise ValueError(f"Unsupported env_type: {self.env_type}")
        return sandbox_class(obj=obj, name=name)

    def destroy_sandbox(self, sandbox: Sandbox):
        name = sandbox.name
        if not name.startswith("sandbox-"):
            name = "sandbox-" + name
        self.client.delete(name)


if __name__ == "__main__":
    manager = sandboxManager()
    # 创建沙箱
    sandbox = manager.create_sandbox(image="harbor.wenge.com/algorithm/python:3.12", name="test-sandbox", command="sleep infinity")
    
    # 执行命令
    output = sandbox.exec_command("echo hello world")
    print(output)

    # 销毁沙箱
    manager.destroy_sandbox(sandbox)
