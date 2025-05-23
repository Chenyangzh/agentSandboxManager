from abc import ABC, abstractmethod

class SandboxClient(ABC):
    @abstractmethod
    def create(self,):
        """
        create a sandbox
        """
        pass

    @abstractmethod
    def delete(self,) -> None:
        """
        delete a sandbox
        """
        pass
