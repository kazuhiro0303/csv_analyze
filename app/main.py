from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
from sklearn.linear_model import LinearRegression
import io
import redis
import pickle

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Redis接続（Dockerネットワーク内なのでサービス名）
r = redis.Redis(host="redis", port=6379, decode_responses=False)


# ==============================
# Redis保存・読込
# ==============================

def save_df(df):
    r.set("data", pickle.dumps(df))


def load_df():
    data = r.get("data")
    if data is None:
        return None
    return pickle.loads(data)


# ==============================
# 画面表示
# ==============================

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ==============================
# 解析処理
# ==============================

@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    request: Request,
    file: UploadFile = File(...),
    feature: str = Form(...),
    target: str = Form(...)
):
    try:
        # CSV読み込み
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        # Redisに保存
        save_df(df)

        # Redisから読み出し（実運用想定）
        df = load_df()
        if df is None:
            return templates.TemplateResponse(
                "result.html",
                {"request": request, "error": "データが保存されていません"}
            )

        # 列存在チェック
        if feature not in df.columns or target not in df.columns:
            return templates.TemplateResponse(
                "result.html",
                {"request": request, "error": "指定した列が存在しません"}
            )

        # 回帰
        X = df[[feature]]
        y = df[target]

        model = LinearRegression()
        model.fit(X, y)

        coef = round(model.coef_[0], 2)
        intercept = round(model.intercept_, 2)

        # 統計量
        stats = df.describe().to_dict()

        return templates.TemplateResponse(
            "result.html",
            {
                "request": request,
                "coef": coef,
                "intercept": intercept,
                "feature": feature,
                "target": target,
                "stats": stats
            }
        )

    except Exception as e:
        return templates.TemplateResponse(
            "result.html",
            {"request": request, "error": str(e)}
        )