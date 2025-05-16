# app.py
from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super_secret_key"  # zmień na bezpieczny klucz
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

# Lista etapów produkcji
ETAPY = [
    "przyjęcie",
    "projektowanie",
    "akceptacja",
    "druk",
    "falcowanie",
    "zbieranie",
    "szycie",
    "klejenie",
    "sztancowanie/bigowanie",
    "foliowanie",
    "cięcie",
    "pakowanie",
    "wysyłka",
    "zakończone"
]

# Model zlecenia
class Zlecenie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    klient = db.Column(db.String(100), nullable=False)
    opis = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default="przyjęcie")
    data_dodania = db.Column(db.DateTime, default=datetime.utcnow)

# ROUTES

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'admin123':
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template("login.html", error="Błędne hasło.")
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    zlecenia = Zlecenie.query.order_by(Zlecenie.data_dodania.desc()).all()
    return render_template('index.html', zlecenia=zlecenia, etapy=ETAPY)

@app.route('/add', methods=['GET', 'POST'])
def add_order():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        klient = request.form['klient']
        opis = request.form['opis']
        nowe = Zlecenie(klient=klient, opis=opis)
        db.session.add(nowe)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_order.html')

@app.route('/update/<int:id>', methods=['POST'])
def update_status(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    zlecenie = Zlecenie.query.get_or_404(id)
    new_status = request.form['status']
    if new_status in ETAPY:
        zlecenie.status = new_status
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>', methods=['POST'])
def delete_order(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    zlecenie = Zlecenie.query.get_or_404(id)
    db.session.delete(zlecenie)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
