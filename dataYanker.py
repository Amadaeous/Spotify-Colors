import datetime
from spoticolor.storage import Storage
from spoticolor.api import SpotifyAPI
from spoticolor.model1 import create_user_dataset
import orjson
import threading
import time


class dataYanker:
    """
    Module that calls all the API queries and stores all user data.
    Responsible to populate all user data inside storage
    """

    def __init__(self, header, userid, refresh_token):
        self.header = header
        self.userid = userid
        self.api = SpotifyAPI()
        self.api.set_header(header, refresh_token)
        self.track_IDs = set()
        self.artists = set()

        self.responses = []
        self.completed = threading.Event()

    def enqueue_and_wait(self, user_id, func, args=None, kwargs=None):
        self.responses = []
        self.completed.clear()

        def callback(uid, response):
            if uid == user_id:
                self.responses.append(response)
                if len(self.responses) == self.expected_responses:
                    self.completed.set()

        self.expected_responses = 1
        self.api.enqueue_request(
            user_id, func, args or [], kwargs or {}, callback)
        self.completed.wait()

        return self.responses[0]

    def yank(self, storage: Storage):
        print("yank")
        """
        Here all user data is pulled to populate self.track_IDs, then track IDs are saved to storage
        """
        print("started yanker...")
        self.getAllSavedTracks()
        print("Gotten all saved tracks")

        self.getTop()
        print("Gotten all top tracks")

        # self.getPlaylistTracks()
        print("Gotten all playlists tracks")

        # self.getUserQueue() # TODO: FIX THIS, i get Bad OAuth request, yes read-queue not in auth scope

        # self.getArtistTop()
        print("Gotten all artists tracks")

        self.getRecentlyPlayed()
        print("Gotten all recently played tracks")

        print(f"Extracted {len(self.track_IDs)} unique track ids from user")

        self.store_track_ids(storage)
        print("stored all tracks audio analysis")

        print("starting creating user dataset")
        create_user_dataset(self.userid, max_tracks=750)
        print("done creating user dataset")

    def getAllSavedTracks(self):
        trackids = []
        total = self.enqueue_and_wait(
            self.userid, self.api.getUserSavedTracks)["total"]

        x, rest = divmod(total, 50)
        self.expected_responses = x + (1 if rest != 0 else 0)
        for i in range(x + 1):
            items = self.enqueue_and_wait(self.userid, self.api.getUserSavedTracks, kwargs={
                                          "limit": 50, "offset": i*50})["items"]
            for item in items:
                trackids.append(item["track"]["id"])
        self.track_IDs.update(trackids)
        print("finished extracting all saved tracks")

    def getTop(self, time_range='short_term', what='tracks'):
        """
        stores raw json from getTopTracks,
        time_range: 'short_term', 'medium_term', 'long_term'
        what: 'artists', 'tracks'
        """
        total = self.enqueue_and_wait(self.userid, self.api.getUserTop, kwargs={
                                      "requestType": what, "timeRange": time_range})["total"]
        trackids = []

        x, rest = divmod(total, 50)
        for i in range(x):
            items = self.enqueue_and_wait(self.userid, self.api.getUserTop, kwargs={
                                          "requestType": what, "timeRange": time_range, "offset": i*50})["items"]
            for item in items:
                trackids.append(item["id"])
        if rest != 0:
            items = self.enqueue_and_wait(self.userid, self.api.getUserTop, kwargs={
                                          "requestType": what, "timeRange": time_range, "offset": x*50})["items"]
            for item in items:
                trackids.append(item["id"])

        self.track_IDs.update(trackids)
        print("finished extracting all top", what)

    def getPlaylistTracks(self):
        """
        gets list of all playlists and downloads all tracks from them
        """
        playlistsItems = []
        trackids = []
        total = self.enqueue_and_wait(
            self.userid, self.api.getUserPlaylists)['total']

        x, rest = divmod(total, 50)
        for i in range(x):
            playlistsItems.extend(self.enqueue_and_wait(
                self.userid, self.api.getUserPlaylists, kwargs={"limit": 50, "offset": i*50})['items'])
        if rest != 0:
            playlistsItems.extend(self.enqueue_and_wait(
                self.userid, self.api.getUserPlaylists, kwargs={"limit": 50, "offset": x*50})['items'])

        for playlist in playlistsItems:
            totalItems = self.enqueue_and_wait(
                self.userid, self.api.getPlaylistItems, args=(playlist['id'],))['total']
            y, rest = divmod(totalItems, 50)
            for j in range(y):
                playlistComponents = self.enqueue_and_wait(self.userid, self.api.getPlaylistItems, args=(
                    playlist['id'],), kwargs={"limit": 50, "offset": j*50})
                items = playlistComponents['items']
                for item in items:
                    if item['track'] is not None:
                        trackids.append(item['track']['id'])
            if rest != 0:
                allSongs = self.enqueue_and_wait(self.userid, self.api.getPlaylistItems, args=(
                    playlist['id'],), kwargs={"limit": 50, "offset": y*50})
                items = allSongs['items']
                for item in items:
                    if item['track'] is not None:
                        trackids.append(item['track']['id'])

        self.track_IDs.update(trackids)
        print("finished extracting all playlist tracks")

    def getRecentlyPlayed(self):
        """ gets all recently played tracks """
        now = int(datetime.datetime.timestamp(datetime.datetime.now()) * 1000)
        res = self.enqueue_and_wait(self.userid, self.api.getRecentlyPlayed, kwargs={
                                    "before": now, "limit": 5})
        trackids = []

        # self.store(res, 'recentlyPlayed')
        timestamp = res['cursors']['before']
        flag = True
        while flag:
            res = self.enqueue_and_wait(
                self.userid, self.api.getRecentlyPlayed, kwargs={"before": timestamp})
            for item in res['items']:
                trackids.append(item['track']['id'])

            # self.store(res, 'recentlyPlayed')
            try:  # when there are no more tracks in history API returns None as cursors
                timestamp = res['cursors']['after']
            except TypeError:
                flag = False
        self.track_IDs.update(trackids)
        print("finished extracting all recently played tracks")

    def getFollowedArtists(self):
        """ gets all followed artists """
        followedArtists = []
        res = self.enqueue_and_wait(self.userid, self.api.getFollowedArtists)
        for item in res['artists']['items']:
            followedArtists.append(item['id'])
        # self.store(self, res, 'followedArtist')

        try:
            cursor = res['artists']['cursors']['after']
        except ValueError:
            cursor = None
        while cursor is not None:
            res = self.enqueue_and_wait(self.userid, self.api.getFollowedArtists, kwargs={
                                        "type": "artist", "after": cursor})
            # self.store(self, res, 'followedArtist')
            for item in res['artists']['items']:
                followedArtists.append(item['id'])
            try:
                cursor = res['artists']['cursors']['after']
            except ValueError:
                cursor = None
        self.artists.update(followedArtists)

    def getUserQueue(self):
        total = self.enqueue_and_wait(self.userid, self.api.getUserQueue)
        print("amount in queue is: ", len(total), total)
        currentlyPlaying = total["currently_playing"]
        queue = total["queue"]
        print("amount in queue is: ", len(queue), queue)
        trackids = []
        if currentlyPlaying is not None and queue is not None:
            trackids.append(currentlyPlaying['id'])
            for item in queue:
                trackids.append(item['id'])
        elif currentlyPlaying is not None and queue is None:
            trackids.append(currentlyPlaying['id'])
        else:
            return
        self.track_IDs.update(trackids)

    def getArtistTop(self, time_range='short_term', what='artists'):
        self.getFollowedArtists()
        total = self.enqueue_and_wait(self.userid, self.api.getUserTop, kwargs={
                                      "requestType": what, "timeRange": time_range})["total"]
        trackids = []
        topArtists = []

        x, rest = divmod(total, 50)
        for i in range(x):
            items = self.enqueue_and_wait(self.userid, self.api.getUserTop, kwargs={
                                          "requestType": what, "timeRange": time_range, "offset": i*50})["items"]
            for item in items:
                topArtists.append(item['id'])

        if rest != 0:
            items = self.enqueue_and_wait(self.userid, self.api.getUserTop, kwargs={
                                          "requestType": what, "timeRange": time_range, "offset": x*50})["items"]
            for item in items:
                topArtists.append(item['id'])

        self.artists.update(topArtists)

        for artist in self.artists:
            tracks = self.enqueue_and_wait(
                self.userid, self.api.getArtistTop, args=(artist,))['tracks']
            for track in tracks:
                trackids.append(track['id'])

        self.track_IDs.update(trackids)

        print("finished extracting ", len(trackids), " artists top tracks")
        print("The user has ", len(topArtists), ' top artists')

    def store_track_ids(self, storage: Storage, limit=750):
        if limit is None:
            limit = len(self.track_IDs)

        nTracks = 0
        for trackid in list(self.track_IDs)[:limit]:
            if not storage.bTrackExits(trackid):
                track_data = self.enqueue_and_wait(
                    self.userid, self.api.getTrackAudioAnalysis, args=(trackid,))
                storage.addTrackSafe(trackid, track_data=orjson.dumps(
                    track_data).decode('utf-8'), track_tensor="faketensor")
                nTracks += 1

            storage.addUserTrackSafe(self.userid, trackid, None)

        print(f"Stored {nTracks} Tracks")
