# coding: UTF-8
import numpy as np
import pandas as pd
from tensorflow import keras
from pickle import load

from datetime import datetime
from datetime import date, timedelta
import re
import os
import sys
import glob
import shutil
import time
import calendar
import sqlite3

from bs4 import BeautifulSoup
import requests
from urllib.request import urlopen
from shutil import copyfileobj


def predict():
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
    DATABASE = 'database.db'

    # 既存データ読み込み・新規データと連結・整理
    dataframe = pd.read_excel('./Nikkei_10.xlsx', sheet_name='no_nan', usecols=[0, 1, 2, 3, 4, 5, 6, 7])
    dataset = dataframe[['Nikkei', 'EPS_ind', 'JBond10', 'JMB', 'JUER', 'JCPI', 'Dow']]
    dataset = dataset.astype('float32')

    # 今日・昨日・一昨日の日付を取得
    import pytz

    jst = pytz.timezone('Asia/Tokyo')
    today_time = datetime.now().astimezone(jst)
    today = today_time.date()
    yesterday = today - timedelta(days=1)
    the_day_before_yesterday = yesterday - timedelta(days=1)
    print('yesterday = ', yesterday)

    # 前日の日経平均の終値を取得
    r = requests.get('https://www.nikkei.com/markets/worldidx/chart/nk225/')
    soup = BeautifulSoup(r.text, 'html.parser')
    Nikkei_place = soup.find('span', class_='economic_value_now a-fs26')
    Nikkei = Nikkei_place.text
    Nikkei = float(Nikkei.split(' ')[0].replace(',', ''))
    print('Nikkei = ', Nikkei)

    # 前日のPER(指数ベース)終値を取得し、EPSを計算
    r = requests.get('https://indexes.nikkei.co.jp/nkave/archives/data?list=per')
    soup = BeautifulSoup(r.text, 'html.parser')

    elems_td = soup.find_all('td')

    keys = []
    for elem_td in elems_td:
        key = elem_td.text
        keys.append(key)

    keys = keys[3:]

    per_index_list = []
    for i, key in enumerate(keys):
        if i % 3 == 2:
            if key == '-':
                per_index_list.append('nan')
            else:
                per_index_list.append(float(key))

    per_index = per_index_list[-1]

    if per_index == 'nan':
        EPS_ind = float(dataset.EPS_ind[-1:])
    else:
        EPS_ind = float(Nikkei / per_index)

    print('per_index = ', per_index)
    print('EPS_ind = ', EPS_ind)

    # 前日の10年国債利回りの終値を取得
    r = requests.get('https://fund.smtb.jp/smtbhp/qsearch.exe?F=market3')
    soup = BeautifulSoup(r.text, 'html.parser')
    JBond10_place = soup.select_one(
        '#market3 > div > div > div.mod-layout > div > div:nth-child(1) > div > div > ul > li:nth-child(1) > span:nth-child(2) > b')
    JBond10 = JBond10_place.text
    JBond10 = float(JBond10.split(' ')[0].replace(',', ''))
    print('JBond10 = ', JBond10)

    # 前日の日本のマネタリーベースを、日銀サイトからCSVをダウンロードして取得
    current_dir = os.getcwd()  # カレントディレクトリの取得
    tmp_download_dir = f'{current_dir}\\tmpDownload'  # 一時ダウンロードフォルダパスの設定
    if os.path.isdir(tmp_download_dir):  # 一時フォルダが存在していたら消す(前回のが残存しているかも)
        shutil.rmtree(tmp_download_dir)
    os.mkdir(tmp_download_dir)  # 一時ダウンロードフォルダの作成

    url = "https://www.boj.or.jp/statistics/boj/other/mb/mblong.xlsx"
    save_name = url.split('/')[-1]

    with urlopen(url) as input_file, open(save_name, 'wb') as output_file:
        print("ダウンロード中")
        copyfileobj(input_file, output_file)
        print("ダウンロードが完了しました。")

    JMB_df = pd.read_excel(save_name, sheet_name='平残（Average amounts outstanding）', usecols=[2], skiprows=7, )
    JMB_df = JMB_df.dropna(how='all')
    JMB = int(JMB_df.iloc[-1:, 0])
    print('JMB = ', JMB)

    # 前日の失業率を取得
    r = requests.get('https://www.stat.go.jp/data/roudou/sokuhou/tsuki/index.html')
    soup = BeautifulSoup(r.text, 'html.parser')
    JUER_place = soup.select_one(
        '#section > article:nth-child(2) > table > tbody > tr:nth-child(3) > td:nth-child(4) > strong')
    JUER = JUER_place.text
    JUER = float(JUER.split(' ')[0].replace('%', ''))
    print('JUER = ', JUER)

    # 前日のCPIを取得
    r = requests.get('https://www.stat.go.jp/data/cpi/sokuhou/tsuki/index-z.html')
    soup = BeautifulSoup(r.text, 'html.parser')
    JCPI_place = soup.select_one('#section > article:nth-child(2) > div > p')
    # print(JCPI_place)
    JCPI_place_0 = JCPI_place.text.splitlines()[0]
    # print(JCPI_place_0)
    JCPI_place_0_0 = JCPI_place_0.split(' ')[1]
    # print(JCPI_place_0_0)
    JCPI = float(re.findall(r'\d+(?:\.\d+)?', JCPI_place_0_0)[-1])
    print('JCPI = ', JCPI)

    # 前日のダウ平均の終値を取得
    r = requests.get('https://us.kabutan.jp/indexes/%5EDJI/chart')
    soup = BeautifulSoup(r.text, 'html.parser')
    Dow_place = soup.select_one(
        'body > div > div > div.float-left.w-main > main > div.border-azure.border-2 > div.pr-2px.pb-2px.pl-2px > div.flex.justify-between.items-end > div.w-full.pr-2px > div.pl-1.pb-1.pr-2.flex > div.flex.w-full.items-end.justify-between > div.flex-1.text-right.text-3xl.mr-1')
    Dow = Dow_place.text
    Dow = Dow.split(' ')[0].replace('$', '')
    Dow = float(Dow.split(' ')[0].replace(',', ''))
    print('Dow = ', Dow)

    latest = pd.DataFrame(
        data=np.array([[yesterday, Nikkei, EPS_ind, JBond10, JMB, JUER, JCPI, Dow]]),
        columns=['Date', 'Nikkei', 'EPS_ind', 'JBond10', 'JMB', 'JUER', 'JCPI', 'Dow']
    )
    print(latest)
    print(latest.shape)

    # 既存データと新規データ連結・月次データを前月末日までさかのぼって上書き
    dataframe = pd.concat([dataframe, latest], axis=0)

    dt = dataframe['Date'].iloc[-1]
    if dt.month == 1:
        l_year = dt.year - 1
        l_month = 12
    else:
        l_year = dt.year
        l_month = dt.month - 1

    l_day = calendar.monthrange(dt.year, dt.month)[1]
    target_date = datetime(l_year, l_month, l_day)

    dataframe = dataframe.set_index('Date')

    dataframe.loc[target_date:, 'JMB'] = JMB
    dataframe.loc[target_date:, 'JUER'] = JUER
    dataframe.loc[target_date:, 'JCPI'] = JCPI

    dataframe.reset_index(inplace=True)

    dataframe.to_excel('./Nikkei_10.xlsx', sheet_name='no_nan', index=False)

    new_dataset = dataframe[['Nikkei', 'EPS_ind', 'JBond10', 'JMB', 'JUER', 'JCPI', 'Dow']].to_numpy()
    new_dataset = new_dataset.astype('float32')

    print(new_dataset[-10:])
    print(new_dataset.shape)

    lookback = 24
    actual = new_dataset[len(new_dataset) - lookback:, :]

    scaler_train = load(open('nikkei_10_standard.pkl', 'rb'))
    actual = scaler_train.transform(actual)
    mean, scale = scaler_train.mean_[0], scaler_train.scale_[0]

    # print(actual.shape)
    # print(actual)

    actual = actual.reshape(1, actual.shape[0], actual.shape[1])

    # print(actual.shape)
    # print(actual)

    model = keras.models.load_model('nikkei_10_rmse_274.h5', compile=False)

    # model.summary()

    predict = model.predict(actual)
    predict = predict * scale + mean
    predict = float(predict[0][0])

    print('今日の終値は、', predict, '円')

    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    cur.execute('INSERT INTO prediction(Date, predict) VALUES(?, ?)', [today, predict])
    con.commit()
    con.close()

    with sqlite3.connect(DATABASE) as con:
        df_from_sql = pd.read_sql('SELECT * FROM prediction', con)
    df_from_sql = df_from_sql.set_index('Date')
    if str(yesterday) in df_from_sql.index:
        last_predict = df_from_sql.loc[str(yesterday), 'predict']
    else:
        last_predict = 0
    print('last_predict = ', last_predict)

    with sqlite3.connect(DATABASE) as con:
        df_from_sql = pd.read_sql('SELECT * FROM prediction', con)
    df_from_sql = df_from_sql.set_index('Date')
    if str(the_day_before_yesterday) in df_from_sql.index:
        sec_last_predict = df_from_sql.loc[str(the_day_before_yesterday), 'predict']
    else:
        sec_last_predict = 0
    print('sec_last_predict = ', sec_last_predict)

    with sqlite3.connect(DATABASE) as con:
        df_from_sql = pd.read_sql('SELECT * FROM actual', con)
    df_from_sql = df_from_sql.set_index('Date')
    if str(the_day_before_yesterday) in df_from_sql.index:
        sec_last_Nikkei = df_from_sql.loc[str(the_day_before_yesterday), 'Nikkei']
    else:
        sec_last_Nikkei = 0
    print('sec_last_Nikkei = ', sec_last_Nikkei)

    if last_predict == 0:
        gap = 0
    else:
        gap = Nikkei - last_predict
    print('gap = ', gap)

    if sec_last_Nikkei == 0:
        Nikkei_dod = 0
    else:
        Nikkei_dod = Nikkei - sec_last_Nikkei
    print('Nikkei_dod = ', Nikkei_dod)

    if last_predict == 0 or sec_last_predict == 0:
        predict_dod = 0
    else:
        predict_dod = last_predict - sec_last_predict
    print('predict_dod = ', predict_dod)

    if Nikkei_dod == 0 and predict_dod == 0: direction_check = 'アタリ'
    if Nikkei_dod < 0 and predict_dod < 0: direction_check = 'アタリ'
    if Nikkei_dod > 0 and predict_dod > 0: direction_check = 'アタリ'
    if Nikkei_dod < 0 and predict_dod > 0: direction_check = 'はずれ'
    if Nikkei_dod > 0 and predict_dod < 0: direction_check = 'はずれ'
    if Nikkei_dod == 0 and predict_dod > 0: direction_check = 'はずれ'
    if Nikkei_dod == 0 and predict_dod < 0: direction_check = 'はずれ'
    if Nikkei_dod < 0 and predict_dod == 0: direction_check = 'はずれ'
    if Nikkei_dod > 0 and predict_dod == 0: direction_check = 'はずれ'

    print(direction_check)

    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    cur.execute(
        'INSERT INTO actual(Date, Nikkei, last_predict, gap, Nikkei_dod, predict_dod, direction_check) VALUES(?, ?, ?, ?, ?, ?, ? )',
        [yesterday, Nikkei, last_predict, gap, Nikkei_dod, predict_dod, direction_check])
    con.commit()
    con.close()