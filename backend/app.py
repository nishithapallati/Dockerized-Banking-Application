import os
from decimal import Decimal

from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from database import db
from models import User, Account, Transaction


app = Flask(__name__)


# ---------------- DATABASE CONFIGURATION ----------------

DB_USER = os.getenv("MYSQL_USER", "root")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "root123")
DB_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
DB_PORT = os.getenv("MYSQL_PORT", "3306")
DB_NAME = os.getenv("MYSQL_DATABASE", "banking_db")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# ---------------- SECRET KEY ----------------

app.secret_key = os.getenv(
    "SECRET_KEY",
    "banking-secret-key"
)


# ---------------- INITIALIZE DATABASE ----------------

db.init_app(app)


# ---------------- HOME ----------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):

            session["user_id"] = user.id
            session["user_name"] = user.name

            return redirect(url_for("dashboard"))

        return "Invalid email or password"

    return render_template("login.html")


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # Check password confirmation
        if password != confirm_password:
            return "Passwords do not match"

        # Check existing email
        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:
            return "Email already registered"

        # Hash password
        hashed_password = generate_password_hash(password)

        # Create user
        new_user = User(
            name=name,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        # Create bank account
        account_number = "100000" + str(new_user.id)

        new_account = Account(
            user_id=new_user.id,
            account_number=account_number,
            balance=0.00
        )

        db.session.add(new_account)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    # Get user's account
    account = Account.query.filter_by(
        user_id=session["user_id"]
    ).first()

    # Get user's transactions
    transactions = Transaction.query.filter_by(
        user_id=session["user_id"]
    ).order_by(
        Transaction.created_at.desc()
    ).all()

    return render_template(
        "dashboard.html",
        account=account,
        transactions=transactions
    )


# ---------------- DEPOSIT ----------------

@app.route("/deposit", methods=["POST"])
def deposit():

    if "user_id" not in session:
        return redirect(url_for("login"))

    amount_text = request.form["amount"]

    try:
        amount = Decimal(amount_text)
    except:
        return "Invalid deposit amount"

    if amount <= 0:
        return "Deposit amount must be greater than zero"

    account = Account.query.filter_by(
        user_id=session["user_id"]
    ).first()

    if account is None:
        return "Bank account not found"

    account.balance += amount

    transaction = Transaction(
        user_id=session["user_id"],
        type="DEPOSIT",
        amount=amount,
        description="Money deposited into account"
    )

    db.session.add(transaction)
    db.session.commit()

    return redirect(url_for("dashboard"))


# ---------------- WITHDRAW ----------------

@app.route("/withdraw", methods=["POST"])
def withdraw():

    if "user_id" not in session:
        return redirect(url_for("login"))

    amount_text = request.form["amount"]

    try:
        amount = Decimal(amount_text)
    except:
        return "Invalid withdrawal amount"

    if amount <= 0:
        return "Withdrawal amount must be greater than zero"

    account = Account.query.filter_by(
        user_id=session["user_id"]
    ).first()

    if account is None:
        return "Bank account not found"

    if account.balance < amount:
        return "Insufficient balance"

    account.balance -= amount

    transaction = Transaction(
        user_id=session["user_id"],
        type="WITHDRAW",
        amount=amount,
        description="Money withdrawn from account"
    )

    db.session.add(transaction)
    db.session.commit()

    return redirect(url_for("dashboard"))


# ---------------- TRANSFER ----------------

@app.route("/transfer", methods=["POST"])
def transfer():

    if "user_id" not in session:
        return redirect(url_for("login"))

    receiver_account_number = request.form["receiver_account"]
    amount_text = request.form["amount"]

    try:
        amount = Decimal(amount_text)
    except:
        return "Invalid transfer amount"

    if amount <= 0:
        return "Transfer amount must be greater than zero"

    # Sender account
    sender_account = Account.query.filter_by(
        user_id=session["user_id"]
    ).first()

    if sender_account is None:
        return "Sender account not found"

    # Receiver account
    receiver_account = Account.query.filter_by(
        account_number=receiver_account_number
    ).first()

    if receiver_account is None:
        return "Receiver account not found"

    # Prevent self-transfer
    if sender_account.id == receiver_account.id:
        return "You cannot transfer money to your own account"

    # Check balance
    if sender_account.balance < amount:
        return "Insufficient balance"

    # Deduct from sender
    sender_account.balance -= amount

    # Add to receiver
    receiver_account.balance += amount

    # Sender transaction
    sender_transaction = Transaction(
        user_id=sender_account.user_id,
        type="TRANSFER",
        amount=amount,
        description=(
            "Transferred to account "
            + receiver_account.account_number
        )
    )

    # Receiver transaction
    receiver_transaction = Transaction(
        user_id=receiver_account.user_id,
        type="TRANSFER",
        amount=amount,
        description=(
            "Received from account "
            + sender_account.account_number
        )
    )

    db.session.add(sender_transaction)
    db.session.add(receiver_transaction)

    db.session.commit()

    return redirect(url_for("dashboard"))


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )