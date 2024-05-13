import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, is_int

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# def is_int(x):
#     x=abs(x)
#     if (ceil(x)<=x or type(x)==int):
#         return True
#     else:
#         return False


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    user_portfolio = db.execute(
        "SELECT username, symbol, name, TRANSACTION_ID, SUM(shares)  FROM trades WHERE username = ? GROUP BY symbol HAVING SUM(shares) > 0 ORDER BY price DESC", session["user_id"])

    user_cash = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    current_worth = 0
    for stock in user_portfolio:
        stock_data = lookup(stock["symbol"])
        stock["currentprice"] = stock_data["price"]
        stock["totalprice"] = stock_data["price"] * stock["SUM(shares)"]
        current_worth += stock["totalprice"]

    return render_template("index.html", user_cash=user_cash, user_portfolio=user_portfolio, current_worth=current_worth)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure symbol was submitted
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        if symbol == "":
            return apology("must provide symbol", 400)
        if shares == "" or shares.isalpha():
            return apology("MISSING SHARES", 400)
        if not is_int(shares):
            return apology("fractional not supported", 400)
        if int(shares) <= 0:
            return apology("share number can't be negative number or zero!", 400)

        stock_quote = lookup(symbol)

        if not stock_quote:
            return apology("invalid symbol", 400)

        buy_cost = int(shares) * stock_quote["price"]
        user_cash = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])

        if user_cash[0]["cash"] < buy_cost:
            return apology("CANNOT AFFORD STOCK!", 400)
        else:
            db.execute("INSERT INTO trades (username, name, symbol, shares, price) VALUES(?, ?, ?, ?, ?)",
                       session["user_id"], stock_quote["name"], stock_quote['symbol'], int(shares), stock_quote['price'])
            cash = user_cash[0]["cash"]
            db.execute("UPDATE users SET cash = ? WHERE id = ?",
                       cash - buy_cost, session["user_id"])
            flash('Bought!')
            return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    # Get all trades
    trades = db.execute("SELECT * FROM trades WHERE username = ?", session["user_id"])

    return render_template("history.html", trades=trades)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )
        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if symbol == "":
            return apology("must provide symbol", 400)

        stock_quote = lookup(symbol)

        if not stock_quote:
            return apology("invalid symbol", 400)
        else:
            return render_template("quoted.html", stock_quote=stock_quote)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure password was matched with confirm password
        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("password and confirm password must be same", 400)

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        if len(rows) == 1:
            return apology("username already exist", 400)
        else:
            hash_password = generate_password_hash(
                request.form.get("password"), method='pbkdf2', salt_length=16)
            # Query database for username
            db.execute("INSERT INTO users (username, hash) VALUES (?,?)",
                       request.form.get("username"), hash_password)

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        # Ensure symbol is not blank
        if symbol == "":
            return apology("MISSING SYMBOL", 400)
        if shares == "" or shares.isalpha():
            return apology("MISSING SHARES", 400)
        if int(shares) <= 0:
            return apology("share number can't be negative number or zero!", 400)
        stock_quote = lookup(symbol)
        if not stock_quote:
            return apology("INVALID SYMBOL", 400)

        user_cash = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        user_portfolio = db.execute(
            "SELECT username, name, symbol, SUM(shares) FROM trades WHERE username = ? AND symbol = ? GROUP BY symbol HAVING SUM(shares)>0 ", session["user_id"], stock_quote['symbol'])

        if user_portfolio[0]["SUM(shares)"] < int(shares):
            return apology("TOO MANY SHARES", 400)
        else:
            sell_cost = float(shares) * stock_quote["price"]
            db.execute("INSERT INTO trades (username, name, symbol, shares, price) VALUES(?, ?, ?, ?, ?)",
                       session["user_id"], stock_quote["name"], stock_quote['symbol'], -int(shares), stock_quote['price'])
            cash = user_cash[0]["cash"]
            db.execute("UPDATE users SET cash = ? WHERE id = ?",
                       cash + sell_cost, session["user_id"])
            flash('Sold!')
            return redirect("/")

    else:
        user_portfolio = db.execute(
            "SELECT username, name, symbol, SUM(shares) FROM trades WHERE username = ? GROUP BY symbol HAVING SUM(shares)>0 ORDER BY symbol", session["user_id"])

        return render_template("sell.html", user_portfolio=user_portfolio)


@app.route("/pwdchange", methods=["GET", "POST"])
@login_required
def pwdchange():
    if request.method == "POST":
        # Ensure symbol was submitted
        current_pwd = request.form.get("current_pwd")
        new_pwd = request.form.get("new_pwd")
        conf_pwd = request.form.get("conf_pwd")

        if current_pwd == "" or conf_pwd == "" or new_pwd == "":
            return apology("MISSING PASSWORD", 400)

        rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        hash = generate_password_hash(new_pwd, method='pbkdf2', salt_length=16)
        if new_pwd != conf_pwd:
            return apology("PASSWORDS DO NOT MATCH", 400)

        if not check_password_hash(rows[0]["hash"], current_pwd):
            return apology("INVALID PASSWORD", 400)

        else:
            db.execute("UPDATE users SET hash = ? WHERE id = ?", hash, session["user_id"])
            flash('Password Changed!')
            return redirect("/")

    else:
        rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        return render_template("passwordupdate.html", username=rows[0]["username"])



@app.route("/addcash", methods=["GET", "POST"])
@login_required
def addcash():
    if request.method == "POST":
        # Ensure symbol was submitted
        addcash = request.form.get("addcash")

        if addcash == "" or addcash.isalpha():
            return apology("CASH MUST NOT BE EMPTY", 400)
        if int(addcash) <= 0:
            return apology("Cash to be added can't be negative number or zero!", 400)

        rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        cash = rows[0]["cash"] + int(addcash)
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"])
        flash('Cash Added!')
        return redirect("/")

    else:
        rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        return render_template("addcash.html", username=rows[0]["cash"])

