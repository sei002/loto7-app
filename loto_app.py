import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests

# 1. ページ設定 (必ず一番最初に書く)
st.set_page_config(page_title="ロト7 AI分析・予測アプリ", layout="wide")

# --- タイトル ---
st.title("🎯 ロト7 AI分析・予測システム (Auto-Update)")

# --- サイドバー設定 ---
st.sidebar.header("設定")
data_source = st.sidebar.radio("データソースを選択", ("自動更新(ネット)", "手動アップロード(CSV)"))

# 2. データの読み込み
df = None

if data_source == "自動更新(ネット)":
    # あなたのGitHubのRawデータURL
    csv_url = "https://raw.githubusercontent.com/sei002/loto7-app/refs/heads/main/%E3%83%AD%E3%83%887%E9%81%8E%E5%8E%BB%E3%83%87%E3%83%BC%E3%82%BF.csv"
    try:
        df = pd.read_csv(csv_url)
        st.success("最新データをネットから取得しました！")
    except Exception as e:
        st.error(f"ネットからの取得に失敗しました: {e}")

else:
    uploaded_file = st.sidebar.file_uploader("過去データ(CSV)をアップロード", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.success("CSVを読み込みました。")

# 3. メイン処理（データがある場合のみ実行）
if df is not None:
    # --- 列名の設定 (あなたのCSVに合わせて num1~num7 を使用) ---
    target_cols = ['num1', 'num2', 'num3', 'num4', 'num5', 'num6', 'num7']
    
    # 全ての数字を数値型に変換
    for col in target_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 欠損値（空欄）がある行を削除
    df = df.dropna(subset=target_cols)

    # パラメータ設定
    window = st.sidebar.slider("直近分析回数", 5, 30, 10)
    target_set = st.sidebar.selectbox("次回セット予想", list("ABCDEFGHIJ"), index=0)

    # --- 分析エンジン (マルコフ・セット・トレンド) ---
    def get_markov_scores(data, previous_nums):
        matrix = np.zeros(38) # 1~37用
        for i in range(len(data) - 1):
            curr = set(data.iloc[i][target_cols].values)
            if not curr.isdisjoint(previous_nums):
                for n in data.iloc[i+1][target_cols].values:
                    if 1 <= int(n) <= 37:
                        matrix[int(n)] += 1
        return matrix / matrix.sum() if matrix.sum() > 0 else matrix

    def generate_ranking(data, t_set, p_nums):
        score_df = pd.DataFrame({'number': range(1, 38)})
        
        # セット偏差
        total_p = pd.Series(data[target_cols].values.flatten()).value_counts(normalize=True)
        set_data = data[data['set'] == t_set]
        if not set_data.empty:
            set_p = pd.Series(set_data[target_cols].values.flatten()).value_counts(normalize=True)
        else:
            set_p = pd.Series()
        
        score_df['set_bias'] = score_df['number'].apply(lambda n: set_p.get(n, 0) / total_p.get(n, 7/37) if total_p.get(n, 0) > 0 else 0)
        
        # 直近トレンド
        recent = pd.Series(data.tail(window)[target_cols].values.flatten()).value_counts()
        score_df['recent'] = score_df['number'].apply(lambda n: recent.get(n, 0))
        
        # マルコフ
        m = get_markov_scores(data, p_nums)
        score_df['markov'] = score_df['number'].apply(lambda n: m[int(n)] if int(n) < len(m) else 0)
        
        # 総合スコア算出
        score_df['score'] = (score_df['set_bias'] * 0.4) + (score_df['recent'] * 0.4) + (score_df['markov'] * 0.2)
        return score_df.sort_values('score', ascending=False)

    # --- 予測実行 ---
    latest = df.iloc[-1]
    prev = set(latest[target_cols].values)
    ranking = generate_ranking(df, target_set, prev)
    top = ranking['number'].astype(int).tolist()

    st.subheader("🔮 次回ロト7 AI予測結果")
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
    fig = px.bar(ranking, x='number', y='score', title="各数字の総合期待スコア", labels={'number':'数字', 'score':'期待度'})
    st.plotly_chart(fig, use_container_width=True)

    # --- バックテスト ---
    if st.button("過去50回の精度検証を実行"):
        with st.spinner('検証中...'):
            test_results = []
            for i in range(len(df)-50, len(df)):
                if i < 1: continue
                train = df.iloc[:i]
                actual = set(df.iloc[i][target_cols].values)
                r = generate_ranking(train, df.iloc[i]['set'], set(df.iloc[i-1][target_cols].values))
                test_results.append(len(set(r.head(7)['number']) & actual))
            
            st.write(f"✅ **検証完了**： 平均一致数 {np.mean(test_results):.2f} / 最大一致 {np.max(test_results)}")
            st.line_chart(test_results)

else:
    st.info("サイドバーから『自動更新』を選択するか、CSVファイルをアップロードしてください。")
