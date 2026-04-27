from flask import Flask, render_template, request, redirect, url_for, session
from selenium.webdriver.common.by import By
import time,datetime
import re
import sqlite3
import sqlite3 as sql
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from flask_mail import Mail, Message
from bs4 import BeautifulSoup
import requests
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import io
import base64

app = Flask(__name__)
app.secret_key = 'final_zara_2026'

#資料庫----------------------------------------------------------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    
    # 建立帳號表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            name TEXT,
            email TEXT,
            token TEXT
        )
    ''')
    
    # 1. 建立訂單主表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS zara_orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE,
            user_id TEXT INTEGER,
            order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            order_status TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        );
    ''')
    
    # 2. 建立訂單明細表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS zara_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            brand TEXT,
            product_name TEXT,
            price TEXT,
            image_url TEXT,
            quantity INTEGER DEFAULT 1, 
            size TEXT,
            FOREIGN KEY (order_id) REFERENCES zara_orders (order_id)
        );
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 帳號與訂單資料庫已初始化成功！")

def get_next_order_number():
    # 1. 取得今天的日期字串，例如 "20260413"
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    
    # 2. 查詢今天已經有多少筆訂單 (計算 order_number 像今天日期的數量)
    cursor.execute("SELECT COUNT(*) FROM zara_orders WHERE order_number LIKE ?", (f"{today_str}%",))
    count = cursor.fetchone()[0]
    conn.close()
    
    # 3. 序號加 1，並補齊 4 位數 (例如 0001, 0002)
    new_count = count + 1
    order_num = f"{today_str}{new_count:04d}" # 結果會像 202604130001
    return order_num



#資料庫----------------------------------------------------------------------------------------------------------------------------
#寄件----------------------------------------------------------------------------------------------------------------------------
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'paramasundarayogichannel@gmail.com'
app.config['MAIL_PASSWORD'] = 'vgtmojonjvunaprh'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)
#寄件----------------------------------------------------------------------------------------------------------------------------
#主頁----------------------------------------------------------------------------------------------------------------------------


#meun
@app.route('/')
def home(): 
    if "user" in session:
        username = session['user']
        return '登入使用者名稱是:' + username + '<br>' + \
                "<br><a href = '/zara_shop'>進入ZARA購物中心</a></br>"+ \
                "<br><a href = '/net_shop'>進入NET購物中心</a></br>"+ \
                "<br><a href = '/logout'>點選這裡登出</a></br>"
    return "您暫未登入， <br><a href = '/login'></b>" + \
         "點選這裡登入</b></a>"

#註冊
@app.route('/signup', methods = ['POST', 'GET'])
def signup():
    if request.method == 'POST':
        user = request.form['user']
        password = request.form['password']
        name = request.form['name']
        email = request.form['email']
        if not re.fullmatch(r'^[\w\.-]+@[\w\.-]+\.\w+$',email):
            return "信箱輸入錯誤<br><a href = '/signup'></b>" + \
                 "點選這裡重新註冊</b></a>"
        token=0
        #是否帳號重複
        con = sql.connect('shop.db')
        cursor = con.cursor()
        cursor.execute("""
                       SELECT * FROM  users
                       WHERE username=? 
                       """, (user,))
        result = cursor.fetchone()
        if result:
            con.close()
            return "帳號重複<br><a href = '/signup'></b>" + \
                 "點選這裡重新註冊</b></a>"
        else:
            #輸入框不為空
            if (user and email and password and name):
                try:
                     msg = Message('Email 驗證', sender = 'XX購物系統', recipients = [email])
                     msg.html = f'''<br><a href = 'http://127.0.0.1:5000/token?user={user}'>點選這裡驗證成功</a></br>
                                 '''
                     mail.send(msg)
                    
                     with sql.connect("shop.db") as con:
                        cur = con.cursor()
                        cur.execute("INSERT INTO users (username,password,name,email,token) VALUES (?,?,?,?,?)",(user,password,name,email,token)) 
                        con.commit()
                        # msg = "Record successfully added"                             
                except:
                   con.rollback()
                   msg = "error in insert operation"
                   return msg
                finally:
                    con.close()
                    return "請驗證 Email<br><a href = '/login'></b>" + \
                         "點選這裡登入</b></a>"
            else:
                return "輸入錯誤<br><a href = '/signup'></b>" + \
                     "點選這裡重新註冊</b></a>"
       
    else:
        return render_template('signup.html')
#登入
@app.route('/login', methods = ['POST', 'GET'])
def login():
    
    if request.method == 'POST':
        user = request.form.get("login_user")
        password = request.form.get("login_password")
        conn = sql.connect('shop.db')
        cursor = conn.cursor()

        cursor.execute("""
                       SELECT * FROM users 
                       WHERE username=? AND password=? 
                       """, (user, password))

        result = cursor.fetchone()
        print(result)
        conn.close()

        if result[5] == "1":
            session["user_id"] = result[0] # 存入 user_id，結帳才不會出錯
            session["user"] = result[1]
            print(session)
            return redirect(url_for('home'))
        elif result[5] == "99":
            session["user"] = result[1]
            session["role"] = result[5]
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('login.html')
    else:
        return render_template('login.html')
#登出
@app.route('/logout')
def logout():
   session.pop('user', None)
   session.pop('user_id', None)
   session.modified = True
   return redirect(url_for('home'))

#驗證token
@app.route('/token')
def token():
    try:
        user = request.args.get('user')
        with sql.connect("shop.db") as con:
           cur = con.cursor()
           cur.execute('''
                       UPDATE users SET token=1 WHERE username=?
                       ''',(user,))    
           con.commit()
    except:
        con.rollback()
        msg = "error in insert operation"
        return msg
    con.close()       
    return render_template('login.html')
    
#主頁----------------------------------------------------------------------------------------------------------------------------
#管理者----------------------------------------------------------------------------------------------------------------------------
def set_admin():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    admin = cursor.fetchone()
    if not admin:
        try:
            cursor.execute("INSERT INTO users (username,password,name,email,token) VALUES (?,?,?,?,?)",("admin","admin","管理員","",99))
            conn.commit()
        except Exception as e:
            print(e)
        finally:
            conn.close()
# 設定 Matplotlib 字體以支援中文 (若在 Linux 環境可能需要安裝字體)
def get_plot_url(labels, values, chart_type='bar', title=''):
    plt.clf()
    plt.figure(figsize=(12, 5))
    
    if chart_type == 'bar':
        plt.bar(labels, values, color='skyblue')
        plt.xticks(fontsize=8)
        plt.gca().yaxis.set_major_locator(plt.MaxNLocator(integer=True))  # ← 只顯示整數
        plt.ylim(0, max(values) + 1)  # ← 讓刻度不超過最大值太多
    else:
        plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140)
    
    plt.title(title) # 這裡會用到第 4 個參數
    plt.tight_layout()
    
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    plt.close()
    img.seek(0)
    return base64.b64encode(img.getvalue()).decode('utf8')

@app.route("/admin/dashboard")
def admin_dashboard():
    # 權限檢查 (假設 99 是管理員)
    if session.get("role") != "99":
        return redirect(url_for('login'))
    # 獲取前端傳來的品牌參數，預設顯示 'Zara'
    selected_brand = request.args.get('brand', 'ZARA')
    try:
        conn = sql.connect('shop.db')
        conn.row_factory = sql.Row
        cursor = conn.cursor()
    
        # --- 1. 抓取訂單主表 ---
        cursor.execute('SELECT * FROM zara_orders ORDER BY order_date DESC')
        orders_rows = cursor.fetchall() # <--- 這裡一定要有括號 ()

        # --- 2. 抓取訂單明細表 ---
        cursor.execute('SELECT * FROM zara_order_items')
        items_rows = cursor.fetchall() # <--- 這裡一定要有括號 ()

        # 整理數據：將商品細項按 order_id 分組
        items_by_order = {}
        for item in items_rows: # 修正括號後，這裡就不會報錯 iterable 了
            oid = item['order_id']
            if oid not in items_by_order:
                items_by_order[oid] = []
            items_by_order[oid].append(dict(item))

        # 整合主表與細項
        orders = []
        for row in orders_rows:
            d = dict(row)
            d['order_items'] = items_by_order.get(d['order_id'], [])
            orders.append(d)

        # --- 3. 圖表數據 A：品牌排行 ---
        cursor.execute('''
            SELECT product_name, SUM(quantity) as total 
            FROM zara_order_items WHERE brand = ? 
            GROUP BY product_name ORDER BY total DESC LIMIT 10
        ''', (selected_brand,))
        brand_data = cursor.fetchall() # <--- 這裡一定要有括號 ()
        
        # --- 4. 圖表數據 B：市場佔比 ---
        cursor.execute('SELECT brand, SUM(quantity) as total FROM zara_order_items GROUP BY brand')
        market_data = cursor.fetchall() # <--- 這裡一定要有括號 ()
        
        conn.close()

        # 生成圖表 URL (與之前邏輯相同)
        brand_labels = [r['product_name'] for r in brand_data] if brand_data else ["N/A"]
        brand_values = [r['total'] for r in brand_data] if brand_data else [0]
        bar_url = get_plot_url(brand_labels, brand_values, 'bar', f'{selected_brand} Top 5 Sales')

        market_labels = [r['brand'] for r in market_data] if market_data else ["N/A"]
        market_values = [r['total'] for r in market_data] if market_data else [0]
        pie_url = get_plot_url(market_labels, market_values, 'pie', 'Brand Market Share')

        return render_template("admin_dashboard.html", 
                               orders=orders, 
                               bar_url=bar_url, 
                               pie_url=pie_url,
                               selected_brand=selected_brand)
    except Exception as e:
        import traceback
        return f"<pre>{traceback.format_exc()}</pre>"
        return f"後台渲染發生錯誤: {e}"
#管理者----------------------------------------------------------------------------------------------------------------------------
#zara_store----------------------------------------------------------------------------------------------------------------------------
url_map={}
def scrape_zara_item():
    # 使用 undetected_chromedriver 避開偵測
    options = uc.ChromeOptions()
    # 增加模擬真人參數
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--window-position=-2000,0")
    #head
    driver = uc.Chrome(options=options,version_main=147)
    # wait = WebDriverWait(driver, 20)
    if not url_map:
        driver.get("https://www.zara.com/tw/")
        time.sleep(3)
        # 2. 強制等待選單元素加載到 DOM 中 (不一定要點開它)

        target = driver.find_element(By.XPATH, "/html/body/div[1]/div/div[1]/div/div/div/div[2]/header/div[1]/button")
        driver.execute_script("arguments[0].click();", target)
        time.sleep(1.5)

        categories = driver.find_elements(By.CSS_SELECTOR, ".layout-categories-category-wrapper.link")
        
        for cat in categories:
            # print(cat.text)              # 抓取文字內容 (例如: 襯衫)
            # print(cat.get_attribute("href")) # 抓取連結網址
            if cat.text != "" and cat.get_attribute("href") != None:
                url_map["女士-"+cat.text]=cat.get_attribute("href")

        target = driver.find_element(By.XPATH, "/html/body/div[1]/div/div[1]/div/div/div/div[1]/div/div/div/div/div[2]/div/nav/div/div[1]/div/div/div/div/div[2]/a[2]")
        driver.execute_script("arguments[0].click();", target)
        time.sleep(1.5)

        categories = driver.find_elements(By.CSS_SELECTOR, ".layout-categories-category-wrapper.link")

        for cat in categories:
            # print(cat.text)              # 抓取文字內容 (例如: 襯衫)
            # print(cat.get_attribute("href")) # 抓取連結網址
            if cat.text != "" and cat.get_attribute("href") != None:
                url_map["男士-"+cat.text]=cat.get_attribute("href")
    driver.quit()


def scrape_zara_pro(item):
    target_url = url_map.get(item)
    if not target_url:
        print(f"❌ 錯誤：分類 '{item}' 不在 url_map 中")
        return [] # 找不到網址就回傳空列表，不要繼續往下跑
    # 使用 undetected_chromedriver 避開偵測
    options = uc.ChromeOptions()
    # 增加模擬真人參數
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--window-position=-2000,0")
    
    driver = uc.Chrome(options=options,version_main=147)
    wait = WebDriverWait(driver, 15)
    try:
        driver.get(target_url)            
        time.sleep(6)
        
        target = driver.find_element(By.XPATH, "/html/body/div[1]/div/div[1]/div/div/div/div[2]/main/div[2]/div/ul/li[2]/button")
        driver.execute_script("arguments[0].click();", target)
        time.sleep(3)
        # 1. 等待商品容器出現
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "section.product-grid")))
        print(f"✅ 已進入頁面")

        # 2. 修改：自動下滑到底部 (處理動態加載)
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while True:
            # 每次向下滾動一個視窗高度，而不是直接跳到底，這能觸發 Lazy Load
            driver.execute_script("window.scrollBy(0, 1000);") 
            time.sleep(1.5)
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            # 判斷是否真的到底了
            current_pos = driver.execute_script("return window.pageYOffset + window.innerHeight;")
            if current_pos >= new_height:
                print("📏 已滑動至頁面底部")
                break
            last_height = new_height

        # 3. 核心切換：將 Selenium 抓到的 HTML 丟給 BeautifulSoup
        # ... 前面滾動邏輯保持不變 ...

        print("🥣 開始解析資料...")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # 修正 1：擴大搜尋範圍。有時 Zara 不用 li，改用 div 裝商品
        # 嘗試抓取所有包含 product-grid 相關關鍵字的產品區塊
        items = soup.find_all("div", class_="product-grid-product") or \
                soup.find_all("li", class_="product-grid-product")
        
        print(f"📦 偵測到 {len(items)} 個商品節點")
        
        data = []
        for item in items:
            try:
                # 修正 2：使用更彈性的搜尋，不要寫死長長的 Class
                # 搜尋包含 'name' 字眼的類別
                name_el = item.find("div", class_=lambda x: x and 'product-info__name' in x) or \
                          item.find("a", class_=lambda x: x and 'product-info__name' in x)
                
                # 搜尋包含 'price' 字眼的類別
                price_el = item.find("span", class_=lambda x: x and 'price' in x) or \
                           item.select_one(".money-amount__main")
                
                # 修正 3：圖片抓取。Zara 的真實圖通常在 srcset
                img_el = item.find("img")
                img_url = ""
                if img_el:
                    # 依序嘗試不同的屬性
                    img_url = img_el.get("srcset") or img_el.get("data-src") or img_el.get("src")
                    # 如果是 srcset，通常拿第一組網址
                    if img_url and "," in img_url:
                        img_url = img_url.split(" ")[0]
        
                if name_el:
                    name = name_el.get_text(strip=True)
                    price = price_el.get_text(strip=True) if price_el else "尚未標價"
                    
                    data.append({
                        "名稱": name,
                        "價格": price,
                        "圖片": img_url
                    })
            except Exception as e:
                continue
    finally:
        driver.quit()
    return data

ZARA_CACHE = {}
@app.route("/zara_shop", methods=["GET"])
def zara_sch():
    if "user" not in session:
        return render_template('login.html')
    if not url_map:
        scrape_zara_item()
    item = request.args.get("item")
    products = []  # 初始化一個空列表
    
    if item and item != "#":
        # 1. 檢查「全域字典」裡有沒有這份資料
        if item in ZARA_CACHE:
            print(f"🚀 從記憶體載入暫存：{item}")
            products = ZARA_CACHE[item]
        else:
            if item in url_map:
                print(f"📦 記憶體無資料，啟動爬蟲：{item}")
                products = scrape_zara_pro(item)
            # 2. 爬完後存入字典，下次就不用再爬
                ZARA_CACHE[item] = products
                
    current_cart = session.get('zara_cart', [])
    return render_template("zara_shop.html",item=item,products=products, order=current_cart,url_map=url_map)

@app.route("/zara_shop/add", methods=["POST"])
def zara_add():
    # 取得單一商品的資訊
    name = request.form.get("product_id")
    size = request.form.get("size")
    qty = request.form.get("quantity", type=int, default=1)
    
    # 取得現有購物車
    cart = session.get("zara_cart", [])
    
    # 檢查是否已經有相同名稱且相同尺寸的商品，有的話就累加數量
    found = False
    for item in cart:
        if item['name'] == name and item['size'] == size:
            item['qty'] += qty
            found = True
            break
            
    if not found:
        cart.append({
            "name": name,
            "size": size,
            "qty": qty
        })
        
    session["zara_cart"] = cart
    session.modified = True
    print(f"➕ 已加入：{name} ({size}) x {qty}")
    return redirect(request.referrer or url_for("zara_sch"))

@app.route("/zara_shop/order")
def zara_order():
    cart = session.get("zara_cart", [])
    detailed_order = []
    total = 0
    
    for c in cart:
        found_item = None
        # 從暫存中尋找商品詳情
        for cat_items in ZARA_CACHE.values():
            for p in cat_items:
                if p["名稱"] == c["name"]:
                    found_item = p.copy()
                    break
            if found_item: break
        
        if found_item:
            found_item.update(c) # 合併數量與尺寸
            detailed_order.append(found_item)
            
            # 修正：強健的價格解析邏輯
            price_str = found_item.get("價格", "0")
            clean_price = re.sub(r'[^\d]', '', price_str)
            price = int(clean_price) if clean_price else 0
            total += price * c.get("qty", 1)
            
    return render_template("zara_order.html", order=detailed_order, total=total, count=len(detailed_order))

@app.route("/zara_shop/clear", methods=["POST"])
def zara_clear_order():
    session.pop("order", None)
    session.modified = True
    return redirect(url_for("zara_sch"))

@app.route("/zara_remove", methods=["POST"])
def zara_remove():
    # 從表單取得要移除的商品名稱
    target_name = request.form.get("name")
    cart = session.get("zara_cart", [])
    
    # 過濾掉名稱符合的商品 (保留不符合名稱的商品)
    # 注意：如果同名但尺寸不同，建議連尺寸一起比對
    new_cart = [item for item in cart if item['name'] != target_name]
    
    session["zara_cart"] = new_cart
    session.modified = True
    print(f"🗑️ 已移除商品: {target_name}")
    
    return redirect(url_for("zara_order")) # 移除後回到訂單頁面


@app.route("/zara_shop/checkout", methods=["POST"])
def zara_checkout():
    user_id = session.get("user_id")
    cart = session.get("zara_cart", [])
    
    if not user_id or not cart:
        return redirect(url_for("zara_sch"))

    display_order_number = get_next_order_number()
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    
    try:
        # 1. 產生主訂單
        cursor.execute('INSERT INTO zara_orders (order_number, user_id, order_status) VALUES (?, ?, ?)',
                       (display_order_number, user_id, "已付款"))
        order_id = cursor.lastrowid

        # 2. 寫入每一筆商品細節
        for item in cart:
            p_name = item['name']
            p_size = item['size']
            p_qty = item['qty']
            
            # 從 ZARA_CACHE 找回圖片和價格
            p_price, p_img = "0", ""
            for category in ZARA_CACHE.values():
                for p in category:
                    if p["名稱"] == p_name:
                        # 處理價格：去掉 NT$ 與逗號，轉為純數字字串
                        p_price = re.sub(r'[^\d]', '', p["價格"])
                        p_img = p["圖片"]
                        break
                if p_img: break
            
            cursor.execute('''
                INSERT INTO zara_order_items (order_id, brand, product_name, price, image_url, size, quantity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (order_id, "ZARA", p_name, p_price, p_img, p_size, p_qty))

        conn.commit()
        session.pop("zara_cart", None) # 成功後清空 Session
        print(f"✅ 訂單 {display_order_number} 已成功存入資料庫")
        
    except Exception as e:
        print(f"❌ 結帳失敗: {e}")
        conn.rollback()
    finally:
        conn.close()
        
    return redirect(url_for("zara_sch"))
#zara_store----------------------------------------------------------------------------------------------------------------------------
#NET-----------------
NET_DATA = {}
def fetch_product_list(category_url):
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    }
    products = []
    page = 1
    last_first_product = ""
    while True:
        url = f"{category_url}/{page}"
        print(f"爬取第 {page} 頁：{url}")

        res = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(res.text, "html.parser")

        items = soup.select(".js-product-block")

        first_name_tag = items[0].select_one(".main_name a")
        first_name = first_name_tag.text.strip() if first_name_tag else ""

        if first_name == last_first_product:
            print("商品重複，已到最後一頁")
            break

        last_first_product = first_name

        for item in items:
            # 名稱 + 連結
            name_tag = item.select_one(".main_name a")
            name = name_tag.text.strip() if name_tag else ""


            # 價格
            price_tag = item.select_one(".price_special")
            price = parse_price(price_tag.text) if price_tag else 0

            # 圖片
            img_tag = item.select_one(".main_img img")
            image = ""
            if img_tag:
                image = img_tag.get("src") or img_tag.get("data-src") or ""

            products.append(
                {
                    "name": name,
                    "price": price,
                    "image": image,
                }
            )

        page += 1
        time.sleep(1)

    return products
# 價格字串轉數字
def parse_price(text):
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0
def main():
    BASE_URL = "https://www.net-fashion.net"
    global NET_DATA
    # 想爬的分類頁（請依實際網址調整）
    categories = {
        "男裝": f"{BASE_URL}/category/1747",
        "女裝": f"{BASE_URL}/category/1748",
        "男童裝": f"{BASE_URL}/category/1662",
        "女童裝": f"{BASE_URL}/category/2451",
    }
    
    temp_dict = {}
    for category_name, category_url in categories.items():
        print(f"\n 開始爬取分類：{category_name}")
        products_list = fetch_product_list(category_url)
        for p in products_list:
            # 這裡統一欄位名稱為 name, price, image
            temp_dict[p['name']] = {
                "name": p['name'],
                "price": p['price'],
                "image": p['image'], # 這裡對應你爬蟲抓下來的 key
                "category": category_name  # 新增分類標籤
            }
    NET_DATA = temp_dict
    
    print(f"資料初始化完成，共 {len(NET_DATA)} 筆商品")
    return NET_DATA
 
@app.route("/net_shop", methods=["GET"])
def net_sch():
    if "user" not in session:
        return render_template('login.html')
    global NET_DATA
    # 如果字典是空的，嘗試跑一次 main
    if not NET_DATA:
        main()
    # 1. 取得當前分類 (預設男裝)
    current_cat = request.args.get('cat', '男裝')   
    
    # 2. 過濾商品清單
    filtered_products = [p for p in NET_DATA.values() if p.get('category') == current_cat]
    
    # 3. 獲取購物車資料 (統一使用 net_cart)
    cart = session.get("net_cart", [])
    
    # 4. 計算總金額 (單價 * 數量)
    total_price = 0
    for item in cart:
        total_price += int(item.get('price', 0)) * int(item.get('qty', 1))
    
    return render_template("net_shop.html", 
                           products=filtered_products, 
                           cart=cart, 
                           total=total_price, 
                           current_cat=current_cat)

@app.route("/net_shop/add", methods=["POST"])
def net_add():
    try:
        # 1. 接收表單資料
        name = request.form.get("name")
        raw_price = request.form.get("price")
        size = request.form.get("size")
        qty = request.form.get("quantity")
        current_cat = request.form.get("cat", "男裝")

        # 2. 價格清理與數字轉換
        # 移除 NT$ 或逗號，確保變成純數字整數
        price_digits = re.sub(r'[^\d]', '', str(raw_price))
        price_int = int(price_digits) if price_digits else 0
        qty_int = int(qty) if qty else 1

        # 3. 建立商品字典
        new_item = {
            "name": name,
            "price": price_int,
            "size": size,
            "qty": qty_int
        }

        # 4. 更新 Session 購物車
        cart = session.get("net_cart", [])
        cart.append(new_item)
        session["net_cart"] = cart
        session.modified = True  # 必須加上這行，否則右側不會更新

        # 5. 導向回原本查看的分類頁面
        return redirect(url_for("net_sch", cat=current_cat))
    
    except Exception as e:
        print(f"NET 加入錯誤: {e}")
        return "加入購物車失敗", 400

@app.route("/net_shop/clear", methods=["POST"])
def net_clear():
    session.pop("net_cart", None)
    return redirect(url_for("net_sch"))

@app.route("/net_shop/remove", methods=["POST"])
def net_remove_item():
    product_name = request.form.get("name")
    current_cat = request.form.get("cat", "男裝")
    
    # 統一使用 net_cart
    cart = session.get("net_cart", [])
    
    # 過濾掉名稱相符的商品 (移除該項)
    # 使用列表推導式重新產生不含該商品的清單
    new_cart = [item for item in cart if item['name'] != product_name]
    
    session["net_cart"] = new_cart
    session.modified = True
    
    return redirect(url_for("net_sch", cat=current_cat))


@app.route("/net_shop/checkout", methods=["POST"])
def net_checkout():
    user_id = session.get("user_id")
    if not user_id:
        return render_template('login.html')

    cart_items = session.get("net_cart", [])
    if not cart_items:
        return redirect(url_for("net_sch"))

    display_order_number = get_next_order_number()
    brand = "NET"
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    
    try:
        # --- A. 寫入訂單主表 ---
        cursor.execute('''
            INSERT INTO zara_orders (order_number, user_id, order_status)
            VALUES (?, ?, ?)
        ''', (display_order_number, user_id, "已付款"))

        main_order_id = cursor.lastrowid

        # --- B. 逐筆寫入訂單明細 (對應你新的欄位結構) ---
        for item in cart_items:
            name = item['name']
            size = item['size']
            qty = item['qty']
            price_val = item['price'] # 這是整數
            
            # 從 NET_DATA 補齊圖片資料
            product_info = NET_DATA.get(name, {})
            img_url = product_info.get('image', "")
            
            # 格式化價格顯示 (可選)
            price_str = f"NT$ {price_val}"

            # 配合你新增加的 quantity 和 size 欄位進行插入
            cursor.execute('''
                INSERT INTO zara_order_items (
                    order_id, brand, product_name, price, image_url, quantity, size
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (main_order_id, brand, name, price_str, img_url, qty, size))

        conn.commit()
        session.pop("net_cart", None)
        print(f"✅ NET 訂單 {display_order_number} 儲存成功 (含規格)")

    except Exception as e:
        print(f"❌ NET 結帳錯誤: {e}")
        conn.rollback()
    finally:
        conn.close()

    return redirect(url_for("net_sch"))

#NET-----------------
if __name__ == "__main__":
    init_db()
    set_admin()
    app.run()
    