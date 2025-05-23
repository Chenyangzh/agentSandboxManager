from client.sandboxClient import SandboxClient
from client.kubernetesClient import KubernetesClient
from client.localDockerClient import LocalDockerClient

def get_client() -> SandboxClient:
    """
    检查运行环境，是否为container、kubernets、或使用http server。
    """
    # check kubernetes
    if check_kubernetes():
        print("[Kubernetes Check] Kubernetes sandbox environment ready.")
        return KubernetesClient(), "kubernetes"
    
    # check local docker
    elif check_local_docker():
        print("[Docker Check] Local Docker sandbox environment ready.")
        return LocalDockerClient(), "local_container"
    # check http server
    else:
        raise  RuntimeError("[Error] No sandbox environment available.")

def check_local_docker() -> bool:
    try:
        _ = LocalDockerClient()
        return True
    except RuntimeError as e:
        print(f"[Docker Check] {e}")
        return False
    
def check_kubernetes() -> bool:
    try:
        _ = KubernetesClient()
        return False
    except RuntimeError as e:
        print(f"[Kubernetes Check] {e}")
        return False
    
def check_http_server() -> bool:
    raise NotImplementedError