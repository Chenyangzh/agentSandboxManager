import os
import time
import shlex

from kubernetes import client, config
from kubernetes.stream import stream
from kubernetes.client import CoreV1Api
from kubernetes.client.rest import ApiException

from typing import Union, List, Dict, Tuple, Optional
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
    
    def create(self, image: str, name: str, command: str = "sleep infinity", timeout: int = 180) -> Dict:
        """
        Create a kubernetes pod within default 180s.
        """
        command_list = shlex.split(command)
        pod_spec = client.V1Pod(
            metadata=client.V1ObjectMeta(name=name),
            spec=client.V1PodSpec(
                containers=[client.V1Container(name=name, image=image, command=command_list)],
                restart_policy="Never"
            )
        )
        try:
            self.core_api.create_namespaced_pod(namespace=self.namespace, body=pod_spec)
            print(f"Pod '{name}' created. Waiting for Ready...")

            for _ in range(timeout):
                pod = self.core_api.read_namespaced_pod(name=name, namespace=self.namespace)
                if pod.status.phase == "Running":
                    for cond in (pod.status.conditions or []):
                        if cond.type == "Ready" and cond.status == "True":
                            print(f"Pod '{name}' is Ready.")
                            return pod, self.core_api
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
    def exec_command(spod: Tuple, command: Union[str, List[str]], workdir: Optional[str] = None) -> str:
        """
        Exec command in a pod
        """
        pod, api = spod
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