from client.sandboxClient import SandboxClient
from client.kubernetesClient import KubernetesClient
from client.localDockerClient import LocalDockerClient

def get_client() -> SandboxClient:
    """
    Check world environment and return client.
    Kubernetes and local docker are supported for now.
    """
    # check kubernetes
    if check_kubernetes():
        print("Kubernetes sandbox environment ready.")
        return KubernetesClient(), "kubernetes"
    
    # check local docker
    elif check_local_docker():
        print("Local Docker sandbox environment ready.")
        return LocalDockerClient(), "local_container"
    # check http server
    else:
        raise RuntimeError("Error: No sandbox environment available.")

def check_local_docker() -> bool:
    try:
        _ = LocalDockerClient()
        return True
    except RuntimeError as e:
        print(f"Error: {e}")
        return False
    
def check_kubernetes() -> bool:
    try:
        _ = KubernetesClient()
        return True
    except RuntimeError as e:
        print(f"Error: {e}")
        return False
    
def check_http_server() -> bool:
    raise NotImplementedError