# # feasibility_engine.py

# import math
# import numpy as np
# import requests
# from datetime import timedelta
# from sgp4.api import Satrec, jday


# class FeasibilityEngine:

#     MIN_ELEVATION = 20
#     LIGHT_SPEED = 3e8
#     FREQUENCY = 2e14
#     EARTH_RADIUS = 6378.137  # km

#     def evaluate_station(self, gs: dict, request: dict):

#         sat = Satrec.twoline2rv(
#             request["tle_line1"],
#             request["tle_line2"]
#         )

#         start_time = request["start_time"]
#         end_time = request["end_time"]

#         total_bits = 0
#         current_time = start_time

#         cloud_cover = self.get_weather(gs)
#         weather_loss = cloud_cover * 0.2  #Latm​=γatm​×distance

#         while current_time <= end_time:

#             jd, fr = jday(
#                 current_time.year,
#                 current_time.month,
#                 current_time.day,
#                 current_time.hour,
#                 current_time.minute,
#                 current_time.second
#             )

#             e, r, v = sat.sgp4(jd, fr)

#             if e != 0:
#                 current_time += timedelta(seconds=1)
#                 continue

#             elevation, distance = self.compute_elevation_and_range(
#                 np.array(r),
#                 gs,
#                 current_time
#             )

#             if elevation < self.MIN_ELEVATION:
#                 current_time += timedelta(seconds=1)
#                 continue

#             fspl = self.free_space_path_loss(distance * 1000)

#             transmit_power = 40     # PdBm​=10log10​(Pwatts​×1000)
#             tx_gain = 100           # Gt​=(λπD​)2 ,Gt,dB​=10log10​(Gt​)
#             rx_gain = 110           # Gr​=(λπDr​​)2
#             noise_floor = -40       # n​=kTB, Pn​(dBm)=10log10​(kTB)+30

#             received_power = (
#                 transmit_power
#                 + tx_gain
#                 + rx_gain                  ##Pr​=Pt​+Gt​+Gr​−FSPL−Latm​−Lpointing​
#                 - fspl
#                 - weather_loss
#             )                                     

#             snr = received_power - noise_floor    #SNR=Pr​−Pn​

#             rate = self.map_snr_to_rate(snr)

#             total_bits += rate
#             current_time += timedelta(seconds=1)

#         return {
#             "total_bits": total_bits,
#             "total_MB": total_bits / (8 * 1024 * 1024)
#         }

#     # -----------------------------

#     def compute_elevation_and_range(self, sat_eci, gs, time):

#         lat = math.radians(gs["lat"])
#         lon = math.radians(gs["lon"])
#         alt = gs["alt"]

#         theta = self.greenwich_sidereal(time)

#         cos_theta = math.cos(theta)
#         sin_theta = math.sin(theta)

#         sat_ecef = np.array([
#             cos_theta * sat_eci[0] + sin_theta * sat_eci[1],
#             -sin_theta * sat_eci[0] + cos_theta * sat_eci[1],
#             sat_eci[2]
#         ])

#         r = self.EARTH_RADIUS + alt

#         gs_ecef = np.array([
#             r * math.cos(lat) * math.cos(lon),
#             r * math.cos(lat) * math.sin(lon),
#             r * math.sin(lat)
#         ])

#         rho = sat_ecef - gs_ecef
#         distance = np.linalg.norm(rho)

#         up = gs_ecef / np.linalg.norm(gs_ecef)

#         elevation = math.degrees(
#             math.asin(np.dot(rho, up) / distance)
#         )

#         return elevation, distance

#     # -----------------------------

#     def greenwich_sidereal(self, time):

#         jd = (367 * time.year
#               - int((7 * (time.year + int((time.month + 9) / 12))) / 4)
#               + int((275 * time.month) / 9)
#               + time.day + 1721013.5
#               + (time.hour + time.minute / 60 + time.second / 3600) / 24)

#         T = (jd - 2451545.0) / 36525

#         theta = 280.46061837 + 360.98564736629 * (jd - 2451545)

#         return math.radians(theta % 360)

#     # -----------------------------
#     # loss due to the distance FSPL=20log10(4*3.14*distance/lambda)
#     def free_space_path_loss(self, distance_m):
#         wavelength = self.LIGHT_SPEED / self.FREQUENCY
#         return 20 * math.log10((4 * math.pi * distance_m) / wavelength)

#     # -----------------------------

#     def map_snr_to_rate(self, snr):

#         if snr > 20:
#             return 100e9  # 100 Gbps
#         elif snr > 10:
#             return 50e9   # 50 Gbps
#         elif snr > 5:
#             return 10e9   # 10 Gbps
#         else:
#             return 0

#     # -----------------------------

#     def get_weather(self, gs):

#         try:
#             url = (
#                 "https://api.open-meteo.com/v1/forecast"
#                 f"?latitude={gs['lat']}"
#                 f"&longitude={gs['lon']}"
#                 "&hourly=cloudcover"
#                 "&forecast_days=1"
#             )

#             data = requests.get(url, timeout=5).json()
#             return data["hourly"]["cloudcover"][0]

#         except:
#             return 0

# feasibility_engine.py

import math
import numpy as np
import requests
from datetime import timedelta
from sgp4.api import Satrec, jday


class FeasibilityEngine:

    # -----------------------------
    # CONSTANTS
    # -----------------------------
    MIN_ELEVATION = 20                     # degrees
    LIGHT_SPEED = 3e8                      # m/s
    FREQUENCY = 2e14                       # Hz (≈1550nm)
    EARTH_RADIUS = 6378.137                # km
    BOLTZMANN = 1.38e-23                   # J/K
    TEMPERATURE = 290                      # Kelvin

    # ==========================================================
    # MAIN FEASIBILITY FUNCTION
    # ==========================================================
    def evaluate_station(self, gs: dict, request: dict):

        sat = Satrec.twoline2rv(
            request["tle_line1"],
            request["tle_line2"]
        )

        start_time = request["start_time"]
        end_time = request["end_time"]

        total_bits = 0
        current_time = start_time

        # Get weather once per pass
        cloud_cover = self.get_weather(gs)
        weather_loss = cloud_cover * 0.2  # simple atmospheric loss model

        while current_time <= end_time:

            jd, fr = jday(
                current_time.year,
                current_time.month,
                current_time.day,
                current_time.hour,
                current_time.minute,
                current_time.second
            )

            e, r, v = sat.sgp4(jd, fr)

            if e != 0:
                current_time += timedelta(seconds=1)
                continue

            elevation, distance = self.compute_elevation_and_range(
                np.array(r),
                gs,
                current_time
            )

            if elevation < self.MIN_ELEVATION:
                current_time += timedelta(seconds=1)
                continue

            # -----------------------------
            # LINK BUDGET CALCULATION
            # -----------------------------

            fspl = self.free_space_path_loss(distance * 1000)

            # Transmit power from system spec (Watts → dBm)
            transmit_power_watts = 10       # example 10W laser
            transmit_power_dbm = 10 * math.log10(transmit_power_watts * 1000)

            # Aperture diameters (meters)
            tx_diameter = 0.15
            rx_diameter = 0.15

            tx_gain = self.calculate_aperture_gain(tx_diameter, 0.8)
            rx_gain = self.calculate_aperture_gain(rx_diameter, 0.8)

            # Bandwidth (for 100 Gbps system approx)
            bandwidth = 100e9
            noise_floor = self.calculate_noise_floor(bandwidth)

            received_power = (
                transmit_power_dbm
                + tx_gain
                + rx_gain
                - fspl
                - weather_loss
            )

            snr = received_power - noise_floor

            rate = self.map_snr_to_rate(snr)

            total_bits += rate
            current_time += timedelta(seconds=1)

        return {
            "total_bits": total_bits,
            "total_MB": total_bits / (8 * 1024 * 1024)
        }

    # ==========================================================
    # GEOMETRY CALCULATION
    # ==========================================================
    def compute_elevation_and_range(self, sat_eci, gs, time):

        lat = math.radians(gs["lat"])
        lon = math.radians(gs["lon"])
        alt = gs["alt"]

        theta = self.greenwich_sidereal(time)

        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)

        # ECI → ECEF
        sat_ecef = np.array([
            cos_theta * sat_eci[0] + sin_theta * sat_eci[1],
            -sin_theta * sat_eci[0] + cos_theta * sat_eci[1],
            sat_eci[2]
        ])

        r = self.EARTH_RADIUS + alt

        gs_ecef = np.array([
            r * math.cos(lat) * math.cos(lon),
            r * math.cos(lat) * math.sin(lon),
            r * math.sin(lat)
        ])

        rho = sat_ecef - gs_ecef
        distance = np.linalg.norm(rho)

        up = gs_ecef / np.linalg.norm(gs_ecef)

        elevation = math.degrees(
            math.asin(np.dot(rho, up) / distance)
        )

        return elevation, distance

    # ==========================================================
    # SIDEREAL TIME
    # ==========================================================
    def greenwich_sidereal(self, time):

        jd = (367 * time.year
              - int((7 * (time.year + int((time.month + 9) / 12))) / 4)
              + int((275 * time.month) / 9)
              + time.day + 1721013.5
              + (time.hour + time.minute / 60 + time.second / 3600) / 24)

        theta = 280.46061837 + 360.98564736629 * (jd - 2451545)

        return math.radians(theta % 360)

    # ==========================================================
    # FREE SPACE PATH LOSS
    # ==========================================================
    def free_space_path_loss(self, distance_m):

        wavelength = self.LIGHT_SPEED / self.FREQUENCY

        # FSPL = 20log10(4πd/λ)
        return 20 * math.log10((4 * math.pi * distance_m) / wavelength)

    # ==========================================================
    # APERTURE GAIN
    # ==========================================================
    def calculate_aperture_gain(self, diameter_m, efficiency=0.8):

        wavelength = self.LIGHT_SPEED / self.FREQUENCY

        gain_linear = ((math.pi * diameter_m) / wavelength) ** 2
        gain_linear *= efficiency

        return 10 * math.log10(gain_linear)

    # ==========================================================
    # NOISE FLOOR (kTB)
    # ==========================================================
    def calculate_noise_floor(self, bandwidth_hz):

        noise_watts = self.BOLTZMANN * self.TEMPERATURE * bandwidth_hz

        return 10 * math.log10(noise_watts) + 30

    # ==========================================================
    # SNR → RATE MAPPING
    # ==========================================================
    def map_snr_to_rate(self, snr):

        if snr > 20:
            return 100e9  # 100 Gbps
        elif snr > 10:
            return 50e9   
        elif snr > 5:
            return 10e9
        else:
            return 0

    # ==========================================================
    # WEATHER
    # ==========================================================
    def get_weather(self, gs):

        try:
            url = (
                "https://api.open-meteo.com/v1/forecast"
                f"?latitude={gs['lat']}"
                f"&longitude={gs['lon']}"
                "&hourly=cloudcover"
                "&forecast_days=1"
            )

            data = requests.get(url, timeout=5).json()
            return data["hourly"]["cloudcover"][0]

        except:
            return 0

