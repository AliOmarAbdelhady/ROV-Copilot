from __future__ import annotations

from flask import Flask, render_template, request
from markupsafe import Markup

from threat_logic import assess_mission, generate_track_svg, parse_coordinate, parse_heading, parse_keel_depth


app = Flask(__name__)

DEFAULT_FORM = {
    "latitude": "47o39’00” North",
    "longitude": "48o37’00” West",
    "heading": "158o",
    "keel_depth": "99 meters",
}


@app.route("/", methods=["GET", "POST"])
def index():
    form = DEFAULT_FORM.copy()
    result = None
    error = None

    if request.method == "POST":
        form = {
            "latitude": request.form.get("latitude", ""),
            "longitude": request.form.get("longitude", ""),
            "heading": request.form.get("heading", ""),
            "keel_depth": request.form.get("keel_depth", ""),
        }
        try:
            latitude = parse_coordinate(form["latitude"], "latitude")
            longitude = parse_coordinate(form["longitude"], "longitude")
            heading = parse_heading(form["heading"])
            keel_depth = parse_keel_depth(form["keel_depth"])
            assessments = assess_mission(latitude, longitude, heading, keel_depth)
            result = {
                "latitude": latitude,
                "longitude": longitude,
                "heading": heading,
                "keel_depth": keel_depth,
                "assessments": assessments,
                "graph_svg": Markup(generate_track_svg(latitude, longitude, heading, assessments)),
            }
        except ValueError as exc:
            error = str(exc)

    return render_template("index.html", form=form, result=result, error=error)


if __name__ == "__main__":
    app.run(debug=True)
