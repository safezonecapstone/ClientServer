from flask import request, jsonify
from server.utils import closest_stations
from server.models import db
from os import getenv
from requests import get

def route():
    def directions(origin_coord, dest_coord) -> str:
        origin     : str = 'origin={},{}'.format( origin_coord['latitude'], origin_coord['longitude'] )
        destination: str = 'destination={},{}'.format( dest_coord['latitude'], dest_coord['longitude'] )
        parameters : str = '{}&{}&key={}'.format( origin, destination, getenv('G_API_KEY') )
        url        : str = 'https://maps.googleapis.com/maps/api/directions/json?{}&mode=transit&transit_mode=subway&alternatives=true'.format(parameters)
        return url
    
    origin = {
        'latitude' : request.args.get('origin_latitude'),
        'longitude': request.args.get('origin_longitude')
    }

    destination = {
        'latitude' : request.args.get('dest_latitude'),
        'longitude': request.args.get('dest_longitude')
    }

    gmap_request = get( directions(origin, destination) )

    if gmap_request.status_code != 200: return 0, 400

    data = gmap_request.json()

    steps_rating = lambda dest, arrive: ( closest_stations(db, dest['location']['lat'], dest['location']['lng'])[0]['percentile'] + 
        closest_stations(db, arrive['location']['lat'], arrive['location']['lng'])[0]['percentile'] ) / 2

    routes = []

    for route in data['routes']:
        for leg in route['legs']:
            rating, count, lines = 0, 0, []
            for step in leg['steps']:
                if step['travel_mode'] == 'TRANSIT':
                    if step['transit_details']['line']['vehicle']['type'] == 'SUBWAY':
                        details = step['transit_details']
                        departure_stop, arrival_stop = details['departure_stop'], details['arrival_stop']
                        rating, count = rating + steps_rating(departure_stop, arrival_stop), count + 1
                        lines.append(
                            { 
                                'line': step['transit_details']['line']['short_name'], 
                                'direction': 'Towards {}'.format(step['transit_details']['headsign'])
                            }
                        )
            routes.append({
                'rating': round( rating / count, 2 ) if count != 0 else 0,
                'leg': leg,
                'lines': lines
            })

    routes.sort(key=lambda x: x['rating'], reverse=True)
    # Output directions from origin -> destination
    return jsonify( routes )
