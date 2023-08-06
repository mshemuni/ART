from datetime import timedelta, datetime

from astroplan import Observer
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy import units
from astropy.time import Time as aTime
from .tm import Time


class Object:
    def __init__(self, ra: float = None, dec: float = None):
        self.ra = ra
        self.dec = dec

        self.sky = SkyCoord(ra=self.ra, dec=self.dec, unit=(units.hourangle, units.deg))

    @classmethod
    def from_name(cls, name: str):
        coords = SkyCoord.from_name(name)
        return cls(coords.ra.hour, coords.dec.degree)

    def eq2hor(self, dt: Time, longitude: float, latitude: float, altitude: float):
        site = EarthLocation(longitude * units.deg, latitude * units.deg, altitude * units.m)

        frame = AltAz(obstime=dt.dt, location=site)
        altaz = self.sky.transform_to(frame)
        return {
            "alt": altaz.alt.degree,
            "az": altaz.az.degree
        }

    def visibility(self, dt: Time, longitude: float, latitude: float, altitude: float):
        site = EarthLocation(longitude * units.deg, latitude * units.deg, altitude * units.m)
        # t = dt.dt.to_datetime()
        t = datetime.combine(dt.dt.to_datetime(), datetime.min.time())
        one_day = aTime([t + timedelta(hours=d / 2 + 12) for d in range(48)])
        frame = AltAz(obstime=one_day, location=site)

        obj_alt_az = self.sky.transform_to(frame)
        obj_alt = obj_alt_az.alt.degree.tolist()
        return one_day.to_datetime(), obj_alt

    def rise_set(self, dt: Time, longitude: float, latitude: float, altitude: float):
        site = EarthLocation(longitude * units.deg, latitude * units.deg, altitude * units.m)
        obs = Observer(site)
        return {
            "rise": obs.target_set_time(dt.dt, self.sky).strftime("%H:%M:%S"),
            "set": obs.target_rise_time(dt.dt, self.sky).strftime("%H:%M:%S")
        }
