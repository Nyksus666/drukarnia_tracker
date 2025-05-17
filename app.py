from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import json

app = Flask(__name__)
app.secret_key = "super_secret_key"
DB_PATH = os.path.join(os.getcwd(), 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

ETAPY = [
    "przyjęcie", "projektowanie", "akceptacja", "druk", "falcowanie",
    "zbieranie", "szycie", "klejenie", "sztancowanie/bigowanie",
    "foliowanie", "cięcie", "pakowanie", "wysyłka"
]

class Zlecenie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numer_glowny = db.Column(db.String(50), nullable=False)
    klient = db.Column(db.String(100), nullable=False)
    opis = db.Column(db.Text, nullable=True)
    etapy_niezbedne = db.Column(db.Text, nullable=False)
    wykonane_etapy = db.Column(db.Text, default='[]')
    historia_etapow = db.Column(db.Text, default='{}')
    papier = db.Column(db.Text, nullable=True)
    uwagi = db.Column(db.Text, nullable=True)
    zatrzymano = db.Column(db.Boolean, default=False)
    powod_zatrzymania = db.Column(db.Text, nullable=True)
    zakonczone = db.Column(db.Boolean, default=False)
    data_dodania = db.Column(db.DateTime, default=datetime.utcnow)

class PapierTyp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nazwa = db.Column(db.String(100), unique=True)

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
    zlecenia = Zlecenie.query.order_by(Zlecenie.data_dodania.desc()).all()
    for z in zlecenia:
        z.etapy_niezbedne = json.loads(z.etapy_niezbedne or '[]')
        z.wykonane_etapy = json.loads(z.wykonane_etapy or '[]')
        z.historia_etapow = json.loads(z.historia_etapow or '{}')
        z.papier = json.loads(z.papier or '[]')
    return render_template('index.html', zlecenia=zlecenia)

@app.route('/add', methods=['GET', 'POST'])
def add_order():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        klient = request.form['klient']
        numer_glowny = request.form['numer_glowny']
        opis = request.form['opis']
        uwagi = request.form['uwagi']
        etapy = request.form.getlist('etapy_niezbedne')
        papier = request.form.getlist('papier')

        # zapisz nowe typy papierów do bazy
        for p in papier:
            if p and not PapierTyp.query.filter_by(nazwa=p).first():
                db.session.add(PapierTyp(nazwa=p))

        z = Zlecenie(
            numer_glowny=numer_glowny,
            klient=klient,
            opis=opis,
            etapy_niezbedne=json.dumps(etapy),
            papier=json.dumps(papier),
            uwagi=uwagi
        )
        db.session.add(z)
        db.session.commit()
        return redirect(url_for('index'))

    wszystkie_papiery = PapierTyp.query.order_by(PapierTyp.nazwa).all()
    return render_template('add_order.html', etapy=ETAPY, papiery=[p.nazwa for p in wszystkie_papiery])

@app.route('/update/<int:id>', methods=['POST'])
def update_status(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    z = Zlecenie.query.get_or_404(id)
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
    z.powod_zatrzymania = request.form['powod']
    db.session.commit()
    return redirect(url_for('index'))
    
@app.route('/wznów/<int:id>', methods=['POST'])
def wznow_zlecenie(id):
    zlecenie = Zlecenie.query.get_or_404(id)
    zlecenie.zatrzymano = False
    zlecenie.powod_zatrzymania = None
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
