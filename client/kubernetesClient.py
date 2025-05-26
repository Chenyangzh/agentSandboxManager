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
        try:
            self.namespace = namespace
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
        pod_created = False
        try:
            command_list = shlex.split(command)
            pod_spec = client.V1Pod(
                metadata=client.V1ObjectMeta(name=name),
                spec=client.V1PodSpec(
                    containers=[client.V1Container(name=name, image=image, command=command_list)],
                    restart_policy="Never"
                )
            )
            self.core_api.create_namespaced_pod(namespace=self.namespace, body=pod_spec)
            pod_created = True
            print(f"KubernetesClient Pod '{name}' created. Waiting for Ready...")

            for _ in range(timeout):
                pod = self.core_api.read_namespaced_pod(name=name, namespace=self.namespace)
                if pod.status.phase == "Running":
                    conditions = pod.status.conditions or []
                    for cond in conditions:
                        if cond.type == "Ready" and cond.status == "True":
                            print(f"KubernetesClient Pod '{name}' is Ready.")
                            return (pod, self.core_api)
                time.sleep(1)
            raise TimeoutError(f"KubernetesClient Pod '{name}' not Ready after {timeout} seconds.")

        except TimeoutError as te:
            print(str(te))
            if pod_created:
                self.delete(name)
        except ApiException as e:
            print(f"Error Creating pod failed: {e}")
            if pod_created:
                self.delete(name)

    def delete(self, name: str) -> None:
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
        """
        pod, api = spod
        # 如果 command 是字符串，转为列表形式
        if isinstance(command, str):
            command = ["/bin/sh", "-c", command]

        # 如果设置了工作目录，用 `cd` 包装原始命令
        if workdir:
            joined_cmd = ' '.join(command)  # 把列表变成 shell 命令
            command = ["/bin/sh", "-c", f"cd {workdir} && {joined_cmd}"]

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

        return resp