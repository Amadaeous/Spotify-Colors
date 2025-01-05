from typing import Union, List
from spoticolor.storage import Storage
from spoticolor.frozenmodel import FrozenModel


class AIMaster:
    def __init__(self):
        self.storage = Storage()
        self.models = self.loadModelsFromStorage()
        raise NotImplementedError

    def loadModelsFromStorage():
        return self.storage.loadModels()

    def inferUserModel(self, userid: str, tracks: Union[int, List[int]]) -> List[int]:
        """
        userid: userid string that is used to index user in storage
        tracks: one or many ints representing trackids, used to index tracks in storage
        """
        if type(self.models[userid]) != FrozenModel:
            # model is not trained yet
            [self.trainModel(userid)]
        if type(tracks) == int:
            return self.models[userid].infer(tracks)
        return [self.models[userid].infer(track) for track in tracks]

    def trainModel(self, userid):
