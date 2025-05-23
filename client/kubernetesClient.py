from kubernetes import client, config
from kubernetes.client.rest import ApiException

from typing import Optional
from client.sandboxClient import SandboxClient


class KubernetesClient(SandboxClient):
    def __init__(self, client: Optional[client.ApiClient] = None, namespace: str = "default"):
        try:
            config.load_incluster_config()
            self.namespace = namespace
            self.core_api = client.CoreV1Api()
        except Exception as e:
            raise RuntimeError(f"[KubernetesClient] Failed to initialize client: {e}")
    
    def create(self, image: str, name: str, command: str = "sleep infinity"):
        pod_spec = client.V1Pod(
            metadata=client.V1ObjectMeta(name=name),
            spec=client.V1PodSpec(
                containers=[
                    client.V1Container(
                        name="sandbox",
                        image=image,
                        command=command,
                    )
                ],
                restart_policy="Never"
            )
        )
        try:
            self.core_api.create_namespaced_pod(namespace=self.namespace, body=pod_spec)
            print(f"[KubernetesClient] Pod '{name}' created.")
        except ApiException as e:
            print(f"[Error] Creating pod failed: {e}")

    def delete(self, name: str) -> None:
        try:
            self.core_api.delete_namespaced_pod(name=name, namespace=self.namespace)
            print(f"[KubernetesClient] Pod '{name}' deleted.")
        except ApiException as e:
            print(f"[Error] Deleting pod failed: {e}")

    def get_status(self, name: str):
        """获取 sandbox pod 的状态"""
        try:
            pod = self.core_api.read_namespaced_pod(name=name, namespace=self.namespace)
            return pod.status.phase
        except ApiException as e:
            print(f"[Error] Get pod status failed: {e}")
            return "Unknown"