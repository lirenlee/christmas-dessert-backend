import json
import os
import random
import re
from copy import deepcopy
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

try:
    from groq import Groq
except ImportError:
    Groq = None

GROQ_MODEL = "llama3-70b-8192"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'recipes.json')

app = Flask(__name__)
CORS(app)

DEFAULT_CATEGORIES = ['cookies', 'cakes', 'breads']

TYPE_MAP = {
    'cookie': 'cookies',
    'cake': 'cakes',
    'bread': 'breads'
}

RESTRICTION_KEYWORDS = {
    'vegan': ['蛋', '奶', '牛', '蜜', '鮮奶油'],
    'no alcohol': ['酒', '蘭姆', '威士忌', '啤酒'],
    'no dairy': ['奶', '起司', '乳酪', '優格', '奶油'],
    'nut free': ['杏仁', '核桃', '堅果', '花生', '開心果']
}


def load_recipes():
    with open(DATA_PATH, 'r', encoding='utf-8') as fp:
        return json.load(fp)


def normalize_type(user_type: str):
    if not user_type:
        return ['cookies', 'cakes', 'breads']
    key = user_type.strip().lower()
    if key == 'all':
        return ['cookies', 'cakes', 'breads']
    return [TYPE_MAP.get(key, key if key.endswith('s') else f'{key}s')]


def extract_time(recipe):
    total_time = recipe.get('total_time', 0)
    if isinstance(total_time, dict):
        value = total_time.get('min')
        if value is None:
            value = total_time.get('max', 0)
        try:
            return int(value)
        except (TypeError, ValueError):
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return 0
    try:
        return int(total_time)
    except (TypeError, ValueError):
        try:
            return int(float(total_time))
        except (TypeError, ValueError):
            return 0


def violates_restriction(ingredients_text: str, restrictions):
    for r in restrictions:
        keywords = RESTRICTION_KEYWORDS.get(r)
        if not keywords:
            continue
        if any(keyword in ingredients_text for keyword in keywords):
            return True
    return False


def filter_recipes(data, user_type, user_time, user_restrictions):
    categories = normalize_type(user_type)
    restrictions = [r.strip().lower() for r in (user_restrictions or []) if r.strip()]
    categories = categories or ['cookies', 'cakes', 'breads']
    results = []
    cats = data.get('categories', {})

    def iterate_recipes(target_categories):
        for cat in target_categories:
            for recipe in cats.get(cat, []):
                yield recipe

    for recipe in iterate_recipes(categories):
        total_minutes = extract_time(recipe)
        if user_time is not None and (total_minutes == 0 or total_minutes > user_time):
            continue

        ingredients_text = ' '.join(recipe.get('ingredients', [])).lower()
        if violates_restriction(ingredients_text, restrictions):
            continue

        results.append((total_minutes if total_minutes else float('inf'), recipe))

    results.sort(key=lambda item: item[0])
    filtered = [recipe for _, recipe in results]

    if len(filtered) >= 2:
        return filtered[:2]

    final = list(filtered)
    seen_keys = {(recipe.get('id'), recipe.get('name')) for recipe in final}

    def add_from_categories(target_categories):
        nonlocal final, seen_keys
        pool = []
        for recipe in iterate_recipes(target_categories):
            pool.append((extract_time(recipe) or float('inf'), recipe))
        pool.sort(key=lambda item: item[0])
        for _, recipe in pool:
            key = (recipe.get('id'), recipe.get('name'))
            if key in seen_keys:
                continue
            final.append(recipe)
            seen_keys.add(key)
            if len(final) >= 2:
                break

    add_from_categories(categories)
    if len(final) < 2:
        add_from_categories(['cookies', 'cakes', 'breads'])

    return final[:2]


def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or Groq is None:
        return None
    return Groq(api_key=api_key)


def generate_ai_reasons(desserts, user_context):
    """呼叫 Groq Llama3-70B 產生兩段節慶推薦理由，若失敗回傳預設訊息。"""
    if not desserts:
        return ["這道甜點非常適合聖誕節！"]
    
    client = get_groq_client()
    if client is None:
        return [
            f"因為你選擇了 {desserts[0].get('name')}，它能在節慶裡帶來甜蜜的陪伴。",
            f"另外推薦 {desserts[1].get('name')}，暖暖香氣很適合聖誕夜。"
        ] if len(desserts) >= 2 else ["這道甜點非常適合聖誕節！"]

    dessert_names = [d.get("name") for d in desserts[:2]]
    
    prompt_payload = {
        "user_preferences": user_context,
        "desserts": [
            {
                "name": d.get("name"),
                "total_time": d.get("total_time"),
                "ingredients": d.get("ingredients", []),
                "country": d.get("country")
            }
            for d in desserts[:2]
        ]
    }

    system_msg = (
        "你是一位來自台灣、擁有多年經驗的聖誕節甜點專家。"
        "你必須全程使用繁體中文回覆，絕對禁止使用簡體中文。"
        "你絕對不可以夾雜任何英文單字或詞彙，所有內容必須是純繁體中文。"
        "請以溫暖、真摯、帶有濃厚聖誕節氣氛的台灣在地語氣撰寫內容，語氣需甜蜜、溫馨。"
        "針對使用者條件，為兩道甜點各寫一段兩句以內的推薦理由。"
        "推薦理由需能讓人感受到聖誕節的溫暖、甜蜜與節慶氛圍。"
        "句子需自然、貼近台灣人的日常語氣，不可僵硬或像官方文宣。"
        f"第一道甜點名稱是「{dessert_names[0]}」，第二道甜點名稱是「{dessert_names[1]}」。"
        "輸出格式為純 JSON 陣列，格式如下：\n"
        "[{\"name\": \"第一道甜點完整名稱\", \"reason\": \"推薦理由\"}, {\"name\": \"第二道甜點完整名稱\", \"reason\": \"推薦理由\"}]\n"
        "只允許輸出 JSON，不得加入任何額外文字、說明、markdown 標記或程式碼區塊符號。"
    )

    user_msg = (
        "以下是使用者的條件與候選甜點，請依指示產生回覆：\n"
        f"{json.dumps(prompt_payload, ensure_ascii=False)}"
    )

    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.7
        )
        content = completion.choices[0].message.content.strip()
        
        if "```" in content:
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            content = content.strip()
        
        parsed = json.loads(content)
        
        reasons = []
        for item in parsed[:2]:
            reason = item.get("reason", "")
            if reason:
                reasons.append(reason)
        
        if len(reasons) >= 2:
            return reasons[:2]
            
    except Exception:
        pass

    return [
        f"{desserts[0].get('name')} 是最甜蜜的選擇，讓聖誕夜充滿暖意。",
        f"同時試試 {desserts[1].get('name')}，香氣與口感都能為節慶增添驚喜。"
    ] if len(desserts) >= 2 else ["這道甜點非常適合聖誕節！"]


def generate_ai_christmas_card(recipient, desserts, tone):
    """呼叫 Groq Llama3-70B 產生聖誕祝福卡內容，若失敗回傳預設訊息。"""
    client = get_groq_client()
    
    dessert_text = '、'.join(desserts[:3]) if desserts else ''
    
    # 預設訊息（AI 失敗時使用）
    fallback_messages = {
        'warm': f"親愛的 {recipient}，願這個冬夜被閃爍燈火和甜香包圍，{f'特別為你準備了{dessert_text}，' if dessert_text else ''}願你心裡的願望都在雪花落下時悄悄成真 🎄✨",
        'festive': f"嗨嗨！{recipient}，聖誕老公公已經把快樂裝進雪橇，{f'還有{dessert_text}等著你，' if dessert_text else ''}祝你今晚被驚喜和美味包圍 🎅🏼🎉",
        'classic': f"敬愛的 {recipient}，伴隨著聖誕鐘聲，{f'為你獻上{dessert_text}，' if dessert_text else ''}願平安與喜樂在這個季節長駐你心，祝聖誕快樂。"
    }
    
    if client is None:
        return fallback_messages.get(tone, fallback_messages['warm'])

    tone_descriptions = {
        'warm': '溫暖、真摯、甜蜜',
        'festive': '歡樂、活潑、充滿驚喜',
        'classic': '優雅、正式、傳統'
    }
    tone_desc = tone_descriptions.get(tone, tone_descriptions['warm'])

    system_msg = (
        "你是一位來自台灣、擅長撰寫溫馨祝福語的聖誕卡片專家。"
        "你必須全程使用繁體中文回覆，絕對禁止使用簡體中文。"
        "你絕對不可以夾雜任何英文單字或詞彙，所有內容必須是純繁體中文。"
        "請撰寫一段聖誕祝福卡片內容，長度約三到四句話。"
        "內容需充滿聖誕節的溫暖氛圍，讓收到的人感受到滿滿的祝福與愛。"
        "可以適當使用聖誕相關的表情符號，如 🎄✨🎁🎅🏼❄️🌟 等。"
        "只輸出祝福語內容，不要加入任何額外說明或標記。"
    )

    user_msg = (
        f"請為「{recipient}」撰寫一張聖誕祝福卡片。\n"
        f"語氣風格：{tone_desc}\n"
    )
    if dessert_text:
        user_msg += f"卡片中請自然地提及這些甜點：{dessert_text}\n"
    user_msg += "請直接輸出祝福語內容。"

    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.8
        )
        content = completion.choices[0].message.content.strip()
        
        # 移除可能的引號包裹
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        if content.startswith('「') and content.endswith('」'):
            content = content[1:-1]
        
        if content and len(content) > 10:
            return content
            
    except Exception:
        pass

    return fallback_messages.get(tone, fallback_messages['warm'])


def resolve_recipe(data, selection):
    cats = data.get('categories', {})
    if isinstance(selection, dict):
        category = (selection.get('category') or '').strip().lower()
        rid = selection.get('id')
        name = (selection.get('name') or '').strip()
    else:
        category = ''
        rid = None
        name = str(selection or '').strip()

    target_categories = [category] if category in DEFAULT_CATEGORIES else DEFAULT_CATEGORIES
    for cat in target_categories:
        for recipe in cats.get(cat, []):
            if rid is not None and recipe.get('id') == rid:
                return cat, recipe
            if name and recipe.get('name') == name:
                return cat, recipe
    return None, None


@app.route('/recommend', methods=['POST'])
def recommend():
    if not request.is_json:
        return jsonify({'error': 'Request body must be JSON'}), 400

    payload = request.get_json(silent=True) or {}
    user_type = payload.get('type', 'All')
    user_time = payload.get('time', None)
    restrictions = payload.get('restrictions', [])

    if user_time is not None:
        try:
            user_time = int(user_time)
        except (TypeError, ValueError):
            return jsonify({'error': 'time must be an integer (minutes)'}), 400

    try:
        data = load_recipes()
    except Exception as exc:
        return jsonify({'error': 'Failed to load recipes', 'message': str(exc)}), 500

    recommended = filter_recipes(data, user_type, user_time, restrictions)
    reasons = generate_ai_reasons(
        recommended,
        {
            "type": user_type,
            "time": user_time,
            "restrictions": restrictions
        }
    )

    enriched = []
    for recipe, reason in zip(recommended, reasons):
        image_path = recipe.get('image') or f"/static/images/{recipe.get('id')}.png"
        enriched.append({
            'name': recipe.get('name'),
            'ai_reason': reason,
            'image_path': image_path,
            'ingredients': recipe.get('ingredients', []),
            'instructions': recipe.get('instructions', [])
        })

    return jsonify({
        'count': len(enriched),
        'results': enriched,
        'ai_model': GROQ_MODEL if get_groq_client() else None
    })


@app.route('/christmas_card', methods=['POST'])
def christmas_card():
    if not request.is_json:
        return jsonify({'error': 'Request body must be JSON'}), 400

    payload = request.get_json(silent=True) or {}
    recipient = (payload.get('name') or '聖誕甜點好友').strip()
    desserts = payload.get('desserts') or []
    tone = (payload.get('tone') or 'warm').strip().lower()

    # 使用 AI 生成祝福卡內容
    message = generate_ai_christmas_card(recipient, desserts, tone)

    return jsonify({
        'recipient': recipient,
        'tone': tone,
        'message': message,
        'ai_generated': get_groq_client() is not None
    })


@app.route('/shopping_list', methods=['POST'])
def shopping_list():
    if not request.is_json:
        return jsonify({'error': 'Request body must be JSON'}), 400

    payload = request.get_json(silent=True) or {}
    selections = payload.get('recipes')
    if not isinstance(selections, list) or not selections:
        return jsonify({'error': 'recipes must be a non-empty list'}), 400

    try:
        data = load_recipes()
    except Exception as exc:
        return jsonify({'error': 'Failed to load recipes', 'message': str(exc)}), 500

    resolved = []
    ingredients_set = set()

    for item in selections:
        category, recipe = resolve_recipe(data, item)
        if not recipe:
            continue
        ingredient_list = recipe.get('ingredients', [])
        for ingredient in ingredient_list:
            if ingredient:
                ingredients_set.add(ingredient.strip())
        resolved.append({
            'category': category,
            'id': recipe.get('id'),
            'name': recipe.get('name'),
            'ingredients': ingredient_list
        })

    if len(resolved) < 2:
        for fallback_cat in DEFAULT_CATEGORIES:
            for recipe in data.get('categories', {}).get(fallback_cat, []):
                if any(r['category'] == fallback_cat and r['id'] == recipe.get('id') for r in resolved):
                    continue
                ingredient_list = recipe.get('ingredients', [])
                for ingredient in ingredient_list:
                    if ingredient:
                        ingredients_set.add(ingredient.strip())
                resolved.append({
                    'category': fallback_cat,
                    'id': recipe.get('id'),
                    'name': recipe.get('name'),
                    'ingredients': ingredient_list
                })
                if len(resolved) >= 2:
                    break
            if len(resolved) >= 2:
                break

    shopping_items = sorted(ingredients_set)
    return jsonify({
        'count': len(resolved),
        'recipes': resolved[:2],
        'shopping_list': shopping_items
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

