from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import sqlite3

app = Flask(__name__)

DATABASE = 'user_ads.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            price TEXT,
            link TEXT,
            description TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Функция для парсинга объявлений с Avito (город Череповец)
def parse_avito():
    url = "https://www.avito.ru/cherpovets/kvartiry/prodam"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    listings = []
    # Используем data-marker для поиска объявлений
    for item in soup.find_all("div", {"data-marker": "item"}):
        try:
            title_el = item.find("h3")
            if not title_el:
                continue
            title = title_el.text.strip()
            price_el = item.find("meta", itemprop="price")
            if not price_el:
                continue
            price = price_el["content"]
            link_el = item.find("a")
            if not link_el:
                continue
            link = "https://www.avito.ru" + link_el["href"]
            listings.append({"title": title, "price": price, "link": link})
        except Exception as e:
            print("Ошибка при парсинге элемента:", e)
            continue
    return listings

@app.route("/get_properties", methods=["GET"])
def get_properties():
    data = parse_avito()
    return jsonify(data)

@app.route("/get_user_ads", methods=["GET"])
def get_user_ads():
    conn = get_db_connection()
    ads = conn.execute("SELECT * FROM ads").fetchall()
    conn.close()
    ads_list = [dict(ad) for ad in ads]
    return jsonify(ads_list)

@app.route("/create_ad", methods=["POST"])
def create_ad():
    data = request.json
    title = data.get("title", "Без названия")
    price = data.get("price", "")
    link = data.get("link", "")
    description = data.get("description", "")
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO ads (title, price, link, description) VALUES (?, ?, ?, ?)",
              (title, price, link, description))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    new_ad = {"id": new_id, "title": title, "price": price, "link": link, "description": description}
    return jsonify({"status": "ok", "ad": new_ad})

@app.route("/delete_ad", methods=["POST"])
def delete_ad():
    data = request.json
    ad_id = data.get("id")
    if ad_id is None:
        return jsonify({"status": "error", "message": "Не указан id"}), 400
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM ads WHERE id = ?", (str(ad_id),))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/calculate_mortgage", methods=["POST"])
def calculate_mortgage():
    data = request.json
    price = float(data["price"])
    down_payment = float(data["downPayment"])
    interest_rate = float(data["interestRate"])
    loan_term = int(data["loanTerm"])
    loan_amount = price - down_payment
    monthly_rate = (interest_rate / 100) / 12
    number_of_payments = loan_term * 12
    if monthly_rate > 0:
        monthly_payment = (loan_amount * monthly_rate) / (1 - (1 + monthly_rate) ** -number_of_payments)
    else:
        monthly_payment = loan_amount / number_of_payments
    return jsonify({"monthlyPayment": round(monthly_payment, 2)})

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
