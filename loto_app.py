import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup

# --- 【新機能】最新データをネットから取得する関数 ---
@st.cache_data(ttl=3600) # 1時間はキャッシュを保持
def get_latest_loto_data():
    # ※ここでは例として、常に最新のCSVを配信している信頼できるソース、
    # または公式サイトの構造を解析してデータを生成する処理を想定します。
    # 実際には、みずほ銀行のサイト等をスクレイピングするコードを書きます。
    url = "https://www.mizuhobank.co.jp/retail/takarakuji/loto/loto7/index.html"
    # ここにスクレイピングロジックを記述（今回は既存のCSVをベースに、
    # 手動アップロードの手間を省く「URL直接読み込み」を例示します）
    return pd.read_csv('あなたのオンラインストレージ上のCSV_URL')

# --- アプリ本体の改修 ---
st.title("🎯 ロト7 AI分析・予測システム (Auto-Update)")

# データの取得方法を選択できるようにする
data_source = st.radio("データソースを選択", ("自動更新(ネット)", "手動アップロード(CSV)"))

if data_source == "自動更新(ネット)":
    # ネット上の最新CSVを読み込む（GitHubなどに置いておくと便利です）
    csv_url = "https://raw.githubusercontent.com/sei002/loto7-app/refs/heads/main/%E3%83%AD%E3%83%887%E9%81%8E%E5%8E%BB%E3%83%87%E3%83%BC%E3%82%BF.csv"
    try:
        df = pd.read_csv(csv_url)
        st.success("最新データをネットから取得しました！")
    except:
        st.error("データの取得に失敗しました。手動アップロードを試してください。")
# ページ設定
st.set_page_config(page_title="ロト7 AI分析・予測アプリ", layout="wide")

st.title("🎯 ロト7 AI分析・予測システム")
st.sidebar.header("設定")

# 1. データアップロード
uploaded_file = st.sidebar.file_uploader("過去データ(CSV)をアップロード", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    target_cols = df.columns[2:9] # num1~num7
    
    # --- サイドバー設定 ---
    st.sidebar.subheader("分析パラメータ")
    window = st.sidebar.slider("直近分析回数", 5, 30, 10)
    target_set = st.sidebar.selectbox("次回セット予想", list("ABCDEFGHIJ"), index=0)

    # --- 分析エンジン (これまでのロジック) ---
    def get_markov_scores(data, previous_nums):
        matrix = np.zeros(38)
        for i in range(len(data) - 1):
            curr = set(data.iloc[i][target_cols].values)
            if not curr.isdisjoint(previous_nums):
                for n in data.iloc[i+1][target_cols].values:
                    matrix[int(n)] += 1
        return matrix / matrix.sum() if matrix.sum() > 0 else matrix

    def generate_ranking(data, t_set, p_nums):
        score_df = pd.DataFrame({'number': range(1, 38)})
        # セット偏差
        total_p = pd.Series(data[target_cols].values.flatten()).value_counts(normalize=True)
        set_p = pd.Series(data[data['set'] == t_set][target_cols].values.flatten()).value_counts(normalize=True)
        score_df['set_bias'] = score_df['number'].apply(lambda n: set_p.get(n, 0) / total_p.get(n, 7/37))
        # 直近トレンド
        recent = pd.Series(data.tail(window)[target_cols].values.flatten()).value_counts()
        score_df['recent'] = score_df['number'].apply(lambda n: recent.get(n, 0))
        # マルコフ
        m = get_markov_scores(data, p_nums)
        score_df['markov'] = score_df['number'].apply(lambda n: m[int(n)])
        # 総合算出
        score_df['score'] = (score_df['set_bias'] * 0.4) + (score_df['recent'] * 0.4) + (score_df['markov'] * 0.2)
        return score_df.sort_values('score', ascending=False)

    # --- メイン画面：次回予測 ---
    latest = df.iloc[-1]
    prev = set(latest[target_cols].values)
    ranking = generate_ranking(df, target_set, prev)
    top = ranking['number'].tolist()

    st.subheader("🔮 次回ロト7 予測結果")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.success(f"**本命 (F)**\n\n{sorted(top[:7])}")
    with col2:
        st.info(f"**対抗 (R)**\n\n{sorted(top[:5] + top[7:9])}")
    with col3:
        st.warning(f"**穴 (D)**\n\n{sorted(top[:3] + top[14:18])}")

    # --- 統計グラフ ---
    st.divider()
    st.subheader("📊 スコア分析推移")
    fig = px.bar(ranking, x='number', y='score', title="各数字の総合期待スコア")
    st.plotly_chart(fig, use_container_width=True)

    # --- 精度検証 (バックテスト) ---
    if st.button("過去50回の精度検証を実行"):
        with st.spinner('検証中...'):
            results = []
            for i in range(len(df)-50, len(df)):
                train = df.iloc[:i]
                actual = set(df.iloc[i][target_cols].values)
                r = generate_ranking(train, df.iloc[i]['set'], set(df.iloc[i-1][target_cols].values))
                results.append(len(set(r.head(7)['number']) & actual))
            
            st.write(f"✅ **検証完了**： 平均一致数 {np.mean(results):.2f} / 最大一致 {np.max(results)}")
            st.line_chart(results)

else:

    st.info("左側のサイドバーからCSVファイルをアップロードしてください。")
