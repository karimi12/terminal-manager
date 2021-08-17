import re
from flask import Flask, redirect, url_for, request, render_template
import sqlite3
from jinja2 import Template, Environment, PackageLoader, select_autoescape, FileSystemLoader
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from flask import send_file


import os.path
from os import path
import time
from datetime import datetime
from werkzeug.wrappers import response

app = Flask(__name__)
env = Environment(
    loader=FileSystemLoader(searchpath="./"),
    autoescape=select_autoescape()
)
auth = HTTPBasicAuth()
users = {
    "john": generate_password_hash("hello1"),
}
# app.config.from_envvar('config.py')

USERS = []
TERMINALS = []

@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username

def loadUser():
    global USERS
    with open("users.txt", "r") as fu:
        USERS = fu.readlines()
    t = []
    for u in USERS:
        t.append(u.strip())
    USERS = t
    print(USERS)


def loadTerminal():
    global TERMINALS
    with open("terminals.txt", "r") as fu:
        TERMINALS = fu.readlines()
    t = []
    for u in TERMINALS:
        t.append(u.strip())
    TERMINALS = t
    print(TERMINALS)


def setupDB():
    if not path.isfile('Usage.db'):
        conn = sqlite3.connect('Usage.db')
        conn.execute('''CREATE TABLE Usage
                        (ID INTEGER PRIMARY KEY AUTOINCREMENT    NOT NULL,
                        User           TEXT     NOT NULL,
                        Terminal       IEXT     NOT NULL,
                        TakenTime      INT,
                        ReturnTime     INT
                        );''')
        conn.close()
        print("Database Craeted")


def getLastUser(terminal):
    conn = sqlite3.connect('Usage.db')
    cur = conn.cursor()
    cur.execute(
        "SELECT *  FROM Usage WHERE ReturnTime != 'Null' and Terminal ='{}' order by (TakenTime) desc limit 1".format(terminal))
    rows = cur.fetchall()
    r = []
    conn.close()
    if len(rows) == 0:
        return ""
    return rows[0][1]


def getBusyTerminals():
    conn = sqlite3.connect('Usage.db')
    cur = conn.cursor()
    cur.execute("select *  from Usage where ReturnTime = 'Null'")
    rows = cur.fetchall()
    r = []
    for tr in rows:
        a = {
            "id": tr[0],
            "user": tr[1],
            "terminal": tr[2],
            "takenTime": time.strftime("%d/%m/%Y %H:%M:%S", time.gmtime(tr[3])),
            "lastUser": getLastUser(tr[2]),
        }
        r.append(a)

    conn.close()
    return r

def createCSV():
    print("create csv")
    conn = sqlite3.connect('Usage.db')
    cur = conn.cursor()
    cur.execute("SELECT *  FROM Usage")
    rows = cur.fetchall()
    f=open("export.csv","w")
    csvStr="Id,User,Terminal,Taken Time, Return Time,Work Time\n"
    for tr in rows:
        if (type(tr[4]) != float) :
            csvStr=csvStr+"{}, {}, {}, {}, -, -\n".format(tr[0],tr[1],tr[2], time.strftime("%d/%m/%Y %H:%M:%S", time.gmtime(tr[3])))
        else:
            work = tr[4] - tr[3]
            csvStr=csvStr+"{}, {}, {}, {}, {}, {}\n".format(tr[0],tr[1],tr[2], time.strftime("%d/%m/%Y %H:%M:%S", time.gmtime(tr[3])),time.strftime("%d/%m/%Y %H:%M:%S", time.gmtime(tr[4])),time.strftime("%H:%M:%S", time.gmtime(work)))

    conn.close()
    f.write(csvStr)
    f.close()

def insertToDb(user, termianl):
    conn = sqlite3.connect('Usage.db')
    cur = conn.cursor()
    cur.execute(
        "select * from Usage where Terminal = '{}' and ReturnTime = 'Null'".format(termianl))
    rows = cur.fetchall()

    cur.execute(
        "select * from Usage where User = '{}' and ReturnTime = 'Null'".format(user))
    rows2 = cur.fetchall()

    if (len(rows) == 0 and len(rows2) == 0):
        # cur = conn.cursor()
        cur.execute("insert into Usage (User,Terminal,TakenTime,ReturnTime) values ('{}', '{}', {},'Null') ".format(
            user, termianl, datetime.now().timestamp()))
        conn.commit()
        conn.close()
        return cur.lastrowid
    conn.close()
    return None



@app.route("/data", methods=["post"])
@auth.login_required
def removeAll():
    if (request.form.get("action") == "delete"):
        conn = sqlite3.connect('Usage.db')
        cur = conn.cursor()
        cur.execute("DELETE FROM Usage")
        conn.commit()
        conn.close()
    if (request.form.get("action") == "download"):
        createCSV()
        return  send_file("export.csv", as_attachment=True)
    return redirect(url_for("index"), code=302)

@app.route("/")
def index():
    main()
    setupDB()
    return renderMainPage("")


def rturnTerminal(terminal):
    conn = sqlite3.connect('Usage.db')
    cur = conn.cursor()
    cur.execute("update Usage set ReturnTime={} where Terminal = '{}' and ReturnTime = 'Null'".format(
        datetime.now().timestamp(), terminal))
    conn.commit()
    conn.close()


@app.route("/terminal", methods=["post"])
def takenTerminal():
    if (request.form.get("action") == "taken"):
        if (len(request.form.get("user")) != 0 or len(request.form.get("terminal")) != 0):
            if(request.form.get("terminal") not in TERMINALS):
                return renderMainPage("Terminal not found.")
            if(request.form.get("user") not in USERS):
                return renderMainPage("User not found.")
            d = insertToDb(request.form.get("user"),
                           request.form.get("terminal"))
            if (d != None):
                return redirect(url_for("index"), code=302)
            else:
                return renderMainPage(err="Termianl or User is busy.")
    if (request.form.get("action") == "return"):
        rturnTerminal(request.form.get("terminal"))
        return redirect(url_for("index"), code=302)

    return render_template("index.jinja", title="sss", err="ddd")


def countBusyTerminal():
    conn = sqlite3.connect('Usage.db')
    cur = conn.cursor()
    cur.execute("select count(*) from Usage where ReturnTime = 'Null'")
    rows = cur.fetchall()
    r = []
    count = 0
    if len(rows) > 0:
        count = rows[0][0]
    conn.close()
    return count


def countFreeTermianl():
    return len(TERMINALS)-countBusyTerminal()


def renderMainPage(err):
    return render_template("index.jinja", err=err, busyTerminals=getBusyTerminals(), users=USERS, terminals=TERMINALS, countBusyTerminal=countBusyTerminal(), countFreeTermianl=countFreeTermianl())


def main():
    loadTerminal()
    loadUser()


if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    main()
