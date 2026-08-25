# 陳昱傑骨科診所 內容監控

每週監控 [陳昱傑骨科診所](https://orthoblessing.com.tw/) 的新文章。

## 為什麼不是抓 Facebook 粉專

原始需求是監控 [FB 粉專 orthoblessing](https://www.facebook.com/orthoblessing)，但實測不可行：

- `www.facebook.com/orthoblessing` 回 HTTP 200，內容卻是登入牆，只拿得到粉專名稱
- `m.facebook.com` / `mbasic.facebook.com` 直接回 HTTP 400

Meta 自 2018 年起封鎖未登入的粉專內容讀取；用 Graph API 讀取**他人**粉專貼文，
需要通過 App Review 的 Page Public Content Access 權限。

改抓官網 RSS（`https://orthoblessing.com.tw/feed/`），內容與粉專高度重疊：
衛教短影音、PRP 問答、痛痛飛走週報、病人見證。

## 用法

```bash
python3 monitor_posts.py            # 過去 7 天，輸出 Markdown
python3 monitor_posts.py --days 14  # 自訂回溯天數
python3 monitor_posts.py --json     # 輸出 JSON 供程式串接
```

只用 Python 標準函式庫，不需安裝套件。RSS 單頁 10 篇，腳本會自動往回翻頁
直到超出時間範圍，因此一週內發布超過 10 篇也不會漏抓。
