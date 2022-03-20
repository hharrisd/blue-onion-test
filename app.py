import json
import os
from datetime import datetime

from flask import Flask, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from haversine import haversine

app = Flask(__name__)

if __name__ == '__main__':
    app.run(debug=True)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
db = SQLAlchemy(app)


class Mark(db.Model):
    __tablename__ = 'marks'

    pk = db.Column(db.Integer, primary_key=True)
    id = db.Column(db.String)
    longitude = db.Column(db.Float, default=0.0)
    latitude = db.Column(db.Float, default=0.0)
    creation_date = db.Column(db.TIMESTAMP)

    def __repr__(self):
        return f"Sat: {self.id}, longitude: {self.longitude}, latitude: {self.latitude} creation_date: {self.creation_date}"


@app.route('/setup', methods=['GET'])
def setup_db():
    db.drop_all()
    db.create_all()

    with open("starlink_historical_data.json", "r") as f:
        data = json.load(f)

    marks = []
    for record in data:
        marks.append(dict(
            id=record['id'],
            longitude=record['longitude'],
            latitude=record['latitude'],
            creation_date=record['spaceTrack']['CREATION_DATE']
        ))

    db.session.bulk_insert_mappings(Mark, marks)
    db.session.commit()

    count = db.session.query(Mark.id).count()

    return jsonify(f"Database initialized. {count} records loaded.")


@app.route('/sat/lastposition/<id>/<t>/', methods=['GET'])
def get_last_know_possition(id, t):
    """"Fetch the the last known position of a satellite (by id), given a time T"""
    try:
        datetime.strptime(t, '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        return Response("Incorrect data format, should be YYYY-MM-DDTHH:MM:SS", 400)

    sat = db.session.query(Mark).filter_by(id=id, creation_date=t) \
        .order_by(Mark.creation_date.desc(), Mark.pk.desc()) \
        .first()

    if sat:
        return str(sat)
    else:
        return Response("No satellites for the given parameters", 404)


@app.route('/sat/closestfrom/<t>/<latitude>/<longitude>', methods=['GET'])
def get_closest_satellite(t, latitude, longitude):
    """"Fetch from the database the closest satellite at a given time T, and a given a position on a globe as a
        (latitude, longitude) coordinate.
    """
    try:
        datetime.strptime(t, '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        return Response("Incorrect data format, should be YYYY-MM-DDTHH:MM:SS", 400)

    position = (float(latitude), float(longitude))

    marks_in_given_time = db.session.query(Mark).filter_by(creation_date=t).all()

    if marks_in_given_time:
        distances = [
            {'sat': str(mark), 'distance': haversine(position, (mark.longitude, mark.latitude))}
            for mark in marks_in_given_time
        ]

        return jsonify(min(distances, key=lambda x: x['distance']))

    else:
        return Response("No satellites for the given parameters", 404)
