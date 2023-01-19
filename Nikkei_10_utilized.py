# coding: UTF-8
import numpy as np
import pandas as pd
from pandas import read_excel
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.python.keras.models import load_model
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error
from datetime import datetime
from pickle import load

# ! pip install webdriver_manager
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.chrome.options import Options
from time import sleep
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

def predict():

    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
    DATABASE = 'database.db'

    #既存データ読み込み・新規データと連結・整理
    dataframe = pd.read_excel('./Nikkei_10.xlsx',sheet_name='no_nan',usecols=[0,1,2,3,4,5,6,7])
    dataset = dataframe[['Nikkei','EPS_ind','JBond10','JMB','JUER','JCPI','Dow']]
    dataset = dataset.astype('float32')

    # ここから各種データの取得・追加

    def scrape(url):
        options = Options()
        options.add_argument('--headless') # ヘッドレスモード
        driver_path = ChromeDriverManager().install()
        service = Service(executable_path=driver_path)
        browser = webdriver.Chrome(service=service, options=options)
        url = url
        browser.get(url)
        return browser

    def scrape_dl(url): #ファイルダウンロードを伴う処理
        current_dir = os.getcwd() # カレントディレクトリの取得
        tmp_download_dir = f'{current_dir}\\tmpDownload' # 一時ダウンロードフォルダパスの設定
        if os.path.isdir(tmp_download_dir): # 一時フォルダが存在していたら消す(前回のが残存しているかも)
            shutil.rmtree(tmp_download_dir)
        os.mkdir(tmp_download_dir) # 一時ダウンロードフォルダの作成
        from selenium.webdriver.chrome.options import Options
        options = Options()
        options.add_argument('--headless') # ヘッドレスモード
        prefs = {'download.default_directory': tmp_download_dir}
        options.add_experimental_option('prefs', prefs)
        driver_path = ChromeDriverManager().install()
        service = Service(executable_path=driver_path)
        browser = webdriver.Chrome(service=service, options=options)
        url = url
        browser.get(url)
        return browser, tmp_download_dir


    # 今日・昨日・一昨日の日付を取得
    today = date.today()
    yesterday = today - timedelta(days=1)
    the_day_before_yesterday = yesterday - timedelta(days=1)
    print('yesterday = ', yesterday)

    # 前日の日経平均の終値を取得
    browser = scrape('https://www.nikkei.com/markets/worldidx/chart/nk225/')
    Nikkei_place = browser.find_element(By.CLASS_NAME, 'economic_value')
    Nikkei = Nikkei_place.text
    Nikkei = float(Nikkei.split(' ')[0].replace(',',''))
    browser.quit()
    print('Nikkei = ', Nikkei)

    # 前日のPER(指数ベース)終値を取得し、EPSを計算
    browser = scrape('https://indexes.nikkei.co.jp/nkave/archives/data?list=per')

    elems_td = browser.find_elements(By.TAG_NAME, 'td')

    keys = []
    for elem_td in elems_td:
        key = elem_td.text
        keys.append(key)

    keys = keys[3:]

    per_index_list = []
    for i,key in enumerate(keys):
        if i%3 == 2:
            if key == '-':
                per_index_list.append('nan')
            else:
                per_index_list.append(float(key))

    per_index = per_index_list[-1]

    if per_index == 'nan':
        EPS_ind = float(dataset.EPS_ind[-1:])
    else:
        EPS_ind = float(Nikkei / per_index)

    browser.quit()
    print('per_index = ', per_index)
    print('EPS_ind = ', EPS_ind)

    # 前日の10年国債利回りの終値を取得
    browser = scrape('https://www.sbisec.co.jp/ETGate/?_ControlID=WPLETmgR001Control&_PageID=WPLETmgR001Mdtl20&_DataStoreID=DSWPLETmgR001Control&_ActionID=DefaultAID&burl=iris_indexDetail&cat1=market&cat2=index&dir=tl1-idxdtl%7Ctl2-JP10YT%3DXX%7Ctl5-jpn&file=index.html&getFlg=on')
    JBond10_place = browser.find_element(By.ID, 'idxdtlPrice')
    JBond10 = JBond10_place.text
    JBond10 = float(JBond10.split(' ')[0])
    browser.quit()
    print('JBond10 = ', JBond10)


    # 前日の日本のマネタリーベースを、日銀サイトからCSVをダウンロードして取得
    browser,tmp_download_dir = scrape_dl('https://www.boj.or.jp/statistics/boj/other/mb/mblong.xlsx')

    # 待機タイムアウト時間(秒)設定
    timeout_second = 10

    # 指定時間分待機
    for i in range(timeout_second + 1):
        # ファイル一覧取得
        download_fileName = glob.glob(f'{tmp_download_dir}\\*.*')

        # ファイルが存在する場合
        if download_fileName:
            # 拡張子の抽出
            extension = os.path.splitext(download_fileName[0])

            # 拡張子が '.crdownload' ではない ダウンロード完了 待機を抜ける
            if ".crdownload" not in extension[1]:
                time.sleep(2)
                break

        # 指定時間待っても .crdownload 以外のファイルが確認できない場合 エラー
        if i >= timeout_second:
            # == エラー処理をここに記載 ==
            # 終了処理
            browser.quit()
            # 一時フォルダの削除
            shutil.rmtree(tmp_download_dir)
            sys.exit()

        # 一秒待つ
        time.sleep(1)

    # === ダウンロード完了後処理 ===
    # Chromeを閉じる
    browser.quit()

    temp_df = pd.read_excel('./tmpDownload/mblong.xlsx',sheet_name='平残（Average amounts outstanding）',skiprows=7,usecols=[2])
    JMB = int(temp_df.iloc[-1:,0])

    # 一時フォルダの削除
    shutil.rmtree(tmp_download_dir)
    print('JMB = ', JMB)


    # 前日の失業率を取得
    browser = scrape('https://www.stat.go.jp/data/roudou/sokuhou/tsuki/index.html')
    elems_td = browser.find_element(By.CLASS_NAME, 'datatable')
    JUER_place = elems_td.find_element(By.TAG_NAME, 'strong')
    JUER = JUER_place.text
    JUER = float(JUER.replace('%',''))
    browser.quit()
    print('JUER = ', JUER)


    # 前日のCPIを取得
    browser = scrape('https://www.stat.go.jp/data/cpi/sokuhou/tsuki/index-z.html')
    section = browser.find_element(By.ID, "section")
    article = section.find_elements(By.TAG_NAME, "article")[1]
    p = article.find_element(By.TAG_NAME, "p")
    p_0 = p.text.splitlines()[0]
    JCPI = float(re.findall(r'\d+(?:\.\d+)?',p_0)[-1])
    print('JCPI = ', JCPI)
    browser.quit()

    # 前日のダウ平均の終値を取得
    browser = scrape('https://finance.yahoo.co.jp/quote/%5EDJI')
    Dow_place = browser.find_element(By.CLASS_NAME, '_3BGK5SVf')
    Dow = Dow_place.text
    Dow = float(Dow.replace(',',''))
    browser.quit()
    print('Dow = ', Dow)


    latest = pd.DataFrame(
        data=np.array([[yesterday, Nikkei, EPS_ind, JBond10, JMB, JUER, JCPI, Dow]]),
        columns=['Date','Nikkei','EPS_ind','JBond10','JMB','JUER','JCPI','Dow']
        )
    print(latest)
    print(latest.shape)

    #既存データと新規データ連結・月次データを前月末日までさかのぼって上書き
    dataframe = pd.concat([dataframe,latest], axis=0)

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

    dataframe.to_excel('./Nikkei_10.xlsx',sheet_name='no_nan',index=False)

    new_dataset = dataframe[['Nikkei','EPS_ind','JBond10','JMB','JUER','JCPI','Dow']].to_numpy()
    new_dataset = new_dataset.astype('float32')

    print(new_dataset[-10:])
    print(new_dataset.shape)

    lookback = 24
    actual = new_dataset[len(new_dataset)-lookback:,:]

    scaler_train = load(open('nikkei_10_standard.pkl', 'rb'))
    actual = scaler_train.transform(actual)
    mean, scale = scaler_train.mean_[0], scaler_train.scale_[0]

    # print(actual.shape)
    # print(actual)


    actual = actual.reshape(1,actual.shape[0], actual.shape[1])

    # print(actual.shape)
    # print(actual)

    model = keras.models.load_model('nikkei_10_rmse_274.h5', compile=False)

    # model.summary()

    predict = model.predict(actual)
    predict = predict*scale + mean
    predict = float(predict[0][0])
    print('今日の終値は、',predict,'円')

    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    cur.execute('INSERT INTO prediction(Date, predict) VALUES(?, ?)', [today, int(predict)])
    con.commit()
    con.close()

    with sqlite3.connect(DATABASE) as con:
        df_from_sql = pd.read_sql('SELECT * FROM prediction', con)
    df_from_sql = df_from_sql.set_index('Date')
    if str(yesterday) in df_from_sql.index:
        last_predict = df_from_sql.loc[str(yesterday),'predict']
    else:
        last_predict = 0
    print('last_predict = ', last_predict)

    with sqlite3.connect(DATABASE) as con:
        df_from_sql = pd.read_sql('SELECT * FROM prediction', con)
    df_from_sql = df_from_sql.set_index('Date')
    if str(the_day_before_yesterday) in df_from_sql.index:
        sec_last_predict = df_from_sql.loc[str(the_day_before_yesterday),'predict']
    else:
        sec_last_predict = 0
    print('sec_last_predict = ', sec_last_predict)

    with sqlite3.connect(DATABASE) as con:
        df_from_sql = pd.read_sql('SELECT * FROM actual', con)
    df_from_sql = df_from_sql.set_index('Date')
    if str(the_day_before_yesterday) in df_from_sql.index:
        sec_last_Nikkei = df_from_sql.loc[str(the_day_before_yesterday),'Nikkei']
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
    cur.execute('INSERT INTO actual(Date, Nikkei, last_predict, gap, Nikkei_dod, predict_dod, direction_check) VALUES(?, ?, ?, ?, ?, ?, ? )',
                [yesterday, int(Nikkei), int(last_predict), int(gap), int(Nikkei_dod), int(predict_dod), direction_check])
    con.commit()
    con.close()