import docker

from docker.models.containers import Container
from typing import List, Optional, Union

from client.sandboxClient import SandboxClient


class LocalDockerClient(SandboxClient):
    def __init__(self, client: Optional[docker.DockerClient] = None):
        try:
            self.client = client or docker.from_env()
            self.client.ping()
        except docker.errors.DockerException as e:
            raise RuntimeError(
                f"Unable to connect to Docker daemon. Please ensure Docker is running. Error: {e}"
            )

    def create(self, image_name: str, container_name: str, command: str = "sleep infinity") -> Container:
        try:
            existing = self.client.containers.get(container_name)
            raise RuntimeError(f"Container '{container_name}' already exists.")
        except docker.errors.NotFound:
            pass  # Safe to create
        
        container = self.client.containers.create(
            image=image_name,
            name=container_name,
            detach=True,
            stdin_open=True,
            tty=True,
            command=command
        )
        container.start()
        return container

    def delete(self, container_name: str) -> None:
        try:
            container = self.client.containers.get(container_name)
            container.remove(force=True)
        except docker.errors.NotFound:
            raise ValueError(f"Container '{container_name}' not found and cannot be deleted.")

    @staticmethod
    def exec_command(container: Container, command: Union[str, List[str]], workdir: Optional[str] = None) -> str:
        """
        Execute a command in the specified running container.

        Args:
            container: A Continer object.
            command: The command to execute. Can be a string or list of strings.
            workdir: Optional working directory inside the container.

        Returns:
            The stdout of the executed command.
        """
        if isinstance(command, str):
            command = ["/bin/bash", "-c", command]

        exec_result = container.exec_run(
            cmd=command,
            workdir=workdir,
            stdout=True,
            stderr=True,
            demux=True,
        )

        stdout, stderr = exec_result.output
        result = ""
        if stdout:
            result += stdout.decode()
        if stderr:
            result += stderr.decode()

        return result.strip()
