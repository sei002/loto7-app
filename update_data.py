import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime

def get_latest_loto7():
    url = "https://www.mizuhobank.co.jp/retail/takarakuji/check/loto/loto7/index.html"
    response = requests.get(url)
    response.encoding = 'Shift_JIS'
    soup = BeautifulSoup(response.text, 'html.parser')

    # 回号・日付・本数字・セット球を取得するロジック
    # (※サイト構造に合わせて解析)
    try:
        times = soup.find('th', class_='alnCenter shadow').get_text(strip=True).replace('第', '').replace('回', '')
        numbers = [int(td.get_text(strip=True)) for td in soup.find_all('strong', class_='extension color01')]
        # 注意: セット球の自動取得は公式サイトの構造上難易度が高いため、
        # ここでは簡易的に「不明」または推測として処理
        return [times, datetime.date.today().strftime("%Y/%m/%d"), "X"] + numbers
    except:
        return None

# 既存のCSVを読み込んで追記
df = pd.read_csv('ロト7過去データ.csv')
latest_data = get_latest_loto7()

if latest_data and int(latest_data[0]) > int(df.iloc[-1, 0]):
    new_row = pd.Series(latest_data, index=df.columns)
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv('ロト7過去データ.csv', index=False)
    print("データを更新しました！")
else:
    print("更新の必要はありませんでした。")
