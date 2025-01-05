from typing import Union
from pathlib import Path
import numpy as np

from storage import Storage
from dataProcesser import FastProcessOne


class FrozenModel:
    """
    class that can be used to infer already trained models given the weights path
    """
    def __init__(self, weights_path: Union[str, Path]):
        self.weights = Path(weights_path)
        self.model = torch.load(str(self.weights))
        self.storage = Storage()
        self.processer = FastProcessOne()

    def infer(trackid: int) -> np.array[int]:
        data = self.storage.getTrack(trackid)
        if type(data) != torch.Tensor:
            data = self.processer(data)
        return self.model.forward(data)


class ModelTrainer:
    """
    class that is used to train a model for a user
    """
    def __init__(self, userid):
        self.storage = Storage()
        self.model = ActualModel()
        self.user = userid
        self.hyperparams = {
            "lr": 0.008,
            "batch_size": 64,
            "epochs": 60,
        }

    def getData(self):
        """
        gets all user data in tensor shape, if not present, process it.
        """
        raise NotImplementedError
        return data


    def train(self):
        data = self.getData()
        self._train(data)

    def _train(data):
        """
        here the training loop is called
        """
        raise NotImplementedError
