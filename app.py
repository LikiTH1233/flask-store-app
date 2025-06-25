from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"


def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

  
    c.execute("PRAGMA foreign_keys = ON")

   
    c.execute('''CREATE TABLE IF NOT EXISTS items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        stock_quantity INTEGER NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS purchases (
        purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT NOT NULL,
        shipping_address TEXT NOT NULL,
        purchase_date TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS purchase_items (
        purchase_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_id INTEGER,
        item_id INTEGER,
        quantity INTEGER,
        FOREIGN KEY (purchase_id) REFERENCES purchases(purchase_id),
        FOREIGN KEY (item_id) REFERENCES items(item_id)
    )''')

    conn.commit()
    conn.close()


@app.route("/")
def index():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM items")
    items = c.fetchall()
    conn.close()
    return render_template("index.html", items=items)


@app.route("/add-item", methods=["GET", "POST"])
def add_item():
    if request.method == "POST":
        name = request.form["name"]
        price = float(request.form["price"])
        stock = int(request.form["stock_quantity"])

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO items (name, price, stock_quantity) VALUES (?, ?, ?)",
                  (name, price, stock))
        conn.commit()
        conn.close()
        flash(" Item added successfully!", "success")
        return redirect("/")
    return render_template("add_item.html")


@app.route("/update-item/<int:item_id>", methods=["GET", "POST"])
def update_item(item_id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    if request.method == "POST":
        name = request.form["name"]
        price = float(request.form["price"])
        stock = int(request.form["stock_quantity"])
        c.execute("UPDATE items SET name=?, price=?, stock_quantity=? WHERE item_id=?",
                  (name, price, stock, item_id))
        conn.commit()
        conn.close()
        flash(" Item updated!", "success")
        return redirect("/")
    c.execute("SELECT * FROM items WHERE item_id=?", (item_id,))
    item = c.fetchone()
    conn.close()
    return render_template("update_item.html", item=item)


@app.route("/delete-item/<int:item_id>")
def delete_item(item_id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM purchase_items WHERE item_id=?", (item_id,))
    if c.fetchone()[0] > 0:
        flash(" Cannot delete item: already purchased.", "error")
        conn.close()
        return redirect("/")
    c.execute("DELETE FROM items WHERE item_id=?", (item_id,))
    c.execute("SELECT COUNT(*) FROM items")
    if c.fetchone()[0] == 0:
        c.execute("DELETE FROM sqlite_sequence WHERE name='items'")
    conn.commit()
    conn.close()
    flash(" Item deleted.", "success")
    return redirect("/")


@app.route("/purchase", methods=["GET", "POST"])
def purchase():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM items")
    items = c.fetchall()

    if request.method == "POST":
        name = request.form["customer_name"]
        address = request.form["shipping_address"]
        selected_items = request.form.getlist("item_id")
        quantities = request.form.getlist("quantity")

        for item_id, qty in zip(selected_items, quantities):
            if not qty.strip().isdigit():
                flash(" Please enter a valid quantity.", "danger")
                conn.close()
                return render_template("purchase.html", items=items)

            item_id = int(item_id)
            qty = int(qty)

            c.execute("SELECT name, stock_quantity FROM items WHERE item_id=?", (item_id,))
            item = c.fetchone()
            if item:
                item_name, stock = item
                if qty > stock:
                    flash(f" Not enough stock for item '{item_name}'. Available: {stock}", "danger")
                    conn.close()
                    return render_template("purchase.html", items=items)

        c.execute("INSERT INTO purchases (customer_name, shipping_address) VALUES (?, ?)", (name, address))
        purchase_id = c.lastrowid

        for item_id, qty in zip(selected_items, quantities):
            item_id = int(item_id)
            qty = int(qty)
            if qty > 0:
                c.execute("INSERT INTO purchase_items (purchase_id, item_id, quantity) VALUES (?, ?, ?)", 
                          (purchase_id, item_id, qty))
                c.execute("UPDATE items SET stock_quantity = stock_quantity - ? WHERE item_id=?", 
                          (qty, item_id))

        conn.commit()
        conn.close()
        flash(" Purchase successful!", "success")
        return redirect("/purchases")

    conn.close()
    return render_template("purchase.html", items=items)

@app.route("/purchases")
def purchases():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute('''
        SELECT p.purchase_id, p.customer_name, p.shipping_address, p.purchase_date,
               i.name, pi.quantity, i.price
        FROM purchases p
        JOIN purchase_items pi ON p.purchase_id = pi.purchase_id
        JOIN items i ON pi.item_id = i.item_id
        ORDER BY p.purchase_id DESC
    ''')
    rows = c.fetchall()
    conn.close()
    return render_template("purchases.html", rows=rows)


@app.route("/update-purchase/<int:purchase_id>", methods=["GET", "POST"])
def update_purchase(purchase_id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    if request.method == "POST":
        name = request.form["customer_name"]
        address = request.form["shipping_address"]
        selected_items = request.form.getlist("item_id")
        quantities = request.form.getlist("quantity")

        c.execute("UPDATE purchases SET customer_name=?, shipping_address=? WHERE purchase_id=?",
                  (name, address, purchase_id))
        c.execute("DELETE FROM purchase_items WHERE purchase_id=?", (purchase_id,))

        for item_id, qty in zip(selected_items, quantities):
            item_id = int(item_id)
            qty = int(qty)
            if qty > 0:
                c.execute("INSERT INTO purchase_items (purchase_id, item_id, quantity) VALUES (?, ?, ?)",
                          (purchase_id, item_id, qty))

        conn.commit()
        conn.close()
        flash(" Purchase updated!", "success")
        return redirect("/purchases")

    c.execute("SELECT customer_name, shipping_address FROM purchases WHERE purchase_id=?", (purchase_id,))
    purchase = c.fetchone()
    c.execute("SELECT * FROM items")
    items = c.fetchall()
    c.execute("SELECT item_id, quantity FROM purchase_items WHERE purchase_id=?", (purchase_id,))
    purchased_items = dict(c.fetchall())
    conn.close()
    return render_template("update_purchase.html", purchase_id=purchase_id,
                           purchase=purchase, items=items, purchased_items=purchased_items)


@app.route("/delete-purchase/<int:purchase_id>")
def delete_purchase(purchase_id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

   
    c.execute("SELECT item_id, quantity FROM purchase_items WHERE purchase_id=?", (purchase_id,))
    purchase_items = c.fetchall()

   
    for item_id, qty in purchase_items:
        c.execute("UPDATE items SET stock_quantity = stock_quantity + ? WHERE item_id=?", (qty, item_id))

   
    c.execute("DELETE FROM purchase_items WHERE purchase_id=?", (purchase_id,))
    c.execute("DELETE FROM purchases WHERE purchase_id=?", (purchase_id,))

    c.execute("SELECT COUNT(*) FROM purchases")
    if c.fetchone()[0] == 0:
        c.execute("DELETE FROM sqlite_sequence WHERE name='purchases'")
        c.execute("DELETE FROM sqlite_sequence WHERE name='purchase_items'")

    conn.commit()
    conn.close()
    flash(" Purchase deleted and stock restored!", "success")
    return redirect("/purchases")


@app.route("/reset-purchases")
def reset_purchases():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("DELETE FROM purchase_items")
    c.execute("DELETE FROM purchases")
    c.execute("DELETE FROM sqlite_sequence WHERE name='purchases'")
    c.execute("DELETE FROM sqlite_sequence WHERE name='purchase_items'")
    conn.commit()
    conn.close()
    flash(" All purchases deleted and ID counter reset!", "success")
    return redirect("/purchases")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
