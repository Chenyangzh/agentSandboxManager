import os
import time
import shlex

from kubernetes import client, config
from kubernetes.stream import stream
from kubernetes.client import CoreV1Api
from kubernetes.client.rest import ApiException

from typing import Union, List, Generator, Tuple, Optional
from client.sandboxClient import SandboxClient


class KubernetesClient(SandboxClient):
    def __init__(self, core_api: Optional[client.ApiClient] = None, namespace: str = "default"):
        """
        Init a kubernetes client.
        """
        self.namespace = namespace
        try:
            if core_api is not None:
                self.core_api = core_api
            else:
                # 加载配置
                if os.getenv("KUBERNETES_SERVICE_HOST"):
                    config.load_incluster_config()
                else:
                    config.load_kube_config()

                # 初始化 API 客户端
                self.core_api = CoreV1Api()
        except Exception as e:
            raise RuntimeError(f"KubernetesClient Failed to initialize client: {e} or donot have KUBERNETES_SERVICE_HOST")
    
    def _get_pod_spec(self,
                      image,
                      name,
                      command,
                      container_port: int = None,
                      volume_type: str = None,
                      container_dir: str = None,
                      volume_name: str = None,
                      host_dir: str = None,) -> client.V1Pod:
        """
            get pod specific config
        """
        # command
        if not command:
            command = "sleep infinity"
        command_list = shlex.split(command)

        # ports
        container_ports = []
        if container_port:
            container_ports.append(client.V1ContainerPort(container_port=container_port))

        # volume mounts
        volume_mounts = []
        volumes = []
        if container_dir and volume_type:
            volume_mounts.append(client.V1VolumeMount(
                mount_path=container_dir,
                name="mount-volume"
            ))

            if volume_type == "hostPath":
                if not host_dir:
                    raise ValueError("host_dir must be provided for hostPath volume.")
                volumes.append(client.V1Volume(
                    name="mount-volume",
                    host_path=client.V1HostPathVolumeSource(path=host_dir)
                ))

            elif volume_type == "emptyDir":
                volumes.append(client.V1Volume(
                    name="mount-volume",
                    empty_dir=client.V1EmptyDirVolumeSource()
                ))

            elif volume_type == "pvc":
                if not volume_name:
                    raise ValueError("volume_name (PVC name) must be provided for pvc volume.")
                volumes.append(client.V1Volume(
                    name="mount-volume",
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(claim_name=volume_name)
                ))

            else:
                raise ValueError(f"Unsupported volume_type: {volume_type}")
        
        working_dir = container_dir if container_dir else None

        # container and pod
        container = client.V1Container(
            name=name,
            image=image,
            command=command_list,
            ports=container_ports,
            volume_mounts=volume_mounts,
            working_dir=working_dir,
        )
        pod_spec = client.V1Pod(
            metadata=client.V1ObjectMeta(name=name),
            spec=client.V1PodSpec(
                containers=[container],
                volumes=volumes,
                restart_policy="Never"
            )
        )

        return pod_spec

    def create(self,
               image: str, 
               name: str, 
               command: str = "sleep infinity", 
               container_port: int = None, 
               host_dir: str = None, 
               container_dir: str = None, 
               timeout: int = 180, ) -> Tuple:
        """
        Create a kubernetes pod within default 180s.
        """
        try:
            pod_spec = self._get_pod_spec(
                image = image,
                name = name,
                command = command,
                container_port = container_port,
                volume_type = "hostPath" if host_dir else None,
                host_dir = host_dir,
                container_dir = container_dir,
            )
            self.core_api.create_namespaced_pod(namespace=self.namespace, body=pod_spec)
            print(f"Pod '{name}' created. Waiting for Ready...")

            for _ in range(timeout):
                pod = self.core_api.read_namespaced_pod(name=name, namespace=self.namespace)
                if pod.status.phase == "Running":
                    for cond in (pod.status.conditions or []):
                        if cond.type == "Ready" and cond.status == "True":
                            print(f"Pod '{name}' is Ready.")
                            return self.core_api, pod
                time.sleep(1)

            raise TimeoutError(f"Pod '{name}' not Ready after {timeout} seconds.")

        except (TimeoutError, ApiException) as e:
            print(f"Error while creating pod '{name}': {e}")
            self.delete(name=name)
            raise RuntimeError(f"Failed to create and initialize pod '{name}': {e}")

    def delete(self, name: str) -> None:
        """
        Delete a pod by name.
        """
        try:
            self.core_api.delete_namespaced_pod(
                name=name,
                namespace=self.namespace,
                body=client.V1DeleteOptions(grace_period_seconds=0)
            )
            print(f"KubernetesClient Pod '{name}' deleted.")
        except ApiException as e:
            print(f"Error Deleting pod failed: {e}")

    def get_status(self, name: str):
        """
        """
        try:
            pod = self.core_api.read_namespaced_pod(name=name, namespace=self.namespace)
            return pod.status.phase
        except ApiException as e:
            print(f"Error Get pod status failed: {e}")
            return "Unknown"
    
    @staticmethod
    def exec_command(api: client.ApiClient, pod: client.V1Pod, command: Union[str, List[str]], workdir: Optional[str] = None) -> str:
        """
        Exec command in a pod
        """
        try:
            if isinstance(command, str):
                command = ["/bin/bash", "-c", command]

            if workdir:
                # 安全拼接命令
                inner_cmd = " ".join(shlex.quote(arg) for arg in command)
                command = ["/bin/bash", "-c", f"cd {shlex.quote(workdir)} && {inner_cmd}"]

            resp = stream(
                api.connect_get_namespaced_pod_exec,
                name=pod.metadata.name,
                namespace=pod.metadata.namespace,
                command=command,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False,
            )

            return resp.strip()

        except ApiException as e:
            raise RuntimeError(f"Failed to exec command in pod '{pod.metadata.name}': {e}")
        

    def exec_command_stream(api: client.ApiClient, 
                            pod: client.V1Pod, 
                            command: Union[str, List[str]], 
                            workdir: Optional[str] = None) -> Generator:
        """
        实时执行命令并流式返回输出（打印到控制台）
        """
        exit_code = -1

        if isinstance(command, str):
            command = ["/bin/bash", "-c", command]

        if workdir:
            inner_cmd = " ".join(shlex.quote(arg) for arg in command)
            command = ["/bin/bash", "-c", f"cd {shlex.quote(workdir)} && {inner_cmd}"]

        try:
            # 打开 WebSocket 连接
            resp = stream(
                api.connect_get_namespaced_pod_exec,
                name=pod.metadata.name,
                namespace=pod.metadata.namespace,
                command=command,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False,
                _preload_content=False
            )

            while resp.is_open():
                resp.update(timeout=1)
                if resp.peek_stdout():
                    out = resp.read_stdout()
                    yield {"stdout", out}
                if resp.peek_stderr():
                    err = resp.read_stderr()
                    yield {"stderr", err}
            resp.close()
            exit_code = 0

        except Exception as e:
            yield {"error": f"Exception during exec in pod '{pod.metadata.name}': {str(e)}"}
            # 设置失败退出码
            exit_code = -1

        finally:
            yield {"exit_code": exit_code}