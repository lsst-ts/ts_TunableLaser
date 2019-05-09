import abc
import yaml
import pathlib

class ConfigReader(abc.ABC):
    def __init__(self,config):
        self._content = {}
    
    @abc.abstractmethod
    def get_setting(self, name:str):
        pass

    @abc.abstractmethod
    def find_config_files(self):
        pass

    @abc.abstractmethod
    def read_files(self) -> dict:
        pass

class ConfigYamlReader(ConfigReader):
    def __init__(self,config_folder):
        self._content = {}
        self.config_folder = config_folder

    def change_config_directory(self,config_dir):
        self.config_folder = config_dir

    def get_setting(self, name:str):
        return self._content[name]

    def find_config_files(self):
        p = pathlib.Path(self.config_folder)
        config_file_list = p.glob("TunableLaser_*.yaml")
        return config_file_list

    def read_files(self):
        files = self.find_config_files()
        for file in files:
            with open(file,'r') as f:
                self._content.update(yaml.safe_load(f))
        

def laser_configuration():
    pass
