from sporticolor.storage import Storage


class DataProcesser:
    """
    class responsible of processing large batches of raw track audio analysis data to tensor.
    This also stores to tracks table all the results
    """
    def __init__(self):
        self.storage = Storage()
        raise NotImplementedError

    def processBatch(trackids):
        for track in trackids:
            ... # add here from raw data to  tensor ready data
            storage.store(track_tensor)

class FastProcessOne:
    """
    fast version of a process class that optimizes getting a track
    to tensor ready. this needs to be fast cause its used live to get results for a single track.
    This also stores to tracks table all the results
    """
    def __init__(self):
        self.storage = Storage()
        raise NotImplementedError

    def process(trackid):
        raise NotImplementedError
        self.storage.store({"trackid": trackid, "tracktensor": track_tensor})
        return track_tensor
