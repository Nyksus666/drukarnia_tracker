from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import json

app = Flask(__name__)
app.secret_key = "super_secret_key"
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.getcwd(), 'database.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

ETAPY = [
    "przyjęcie", "projektowanie", "akceptacja", "druk", "foliowanie", "lakierowanie",
    "falcowanie", "zbieranie", "szycie", "klejenie", "sztancowanie/bigowanie",
    "cięcie", "pakowanie", "wysyłka"
]

PRODUKTY_ETAPY = {
    "Wizytówka bez folii": ["przyjęcie", "projektowanie", "akceptacja", "druk", "cięcie", "pakowanie", "wysyłka"],
    "Wizytówka foliowana": ["przyjęcie", "projektowanie", "akceptacja", "druk", "foliowanie", "cięcie", "pakowanie", "wysyłka"],
    "Wizytówka z Lakierem UV": ["przyjęcie", "projektowanie", "akceptacja", "druk", "foliowanie", "lakierowanie", "cięcie", "pakowanie", "wysyłka"],
    "Ulotka": ["przyjęcie", "projektowanie", "akceptacja", "druk", "cięcie", "pakowanie", "wysyłka"],
    "Ulotka falcowana": ["przyjęcie", "projektowanie", "akceptacja", "druk", "falcowanie", "pakowanie", "wysyłka"],
    "Teczka": ["przyjęcie", "projektowanie", "akceptacja", "druk", "sztancowanie/bigowanie", "pakowanie", "wysyłka"],
    "Broszura szyta": ["przyjęcie", "projektowanie", "akceptacja", "druk", "falcowanie", "zbieranie", "szycie", "pakowanie", "wysyłka"],
    "Broszura klejona": ["przyjęcie", "projektowanie", "akceptacja", "druk", "falcowanie", "zbieranie", "klejenie", "pakowanie", "wysyłka"]
}

class Zlecenie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numer_glowny = db.Column(db.String(50), nullable=False)
    klient = db.Column(db.String(100), nullable=False)
    produkt = db.Column(db.String(100))
    etapy_niezbedne = db.Column(db.Text)
    wykonane_etapy = db.Column(db.Text, default='[]')
    historia_etapow = db.Column(db.Text, default='{}')
    papier = db.Column(db.Text)
    uwagi = db.Column(db.Text)
    zatrzymano = db.Column(db.Boolean, default=False)
    powod_zatrzymania = db.Column(db.Text)
    zakonczone = db.Column(db.Boolean, default=False)
    data_dodania = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST' and request.form.get('password') == 'admin123':
        session['logged_in'] = True
        return redirect(url_for('index'))
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    filtr = request.args.get("filtr", "wszystkie")
    q = Zlecenie.query.order_by(Zlecenie.data_dodania.desc())

    if filtr == "zatrzymane":
        q = q.filter_by(zatrzymano=True)
    elif filtr == "w_produkcji":
        q = q.filter_by(zatrzymano=False, zakonczone=False)
    elif filtr == "zakonczone":
        q = q.filter_by(zakonczone=True)

    zlecenia = q.all()

    for z in zlecenia:
        z.etapy_niezbedne = json.loads(z.etapy_niezbedne or '[]')
        z.wykonane_etapy = json.loads(z.wykonane_etapy or '[]')
        z.historia_etapow = json.loads(z.historia_etapow or '{}')
        z.papier = json.loads(z.papier or '[]')

    return render_template('index.html', zlecenia=zlecenia, filtr=filtr)

@app.route('/add', methods=['GET', 'POST'])
def add_order():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        klient = request.form['klient']
        numer = request.form['numer_glowny']
        produkt = request.form['produkt']
        uwagi = request.form['uwagi']

        papiery = []
        typy = request.form.getlist('papier_typ')
        ilosci = request.form.getlist('papier_ilosc')
        for t, i in zip(typy, ilosci):
            if t.strip() and i.strip():
                papiery.append({"typ": t.strip(), "ilosc": i.strip()})

        etapy = PRODUKTY_ETAPY.get(produkt, [])

        z = Zlecenie(
            klient=klient,
            numer_glowny=numer,
            produkt=produkt,
            etapy_niezbedne=json.dumps(etapy),
            papier=json.dumps(papiery),
            uwagi=uwagi
        )
        db.session.add(z)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('add_order.html', produkty=list(PRODUKTY_ETAPY.keys()))

@app.route('/update/<int:id>', methods=['POST'])
def update_status(id):
    z = Zlecenie.query.get_or_404(id)
    if z.zatrzymano:
        return redirect(url_for('index'))

    wykonane = request.form.getlist('wykonane_etapy')
    historia = json.loads(z.historia_etapow or '{}')
    for etap in wykonane:
        if etap not in historia:
            historia[etap] = datetime.now().isoformat()
    z.wykonane_etapy = json.dumps(wykonane)
    z.historia_etapow = json.dumps(historia)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/zatrzymaj/<int:id>', methods=['POST'])
def zatrzymaj(id):
    z = Zlecenie.query.get_or_404(id)
    z.zatrzymano = True
    z.powod_zatrzymania = request.form.get('powod')
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/wznów/<int:id>', methods=['POST'])
def wznow_zlecenie(id):
    z = Zlecenie.query.get_or_404(id)
    z.zatrzymano = False
    z.powod_zatrzymania = None
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/zakoncz/<int:id>', methods=['POST'])
def zakoncz(id):
    z = Zlecenie.query.get_or_404(id)
    z.zakonczone = True
    db.session.commit()
    return redirect(url_for('index'))

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
