
from abc import ABC, abstractmethod
from typing import Any

from client import LocalDockerClient, get_client


class Sandbox(ABC):
    def __init__(self, obj: Any, name: str):
        self.obj = obj
        self.name = name

    @abstractmethod
    def exec_command(self, command: str) -> str:
        pass

class LocalContainerSandbox(Sandbox):
    def __init__(self, obj: Any, name: str):
        super().__init__(obj, name)
    
    def exec_command(self, command):
        return LocalDockerClient.exec_command(
            self.obj, 
            command
        )

sandbox_mapping = {
    "local_container": LocalContainerSandbox,
    "kubernetes_pod": None,
}

class sandboxManager(object):
    def __init__(self, ):
        self.client, self.env_type = get_client()

    def create_sandbox(self, image: str, name: str, command: str = None) -> Sandbox:
        if not name.startswith("sandbox_"):
            name = "sandbox_" + name
        if command:
            obj = self.client.create(image, name, command)
        else:
            obj = self.client.create(image, name)
        return sandbox_mapping[self.env_type](obj=obj, name=name)

    def destroy_sandbox(self, sandbox: Sandbox):
        name = sandbox.name
        if not name.startswith("sandbox_"):
            name = "sandbox_" + name
        self.client.delete(sandbox.name)


if __name__ == "__main__":
    manager = sandboxManager()
    # 创建沙箱
    sandbox = manager.create_sandbox(image="python:3.12", name="test-sandbox", command="sleep infinity")
    # 执行命令
    output = sandbox.exec_command("echo hello world")
    print(output)
    # 销毁沙箱
    manager.destroy_sandbox(sandbox)
