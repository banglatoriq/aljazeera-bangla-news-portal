import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from streamlit_autorefresh import st_autorefresh
import math

# --- পেইজ সেটআপ ---
st.set_page_config(page_title="বাংলা নিউজ পোর্টাল", page_icon="📰", layout="wide")

# ১ ঘণ্টা পর পর নিউজ অটো-রিফ্রেশ করার জন্য (মিলিসেকেন্ডে হিসাব)
st_autorefresh(interval=60 * 60 * 1000, key="news_update_timer")

# --- ডাটাবেস সেটআপ ---
@st.cache_resource
def init_db():
    conn = sqlite3.connect('news_db_final.db', check_same_thread=False)
    c = conn.cursor()
    # নিউজ টেবিল
    c.execute('''CREATE TABLE IF NOT EXISTS news_table
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  title TEXT, link TEXT, translated_title TEXT, 
                  full_text TEXT, image_url TEXT, category TEXT, date TIMESTAMP)''')
    # মেটাডাটা টেবিল (অটো-স্ক্র্যাপিং টাইম ট্র্যাক করতে)
    c.execute('''CREATE TABLE IF NOT EXISTS metadata (last_scrape TIMESTAMP)''')
    conn.commit()
    return conn, c

conn, c = init_db()

# --- অটো-স্ক্র্যাপিং লজিক ---
def scrape_news():
    url = "https://www.aljazeera.com/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        articles = soup.find_all('h3', class_='gc__title')[:15] # ১৫টি খবর চেক করবে
        
        translator = GoogleTranslator(source='en', target='bn')
        
        for article in articles:
            title = article.text.strip()
            link_tag = article.find('a')
            if not link_tag: continue
            
            link = "https://www.aljazeera.com" + link_tag['href'] if not link_tag['href'].startswith('http') else link_tag['href']
            
            c.execute("SELECT * FROM news_table WHERE link=?", (link,))
            if not c.fetchone():
                try:
                    art_resp = requests.get(link, headers=headers)
                    art_soup = BeautifulSoup(art_resp.content, 'html.parser')
                    
                    # ছবি ও ক্যাটাগরি সংগ্রহ
                    og_image = art_soup.find('meta', property='og:image')
                    image_url = og_image['content'] if og_image else ""
                    
                    try: category = translator.translate(link.split('/')[3].capitalize())
                    except: category = "আন্তর্জাতিক"
                        
                    paragraphs = art_soup.find_all('p')
                    full_english = " ".join([p.text for p in paragraphs[1:6]])
                    
                    # অনুবাদ
                    bn_title = translator.translate(title)
                    bn_text = translator.translate(full_english[:4000]) if full_english else ""
                    
                    c.execute('''INSERT INTO news_table (title, link, translated_title, full_text, image_url, category, date) 
                                 VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                              (title, link, bn_title, bn_text, image_url, category, datetime.now()))
                    conn.commit()
                except: continue
        
        # সর্বশেষ আপডেটের সময় সেভ করা
        c.execute("DELETE FROM metadata")
        c.execute("INSERT INTO metadata VALUES (?)", (datetime.now(),))
        conn.commit()
        return True
    except:
        return False

# ৭ দিন আগের নিউজ ডিলিট করা
def auto_delete_old():
    limit = datetime.now() - timedelta(days=7)
    c.execute("DELETE FROM news_table WHERE date < ?", (limit,))
    conn.commit()

# অটো-চেক: ১ ঘণ্টা পার হয়েছে কি না
c.execute("SELECT last_scrape FROM metadata")
last_time = c.fetchone()
if last_time is None or (datetime.now() - datetime.strptime(last_time[0], '%Y-%m-%d %H:%M:%S.%f')) > timedelta(hours=1):
    scrape_news()
    auto_delete_old()

# --- UI এবং নেভিগেশন ---
if 'page_num' not in st.session_state: st.session_state.page_num = 1
if 'view' not in st.session_state: st.session_state.view = 'home'
if 'selected_news' not in st.session_state: st.session_state.selected_news = None

# আর্কাইভ পেইজে ফিরে আসা
if st.session_state.view == 'home':
    st.title("📰 আল-জাজিরা বাংলা")
    
    # মোট নিউজ সংখ্যা বের করা
    c.execute("SELECT COUNT(*) FROM news_table")
    total_news = c.fetchone()[0]
    st.write(f"বর্তমানে মোট **{total_news}টি** খবর সংরক্ষিত আছে। (প্রতি ১ ঘণ্টা পর পর স্বয়ংক্রিয়ভাবে আপডেট হয়)")
    st.write("---")

    # নিউজ লোড করা
    c.execute("SELECT id, translated_title, image_url, category, date, full_text, link FROM news_table ORDER BY date DESC")
    all_news = c.fetchall()

    if not all_news:
        st.info("নিউজ লোড হচ্ছে... অনুগ্রহ করে কিছুক্ষণ পর রিলোড দিন।")
    else:
        # প্যাজিনেশন ক্যালকুলেশন
        items_per_page = 10
        total_pages = math.ceil(len(all_news) / items_per_page)
        
        start_idx = (st.session_state.page_num - 1) * items_per_page
        end_idx = start_idx + items_per_page
        current_news_list = all_news[start_idx:end_idx]

        # নিউজ লিস্ট লেআউট (ছোট থাম্বনেইল)
        for news in current_news_list:
            n_id, n_title, n_img, n_cat, n_date, n_text, n_link = news
            
            # কলম লেআউট (ছবি বামে, লেখা ডানে)
            col1, col2 = st.columns([1, 3])
            
            with col1:
                if n_img: st.image(n_img, use_container_width=True)
                else: st.image("https://via.placeholder.com/150", width=150)
            
            with col2:
                st.caption(f"{n_cat} | {n_date[:16]}")
                if st.button(n_title, key=f"title_{n_id}", help="বিস্তারিত পড়তে ক্লিক করুন"):
                    st.session_state.selected_news = news
                    st.session_state.view = 'details'
                    st.rerun()
            st.write("---")

        # প্যাজিনেশন কন্ট্রোল
        page_col1, page_col2, page_col3 = st.columns([1, 2, 1])
        with page_col2:
            if total_pages > 1:
                cols = st.columns(total_pages if total_pages < 10 else 10)
                for p in range(1, total_pages + 1):
                    if st.button(str(p), key=f"page_{p}"):
                        st.session_state.page_num = p
                        st.rerun()

elif st.session_state.view == 'details':
    # সিঙ্গেল নিউজ ভিউ
    news = st.session_state.selected_news
    if st.button("⬅️ খবরে ফিরে যান"):
        st.session_state.view = 'home'
        st.rerun()
    
    st.write("---")
    st.header(news[1])
    st.caption(f"বিভাগ: {news[3]} | তারিখ: {news[4][:16]}")
    if news[2]: st.image(news[2], use_container_width=True)
    
    st.write("---")
    st.markdown(f"<div style='font-size:20px; line-height:1.8;'>{news[5]}</div>", unsafe_allow_html=True)
    st.write("---")
    st.markdown(f"[মূল খবরটি ইংরেজিতে পড়ুন]({news[6]})")
