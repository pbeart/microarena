import random

from abc import abstractmethod

class EntityDriver[ShipT]:
    "Class which drives a game ship, and reads from and updates the corresponding ReadFromT and WriteToT respectively"
    
    @abstractmethod
    def update(self, on: ShipT):
        pass
