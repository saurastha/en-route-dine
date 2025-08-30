import requests


def get_user_location():
    try:
        res = requests.get("https://ipinfo.io")
        data = res.json()
        loc = data.get("loc")
        if loc:
            lat, lon = loc.split(",")
            return float(lat), float(lon)
        return None
    except Exception as e:
        print("Error:", e)
        return ()
