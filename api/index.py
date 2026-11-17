# Instrument Rental is a free instrument library + people renting their instruments to others.
# There are no website fees: the owner gets the full rental price.
# A price limit (ceiling) for each instrument stops people from overcharging.
# A site manager can remove listings and change the price limits.

import json
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
from html import escape  # stops people from typing code into the boxes

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
if os.environ.get("VERCEL"):
    DATA_FILE = "/tmp/data.json"  # on Vercel, only the /tmp folder can be written to

# ---------------- Data ----------------
# Highest price per day an owner is allowed to charge for each instrument.
price_limits = {
    "Guitar": 10,
    "Violin": 10,
    "Viola": 10,
    "Cello": 15,
    "Keyboard": 12,
    "Flute": 8,
    "Clarinet": 8,
    "Trumpet": 8,
    "Trombone": 8,
    "Saxophone": 12,
    "Drums": 15,
    "Other": 10,
}

# Each instrument is a dictionary. "price" of 0 means it's from the free library.
instruments = [
    {"id": 1, "name": "Guitar", "owner": "Library", "price": 0, "available": True},
    {"id": 2, "name": "Violin", "owner": "Library", "price": 0, "available": True},
    {"id": 3, "name": "Guitar", "owner": "Alex", "price": 5, "available": True},
    {"id": 4, "name": "Guitar", "owner": "Sam", "price": 4, "available": True},
    {"id": 5, "name": "Keyboard", "owner": "Jordan", "price": 6, "available": True},
]
rentals = []


def save_data():
    file = open(DATA_FILE, "w")
    json.dump({"instruments": instruments, "rentals": rentals, "price_limits": price_limits}, file)
    file.close()


def load_data():
    global instruments, rentals, price_limits
    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        file = open(DATA_FILE)
        data = json.load(file)
        file.close()
        instruments = data["instruments"]
        rentals = data["rentals"]
        if "price_limits" in data:
            price_limits = data["price_limits"]


def find_instrument(id):
    for item in instruments:
        if item["id"] == id:
            return item
    return None


def get_limit(name):
    if name in price_limits:
        return price_limits[name]
    return price_limits["Other"]


# ---------------- Pages ----------------
STYLE = """
body { margin: 0; font-family: Arial, sans-serif; background: #f4f1fb; color: #2b2540; }
header { background: linear-gradient(135deg, #5b3cc4, #8e5cf7); color: white; padding: 22px 32px;
         display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }
header h1 { margin: 0; }
nav a { color: white; text-decoration: none; margin-left: 8px; padding: 8px 14px;
        border-radius: 20px; background: rgba(255,255,255,.15); font-weight: bold; }
nav a:hover { background: rgba(255,255,255,.3); }
main { max-width: 1000px; margin: 32px auto; background: white; padding: 28px 32px;
       border-radius: 14px; box-shadow: 0 4px 20px rgba(0,0,0,.08); }
h2 { margin-top: 0; color: #5b3cc4; }
h3 { color: #5b3cc4; }
table { width: 100%; border-collapse: collapse; }
th { background: #ede7fd; color: #4a2fa8; text-align: left; padding: 12px; }
td { padding: 12px; border-bottom: 1px solid #eee8f7; }
tr:hover td { background: #faf8ff; }
input, select { padding: 8px; border: 1px solid #d3c9ef; border-radius: 8px; }
input[type=number] { width: 70px; }
button { background: #ff8a3d; color: white; border: none; padding: 9px 18px;
         border-radius: 8px; font-weight: bold; cursor: pointer; }
button:hover { background: #f06f1c; }
.free { color: #1a9e5c; font-weight: bold; }
.box { background: #f4f1fb; border-left: 5px solid #8e5cf7; padding: 16px 20px; border-radius: 8px; }
.error { background: #fdecec; border-left: 5px solid #d64545; padding: 16px 20px; border-radius: 8px; }
"""


def make_page(content):
    html = "<html><head><title>Instrument Rental</title><style>" + STYLE + "</style></head><body>"
    html += "<header><h1>&#127925; Instrument Rental</h1><nav>"
    html += "<a href='/'>Browse</a><a href='/list'>List an Instrument</a><a href='/rentals'>My Rentals</a>"
    html += "<a href='/rules'>Price Rules</a><a href='/manager'>Site Manager</a>"
    html += "</nav></header><main>" + content + "</main></body></html>"
    return html


def browse_page(search):
    html = "<h2>Available Instruments</h2>"
    html += "<form action='/'>Search instrument: <input name='q' value='" + escape(search) + "'> <button>Search</button></form><br>"
    html += "<table><tr><th>Instrument</th><th>From</th><th>Price</th><th>Rent</th></tr>"

    found = False
    for item in instruments:
        if item["available"] and search.lower() in item["name"].lower():
            found = True
            if item["price"] == 0:
                price = "<span class='free'>Library (free)</span>"
            else:
                price = "$" + format(item["price"], ".2f") + "/day"
            html += "<tr><td>" + item["name"] + "</td><td>" + item["owner"] + "</td><td>" + price + "</td>"
            html += "<td><form method='post' action='/rent'>"
            html += "<input type='hidden' name='id' value='" + str(item["id"]) + "'>"
            html += "Your name: <input name='renter' required> "
            html += "Days: <input name='days' type='number' min='1' value='1' required> "
            html += "<button>Rent</button></form></td></tr>"

    if not found:
        html += "<tr><td colspan='4'>No instruments available.</td></tr>"
    html += "</table>"
    return make_page(html)


def list_page(message):
    html = "<h2>List Your Instrument</h2>"
    if message != "":
        html += "<p class='error'>" + message + "</p>"
    html += "<form method='post' action='/list'>"
    html += "Instrument: <select name='name'>"
    for name in price_limits:
        html += "<option>" + name + "</option>"
    html += "</select><br><br>"
    html += "Your name: <input name='owner' required><br><br>"
    html += "Price per day ($): <input name='price' type='number' step='0.01' min='0' required><br><br>"
    html += "<button>List Instrument</button></form>"
    html += "<p>Each instrument has a highest price you can charge. See <a href='/rules'>Price Rules</a>.</p>"
    return make_page(html)


def rules_page():
    html = "<h2>Price Rules</h2>"
    html += "<ul>"
    html += "<li>There are no website fees. The owner gets the full rental price.</li>"
    html += "<li>Library instruments are always free.</li>"
    html += "<li>Owners set their own price per day, but it can't go over the price limit below.</li>"
    html += "<li>The site manager can remove any listing that breaks these rules.</li>"
    html += "</ul>"
    html += "<table><tr><th>Instrument</th><th>Highest price per day</th></tr>"
    for name in price_limits:
        html += "<tr><td>" + name + "</td><td>$" + format(price_limits[name], ".2f") + "</td></tr>"
    html += "</table>"
    return make_page(html)


def rentals_page():
    html = "<h2>Current Rentals</h2>"
    html += "<table><tr><th>Instrument</th><th>From</th><th>Renter</th><th>Days</th><th>Total</th><th></th></tr>"
    if len(rentals) == 0:
        html += "<tr><td colspan='6'>No current rentals.</td></tr>"
    for i in range(len(rentals)):
        r = rentals[i]
        html += "<tr><td>" + r["name"] + "</td><td>" + r["owner"] + "</td><td>" + r["renter"] + "</td>"
        html += "<td>" + str(r["days"]) + "</td><td>$" + format(r["total"], ".2f") + "</td>"
        html += "<td><form method='post' action='/return'><input type='hidden' name='num' value='" + str(i) + "'>"
        html += "<button>Return</button></form></td></tr>"
    html += "</table>"
    return make_page(html)


def confirm_page(r):
    html = "<h2>Rental Confirmed</h2>"
    html += "<p>You rented a <b>" + r["name"] + "</b> from <b>" + r["owner"] + "</b> for " + str(r["days"]) + " day(s).</p>"
    html += "<p class='box'>Total: $" + format(r["total"], ".2f") + "<br>"
    html += "The owner receives the full amount (no website fees).</p>"
    return make_page(html)


def manager_page():
    html = "<h2>Site Manager</h2>"

    html += "<h3>All Listings</h3>"
    html += "<table><tr><th>Instrument</th><th>Owner</th><th>Price</th><th>Limit</th><th>Status</th><th></th></tr>"
    for item in instruments:
        if item["available"]:
            status = "Available"
        else:
            status = "Rented"
        html += "<tr><td>" + item["name"] + "</td><td>" + item["owner"] + "</td>"
        html += "<td>$" + format(item["price"], ".2f") + "</td><td>$" + format(get_limit(item["name"]), ".2f") + "</td>"
        html += "<td>" + status + "</td>"
        html += "<td><form method='post' action='/remove'>"
        html += "<input type='hidden' name='id' value='" + str(item["id"]) + "'>"
        html += "<button>Remove</button></form></td></tr>"
    html += "</table>"

    html += "<h3>Change Price Limits</h3>"
    html += "<table><tr><th>Instrument</th><th>Highest price per day</th><th></th></tr>"
    for name in price_limits:
        html += "<tr><td>" + name + "</td><td><form method='post' action='/set_limit'>"
        html += "<input type='hidden' name='name' value='" + name + "'>"
        html += "$ <input name='limit' type='number' step='0.01' min='0' value='" + str(price_limits[name]) + "'> "
        html += "<button>Save</button></form></td><td></td></tr>"
    html += "</table>"
    return make_page(html)


# ---------------- Actions ----------------
def rent_instrument(id, renter, days):
    renter = escape(renter)
    item = find_instrument(id)
    if item == None or item["available"] == False:
        return make_page("<p>Sorry, that instrument is no longer available.</p>")
    total = item["price"] * days
    item["available"] = False
    rental = {"id": id, "name": item["name"], "owner": item["owner"], "renter": renter,
              "days": days, "total": total}
    rentals.append(rental)
    save_data()
    return confirm_page(rental)


def add_instrument(name, owner, price):
    name = escape(name)
    owner = escape(owner)
    # The price check: owners can't charge more than the limit
    limit = get_limit(name)
    if price > limit:
        return "The highest price for a " + name + " is $" + format(limit, ".2f") + " per day. Please lower your price."
    new_id = 1
    for item in instruments:
        if item["id"] >= new_id:
            new_id = item["id"] + 1
    instruments.append({"id": new_id, "name": name, "owner": owner, "price": price, "available": True})
    save_data()
    return ""


def return_instrument(num):
    rental = rentals.pop(num)
    item = find_instrument(rental["id"])
    if item != None:
        item["available"] = True
    save_data()


def remove_instrument(id):
    item = find_instrument(id)
    if item != None:
        instruments.remove(item)
    # also remove any rental of this instrument
    for r in rentals[:]:
        if r["id"] == id:
            rentals.remove(r)
    save_data()


# ---------------- Server ----------------
class Handler(BaseHTTPRequestHandler):

    def show(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def go_to(self, page):
        self.send_response(303)
        self.send_header("Location", page)
        self.end_headers()

    # Opening a page
    def get_page(self):
        page = self.path.split("?")[0]
        if page.startswith("/api/index"):
            page = page[len("/api/index"):]
        if page == "":
            page = "/"
        return page

    def do_GET(self):
        load_data()
        page = self.get_page()
        if page == "/":
            search = ""
            if "?" in self.path:
                query = parse_qs(self.path.split("?")[1])
                if "q" in query:
                    search = query["q"][0]
            self.show(browse_page(search))
        elif page == "/list":
            self.show(list_page(""))
        elif page == "/rentals":
            self.show(rentals_page())
        elif page == "/rules":
            self.show(rules_page())
        elif page == "/manager":
            self.show(manager_page())
        else:
            self.send_error(404)

    # Clicking a button
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        form = parse_qs(self.rfile.read(length).decode())
        load_data()
        page = self.get_page()

        if page == "/rent":
            id = int(form["id"][0])
            renter = form["renter"][0]
            days = int(form["days"][0])
            self.show(rent_instrument(id, renter, days))
        elif page == "/list":
            message = add_instrument(form["name"][0], form["owner"][0], float(form["price"][0]))
            if message == "":
                self.go_to("/")
            else:
                self.show(list_page(message))
        elif page == "/return":
            return_instrument(int(form["num"][0]))
            self.go_to("/rentals")

        # Site manager buttons
        elif page == "/remove":
            remove_instrument(int(form["id"][0]))
            self.show(manager_page())
        elif page == "/set_limit":
            price_limits[form["name"][0]] = float(form["limit"][0])
            save_data()
            self.show(manager_page())


# Vercel looks for a class called "handler"
handler = Handler


# ---------------- Start (on your computer) ----------------
def start():
    load_data()
    try:
        server = HTTPServer(("", 8000), Handler)
        print("Running at http://localhost:8000  (press Ctrl+C to stop)")
        webbrowser.open("http://localhost:8000")
        server.serve_forever()
    except OSError:
        print("The website is already running. Opening it...")
        webbrowser.open("http://localhost:8000")
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    start()
