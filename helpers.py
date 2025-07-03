import csv
import datetime
import pytz
import requests
import urllib
import uuid

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

def lookup(symbol):
    """Look up quote for symbol using Twelve Data API in INR."""

    symbol = symbol.upper()
    API_KEY = '69a1b2d94ccc448483e043654f271e9d'  # Replace this with your actual key

    # For NSE or BSE Indian stocks, use full name
    if not symbol.endswith(".NSE") and not symbol.endswith(".BSE"):
        symbol += ".NSE"  # default to NSE if Indian

    url = f"https://api.twelvedata.com/quote?symbol={urllib.parse.quote_plus(symbol)}&apikey={API_KEY}"

    try:
        response = requests.get(
            url,
            cookies={"session": str(uuid.uuid4())},
            headers={"Accept": "*/*", "User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()
        data = response.json()

        if "close" not in data or "name" not in data:
            return None

        price = round(float(data["close"]), 2)
        name = data["name"]

        return {"price": price, "symbol": symbol, "name": name}
    except (KeyError, IndexError, requests.RequestException, ValueError):
        return None



def inr(value):
    """Format value as INR."""
    return f"₹{value:,.2f}"

def is_int(s):
    """ check if the input is an integer """
    try:
        int(s)
        return True
    except ValueError:
        return False
