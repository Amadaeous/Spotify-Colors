import numpy as np
import onnxruntime
import time


class ModelUno:
    _instance = None

    def __new__(cls, model_path):
        if cls._instance is None:
            cls._instance = super(ModelUno, cls).__new__(cls)
            cls._instance.model = onnxruntime.InferenceSession(model_path)

            cls._instance.input_name = cls._instance.model.get_inputs()[0].name
            cls._instance.output_name = cls._instance.model.get_outputs()[
                0].name

        return cls._instance

    def __call__(self, x):
        """
        :param x: np.ndarray of shape (n_segments, n_features)
        """
        return self.model.run([self.output_name], {self.input_name: x})[0]


def create_user_dataset(userid, max_tracks=750):
    from spoticolor.storage import Storage
    padSize = 750
    model = ModelUno("models/modelunoEm6B32.onnx")
    store = Storage()
    t1 = time.time()
    padded_tracks, track_ids = store.preprocess_tracks(None, userid=userid)
    if len(padded_tracks) > max_tracks:
        padded_tracks, track_ids = padded_tracks[:max_tracks], track_ids[:max_tracks]
    tokens = []
    for track, track_id in zip(padded_tracks, track_ids):
        model_output = model(track)
        tokens.append((track_id, model_output))

    for track_id, model_output in tokens:
        store.updateTrackTensor(track_id, model_output)

    embSize = len(tokens[0][1][1])
    padded_result = np.full((len(tokens), padSize, embSize), np.nan)

    for i, x in enumerate([t[1] for t in tokens]):
        nSeg = min(x.shape[0], 750)
        padded_result[i, :nSeg, :] = x[:nSeg]
    t2 = time.time()
    print(padded_result.shape)
    padded_result = np.nan_to_num(padded_result, nan=0.0)

    min_val = np.nanmin(padded_result, axis=(1, 2), keepdims=True)
    max_val = np.nanmax(padded_result, axis=(1, 2), keepdims=True)

    range_val = max_val - min_val
    range_val[range_val == 0] = 1  # Prevent division by zero

    # Perform min-max scaling
    scaled_array = (padded_result - min_val) / range_val

    # Handle the case where min_val == max_val
    scaled_array[(max_val == min_val).repeat(padded_result.shape[1], axis=1).repeat(padded_result.shape[2], axis=2)] = 0  # or padded_result[(max_val == min_val).repeat(padded_result.shape[1], axis=1).repeat(padded_result.shape[2], axis=2)]
    scaled_result = scaled_array

    #for i in range(padded_result.shape[0]):
    #    for j in range(padded_result.shape[1]):
    #        item = padded_result[i, j, :]
    #        min_val = np.nanmin(item)
    #        max_val = np.nanmax(item)
    #        if min_val == max_val:
    #            scaled_array[i, j, :] = 0  # or scaled_array[i, j, :] = item, depending on your needs
    #        else:
    #            scaled_array[i, j, :] = (item - min_val) / (max_val - min_val)

    print(f"took {(t2-t1)*1000}ms for {padded_result.shape[0]} tracks")

    padded_result.tofile(f"spoticolor/static/datasets/{userid}_dataset.bin")
    with open(f"spoticolor/static/datasets/{userid}_dataset_shape.txt", "w") as f:
        f.write(str(padded_result.shape))

    with open(f'spoticolor/static/datasets/{userid}_dataset_trackids.txt', 'w') as f:
        for item in track_ids:
            f.write(f"{item}\n")
    return padded_result, track_ids


if __name__ == "__main__":
    array, track_ids = create_user_dataset("31kbrhyfxsw2qcosmsgycku2kxwu")
    print(array.shape, np.nanmax(array), np.nanmin(array), "\n", array)
    print(f"Does the data contain NaNs?: {np.isnan(array).any()}")
