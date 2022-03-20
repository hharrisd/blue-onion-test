# Blue Onion Labs Take Home Test Response

Response to the code test tasks described in
the [Blue Onion Labs Take Home](https://github.com/BlueOnionLabs/api-spacex-backend) repository.

## Project configuration

The approach selected for this activity was as follows:

- Python as a programming language
- PostgreSQL as database engine
- SQLAlchemy as data abstraction layer
- Flask for data presentation

To configure the project, follow the next steps

- Clone this repository
- Enter the generated directory
- Run the command: `docker-compose up --build` to create the container

```
git clone https://github.com/hharrisd/blue-onion-test.git
cd blue-onion-test
docker-compose up --build
```

A **Mark** model was implemented in SQLAlchemy to represent the entity with the required fields and a primary key (pk) was
added to identify positions that have the same timestamp for a specific satellite.

```python
class Mark(db.Model):
    __tablename__ = 'marks'

    pk = db.Column(db.Integer, primary_key=True)
    id = db.Column(db.String)
    longitude = db.Column(db.Float, default=0.0)
    latitude = db.Column(db.Float, default=0.0)
    creation_date = db.Column(db.TIMESTAMP)

    def __repr__(self):
        return f"Sat: {self.id}, longitude: {self.longitude}, latitude: {self.latitude} creation_date: {self.creation_date}"
```

## The Task (Part 1): Stand up your favorite database

Configuring two services in Docker

- db: which serves a _PostgreSQL_ database and listens on port **5432**.
- pythonapp: which serves a _Flask_ web application and listens on port **3000**.

## The Task (Part 2): Load data from starlink_historical_data.json

This operation is executed requesting this url: [http://localhost:3000/setup](http://localhost:3000/setup)

The approach for this task, is to initialize the database and to execute a bulk insertion of the records in the JSON
file.

The data from the JSON file is loaded and then iterated to get a list of dictionaries with the required fields.

Then, the method `bulk_insert_mappings` is executed to insert the records in the databse in a very efficient way.

It returns the count of inserted records.

```python
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
```

## The Task (Part 3): Fetch the last known position of a satellite (by id), given a time T

This operation is executed requesting this url: `http://localhost:3000/sat/<id>/<t>`, where `id` is a satellite's id
and `t`
is a given time. Ex.:

[http://localhost:3000/sat/lastposition/5eed7714096e590006985647/2020-09-17T01:36:09](http://localhost:3000/sat/lastposition/5eed7714096e590006985647/2020-09-17T01:36:09)

The aproach for this task was receive the required parameters and to query for one result in the databse.

Since there are many satellites with the same id and creation date, the query is ordered by the satellite's id and the
primary key (pk) created, in order to retrieve the last possition recorded.

The resultant query is like this:

```sql
SELECT marks.pk, marks.id, marks.longitude, marks.latitude, marks.creation_date
FROM marks
WHERE marks.id = '5eed7714096e590006985647'
  AND marks.creation_date = '2020-09-17T01:36:09'
ORDER BY marks.creation_date DESC, marks.pk DESC 
LIMIT 1;
```

And the implementation is this:

```python
@app.route('/sat/lastposition/<id>/<t>/', methods=['GET'])
def get_last_know_possition(id, t):
    """"Fetch the the last known position of a satellite (by id), given a time T"""
    try:
        datetime.strptime(t, '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        return Response("Incorrect data format, should be YYYY-MM-DDTHH:MM:SS", 400)

    sat = db.session.query(Mark).filter_by(id=id, creation_date=t)
    .order_by(Mark.creation_date.desc(), Mark.pk.desc())
    .first()


if sat:
    return str(sat)
else:
    return Response("No satellites for the given parameters", 404)
```

## The Task (Part 4): Fetch from the database the closest satellite at a given time T, and a given a position

This operation is executed requesting this url: `http://localhost:3000/sat/closestfrom/<t>/<latitude>/<longitude>`,
where `t` is a given time, and `latitude` and `longitud` are parameters for a given coordinate. Ex.:

[http://localhost:3000/sat/closestfrom/2020-09-17T01:36:09/16.2/7.74](http://localhost:3000/sat/closestfrom/2020-09-17T01:36:09/16.2/7.74)

The approach here was:

1. To get all the satellites that match a given creation date
2. To apply the function `haversine` to every record to obtain the **distance** (in _kilometers_, the default unit) from to
   satellite to the given possition
3. To return the satellite with the **minimum distance** to the given possition

Returning a result like this:

```json
{
  "distance": 1352.6973556164726,
  "sat": "Sat: 5eed7714096e590006985647, longitude: 26.0, latitude: 0.0 creation_date: 2020-09-17 01:36:09"
}
```

And the implementation is this:

```python
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
```