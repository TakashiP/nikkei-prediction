from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from datetime import date, datetime, timedelta
import pandas as pd
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
yesterday = today - timedelta(days=1)

# set configuration values
class Config:
    SCHEDULER_API_ENABLED = True

app.config.from_object(Config())

# initialize scheduler
scheduler = APScheduler()
# if you don't wanna use a config, you can set options here:
# scheduler.api_enabled = True
scheduler.init_app(app)

@scheduler.task('cron', id='do_job_1', hour='16', minute='50', timezone=jst) #11:30に設定すると7:40に動いた(サーバー時刻は22:40)。日ズレがKeyErrorを起こしている可能性があるため、一旦日を揃えるべく4時に設定し、11時起動を狙う。、1:20減らして10:20に設定し、6:30起動を目指す
def nikkei_prediction():
    Nikkei_10_utilized.predict()

scheduler.start()
## ここまでスケジューラー

@app.route('/')
def index():
    with sqlite3.connect(DATABASE) as con:
        df_from_sql = pd.read_sql('SELECT * FROM prediction', con)
    update_time = df_from_sql.iloc[-1,0]
    print(update_time)
    df_from_sql = df_from_sql.set_index('Date')
    if str(today) in df_from_sql.index:
        predict = df_from_sql.loc[str(today),'predict']
    else:
        predict = df_from_sql.loc[str(yesterday), 'predict']
    predict = "{:,.0f}".format(predict)
    print(predict)

    con = sqlite3.connect(DATABASE)
    actual_data = con.execute('SELECT * FROM actual LIMIT 30') .fetchall()
    con.close()
    print(actual_data)

    d_html = datetime.strptime(update_time, '%Y-%m-%d').strftime('%-m/%-d') #ゼロ埋め削除。Windowsでは、-mなどではなく、#mなどと表記する必要

    data = []
    for row in actual_data:
        data.append({'Date':row[0], 'Nikkei':"{:,.0f}".format(row[1]), 'predict':"{:,.0f}".format(row[2]), 'gap':"{:,.0f}".format(row[3]), 'Nikkei_dod':"{:,.0f}".format(row[4]), 'predict_dod':"{:,.0f}".format(row[5]), 'direction_check':row[6]})

    return render_template(
        'index.html',
        d_html=d_html,
        predict=predict,
        data=data
    )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host ='0.0.0.0',port = port)