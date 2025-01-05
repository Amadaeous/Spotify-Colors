from storage import Storage
import pandas as pd
from pathlib import Path
import sqlite3
import json
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from tqdm import tqdm
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.model_selection import train_test_split
import ast

storage = Storage()
db_file = Path('data.db')
# Connect to the SQLite database
conn = sqlite3.connect(db_file, check_same_thread=False)
# query = "SELECT track_data FROM tracks"  # Adjust the query as needed
# data = pd.read_sql_query(query, conn)
# conn.close()

# cursor = conn.execute(
#     "SELECT track_id, track_data FROM tracks WHERE track_data NOT LIKE '%\"error\":%'")
# data = cursor.fetchall()

data = storage.getValidTracks()

tracks_data = []

for track_id, track_data in data:
    try:
       decoded_data = json.loads(track_data)
       tracks_data.append((track_id, decoded_data))
    except json.JSONDecodeError:
        print(f"Error processing data for track_id: {track_id}. Data: {track_data}")

print(tracks_data[0][1]['segments'][1])
print(storage.getTrack('05wb6MEyJeG2z1MVCIXxC8'))

features = ['start', 'duration', 'confidence', 'loudness_start', 'loudness_max', 'loudness_max_time', 'loudness_end', 'pitches', 'timbre']

scalers = {feature: MinMaxScaler() for feature in ['start', 'duration', 'confidence', 'loudness_start']}
# Feel like min max is worse for loudenss but idk we have to test it ig
scalers.update({feature: StandardScaler() for feature in ['loudness_start', 'loudness_max', 'loudness_end']})

for feature in features:
    all_values = np.array([seg[feature] for _, track_data in tracks_data for seg in track_data['segments']]).reshape(-1, 1)
    scalers[feature].fit(all_values)
    
    for _, track_data in tracks_data:
        for seg in track_data['segments']:
            seg[feature] = scalers[feature].transform([[seg[feature]]])[0][0]

print(tracks_data[0][1]['segments'][1])
# # Remove rows where 'track_data' column contains '{"error": {"status": 429}}'
# data = data[data['track_data'] != 'fakedata']
# data = data[~data['track_data'].str.contains('error')]
# df = pd.DataFrame(data)

# print(df.iloc[5])

# # Extract just the "segments" information
# segments_df = pd.json_normalize(df['track_data'].apply(json.loads).apply(lambda x: x['segments']))
# max_segments = segments_df.apply(lambda row: len(row.dropna()), axis=1).max()
# # Calculate the number of segments for each song
# num_segments_per_song = segments_df.apply(lambda row: len(row.dropna()), axis=1)

# # Create a histogram
# plt.figure(figsize=(10, 6))
# plt.hist(num_segments_per_song, bins=range(0, max_segments + 1), edgecolor='black')
# plt.xlabel('Number of Segments')
# plt.ylabel('Frequency')
# plt.title('Distribution of Number of Segments per Song')
# plt.grid(True)
# plt.show()


