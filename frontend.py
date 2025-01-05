from flask import Flask, request, redirect, g, url_for, render_template, session

from spotify_color.auth import *

from spotify_color.api import SpotifyAPI
from spotify_color.vis import vis
from spotify_color.dataYanker import dataYanker
from spotify_color.storage import Storage


# init flask
app = Flask(__name__)
app.secret_key = 'oogaboogacoccobello'

# ----------------------- AUTH API PROCEDURE -------------------------

@app.route("/auth")
def auth():
    return redirect(REDIRECT_URL)


@app.route("/callback/")
def callback():
    auth_token = request.args['code']
    auth_header, refresh_token = authorize(auth_token)
    session['auth_header'] = auth_header
    session['name'] = api.getUser(auth_header)['email']
    # store refresh token
    keyServer.addUser(session['name'], refresh_token)

    app.logger.warning(f'auth_header: {auth_header}')
    return profile()

def valid_token(resp):
    return resp is not None and not 'error' in resp

# -------------------------- API REQUESTS ----------------------------


@app.route("/")
def index():
    return render_template('index.html')


@app.route('/dash/<trackid>')
def dash(trackid):
    if 'auth_header' in session:
        auth_header = session["auth_header"]
        analJSON = api.getTrackAudioAnalysis(trackid)
        featJSON = api.getTrackAudioFeatures(trackid)
        trackJSON = api.getTrack(trackid)

        if not trackJSON["album"]["images"] is None:
            colors = vis.generate_colors(trackJSON["album"]["images"][0]["url"])
        else:
            colors = vis.generate_colors()

        graphJSON = vis.radar_json(featJSON, colors[0])
        startVectors = vis.gen_durr_arrays(analJSON)
        chromaVector = vis.gen_chroma(analJSON)

        return render_template("dash.html",
                               graphJSON=graphJSON,
                               analJSON=analJSON,
                               startVectors=startVectors,
                               chromaVector=chromaVector,
                               colors=colors,
                               trackJSON=trackJSON,
                               trackname=trackJSON["name"])
    return redirect(url_for('index'))


@app.route('/profile')
def profile():
    if 'auth_header' in session:
        auth_header = session['auth_header']
        # get profile data
        profile_data = api.getUser(auth_header)
        # get user playlist data
        playlist_data = api.getUserPlaylists(auth_header)
        # get user recently played tracks
        recently_played = api.getRecentlyPlayed(auth_header)
        #session['name'] = profile_data['email']

        if valid_token(recently_played):
            return render_template("profile.html",
                                   user=profile_data,
                                   playlists=playlist_data["items"],
                                   recently_played=recently_played["items"]
                                   )
    return render_template('profile.html')


@app.route('/yank')
def yank():
    # TODO make downloading data async
    # download all data & store
    dataYanker.yank(session['auth_header'])
    return redirect(url_for('profile'))

@app.route('/contact')
def contact():
    return render_template('contact.html')


def startlocal():
    app.run(debug=True, host='localhost', port=8421)


def start():
    app.run(debug=True, host='139.162.132.192', port=80)


if __name__ == "__main__":
    startlocal()
