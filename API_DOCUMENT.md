# 🎄 聖誕甜點推薦系統 API 文件

## Base URL
```
https://christmas-dessert-backend.onrender.com
```

---

## 1. 甜點推薦 `/recommend`

根據使用者條件篩選甜點，並由 AI 生成推薦理由。

**Method:** `POST`

**Request Body:**
```json
{
  "type": "Cookie",
  "time": 60,
  "restrictions": ["Vegan", "Nut Free"]
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| type | string | 否 | `Cookie` / `Cake` / `Bread` / `All`（預設 `All`） |
| time | number | 否 | 最大可投入時間（分鐘） |
| restrictions | array | 否 | 飲食限制：`Vegan` / `No Alcohol` / `No Dairy` / `Nut Free` |

**Response:**
```json
{
  "count": 2,
  "results": [
    {
      "name": "英國：雪球曲奇（Melting Moments）",
      "ai_reason": "這款雪球曲奇入口即化，是聖誕夜最溫暖的選擇...",
      "image_path": "/static/images/1.png",
      "ingredients": ["無鹽奶油 100g", "糖粉 40g", "..."],
      "instructions": ["將奶油軟化後加入糖粉攪拌", "..."]
    },
    {
      "name": "德國：香料餅乾（Lebkuchen）",
      "ai_reason": "充滿肉桂與薑的香氣，讓整個廚房都瀰漫著節慶氛圍...",
      "image_path": "/static/images/2.png",
      "ingredients": ["..."],
      "instructions": ["..."]
    }
  ],
  "ai_model": "llama3-70b-8192"
}
```

---

## 2. 聖誕祝福卡 `/christmas_card`

由 AI 生成個人化聖誕祝福卡內容。

**Method:** `POST`

**Request Body:**
```json
{
  "name": "小雪",
  "desserts": ["雪球曲奇", "聖誕樹麵包"],
  "tone": "warm"
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| name | string | 否 | 收件人姓名（預設「聖誕甜點好友」） |
| desserts | array | 否 | 甜點名稱列表（會自然融入祝福語） |
| tone | string | 否 | 語氣風格：`warm`（溫暖）/ `festive`（歡樂）/ `classic`（經典） |

**Response:**
```json
{
  "recipient": "小雪",
  "tone": "warm",
  "message": "親愛的小雪，願這個聖誕夜被雪球曲奇的甜蜜與聖誕樹麵包的香氣包圍，讓溫暖的燭光照亮你的每一個願望 🎄✨",
  "ai_generated": true
}
```

---

## 3. 購物清單 `/shopping_list`

根據選擇的甜點生成合併的購物清單。

**Method:** `POST`

**Request Body:**
```json
{
  "recipes": [
    {"name": "英國：雪球曲奇（Melting Moments）"},
    {"id": 2, "category": "cookies"}
  ]
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| recipes | array | 是 | 甜點列表，可用 `name` 或 `id` + `category` 指定 |

**Response:**
```json
{
  "count": 2,
  "recipes": [
    {
      "category": "cookies",
      "id": 1,
      "name": "英國：雪球曲奇（Melting Moments）",
      "ingredients": ["無鹽奶油 100g", "糖粉 40g", "..."]
    },
    {
      "category": "cookies",
      "id": 2,
      "name": "德國：香料餅乾（Lebkuchen）",
      "ingredients": ["..."]
    }
  ],
  "shopping_list": [
    "低筋麵粉 150g",
    "無鹽奶油 100g",
    "糖粉 40g",
    "..."
  ]
}
```

---

## 錯誤回應格式

所有 API 在發生錯誤時會回傳：

```json
{
  "error": "錯誤類型說明",
  "message": "詳細錯誤訊息（選填）"
}
```

| HTTP 狀態碼 | 說明 |
|-------------|------|
| 400 | 請求格式錯誤（如非 JSON 或缺少必填欄位） |
| 500 | 伺服器內部錯誤 |

---

## 注意事項

1. **所有請求須設定 Header**：`Content-Type: application/json`
2. **AI 生成內容**：`/recommend` 與 `/christmas_card` 的回應由 AI 動態生成，每次可能略有不同
3. **回應語言**：所有 AI 生成內容皆為繁體中文
4. **跨網域請求**：已啟用 CORS，前端可直接呼叫

---

## 快速測試範例（使用 fetch）

```javascript
// 甜點推薦
fetch('https://christmas-dessert-backend.onrender.com/recommend', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    type: 'Cookie',
    time: 60,
    restrictions: []
  })
})
.then(res => res.json())
.then(data => console.log(data));

// 聖誕祝福卡
fetch('https://christmas-dessert-backend.onrender.com/christmas_card', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: '小雪',
    desserts: ['雪球曲奇'],
    tone: 'warm'
  })
})
.then(res => res.json())
.then(data => console.log(data));

// 購物清單
fetch('https://christmas-dessert-backend.onrender.com/shopping_list', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    recipes: [{ name: '英國：雪球曲奇（Melting Moments）' }]
  })
})
.then(res => res.json())
.then(data => console.log(data));
```

---

## 聯絡資訊

如有問題請聯繫後端組 🎁