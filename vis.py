import shutil
import requests
from typing import List

import numpy as np

from spoticolor.colorz import open_malloc_img, colorz, hexify
import plotly.graph_objects as go
import plotly


def radar_json(featJSON, col)->str:
    """
    Generates a radar plot per track.
    """
    categories = ["acousticness",
                  "danceability",
                  "instrumentalness",
                  "liveness",
                  "speechiness",
                  "valence"]

    featJSON = featJSON['audio_features'][0]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolargl(
        r=np.asarray(
            [ featJSON[field] for field in categories]
        ) * 4.0 + 1.0,
        theta=[cat[0].capitalize() for cat in categories],
        fill='toself',
        mode='lines',
        line={"color": col},
        textfont={"size": 60}
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                showticklabels=False,
                range=[0, 5]
            )),
        margin=dict(l=20, r=20, t=20, b=20)
    )

    plot_as_string = plotly.io.to_html(fig, include_plotlyjs=False, default_height="200px", default_width="200px")

    return plot_as_string


def gen_durr_arrays(analJSON):
    """
    Extract sequential duration from audio analysis.
    """

    fields = ["sections",
              "bars",
              "beats",
              "segments",
              "tatums" ]


    cap = analJSON[fields[0]][-1]["start"] + analJSON[fields[0]][-1]["duration"]
    result = { fl : [ {"start": obj["start"]/cap,
                       "duration": obj["duration"]/cap}
                      for obj in analJSON[fl] ]
              for fl in fields}

    return result


def download_img(url: str) -> str:
    try:
        response = requests.get(url, stream=True)
        fname = "/tmp/spc-img-%s.png" % (url.rsplit('/', 1)[-1])
        with open(fname, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
            del response
        return fname
    except Exception:
        return None


def generate_colors(imageurl:str =None)->List[str]:
    """
    Generate 16 colors with pywal.
    Return default scheme if None provided
    """

    imgalloc = download_img(imageurl)
    if imgalloc is None:
        return ['rgba(30,215,96, 0.9)',
                'rgba(245,115,160, 0.9)',
                'rgba(80,155,245, 0.9)',
                'rgba(255,100,55, 0.9)',
                'rgba(180,155,200, 0.9)',
                'rgba(250,230,45, 0.9)',
                'rgba(0,100,80, 0.9)',
                'rgba(175,40,150, 0.9)',
                'rgba(30,50,100, 0.9)']

    colors = colorz(imgalloc,
                    8)

    hexc = [ hexify( col[0] ) for col in colors]

    return hexc


def gen_chroma(analJSON: str) -> List[float]:
    """
    Generate average normalized chroma vector for the whole song.
    """
    chroma = np.asarray([np.asarray(seg["pitches"]) for seg in analJSON["segments"]])
    avgchroma = chroma.sum(axis=0)
    normchroma = avgchroma / avgchroma.max()
    print(normchroma)

    return list(normchroma)
