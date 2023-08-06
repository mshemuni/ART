from astropy.time import Time as aTime
from astropy.coordinates import EarthLocation
from astropy import units
from astroplan import Observer
import dateutil.parser
from _datetime import datetime


def auto_parse(dt: str):
    return dateutil.parser.parse(dt).strftime("%Y-%m-%dT%H:%M:%S.%f")


def now():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")


class Time:
    def __init__(self, dt: str, scale: str = "utc", format: str = "isot") -> None:
        self.dt = aTime(dt, scale=scale, format=format)

    def jd(self):
        return {
            "jd": self.dt.jd,
            "mjd": self.dt.mjd
        }

    def sidereal(self, longitude: float):
        return self.dt.sidereal_time("mean", longitude * units.deg).to_string(sep=":")

    def twilight(self, longitude: float, latitude: float, altitude: float):
        site = EarthLocation(longitude * units.deg, latitude * units.deg, altitude * units.m)
        obs = Observer(site)
        return {
            "morning": obs.twilight_morning_astronomical(
                self.dt, which="nearest").strftime("%H:%M:%S"),
            "evening": obs.twilight_evening_astronomical(
                self.dt, which="nearest").strftime("%H:%M:%S")
        }

    def moon(self, longitude: float, latitude: float, altitude: float):
        site = EarthLocation(longitude * units.deg, latitude * units.deg, altitude * units.m)
        obs = Observer(site)

        return {
            "rise": obs.moon_rise_time(self.dt, which="nearest").strftime("%H:%M:%S"),
            "set": obs.moon_set_time(self.dt, which="nearest").strftime("%H:%M:%S"),
            "phase": round(obs.moon_illumination(self.dt), 4)
        }
