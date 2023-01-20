"""
# 起動するときは、以下を入力して、Flaskアプリを環境変数に一時的に設定してから実行
# Pycharmのターミナルの場合
$env:FLASK_APP='main'
$env:FLASK_ENV='development'
flask run

# WindowsのCMDの場合
set FLASK_APP=main # フォルダ名に揃える
set FLASK_ENV=development
flask run

# http://127.0.0.1:5000/ の意味。Webアプリを提供しているローカルホストサーバーの入口のうち、5000番にWebブラウザでアクセスしている。
http://127.0.0.1: ローカルホストサーバー。自分のコンピューターの中に立ち上げたWebサーバー。Webアプリを提供しているもの。
5000：ポート。データを受け渡しする入口
"""