import sqlite3

DATABASE = 'database.db'

def create_actual_table(): #actualのテーブルをつくる関数を定義する。
    con = sqlite3.connect(DATABASE)
    con.execute("CREATE TABLE IF NOT EXISTS actual (Date DATE PRIMARY KEY,Nikkei FLOAT64,last_predict FLOAT64,gap FLOAT64,Nikkei_dod FLOAT64,predict_dod FLOAT64,direction_check STRING)")
    con.close()

def create_prediction_table(): #predictのテーブルをつくる関数を定義する。
    con = sqlite3.connect(DATABASE)
    con.execute("CREATE TABLE IF NOT EXISTS prediction (Date DATE PRIMARY KEY, predict FLOAT64)")
    con.close()
