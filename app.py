from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

# ==========================================
# 1. データ読み込みと前処理
# ==========================================

# --- 映画データ (movies_100k.csv) ---
# 特徴: パイプ(|)区切り, 列名が movie_id, movie_title
try:
    movies = pd.read_csv('movies_100k.csv', sep='|', encoding='utf-8')
except UnicodeDecodeError:
    movies = pd.read_csv('movies_100k.csv', sep='|', encoding='cp932')

# プログラムで扱いやすいように列名を変更 (movie_id -> movieId, movie_title -> title)
movies = movies.rename(columns={'movie_id': 'movieId', 'movie_title': 'title'})

# 文字列型に変換（結合のキーにするため）
movies['movieId'] = movies['movieId'].astype(str)


# --- 評価データ (ratings_100k.csv) ---
# 特徴: カンマ(,)区切り, 列名が userId, movieId ... (最初からこの名前)
ratings = pd.read_csv('ratings_100k.csv', sep=',')

# 文字列型に変換（結合のキーにするため）
ratings['movieId'] = ratings['movieId'].astype(str)


# --- データの結合 ---
# movieId をキーにして結合します
data = pd.merge(ratings, movies, on='movieId')


# --- 協調フィルタリング用のデータ作成 ---
# 評価値(rating)を数値型に変換
data['rating'] = pd.to_numeric(data['rating'], errors='coerce')

# ユーザー×映画のクロス集計表を作成
# 行: userId, 列: title, 値: rating
user_movie_rating = data.pivot_table(index='userId', columns='title', values='rating')


# ==========================================
# 2. ロジック関数定義
# ==========================================

def get_top_rated_movies(n=5):
    """未選択時: 人気ランキング"""
    # 映画ごとの評価数と平均点を計算
    rating_stats = data.groupby('title')['rating'].agg(['count', 'mean'])
    
    # 評価数が10件以上の映画に絞る（信頼性担保）
    popular_movies = rating_stats[rating_stats['count'] > 10]
    
    # 平均点が高い順にソート
    top_movies = popular_movies.sort_values(by='mean', ascending=False).head(n)
    return top_movies.index.tolist()

def get_recommendations(selected_movies, n=5):
    """選択時: アイテムベース協調フィルタリング"""
    similar_scores = pd.Series(dtype='float64')

    for movie_title in selected_movies:
        if movie_title not in user_movie_rating.columns:
            continue # データにない映画は無視

        # その映画と似ている（相関が高い）映画を探す
        similar_movies = user_movie_rating.corrwith(user_movie_rating[movie_title])
        
        # スコアを加算
        similar_scores = similar_scores.add(similar_movies, fill_value=0)

    # スコア順に並び替え
    recommendations = similar_scores.sort_values(ascending=False)
    
    # 自分自身（選んだ映画）は除外
    recommendations = recommendations.drop(labels=selected_movies, errors='ignore')
    
    return recommendations.head(n).index.tolist()


# ==========================================
# 3. ルーティング設定
# ==========================================

@app.route('/', methods=['GET', 'POST'])
def index():
    # 全映画リストを画面に渡す（重複なし、ソート済み）
    all_titles = movies['title'].sort_values().unique()
    return render_template('index.html', movies=all_titles)

@app.route('/recommend', methods=['POST'])
def recommend():
    movie1 = request.form.get('movie1')
    movie2 = request.form.get('movie2')
    movie3 = request.form.get('movie3')
    
    # 空白を除去してリスト化
    selected = [m for m in [movie1, movie2, movie3] if m]

    if not selected:
        # 未選択ならランキング
        result_movies = get_top_rated_movies()
        title_text = "未選択のため、高評価の映画を表示します"
    else:
        # 選択があればレコメンド
        result_movies = get_recommendations(selected)
        title_text = "オススメ映画トップ5"

    return render_template('result.html', recommendations=result_movies, title_text=title_text)

if __name__ == '__main__':
    app.run(debug=True)