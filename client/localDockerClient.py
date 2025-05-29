
import time
import docker

from docker.models.containers import Container
from typing import List, Optional, Union, Generator

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

    def create(self, 
               image: str, 
               name: str, 
               command: str = "sleep infinity", 
               host_port: int = None,
               container_port: int = None,
               host_dir: str = None,
               container_dir: str = None,
               timeout: int = 180) -> Container:
        """
        Create container within default 180s.
        """
        # 1. check exist
        try:
            self.client.containers.get(name)
            raise RuntimeError(f"Container '{name}' already exists.")
        except docker.errors.NotFound:
            pass  # safe to create
        
        if not command:
            command = "sleep infinity"
        container = None
        try:
            # 2. create and start
            port_bindings = {f"{container_port}/tcp": host_port} if host_port and container_port else None
            volume_bindings = {host_dir: {'bind': container_dir, 'mode': 'rw'}} if host_dir and container_dir else None
            working_dir = container_dir if container_dir else None
            container = self.client.containers.create(
                image=image,
                name=name,
                detach=True,
                stdin_open=True,
                tty=True,
                command=command,
                ports=port_bindings,
                volumes=volume_bindings,
                working_dir=working_dir,
            )
            container.start()

            # 3. waiting for running
            for _ in range(timeout):
                container.reload()
                if container.status == 'running':
                    print(f"Container '{name}' is running.")
                    return self.client, container
                time.sleep(1)

            raise RuntimeError(f"Container '{name}' did not reach 'running' state within {timeout} seconds.")

        except Exception as e:
            # 4. any error clean up
            if container is not None:
                try:
                    container.remove(force=True)
                    print(f"Container '{name}' removed due to error.")
                except Exception as cleanup_err:
                    print(f"Warning: Failed to clean up container '{name}': {cleanup_err}")
            raise RuntimeError(f"Failed to create container '{name}': {e}")

    def delete(self, name: str) -> None:
        """
        Delete a running container.
        """
        try:
            container = self.client.containers.get(name)
            container.remove(force=True)
        except docker.errors.NotFound:
            raise ValueError(f"Container '{name}' not found and cannot be deleted.")
        except docker.errors.APIError as e:
            raise RuntimeError(f"Failed to delete container '{name}': {str(e)}")

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

    @staticmethod
    def exec_command_stream(client: docker.DockerClient,
                            container: Container,
                            command: Union[str, List[str]],
                            workdir: Optional[str] = None) -> Generator:
        """
        Execute a command in the specified running container in stream mode.
        """
        if isinstance(command, str):
            command = ["/bin/bash", "-c", command]

        # 创建 exec 实例
        exec_id = client.api.exec_create(
            container.id,
            cmd=command,
            workdir=workdir,
            stdout=True,
            stderr=True,
            tty=True,  # 必须为 True 否则部分输出不会立即刷新（比如进度条）
        )["Id"]

        # 以流式方式启动 exec
        sock = client.api.exec_start(exec_id, stream=True, demux=True)

        # 实时读取输出
        for stdout_chunk, stderr_chunk in sock:
            if stdout_chunk:
                yield {"stdout": stdout_chunk.decode()}
            if stderr_chunk:
                yield {"stderr": stderr_chunk.decode()}

        # 获取最终退出码
        resp = client.api.exec_inspect(exec_id)
        exit_code = resp["ExitCode"]
        yield {"exit_code": exit_code}