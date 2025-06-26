from abc import abstractmethod
from archtool.layers.default_layer_interfaces import ABCController

from click import Group

class CommanderControllerABC(ABCController):
    cli: Group

    @abstractmethod
    def reg_commands(self):
        ...