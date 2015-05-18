import flask
from flask import Flask
from flask import render_template
from flask.ext.sqlalchemy import SQLAlchemy
from celery import Celery
import requests
from datetime import timedelta
import os

class FlaskCelery(Celery):
    def __init__(self, *args, **kwargs):
        super(FlaskCelery, self).__init__(*args, **kwargs)
        self.patch_task()

        if 'app' in kwargs:
            self.init_app(kwargs['app'])

    def patch_task(self):
        TaskBase = self.Task
        _celery = self

        class ContextTask(TaskBase):
            abstract = True

            def __call__(self, *args, **kwargs):
                if flask.has_app_context():
                    return TaskBase.__call__(self, *args, **kwargs)
                else:
                    with _celery.app.app_context():
                        return TaskBase.__call__(self, *args, **kwargs)

        self.Task = ContextTask

    def init_app(self, app):
        self.app = app
        self.config_from_object(app.config)


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sites.db'
app.config.update(
    CELERY_BROKER_URL=os.environ['REDIS_URL'],
    CELERY_RESULT_BACKEND=os.environ['REDIS_URL'],
    CELERY_TIMEZONE = 'UTC',
    CELERYBEAT_SCHEDULE={
        'update-every-30-seconds': {
            'task': 'checker.update_sites',
            'schedule': timedelta(seconds=30),
        },
    },
)

db = SQLAlchemy(app)
celery = FlaskCelery(app=app, broker=app.config['CELERY_BROKER_URL'])


class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String, unique=True)
    status = db.Column(db.Enum('online', 'offline'))

    def __repr__(self):
        return '<Address: {0.address}, Status: {0.status}>'.format(self)


@celery.task
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


@app.route('/')
def index():
    return "Hello -> go to /add"

@app.route('/add/<path:site>')
def add_site(site):
    new_site = Site(address=site)
    db.session.add(new_site)
    db.session.commit()
    return "Added {}"format(site)


@app.route('/sites')
def checks():
    sites = Site.query.all()
    #sites = [{"name":"www.wp.pl", "status": "down"},
    #        {"name":"www.google.pl", "status": "up"}
    #        ]
    return render_template("sites.html", sites=sites)

if __name__ == '__main__':
    db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
