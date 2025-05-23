import kubernetes

from typing import Optional
from client.sandboxClient import SandboxClient


class KubernetesClient(SandboxClient):
    def __init__(self, client: Optional[kubernetes.client.ApiClient] = None):
        pass
    
    def create(self, ):
        pass

    def delete(self, ) -> None:
        pass