
from abc import ABC, abstractmethod
from typing import Optional

from client import LocalDockerClient, KubernetesClient, get_client


class Sandbox(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def exec_command(self, command: str) -> str:
        pass

    @abstractmethod
    def exec_command_stream(self, command: str, workdir: Optional[str] = None) -> str:
        pass


class LocalContainerSandbox(Sandbox):
    def __init__(self, cli, container, name: str):
        super().__init__(name)
        self.cli = cli
        self.container = container
    
    def exec_command(self, command):
        return LocalDockerClient.exec_command(
            self.container, 
            command
        )

    def exec_command_stream(self, command):
        return LocalDockerClient.exec_command_stream(
            self.cli,
            self.container, 
            command
        )

class KubernetesSandbox(Sandbox):
    def __init__(self, core_api, pod, name: str):
        super().__init__(name)
        self.cli = core_api
        self.pod = pod
    
    def exec_command(self, command):
        return KubernetesClient.exec_command(
            self.cli,
            self.pod, 
            command
        )
    
    def exec_command_stream(self, command):
        return LocalDockerClient.exec_command_stream(
            self.cli,
            self.pod, 
            command
        )

sandbox_mapping = {
    "local_container": LocalContainerSandbox,
    "kubernetes": KubernetesSandbox,
}


class sandboxManager(object):
    def __init__(self, ):
        self.client, self.env_type = get_client()

    def create_sandbox(self, 
                       image: str, 
                       name: str, 
                       command: str, 
                       sandbox_port: int = None, 
                       mount_path: str = None) -> Sandbox:
        if not name.startswith("sandbox-"):
            name = "sandbox-" + name

        sandbox_cls = sandbox_mapping.get(self.env_type)
        if sandbox_cls is None:
            raise RuntimeError(f"[Error] No sandbox implementation for type: {self.env_type}")
        
        if self.env_type == "local_container":
            # Docker: host_port -> sandbox_port, container_port = 8080
            cli, conta = self.client.create(image, name, command, 
                                     host_port = sandbox_port, 
                                     container_port = 8080, 
                                     host_dir = mount_path, 
                                     container_dir = "/workspace")
            sandbox = sandbox_cls(cli, conta, name)
        elif self.env_type == "kubernetes":
            # Kubernetes: container_port = sandbox_port
            core_api, pod = self.client.create(image, name, command, 
                                     container_port = sandbox_port, 
                                     host_dir = mount_path, 
                                     container_dir = "/workspace")
            sandbox = sandbox_cls(core_api, pod, name)
        else:
            raise RuntimeError(f"[Error] Unsupported sandbox environment type: {self.env_type}")

        return sandbox

    def destroy_sandbox(self, sandbox: Sandbox):
        name = sandbox.name
        if not name.startswith("sandbox-"):
            name = "sandbox-" + name
        self.client.delete(name)
