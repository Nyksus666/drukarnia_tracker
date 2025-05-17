from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import json

app = Flask(__name__)
app.secret_key = "super_secret_key"

# Konfiguracja SQLite
DB_PATH = os.path.join(os.getcwd(), 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Lista etapów produkcyjnych
ETAPY = [
    "przyjęcie", "projektowanie", "akceptacja", "druk", "falcowanie",
    "zbieranie", "szycie", "klejenie", "sztancowanie/bigowanie", "foliowanie",
    "cięcie", "pakowanie", "wysyłka", "zakończone"
]

# Model Zlecenia
class Zlecenie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numer_glowny = db.Column(db.String(50), nullable=False)
    klient = db.Column(db.String(100), nullable=False)
    opis = db.Column(db.Text, nullable=True)
    etapy_niezbedne = db.Column(db.Text, nullable=False)  # JSON list
    wykonane_etapy = db.Column(db.Text, default='[]')     # JSON list
    papier = db.Column(db.Text, nullable=True)            # JSON list
    uwagi = db.Column(db.Text, nullable=True)
    zatrzymano = db.Column(db.Boolean, default=False)
    powod_zatrzymania = db.Column(db.Text, nullable=True)
    data_dodania = db.Column(db.DateTime, default=datetime.utcnow)

# Routen login/logout
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'admin123':
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template("login.html", error="Błędne hasło.")
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# Strona główna – lista zleceń
@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    zlecenia = Zlecenie.query.order_by(Zlecenie.data_dodania.desc()).all()

    # Dekoduj JSON do list
    for z in zlecenia:
        z.etapy_niezbedne = json.loads(z.etapy_niezbedne or '[]')
        z.wykonane_etapy = json.loads(z.wykonane_etapy or '[]')
        z.papier = json.loads(z.papier or '[]')

    return render_template('index.html', zlecenia=zlecenia, etapy=ETAPY)

# Dodawanie zlecenia
@app.route('/add', methods=['GET', 'POST'])
def add_order():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        klient = request.form['klient']
        numer_glowny = request.form['numer_glowny']
        opis = request.form['opis']
        papier = request.form.getlist('papier')
        etapy_niezbedne = request.form.getlist('etapy_niezbedne')
        uwagi = request.form['uwagi']

        nowe = Zlecenie(
            klient=klient,
            numer_glowny=numer_glowny,
            opis=opis,
            papier=json.dumps(papier),
            etapy_niezbedne=json.dumps(etapy_niezbedne),
            uwagi=uwagi
        )
        db.session.add(nowe)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_order.html', etapy=ETAPY)

# Aktualizacja wykonanych etapów
@app.route('/update/<int:id>', methods=['POST'])
def update_status(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    zlecenie = Zlecenie.query.get_or_404(id)
    wykonane = request.form.getlist('wykonane_etapy')
    zlecenie.wykonane_etapy = json.dumps(wykonane)
    db.session.commit()
    return redirect(url_for('index'))

# Zatrzymywanie zlecenia
@app.route('/zatrzymaj/<int:id>', methods=['POST'])
def zatrzymaj(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    powod = request.form['powod']
    zlecenie = Zlecenie.query.get_or_404(id)
    zlecenie.zatrzymano = True
    zlecenie.powod_zatrzymania = powod
    db.session.commit()
    return redirect(url_for('index'))

# Tworzenie tabel przy starcie
with app.app_context():
    db.create_all()

# Lokalnie do testów
if __name__ == '__main__':
    app.run(debug=True)
