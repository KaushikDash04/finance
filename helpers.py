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
    """Look up quote for symbol."""

    # Prepare API request
    # end = datetime.datetime.now(pytz.timezone("US/Eastern"))
    # start = end - datetime.timedelta(days=7)

    # # Yahoo Finance API
    # url = (
    #     f"https://query1.finance.yahoo.com/v7/finance/download/{urllib.parse.quote_plus(symbol)}"
    #     f"?period1={int(start.timestamp())}"
    #     f"&period2={int(end.timestamp())}"
    #     f"&interval=1d&events=history&includeAdjustedClose=true"
    # )

    # IEX Cloud API
    API_KEY = "pk_8a1e00f58d2944afab09e21eba2c54c4"
    url = (
        f"https://api.iex.cloud/v1/data/core/quote/"
        f"{urllib.parse.quote_plus(symbol)}"
        f"?token={API_KEY}"
    )

    # Query API
    try:
        response = requests.get(
            url,
            cookies={"session": str(uuid.uuid4())}
            # headers={"Accept": "*/*", "User-Agent": request.headers.get("User-Agent")},
        )
        response.raise_for_status()
        # Parse response
        quotes = response.json()
        # CSV header: Date,Open,High,Low,Close,Adj Close,Volume
        latestPrice = round(float(quotes[0]["latestPrice"]), 2)
        companyName = quotes[0]["companyName"]
        return {"price": latestPrice, "symbol": quotes[0]["symbol"], "name" : companyName}
    except (KeyError, IndexError, requests.RequestException, ValueError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"

def is_int(s):
    """ check if the input is an integer """
    try:
        int(s)
        return True
    except ValueError:
        return False
