import json
import numpy as np
import torch
from torch.utils.data import TensorDataset, DataLoader
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.model_selection import train_test_split
from storage import Storage


class Preprocessing:

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tracks_data = []
        self.store = Storage()
        self.data()
        self.max_segments = max(len(track_data['segments']) for _, track_data in self.tracks_data)
        self.padded_tracks, self.tracks_lens = self.pad_tracks(self.tracks_data, self.max_segments)
        self.trainDataset, self.trainDataloader, self.testDataset, self.testDataloader = self.finalize_model1_input()

    def data(self):
        validTracks = self.store.getValidTracks()

        for track_id, track_data in validTracks:
            try:
                decoded_data = json.loads(track_data)
                self.tracks_data.append((track_id, decoded_data))
            except json.JSONDecodeError:
                print(f"Error processing data for track_id: {track_id}. Data: {track_data}")

    def feature_extraction(self):
        features = ['start', 'duration', 'confidence', 'loudness_start', 'loudness_max', 'loudness_max_time', 'loudness_end', 'pitches', 'timbre']

        scalers = {feature: MinMaxScaler() for feature in ['start', 'duration', 'confidence', 'loudness_start']}
        # Feel like min max is worse for loudenss but idk we have to test it ig
        scalers.update({feature: StandardScaler() for feature in ['loudness_start', 'loudness_max', 'loudness_end']})

        for feature in features:
            all_values = np.array([seg[feature] for _, track_data in self.tracks_data for seg in track_data['segments']]).reshape(-1, 1)
            scalers[feature].fit(all_values)

            for _, track_data in self.tracks_data:
                for seg in track_data['segments']:
                    seg[feature] = scalers[feature].transform([[seg[feature]]])[0][0]



    def flatten_segments(self, segments):
        flattened_segments = [np.array([
            seg['start'], seg['duration'], seg['confidence'], seg['loudness_start'],
            seg['loudness_max_time'], seg['loudness_max'], seg['loudness_end']
        ] + seg['pitches'] + seg['timbre']) for seg in segments]

        return np.array(flattened_segments)

    def pad_tracks(self, tracks, max_segments, segment_size=31):
        tracks_lens = []
        padded_tracks = np.zeros((len(tracks), max_segments, segment_size))

        for i, (_, track_data) in enumerate(tracks):
            flattened_segments = self.flatten_segments(track_data['segments'])
            num_segments = len(flattened_segments)
            tracks_lens.append(num_segments)
            padded_tracks[i, :num_segments, :] = flattened_segments[:max_segments]
            padded_tracks.shape # (n_tracks, n_segments, n_features)

        return padded_tracks, tracks_lens

    # padded_tracks.shape # (n_tracks, n_segments, n_features)

    def finalize_model1_input(self):

        paddedTracks_train, paddedTracks_test = train_test_split(self.padded_tracks, test_size=0.2, random_state=42)

        tracksTensor_train = torch.tensor(paddedTracks_train, dtype=torch.float32)#.to(self.device)
        trainDataset = TensorDataset(tracksTensor_train)
        trainDataloader = DataLoader(trainDataset, batch_size=32, shuffle=True)

        tracksTensor_test = torch.tensor(paddedTracks_test, dtype=torch.float32)#.to(self.device)
        testDataset = TensorDataset(tracksTensor_test)
        testDataloader = DataLoader(testDataset, batch_size=32, shuffle=False)
        print("preprocessing finished")

        return trainDataset, trainDataloader, testDataset, testDataloader
