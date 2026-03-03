# selection_engine.py

from pass_window_engine import PassWindowEngine
from feasibility_engine import FeasibilityEngine


class SelectionEngine:

    def __init__(self):
        self.pass_engine = PassWindowEngine()
        self.feasibility_engine = FeasibilityEngine()

    def run_selection(self, stations, request):

        final_results = []

        for gs in stations:

            # STEP 1: VISIBILITY
            passes = self.pass_engine.compute_passes(
                request["tle_line1"],
                request["tle_line2"],
                gs["location"]["lat"],
                gs["location"]["lon"],
                gs["location"]["alt_m"],
                request["start_time"],
                request["end_time"],
                request.get("min_elevation_deg", 20)
            )
            # print("passes",passes)
            if not passes:
                continue

            # STEP 2: INTEROP
            if request["required_standard"] not in gs["capabilities"]["standards"]:
                continue

            if request["required_wavelength_nm"] not in gs["capabilities"]["wavelength_nm"]:
                continue

            # STEP 3: OPS
            if gs["ops"]["health_state"] != "OPERATIONAL":
                continue
            print("###################################################",gs)
            # STEP 4: LINK EVAL
            for p in passes:

                result = self.feasibility_engine.evaluate_station(
                    {
                        "gs_id": gs["id"],
                        "lat": gs["location"]["lat"],
                        "lon": gs["location"]["lon"],
                        "alt": gs["location"]["alt_m"] / 1000
                    },
                    {
                        "tle_line1": request["tle_line1"],
                        "tle_line2": request["tle_line2"],
                        "start_time": p["rise_time"],
                        "end_time": p["set_time"]
                    }
                )
                print("fesable ground station",p)
                final_results.append({
                    "gs_id": gs["id"],
                    "pass_start": p["rise_time"],
                    "pass_end": p["set_time"],
                    "max_elevation": p["max_elevation_deg"],
                    "total_MB": result["total_MB"]
                })

        final_results.sort(key=lambda x: x["total_MB"], reverse=True)
        return final_results
