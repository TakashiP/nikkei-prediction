from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from datetime import date, datetime
import os
import sqlite3
import sys
sys.path.append("..\\NikkeiPredictionPackage")

app = Flask(__name__)
bootstrap = Bootstrap(app)

import Nikkei_10_utilized
import db

DATABASE = 'database.db'
db.create_actual_table()
db.create_prediction_table()

## ここからスケジューラー
from flask_apscheduler import APScheduler
import pytz

jst = pytz.timezone('Asia/Tokyo')
today_time = datetime.now().astimezone(jst)
today = today_time.date()

# set configuration values
class Config:
    SCHEDULER_API_ENABLED = True

app.config.from_object(Config())

# initialize scheduler
scheduler = APScheduler()
# if you don't wanna use a config, you can set options here:
# scheduler.api_enabled = True
scheduler.init_app(app)

@scheduler.task('cron', id='do_job_1', hour='7', minute='00', timezone=jst)
def nikkei_prediction():
    Nikkei_10_utilized.predict()
    today_time = datetime.now().astimezone(jst)
    today = today_time.date()

scheduler.start()
## ここまでスケジューラー

@app.route('/')
def index():
    con = sqlite3.connect(DATABASE)
    predicted_data = con.execute('SELECT predict FROM prediction WHERE DATE = ?', [today]).fetchone()
    con.close()
    predict = "{:,.0f}".format(predicted_data[0])
    print(predict)

    con = sqlite3.connect(DATABASE)
    actual_data = con.execute('SELECT * FROM actual LIMIT 30') .fetchall()
    con.close()
    print(actual_data)

    d_html = today_time.strftime('%-m/%-d') #ゼロ埋め削除。Windowsでは、-mなどではなく、#mなどと表記する必要
    t_html = today_time.strftime('%-H:%M') #ゼロ埋め削除。Windowsでは、-Hなどではなく、#Hなどと表記する必要

    data = []
    for row in actual_data:
        data.append({'Date':row[0], 'Nikkei':"{:,.0f}".format(row[1]), 'predict':"{:,.0f}".format(row[2]), 'gap':"{:,.0f}".format(row[3]), 'Nikkei_dod':"{:,.0f}".format(row[4]), 'predict_dod':"{:,.0f}".format(row[5]), 'direction_check':row[6]})

    return render_template(
        'index.html',
        d_html=d_html,
        t_html=t_html,
        predict=predict,
        data=data
    )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host ='0.0.0.0',port = port)