import math

import requests


class Weather:
    def __init__(self):
        self.apikey = "71a299a755a1d0b5b5ed8a483ed22e82"

    def get(self, longitude: float, latitude: float):
        r = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&units=metric&appid={self.apikey}"
        )
        if r.ok:
            data = r.json()
            description = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            pressure = data["main"]["pressure"]
            humidity = data["main"]["humidity"]
            wind = data["wind"]
            # see: DOĞU ANADOLU GÖZLEMEVİ (DAG) YERLEŞKESİNİN
            # BULUT SENSÖRÜ İLE BULUTLULUK VE ATMOSFERİK 740674
            dew = round(math.sqrt(humidity / 100) * (112 + 0.9 * temp) + 0.1 * temp - 112, 2)
            return {
                "description": description,
                "temp": temp,
                "dew": dew,
                "pressure": pressure,
                "humidity": humidity,
                "wind": wind
            }
