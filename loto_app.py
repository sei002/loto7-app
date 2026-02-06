import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. ページ設定
st.set_page_config(page_title="ロト7 AIセット別分析アプリ", layout="wide")

# --- タイトル ---
st.title("🎯 ロト7 AI分析・予測システム (Set-Specific)")

# --- サイドバー設定 ---
st.sidebar.header("設定")
data_source = st.sidebar.radio("データソースを選択", ("自動更新(ネット)", "手動アップロード(CSV)"))

# 2. データの読み込み
df = None

if data_source == "自動更新(ネット)":
    csv_url = "https://raw.githubusercontent.com/sei002/loto7-app/refs/heads/main/%E3%83%AD%E3%83%887%E9%81%8E%E5%8E%BB%E3%83%87%E3%83%BC%E3%82%BF.csv"
    try:
        df = pd.read_csv(csv_url)
        st.success("最新データを取得しました！")
    except Exception as e:
        st.error(f"取得失敗: {e}")
else:
    uploaded_file = st.sidebar.file_uploader("CSVをアップロード", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)

# 3. メイン処理
if df is not None:
    # データクレンジング
    target_cols = ['num1', 'num2', 'num3', 'num4', 'num5', 'num6', 'num7']
    for col in target_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=target_cols)

    # --- セット球選択ボタン (タブ形式) ---
    st.subheader("📂 分析対象のセット球を選択してください")
    tabs = st.tabs([f"セット {s}" for s in "ABCDEFGHIJ"])
    
    # 選択されたセットを判定（タブのインデックスからA-Jを取得）
    selected_set_index = 0
    for i, tab in enumerate(tabs):
        with tab:
            target_set = chr(65 + i)  # A, B, C...
            st.write(f"### セット {target_set} のデータに基づいた予測")
            # このタブが選択されている時に処理を走らせるためのフラグ
            selected_set = target_set

    # --- フィルタリング ---
    # 1. 全データ (マルコフ連鎖などの推移計算用)
    # 2. 選択されたセットのみのデータ (セット傾向分析用)
    df_set_only = df[df['set'] == selected_set]
    
    if df_set_only.empty:
        st.warning(f"セット {selected_set} のデータがCSV内に見つかりません。")
    else:
        # パラメータ設定
        window = st.sidebar.slider(f"セット {selected_set} の直近分析回数", 3, len(df_set_only), min(10, len(df_set_only)))

        # --- 分析エンジン ---
        def generate_ranking(full_data, set_data, p_nums):
            score_df = pd.DataFrame({'number': range(1, 38)})
            
            # 1. セット内出現頻度 (このセットでよく出る数字)
            set_counts = pd.Series(set_data[target_cols].values.flatten()).value_counts(normalize=True)
            score_df['set_bias'] = score_df['number'].apply(lambda n: set_counts.get(n, 0))
            
            # 2. 直近トレンド (このセットにおける最近の傾向)
            recent = pd.Series(set_data.tail(window)[target_cols].values.flatten()).value_counts()
            score_df['recent'] = score_df['number'].apply(lambda n: recent.get(n, 0))
            
            # 3. マルコフ連鎖 (全データからの推移確率)
            # ※前回がどのセットでも、今の数字から次に出やすい数字を計算
            matrix = np.zeros(38)
            for i in range(len(full_data) - 1):
                curr = set(full_data.iloc[i][target_cols].values)
                if not curr.isdisjoint(p_nums):
                    for n in full_data.iloc[i+1][target_cols].values:
                        if 1 <= int(n) <= 37: matrix[int(n)] += 1
            
            m_norm = matrix / matrix.sum() if matrix.sum() > 0 else matrix
            score_df['markov'] = score_df['number'].apply(lambda n: m_norm[int(n)])
            
            # 総合スコア
            score_df['score'] = (score_df['set_bias'] * 0.5) + (score_df['recent'] * 0.3) + (score_df['markov'] * 0.2)
            return score_df.sort_values('score', ascending=False)

        # 予測実行
        latest_nums = set(df.iloc[-1][target_cols].values)
        ranking = generate_ranking(df, df_set_only, latest_nums)
        top = ranking['number'].astype(int).tolist()

        # --- 結果表示 ---
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.success(f"**本命 (F)**\n\n{sorted(top[:7])}")
        with col2:
            st.info(f"**対抗 (R)**\n\n{sorted(top[:5] + top[7:9])}")
        with col3:
            st.warning(f"**穴 (D)**\n\n{sorted(top[:3] + top[14:18])}")

        # 統計グラフ
        st.subheader(f"📊 セット {selected_set} 分析スコア")
        fig = px.bar(ranking, x='number', y='score', color='score', color_continuous_scale='Viridis')
        st.plotly_chart(fig, use_container_width=True)

        # --- セット限定の過去50回検証 ---
        if st.button(f"セット {selected_set} 限定で精度検証"):
            with st.spinner('検証中...'):
                test_results = []
                # セット球限定のデータでバックテスト
                for i in range(len(df_set_only)-10, len(df_set_only)):
                    if i < 2: continue
                    test_train = df_set_only.iloc[:i]
                    actual = set(df_set_only.iloc[i][target_cols].values)
                    # その時の「前回の数字」を取得
                    original_idx = df_set_only.index[i]
                    prev_nums = set(df.loc[original_idx-1][target_cols].values)
                    
                    r = generate_ranking(df.loc[:original_idx-1], test_train, prev_nums)
                    test_results.append(len(set(r.head(7)['number']) & actual))
                
                st.write(f"✅ **検証完了** (直近{len(test_results)}回)： 平均一致数 {np.mean(test_results):.2f}")
                st.line_chart(test_results)

else:
    st.info("データを選択してください。")
