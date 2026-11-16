# 好日子創意所（Gooday Creative）網站

GitHub Pages 網站：https://goingtang.github.io/gooday-apps/

| 路徑 | 內容 |
|---|---|
| `index.html` | 開發者首頁 |
| `petpal/index.html` | PetPal 支援頁（常見問題） |
| `petpal/privacy.html` | PetPal 隱私權政策（商店上架使用） |
| `petpal/data/tw-pets.json` | 店家名冊資料（農業部公開資料，App 會下載） |
| `caresync/index.html` | 孝親協作站支援頁（常見問題） |
| `caresync/privacy.html` | 孝親協作站隱私權政策（商店上架使用） |
| `caresync/terms.html` | 孝親協作站使用條款 |

店家名冊每月 2 日由 `.github/workflows/tw-pets.yml` 自動更新（`scripts/build-tw-pets.py`）。下載失敗或筆數異常時不會覆蓋舊資料。

資料來源：農業部「獸醫師(佐)開業執照」「合法特定寵物業名單」，依政府資料開放授權條款－第 1 版使用。寵物業者的負責人與專任人員姓名不收錄。
