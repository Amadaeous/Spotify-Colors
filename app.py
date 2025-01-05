from flask import Flask, request, redirect, url_for, render_template, session, jsonify,  make_response
import os
from logging.config import dictConfig
from datetime import datetime
import threading

from spoticolor.auth import AuthHandler
from spoticolor.secret import hostname
from spoticolor.storage import Storage
from spoticolor.api import SpotifyAPI
from spoticolor.dataYanker import dataYanker
from spoticolor import vis

# init flask
app = Flask(__name__)
dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://sys.stdout',  # <-- Solution
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})
app.secret_key = 'oogaboogacoccobello'
app_context = app.app_context()
app_context.push()

# Init Modules as Nones, populate them at app startup
storage = None
auth_client = None

# ----------------------- ENDPOINTS -------------------------


@app.route("/auth")
def auth():
    return redirect(auth_client.redirect_url)


@app.route("/callback/")
def callback():
    api = SpotifyAPI()
    auth_token = request.args['code']
    auth_header, refresh_token = auth_client.authorize(auth_token)
    print(f"auth_header: {auth_header}")
    print(f"refresh_token: {refresh_token}")
    api.set_header(auth_header, refresh_token)
    session["auth_header"] = auth_header
    session["refresh_token"] = refresh_token
    session['name'] = api.getUser()
    session["userid"] = session["name"]["id"]
    session["username"] = session["name"]["display_name"]
    session["yanked_data"] = False
    print(f"session['name']: {session['name']}", session)
    # store refresh token
    storage.addUser(session['name']["email"], refresh_token)
    app.logger.warning(f'auth_header: {auth_header}')
    app.logger.info(session["name"])
    return profile()


def valid_token(resp):
    return resp is not None and not 'error' in resp


@app.route("/")
def index():
    model2_cookie = request.cookies.get('model2')
    response = make_response(render_template('index.html'))
    if model2_cookie is None:
        response.set_cookie('model2', 'False', path='/')
        app.logger.info("Model2 cookie initialized to False")
    if session.get("yanked-data", None) is None:
        session["yanked_data"] = False
    return response


@app.route("/model")
def model2():
    if 'auth_header' not in session and 'refresh_token' not in session:
        return redirect("/auth")
    if not session["yanked_data"]:
        yanker = dataYanker(
            session['auth_header'], session["userid"], session["refresh_token"])
        t1 = threading.Thread(target=yanker.yank, args=(storage,))
        t1.start()
        session["yanked_data"] = True
    return render_template("model2.html", userid=session["userid"], username=session["username"])


@app.route("/check-dataset")
def check_dataset():
    file_path = f"spoticolor/static/datasets/{session['userid']}_dataset.bin"
    exists = os.path.isfile(file_path)
    return jsonify({'exists': exists})


@app.route('/dash/<trackid>')
def dash(trackid):
    if 'auth_header' in session and 'refresh_token' in session:
        api = SpotifyAPI()
        api.set_header(session["auth_header"], session["refresh_token"])
        analJSON = api.getTrackAudioAnalysis(trackid)
        # featJSON = api.getTrackAudioFeatures(trackid)
        trackJSON = api.getTrack(trackid)

        if not trackJSON["album"]["images"] is None:
            colors = vis.generate_colors(
                trackJSON["album"]["images"][0]["url"])
        else:
            colors = vis.generate_colors()

        # TODO kiko fix pls
        # graphJSON = vis.radar_json(featJSON, colors[0])

        startVectors = vis.gen_durr_arrays(analJSON)
        chromaVector = vis.gen_chroma(analJSON)

        artists = trackJSON["artists"]
        artistString = artists[0]["name"]
        for i in range(1, len(artists)):
            artistString += ", " + artists[i]["name"]

        return render_template("dash.html",
                               # graphJSON=graphJSON,
                               analJSON=analJSON,
                               startVectors=startVectors,
                               chromaVector=chromaVector,
                               colors=colors,
                               trackJSON=trackJSON,
                               artists=artistString,
                               albumName=trackJSON["album"]["name"],
                               songSpotURL=trackJSON["external_urls"]["spotify"],
                               trackname=trackJSON["name"])

    return redirect(url_for('index'))


@app.route('/profile')
def profile():
    if 'auth_header' not in session and 'refresh_token' not in session:
        return redirect("/auth")

    model2_cookie = request.cookies.get('model2')

    # If the 'model2' cookie doesn't exist, set it to 'False'
    if model2_cookie is None:
        response = make_response(redirect(request.url))  # redirect to the same route to set the cookie
        response.set_cookie('model2', 'False', path='/')
        app.logger.info("Model2 cookie initialized to False")
        return response

    if model2_cookie == 'False':
        app.logger.info("Model not trained, redirecting to model page")
        return redirect("/model")

    if 'auth_header' in session and 'refresh_token' in session:
        api = SpotifyAPI()
        api.set_header(session["auth_header"], session["refresh_token"])
        # get profile data
        profile_data = api.getUser()
        # get user playlist data
        playlist_data = api.getUserPlaylists()
        # get user recently played tracks
        recently_played = api.getRecentlyPlayed()
        # session['name'] = profile_data['email']
        app.logger.info(f"Its easter: {api.nothing().status_code == 204}")
        hour = datetime.now().hour
        timeOfDay = ""
        if 0 <= hour < 12:
            timeOfDay = "morning"
        elif 12 <= hour < 18:
            timeOfDay = "afternoon"
        elif 18 <= hour < 24:
            timeOfDay = "evening"
        greeting = "Good {0}".format(timeOfDay)

        if valid_token(recently_played):
            return render_template("profile.html",
                                   user=profile_data,
                                   playlists=playlist_data["items"],
                                   recently_played=recently_played["items"],
                                   greeting=greeting,
                                   tracks=recently_played
                                   )
    return render_template('profile.html')


@app.route('/cube')
def cube():
    if 'auth_header' in session and 'refresh_token' in session:
        api = SpotifyAPI()
        api.set_header(session["auth_header"], session["refresh_token"])
        # TODO: replace with whatever we need
        tracks = api.getRecentlyPlayed()
        trackItems = tracks["items"]
        seen = set()
        uniqueTrackItems = []
        for track in trackItems:
            trackID = track["track"]["id"]
            if trackID not in seen:
                uniqueTrackItems.append(track)
                seen.add(trackID)

        profile_data = api.getUser()

        if valid_token(tracks):
            return render_template('cube.html',
                                   tracks=tracks,
                                   trackItems=trackItems,
                                   uniqueTrackItems=uniqueTrackItems,
                                   user=profile_data)
    return render_template('cube.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


def startlocal():
    global storage, auth_client
    # Add objs to Flask's context
    port = 8080
    storage = Storage()
    print(storage.fetch_all_users())
    auth_client = AuthHandler("http://localhost:"+str(port))
    app.run(debug=True, host='localhost', port=port)


def start():
    global storage, auth_client
    # Add objs to Flask's context
    storage = Storage()
    auth_client = AuthHandler(hostname)
    app.run(debug=True, host=hostname.split("//")[1], port=80)


if __name__ == "__main__":
    startlocal()
