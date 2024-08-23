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

# Configure CS50 Library to use PostgreSQL database
db = SQL("postgresql://default:PDpm84UZXVKd@ep-spring-wildflower-a1xtzkme.ap-southeast-1.aws.neon.tech:5432/verceldb?sslmode=require")

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
        """
        SELECT symbol, name, SUM(shares) AS total_shares
        FROM trades
        WHERE username = ?
        GROUP BY symbol, name
        HAVING SUM(shares) > 0
        """,
        session["user_id"]
    )

    user_cash_row = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
    user_cash = user_cash_row[0]["cash"] if user_cash_row else 0
    current_worth = 0

    for stock in user_portfolio:
        print(f"Processing stock: {stock}")  # Debug print
        stock_data = lookup(stock["symbol"])
        if stock_data:
            print(f"Stock data: {stock_data}")  # Debug print
            stock["currentprice"] = stock_data["price"]
            stock["totalprice"] = stock_data["price"] * stock["total_shares"]
            current_worth += stock["totalprice"]
        else:
            print(f"No data found for symbol: {stock['symbol']}")  # Debug print
            stock["currentprice"] = 0
            stock["totalprice"] = 0

    return render_template("index.html", user_cash=user_cash, user_portfolio=user_portfolio, current_worth=current_worth)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
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
        user_cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

        if user_cash[0]["cash"] < buy_cost:
            return apology("CANNOT AFFORD STOCK!", 400)
        else:
            # Insert without 'type', assuming a trigger is handling it
            db.execute("INSERT INTO trades (username, symbol, name, shares, price) VALUES (?, ?, ?, ?, ?);",
                       session["user_id"], stock_quote['symbol'], stock_quote["name"], int(shares), stock_quote['price'])
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
    trades = db.execute("SELECT * FROM trades WHERE username = ?", session["user_id"])

    return render_template("history.html", trades=trades)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 400)

        elif not request.form.get("password"):
            return apology("must provide password", 400)

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 400)

        session["user_id"] = rows[0]["id"]
        user_login = rows[0]["username"]
        print(f"User login: {user_login}")
        return redirect("/")

    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
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
    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 400)

        elif not request.form.get("password"):
            return apology("must provide password", 400)

        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("password and confirm password must be same", 400)

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        if len(rows) == 1:
            return apology("username already exists", 400)
        else:
            hash_password = generate_password_hash(request.form.get("password"), method='pbkdf2', salt_length=16)
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)",
                       request.form.get("username"), hash_password)
        return redirect("/")

    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        if symbol == "":
            return apology("MISSING SYMBOL", 400)
        if shares == "" or shares.isalpha():
            return apology("MISSING SHARES", 400)
        if int(shares) <= 0:
            return apology("share number can't be negative number or zero!", 400)

        stock_quote = lookup(symbol)
        if not stock_quote:
            return apology("INVALID SYMBOL", 400)

        user_cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        user_portfolio = db.execute(
            """
            SELECT symbol, SUM(shares) AS total_shares
            FROM trades
            WHERE username = ? AND symbol = ?
            GROUP BY symbol
            HAVING SUM(shares) > 0
            """,
            session["user_id"], stock_quote['symbol']
        )

        if len(user_portfolio) == 0 or user_portfolio[0]["total_shares"] < int(shares):
            return apology("TOO MANY SHARES", 400)
        else:
            sell_cost = float(shares) * stock_quote["price"]
            db.execute("INSERT INTO trades (username, name, symbol, shares, price) VALUES (?, ?, ?, ?, ?)",
                       session["user_id"], stock_quote["name"], stock_quote['symbol'], -int(shares), stock_quote['price'])
            cash = user_cash[0]["cash"]
            db.execute("UPDATE users SET cash = ? WHERE id = ?",
                       cash + sell_cost, session["user_id"])
            flash('Sold!')
            return redirect("/")

    else:
        user_portfolio = db.execute(
            """
            SELECT symbol, SUM(shares) AS total_shares
            FROM trades
            WHERE username = ?
            GROUP BY symbol
            HAVING SUM(shares) > 0
            ORDER BY symbol
            """,
            session["user_id"]
        )

        return render_template("sell.html", user_portfolio=user_portfolio)

@app.route("/pwdchange", methods=["GET", "POST"])
@login_required
def pwdchange():
    if request.method == "POST":
        current_pwd = request.form.get("current_pwd")
        new_pwd = request.form.get("new_pwd")
        conf_pwd = request.form.get("conf_pwd")

        if current_pwd == "" or conf_pwd == "" or new_pwd == "":
            return apology("MISSING PASSWORD", 400)

        rows = db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])
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
        rows = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
        return render_template("passwordupdate.html", username=rows[0]["username"])

@app.route("/addcash", methods=["GET", "POST"])
@login_required
def addcash():
    if request.method == "POST":
        addcash = request.form.get("addcash")

        if addcash == "" or addcash.isalpha():
            return apology("CASH MUST NOT BE EMPTY", 400)
        if int(addcash) <= 0:
            return apology("Cash to be added can't be negative number or zero!", 400)

        rows = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        cash = rows[0]["cash"] + int(addcash)
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"])
        flash('Cash Added!')
        return redirect("/")

    else:
        rows = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        return render_template("addcash.html", cash=rows[0]["cash"])

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)
