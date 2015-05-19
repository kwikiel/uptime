import flask
from flask import Flask
from flask import render_template
from flask.ext.sqlalchemy import SQLAlchemy
#from celery import Celery
import requests
from datetime import timedelta
import os
import subprocess
from flask import redirect, url_for
#iNSECURE and bad
#Also bad because importing all things




app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sites.db'
db = SQLAlchemy(app)


class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String, unique=True)
    status = db.Column(db.Enum('online', 'offline'))

    def __repr__(self):
        return '<Address: {0.address}, Status: {0.status}>'.format(self)


@app.route('/')
def update_sites():
    print 'Updating everything'
    for site in Site.query.all():
        print 'Updating', site
        try:
            req = requests.get('http://' + site.address)
            req.raise_for_status()
            site.status = 'online'
            print 'Is online actually'
        except:
            site.status = 'offline'
            print 'It is died'

    db.session.commit()
    return redirect(url_for('checks'))


@app.route('/hello')
def index():
    return "Hello -> go to /add"


@app.route('/add/<path:site>')
def add_site(site):
    new_site = Site(address=site)
    db.session.add(new_site)
    db.session.commit()
    return "Added {}".format(site)


@app.route('/sites')
def checks():
    sites = Site.query.all()
    #sites = [{"name":"www.wp.pl", "status": "down"},
    #        {"name":"www.google.pl", "status": "up"}
    #        ]
    return render_template("sites.html", sites=sites)

if __name__ == '__main__':
    db.create_all()
    app.run(host='0.0.0.0', port=5000)
