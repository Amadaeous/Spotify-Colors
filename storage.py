from typing import Dict, Union
from pathlib import Path
import sqlite3
import datetime
import numpy as np
from sklearn.preprocessing import MinMaxScaler, StandardScaler
import json
import pickle


class Storage:
    """
    Interface to sqlite3 database.
    Provides the functionality for all modules to get and push data from/to the db.
    """

    def __init__(self):
        self.db_file = Path('data.db')
        print(self.db_file)
        self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
        self.curs = self.conn.cursor()

    # ---- Create ----
    def createTables(self):
        with self.conn as conn:
            # No changes to users and tracks tables
            conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                mail TEXT UNIQUE NOT NULL,
                token TEXT NOT NULL,
                last_data_updated TIMESTAMP,
                last_model_updated TIMESTAMP
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                track_id TEXT PRIMARY KEY,
                track_data TEXT NOT NULL,
                track_tensor BLOB
            );
            """)
            # Modified user_tracks table creation
            conn.execute("""
            CREATE TABLE IF NOT EXISTS user_tracks (
                user_id INTEGER,
                track_id TEXT,
                token TEXT,
                PRIMARY KEY (user_id, track_id),
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(track_id) REFERENCES tracks(track_id)
            );
            """)
            # No changes to model_data table
            conn.execute("""
            CREATE TABLE IF NOT EXISTS model_data (
                user_id INTEGER,
                model_blob BLOB,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );
            """)

    # ---- User - CRUD Operations ----
    # Users - Create

    def addUser(self, mail, token):
        """
        Adds to the users table the email and the refresh token and the last time the model / data fetch was updated,
        only if the user does not already exist.
        """
        with self.conn as conn:
            cursor = conn.cursor()

            # Check if user already exists
            cursor.execute('SELECT * FROM users WHERE mail = ?', (mail,))
            if cursor.fetchone() is None:
                # User does not exist, so insert new user
                sql = 'INSERT INTO users (mail, token, last_data_updated, last_model_updated) VALUES (?, ?, ?, ?)'
                cursor.execute(sql, (mail, token, None, None))
                conn.commit()
                print("User added:", mail)
            else:
                # User already exists, so do not insert
                print("User already exists:", mail)

    # Users - Read
    def getUser(self, user_id):
        with self.conn as conn:
            sql = 'SELECT * FROM users WHERE user_id = ?'
            return conn.execute(sql, (user_id,)).fetchone()

    def fetch_all_users(self):
        self.curs.execute("SELECT * FROM users")
        return self.curs.fetchall()

    def getUserByMail(self, email):
        with self.conn as conn:
            sql = 'SELECT * FROM users WHERE mail = ?'
            cursor = conn.execute(sql, (email,))
            return cursor.fetchone()

    # Users - Update
    def updateUser(self, user_id, updateData):
        with self.conn as conn:
            updated = ', '.join([f'{key} = ?' for key in updateData])
            values = list(updateData.values()) + [user_id]
            sql = f'UPDATE users SET {updated} WHERE user_id = ?'
            conn.execute(sql, values)
            conn.commit()

    # Users - Delete
    def deleteUser(self, user_id):
        with self.conn as conn:
            sql = 'DELETE FROM users WHERE user_id = ?'
            conn.execute(sql, (user_id,))
            conn.commit()

    # ---- Tracks - CRUD Operations ----
    # Tracks - Create
    def addTrack(self, track_id, track_data=None, track_tensor=None):
        with self.conn as conn:
            sql = 'INSERT INTO tracks (track_id, track_data, track_tensor) VALUES (?, ?, ?)'
            conn.execute(sql, (track_id, track_data, track_tensor))

            if track_data is not None:
                sql = 'UPDATE users SET last_data_updated = ? WHERE user_id = ?'
                conn.execute(sql, (datetime.datetime.now(), user_id))

            conn.commit()

    # Tracks - Read
    def getTrack(self, track_id):
        with self.conn as conn:
            sql = "SELECT track_id, track_data FROM tracks WHERE track_id = ? AND track_data NOT LIKE '%\"error\":%'"
            return conn.execute(sql, (track_id,)).fetchone()

    def getTracks(self, track_ids):
        with self.conn as conn:
            values = ', '.join('?' for _ in track_ids)
            sql = f"SELECT track_id, track_data FROM tracks WHERE track_id IN ({values}) AND track_data NOT LIKE '%\"error\":%'"
            return conn.execute(sql, track_ids).fetchall()

    def getTrackTensor(self, track_id):
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT track_tensor FROM tracks WHERE track_id = ?;
        """, (track_id,))
        result = cursor.fetchone()
        if result and result[0]:
            return pickle.loads(result[0])
        return None

    def getValidTracks(self):
        """
        Extracts and returns valid track data from the database, excluding any with errors.
        """
        with self.conn as conn:
            cursor = conn.execute(
                "SELECT track_id, track_data FROM tracks WHERE track_data NOT LIKE '%\"error\":%'")
            return cursor.fetchall()

    def getValidUserTracks(self, userid):
        """
        Extracts and returns valid track data from the database for users tracks
        """
        with self.conn as conn:
            cursor = conn.execute(
                "SELECT tracks.track_id, tracks.track_data FROM tracks INNER JOIN user_tracks ON tracks.track_id = user_tracks.track_id WHERE user_tracks.user_id = ?", (userid,))
            return cursor.fetchall()

    def decodeTracks(self, tracks):
        if tracks is None:  # ehhh not amazing but for now im tired
            tracks = self.getValidTracks()

        decoded_tracks = []

        for track_id, track_data in tracks:
            try:
                decoded_data = json.loads(track_data)
                decoded_tracks.append((track_id, decoded_data))

            except json.JSONDecodeError:
                # Do something idk
                print(
                    f"Error processing data for track_id: {track_id}. Data: {track_data}")
                pass

        return decoded_tracks

    def scaleFeatures(self, tracks_data, features):
        unscaled_features = features
        scaled_features = [f for f in features if f not in unscaled_features]

        scalers = {feature: (MinMaxScaler() if feature not in [
                             'loudness_max_time', 'loudness_start', 'loudness_max', 'loudness_end'] else StandardScaler()) for feature in scaled_features}

        # Prepare feature arrays
        feature_arrays = {feature: [] for feature in scaled_features}
        for _, track_data in tracks_data:
            for seg in track_data['segments']:
                for feature in scaled_features:
                    feature_arrays[feature].append(seg[feature])

        # Scale features in bulk
        for feature in scaled_features:
            all_values = np.array(feature_arrays[feature]).reshape(-1, 1)
            scalers[feature].fit(all_values)
            scaled_values = scalers[feature].transform(all_values)
            index = 0
            for _, track_data in tracks_data:
                for seg in track_data['segments']:
                    seg[feature] = scaled_values[index]
                    index += 1

    def padTracks(self, tracks_data, features, max_segments=None):
        segment_size = 31

        if max_segments is not None:
            padded_tracks = np.zeros(
                (len(tracks_data), max_segments, segment_size), dtype=np.float32)
        else:
            padded_tracks = []

        for i, (_, track_data) in enumerate(tracks_data):
            segments = track_data['segments']
            num_segments = len(segments)

            flattened_segments = np.array([
                np.concatenate(([seg[f] for f in features],
                               seg['pitches'], seg['timbre']))
                for seg in segments], dtype=np.float32)

            if max_segments is not None:
                padded_tracks[i, :num_segments,
                              :] = flattened_segments[:max_segments]
            else:
                padded_tracks.append(flattened_segments)

        return padded_tracks

    def preprocess_tracks(self, track_ids, max_segments=None, userid=None):
        if userid is None:
            tracks = self.getTracks(
                track_ids) if track_ids is not None else self.getValidTracks()
        else:
            print(f"getting tracks for user: {userid}")
            tracks = self.getValidUserTracks(userid)

        decoded_tracks = self.decodeTracks(tracks)
        self.scaleFeatures(decoded_tracks, ['start', 'duration', 'confidence', 'loudness_start',
                                            'loudness_max', 'loudness_max_time', 'loudness_end'])

        # This some ugly ass code ngl
        padded_tracks = self.padTracks(decoded_tracks, ['start', 'duration', 'confidence', 'loudness_start',
                                                        'loudness_max', 'loudness_max_time', 'loudness_end'], max_segments)

        trakids = [track[0] for track in decoded_tracks]

        return padded_tracks, trakids

    def bTrackExits(self, track_id):
        with self.conn as conn:
            sql = 'SELECT 1 FROM tracks WHERE track_id = ?'
            return conn.execute(sql, (track_id,)).fetchone() is not None

    # Tracks - Update
    def updateTrack(self, track_id, updateData):
        with self.conn as conn:
            updated = ', '.join([f"{key} = ?" for key in updateData])
            values = list(updateData.values()) + [track_id]
            sql = f'UPDATE tracks SET {updated} WHERE track_id = ?'
            conn.execute(sql, values)
            conn.commit()

    def updateTrackTensor(self, track_id, track_tensor):
        with self.conn:
            self.conn.execute("""
            UPDATE tracks
            SET track_tensor = ?
            WHERE track_id = ?;
            """, (pickle.dumps(track_tensor), track_id))

    # Tracks - Delete
    def deleteTrack(self, track_id):
        with self.conn as conn:
            sql = 'DELETE FROM tracks WHERE track_id = ?'
            conn.execute(sql, (track_id,))
            conn.commit()

    # ---- UserTracks - CRUD Operations ----
    # UserTracks - Craete
    def addUserTrack(self, user_id, track_id, token):
        """
        Adds to user_tracks table the track_id and its generated token
        """
        with self.conn as conn:
            sql = 'INSERT INTO user_tracks (user_id, track_id, token) VALUES (?, ?, ?)'
            conn.execute(sql, (user_id, track_id, token))
            conn.commit()

    # UserTracks - Read
    def getUserTrack(self, user_id, track_id):
        with self.conn as conn:
            sql = 'SELECT * FROM user_tracks WHERE user_id = ? AND track_id = ?'
            return conn.execute(sql, (user_id, track_id)).fetchone()

    # UserTracks - Update
    def updateUserTrack(self, user_id, track_id, new_token):
        with self.conn as conn:
            sql = 'UPDATE user_tracks SET token = ? WHERE user_id = ? AND track_id = ?'
            conn.execute(sql, (new_token, user_id, track_id))
            conn.commit()

    # UserTracks - Delete
    def deleteUserTrack(self, user_id, track_id):
        with self.conn as conn:
            sql = 'DELETE FROM user_tracks WHERE user_id = ? AND track_id = ?'
            conn.execute(sql, (user_id, track_id))
            conn.commit()

    # ---- ModelData - CRUD Operations ----
    # ModelData - Create
    def addModelData(self, user_id, model_blob):
        """
        Adds model data for a specific user.
        """
        with self.conn as conn:
            sql = 'INSERT INTO model_data (user_id, model_blob) VALUES (?, ?)'
            conn.execute(sql, (user_id, model_blob))
            conn.commit()

    # ModelData - Read
    def getModelData(self, user_id):
        with self.conn as conn:
            sql = 'SELECT model_blob FROM model_data WHERE user_id = ?'
            return conn.execute(sql, (user_id,)).fetchone()

    # ModelData - Update
    def updateModelData(self, user_id, new_model_blob):
        with self.conn as conn:
            sql = 'UPDATE model_data SET model_blob = ? WHERE user_id = ?'
            conn.execute(sql, (new_model_blob, user_id))

            sql = 'UPDATE users SET last_model_updated = ? WHERE user_id = ?'
            conn.execute(sql, (datetime.datetime.now(), user_id))
            conn.commit()

    # ModelData - Delete
    def deleteModelData(self, user_id):
        with self.conn as conn:
            sql = 'DELETE FROM model_data WHERE user_id = ?'
            conn.execute(sql, (user_id,))
            conn.commit()

    # ---- ???? ----
    # Uhhh im nto very sure what to display but ig this makes the most sense hahah
    def printInfo(self):
        with self.conn as conn:
            nUsers = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            nTracks = conn.execute('SELECT COUNT(*) FROM tracks').fetchone()[0]
            print(f'Total Users: {nUsers} \n Total Tracks: {nTracks}')

    # What is model status?, just did model_blob rnow cause thats all i have
    def getAllModelStatus(self) -> Dict[str, Union[str]]:
        """
        Return model status for all users
        """
        with self.conn as conn:
            cursor = conn.execute("SELECT user_id, model_blob FROM users")
            return {i['user_id']: i['model_blob'] for i in cursor.fetchall()}

    # ---- Generic CRUD ----
    def store(self, data: Dict):
        """
        Generic method to store any data that is storable
        The input is of shape {"datatype": data}
        so check if datatype is storable and if so call correct submethod
        """
        # TODO check what data it is (track, artist, etc..) and store if possible
        raise NotImplementedError

    def addTrackSafe(self, track_id, track_data=None, track_tensor=None, user_id=None):
        """
        If the track already exists, updates its data; otherwise, adds a new track.
        """
        with self.conn as conn:
            # We assume track_id is the PRIMARY KEY. If not, modify accordingly.
            sql = '''
            INSERT INTO tracks (track_id, track_data, track_tensor)
            VALUES (?, ?, ?)
            ON CONFLICT(track_id)
            DO UPDATE SET track_data=excluded.track_data, track_tensor=excluded.track_tensor;
            '''
            conn.execute(sql, (track_id, track_data, track_tensor))

            if track_data is not None and user_id is not None:
                sql = '''
                UPDATE users SET last_data_updated = ?
                WHERE user_id = ?;
                '''
                conn.execute(sql, (datetime.datetime.now(), user_id))

            conn.commit()

    def addUserTrackSafe(self, user_id, track_id, token):
        """
        If the user_track already exists, updates its token; otherwise, adds a new user_track.
        """
        with self.conn as conn:
            # Assuming user_id and track_id together form the composite PRIMARY KEY.
            # If not, modify accordingly.
            sql = '''
            INSERT INTO user_tracks (user_id, track_id, token)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, track_id)
            DO UPDATE SET token=excluded.token;
            '''
            conn.execute(sql, (user_id, track_id, token))
            conn.commit()

    def getTracksData(self):
        tracks_data = []

        for track_id, track_data in self.getValidTracks():
            try:
                decoded_data = json.loads(track_data)
                tracks_data.append((track_id, decoded_data))
            except json.JSONDecodeError:
                # Fake data
                pass

        return tracks_data


if __name__ == "__main__":
    s = Storage()
    s.createTables()
