from abc import abstractmethod

class SimDriver:

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def step(self):
        pass