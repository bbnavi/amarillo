import json
from typing import Dict
from app.models.Carpool import Carpool
from app.services.trips import TripStore


class CarpoolService():

    def __init__(self, trip_store):
        self.trip_store = trip_store
        self.carpools: Dict[str, Carpool] = {}

    def get(self, agency_id: str, carpool_id: str):
        return self.carpools.get(f"{agency_id}:{carpool_id}")

    def get_all_ids(self):
        return list(self.carpools)

    def put(self, agency_id: str, carpool_id: str, carpool):
        self.carpools[f"{agency_id}:{carpool_id}"] = carpool
        self.trip_store.put_carpool(carpool)

    def delete(self, agency_id: str, carpool_id: str):
        id = f"{agency_id}:{carpool_id}"
        if id in self.carpools:
            del self.carpools[id]
        self.trip_store.delete_carpool(agency_id, carpool_id)
