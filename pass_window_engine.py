

from datetime import datetime
from skyfield.api import load, EarthSatellite, wgs84


class PassWindowEngine:
    """
    Computes satellite pass windows over a ground station.
    """

    def __init__(self):
        self.ts = load.timescale() # initilize the time 

    def compute_passes(
        self,
        tle_line1: str,
        tle_line2: str,
        gs_lat: float,
        gs_lon: float,
        gs_alt_m: float,
        start_time: datetime,
        end_time: datetime,
        min_elevation: float = 20
    ):

        satellite = EarthSatellite(tle_line1, tle_line2, "SAT", self.ts)# satellite object initilization
        ground_station = wgs84.latlon(gs_lat, gs_lon, elevation_m=gs_alt_m)# to make the value into precicse earth location

        # converts python time to skyfied time UTC
        t0 = self.ts.utc(
            start_time.year, start_time.month, start_time.day,
            start_time.hour, start_time.minute, start_time.second
        )
        t1 = self.ts.utc(
            end_time.year, end_time.month, end_time.day,
            end_time.hour, end_time.minute, end_time.second
        )
        times, events = satellite.find_events(
            ground_station,
            t0,
            t1,
            altitude_degrees=min_elevation
        )

        passes = []
        current_pass = {}

        for t, event in zip(times, events):

            utc_time = t.utc_datetime()

            if event == 0:  # Rise
                current_pass = {
                    "rise_time": utc_time
                }

            elif event == 1:  # Max elevation
                if current_pass:
                    difference = satellite - ground_station
                    topocentric = difference.at(t)
                    alt, az, distance = topocentric.altaz()

                    current_pass["max_time"] = utc_time
                    current_pass["max_elevation_deg"] = alt.degrees

            elif event == 2:
                current_pass["set_time"] = utc_time
                current_pass["duration_seconds"] = (
                    current_pass["set_time"] -
                    current_pass["rise_time"]
                ).total_seconds()

                passes.append(current_pass)


        return passes

