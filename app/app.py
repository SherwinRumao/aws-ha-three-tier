"""Flask demo app for the HA three-tier project.

Shows the serving instance ID and availability zone, and a small notes list stored in RDS MySQL.
The database password is read at runtime from SSM Parameter Store (/ha/db_password).
Replace PASTE-RDS-ENDPOINT before running. The same code is embedded in user-data.sh.
"""
import html
import urllib.request
import boto3
import pymysql
from flask import Flask, request, redirect

REGION = "ap-south-1"
DB_HOST = "PASTE-RDS-ENDPOINT"
DB_USER = "admin"
DB_NAME = "appdb"
PARAM_NAME = "/ha/db_password"

app = Flask(__name__)
_pw = None

def imds(path):
    t = urllib.request.Request(
        "http://169.254.169.254/latest/api/token", method="PUT",
        headers={"X-aws-ec2-metadata-token-ttl-seconds": "300"})
    token = urllib.request.urlopen(t, timeout=2).read().decode()
    r = urllib.request.Request(
        "http://169.254.169.254/latest/meta-data/" + path,
        headers={"X-aws-ec2-metadata-token": token})
    return urllib.request.urlopen(r, timeout=2).read().decode()

def db():
    global _pw
    if _pw is None:
        ssm = boto3.client("ssm", region_name=REGION)
        _pw = ssm.get_parameter(Name=PARAM_NAME, WithDecryption=True)["Parameter"]["Value"]
    c = pymysql.connect(host=DB_HOST, user=DB_USER, password=_pw,
                        database=DB_NAME, connect_timeout=3, autocommit=True)
    cur = c.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS notes (id INT AUTO_INCREMENT PRIMARY KEY, msg VARCHAR(200), served_by VARCHAR(40), created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    return c

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        msg = request.form.get("msg", "").strip()[:200]
        if msg:
            try:
                c = db()
                c.cursor().execute("INSERT INTO notes (msg, served_by) VALUES (%s, %s)", (msg, imds("instance-id")))
                c.close()
            except Exception as e:
                print("DB write error:", repr(e), flush=True)
        return redirect("/")
    page = "<h1>HA three-tier demo</h1>"
    page += "<p>Instance: " + imds("instance-id") + " | AZ: " + imds("placement/availability-zone") + "</p>"
    page += '<form method="post"><input name="msg" maxlength="200"><button>Add note</button></form>'
    try:
        c = db()
        cur = c.cursor()
        cur.execute("SELECT msg, served_by, created FROM notes ORDER BY id DESC LIMIT 10")
        rows = cur.fetchall()
        c.close()
        page += "<ul>" + "".join("<li>%s <small>(%s, %s)</small></li>" % (html.escape(r[0]), r[1], r[2]) for r in rows) + "</ul>"
    except Exception as e:
        print("DB read error:", repr(e), flush=True)
        page += "<p>Database unavailable</p>"
    return page

# Health check does not touch the database, so a database problem does not
# cause the load balancer to mark every web server unhealthy.
@app.route("/health")
def health():
    return "ok", 200

app.run(host="0.0.0.0", port=80)
