from abc import ABC, abstractmethod
from pathlib import Path
class StorageProvider(ABC):
    @abstractmethod
    def save(self, project_id:int, filename:str, content:bytes)->str: ...
    @abstractmethod
    def read(self, path:str)->bytes: ...

class LocalSecureStorage(StorageProvider):
    def __init__(self,root:Path): self.root=root.resolve(); self.root.mkdir(parents=True,exist_ok=True)
    def save(self,project_id:int,filename:str,content:bytes)->str:
        folder=(self.root/str(project_id)).resolve()
        if self.root not in folder.parents: raise ValueError("Unsafe storage path")
        folder.mkdir(parents=True,exist_ok=True); target=folder/filename; target.write_bytes(content); return str(target.relative_to(self.root))
    def read(self,path:str)->bytes:
        target=(self.root/path).resolve()
        if self.root not in target.parents: raise ValueError("Unsafe storage path")
        return target.read_bytes()

