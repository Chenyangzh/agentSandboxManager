
import time
import docker

from docker.models.containers import Container
from typing import List, Optional, Union

from client.sandboxClient import SandboxClient


class LocalDockerClient(SandboxClient):
    def __init__(self, client: Optional[docker.DockerClient] = None):
        """
        Init a docker client.
        """
        try:
            self.client = client or docker.from_env()   # input DockerClient or get from env
            self.client.ping()
        except docker.errors.DockerException as e:
            raise RuntimeError(
                f"Unable to connect to Docker daemon. Please ensure Docker is running. Error: {e}"
            )

    def create(self, image_name: str, container_name: str, command: str = "sleep infinity", timeout: int = 180) -> Container:
        """
        Create container within default 180s.
        """
        # 1. check exist
        try:
            self.client.containers.get(container_name)
            raise RuntimeError(f"Container '{container_name}' already exists.")
        except docker.errors.NotFound:
            pass  # safe to create
 
        container = None
        try:
            # 2. create and start
            container = self.client.containers.create(
                image=image_name,
                name=container_name,
                detach=True,
                stdin_open=True,
                tty=True,
                command=command
            )
            container.start()

            # 3. waiting for running
            for _ in range(timeout):
                container.reload()
                if container.status == 'running':
                    print(f"Container '{container_name}' is running.")
                    return container
                time.sleep(1)

            raise RuntimeError(f"Container '{container_name}' did not reach 'running' state within {timeout} seconds.")

        except Exception as e:
            # 4. any error clean up
            if container is not None:
                try:
                    container.remove(force=True)
                    print(f"Container '{container_name}' removed due to error.")
                except Exception as cleanup_err:
                    print(f"Warning: Failed to clean up container '{container_name}': {cleanup_err}")
            raise RuntimeError(f"Failed to create container '{container_name}': {e}")



    def delete(self, container_name: str) -> None:
        """
        Delete a running container.
        """
        try:
            container = self.client.containers.get(container_name)
            container.remove(force=True)
        except docker.errors.NotFound:
            raise ValueError(f"Container '{container_name}' not found and cannot be deleted.")
        except docker.errors.APIError as e:
            raise RuntimeError(f"Failed to delete container '{container_name}': {str(e)}")

    @staticmethod
    def exec_command(container: Container, command: Union[str, List[str]], workdir: Optional[str] = None) -> str:
        """
        Execute a command in the specified running container.
        """
        if isinstance(command, str):
            command = ["/bin/bash", "-c", command]

        try:
            exec_result = container.exec_run(
                cmd=command,
                workdir=workdir,
                stdout=True,
                stderr=True,
                demux=True,
            )
        except docker.errors.APIError as e:
            raise RuntimeError(f"Failed to execute command in container '{container.name}': {e}") from e

        stdout, stderr = exec_result.output or (b'', b'')
        result = (stdout or b'').decode() + (stderr or b'').decode()

        if exec_result.exit_code != 0:
            raise RuntimeError(
                f"Command exited with code {exec_result.exit_code}.\n"
                f"Command: {' '.join(command)}\n"
                f"Output:\n{result.strip()}"
            )

        return result.strip()
