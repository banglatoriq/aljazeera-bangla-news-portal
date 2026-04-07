import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from streamlit_autorefresh import st_autorefresh
import math

# --- পেইজ সেটআপ (Centered Layout) ---
# layout="centered" দেওয়ায় এটি আর ফুল-উইডথ থাকবে না, মাঝখানে সুন্দর কন্টেইনারে দেখাবে।
st.set_page_config(page_title="বাংলা নিউজ পোর্টাল", page_icon="📰", layout="centered")

# ৩০ মিনিট (১৮০০ সেকেন্ড) পর পর স্বয়ংক্রিয় রিফ্রেশ
st_autorefresh(interval=1 * 60 * 1000, key="news_update_timer")

# --- ডাটাবেস সেটআপ ---
@st.cache_resource
def init_db():
    conn = sqlite3.connect('news_db_centered.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news_table
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  title TEXT, link TEXT, translated_title TEXT, 
                  full_text TEXT, image_url TEXT, category TEXT, date TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS metadata (last_scrape TIMESTAMP)''')
    conn.commit()
    return conn, c

conn, c = init_db()

# --- তাজা খবর স্ক্র্যাপিং এবং সম্পূর্ণ অনুবাদ লজিক ---
def scrape_news():
    # হোমপেজের বদলে সরাসরি Latest News পেজ থেকে খবর আনবে
    url = "https://www.aljazeera.com/news/" 
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        articles = soup.find_all('h3', class_='gc__title')[:15] # ১৫টি লেটেস্ট খবর চেক করবে
        
        translator = GoogleTranslator(source='en', target='bn')
        new_items = 0
        
        for article in articles:
            title = article.text.strip()
            link_tag = article.find('a')
            if not link_tag: continue
            
            link = "https://www.aljazeera.com" + link_tag['href'] if not link_tag['href'].startswith('http') else link_tag['href']
            
            # ডাটাবেসে না থাকলে তবেই ভেতরে ঢুকবে
            c.execute("SELECT * FROM news_table WHERE link=?", (link,))
            if not c.fetchone():
                try:
                    art_resp = requests.get(link, headers=headers)
                    art_soup = BeautifulSoup(art_resp.content, 'html.parser')
                    
                    # ছবি ও ক্যাটাগরি
                    og_image = art_soup.find('meta', property='og:image')
                    image_url = og_image['content'] if og_image else "https://via.placeholder.com/600x300?text=No+Image"
                    
                    try: category = translator.translate(link.split('/')[3].capitalize())
                    except: category = "তাজা খবর"
                        
                    # সম্পূর্ণ খবর অনুবাদ (প্যারাগ্রাফ চাংকিং পদ্ধতি)
                    paragraphs = art_soup.find_all('p')
                    valid_paragraphs = [p.text.strip() for p in paragraphs if len(p.text.split()) > 10]
                    
                    translated_paragraphs = []
                    # খবরের প্রথম ১২টি প্যারাগ্রাফ নিচ্ছি (যাতে পুরো খবর কভার হয় কিন্তু সার্ভার ব্লক না করে)
                    for p_text in valid_paragraphs[:12]: 
                        try:
                            bn_p = translator.translate(p_text)
                            # প্রতিটি প্যারাগ্রাফ সুন্দর করে সাজানোর জন্য HTML <p> ট্যাগ ব্যবহার
                            translated_paragraphs.append(f"<p style='margin-bottom: 12px; line-height: 1.8; text-align: justify;'>{bn_p}</p>")
                        except: pass
                    
                    bn_title = translator.translate(title)
                    bn_full_text = "".join(translated_paragraphs) if translated_paragraphs else "খবরটি পড়ার জন্য মূল ওয়েবসাইটে যান।"
                    
                    # ডাটাবেসে সেভ
                    c.execute('''INSERT INTO news_table (title, link, translated_title, full_text, image_url, category, date) 
                                 VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                              (title, link, bn_title, bn_full_text, image_url, category, datetime.now()))
                    conn.commit()
                    new_items += 1
                except Exception as e: 
                    continue
        
        c.execute("DELETE FROM metadata")
        c.execute("INSERT INTO metadata VALUES (?)", (datetime.now(),))
        conn.commit()
        return new_items
    except:
        return 0

# --- পুরনো নিউজ ডিলিট ---
def auto_delete_old():
    limit = datetime.now() - timedelta(days=7)
    c.execute("DELETE FROM news_table WHERE date < ?", (limit,))
    conn.commit()

# --- অটো-চেক: ৩০ মিনিট পার হয়েছে কি না ---
c.execute("SELECT last_scrape FROM metadata")
last_time = c.fetchone()
if last_time is None or (datetime.now() - datetime.strptime(last_time[0], '%Y-%m-%d %H:%M:%S.%f')) > timedelta(minutes=30):
    scrape_news()
    auto_delete_old()

# ==========================================
# Frontend ও UI ডিজাইন (Centered & Polished)
# ==========================================

if 'page_num' not in st.session_state: st.session_state.page_num = 1
if 'view' not in st.session_state: st.session_state.view = 'home'
if 'selected_news' not in st.session_state: st.session_state.selected_news = None

# --- হেডার অংশ (সব পেজেই থাকবে) ---
st.markdown("<h1 style='text-align: center; color: #2e86c1;'>📰 আল-জাজিরা বাংলা</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>নির্ভরযোগ্য আন্তর্জাতিক খবরের সরাসরি অনুবাদ</p>", unsafe_allow_html=True)
st.write("---")

# --- ১. হোম/আর্কাইভ পেইজ ---
if st.session_state.view == 'home':
    c.execute("SELECT COUNT(*) FROM news_table")
    total_news = c.fetchone()[0]
    st.caption(f"সর্বমোট **{total_news}টি** তাজা খবর | স্বয়ংক্রিয় আপডেট চালু আছে")
    st.write("")

    c.execute("SELECT id, translated_title, image_url, category, date, full_text, link FROM news_table ORDER BY date DESC")
    all_news = c.fetchall()

    if not all_news:
        st.info("নতুন খবর আনা হচ্ছে... দয়া করে পেজটি কিছুক্ষণ পর রিলোড দিন।")
    else:
        # প্যাজিনেশন
        items_per_page = 10
        total_pages = math.ceil(len(all_news) / items_per_page)
        start_idx = (st.session_state.page_num - 1) * items_per_page
        end_idx = start_idx + items_per_page
        
        for news in all_news[start_idx:end_idx]:
            n_id, n_title, n_img, n_cat, n_date, n_full, n_link = news
            
            # লেআউট রেশিও ১:৩ করা হয়েছে যাতে ছবি ছোট এবং মার্জিত দেখায়
            col1, col2 = st.columns([1, 3]) 
            with col1:
                if n_img: 
                    # ছবিকে একটি নির্দিষ্ট স্টাইলে দেখানোর জন্য HTML/CSS ব্যবহার
                    st.markdown(f'''
                        <div style="border-radius: 8px; overflow: hidden; height: 100px; display: flex; align-items: center; justify-content: center; background-color: #f0f2f6;">
                            <img src="{n_img}" style="width: 100%; height: auto; object-fit: cover;">
                        </div>
                    ''', unsafe_allow_html=True)
            
            with col2:
                formatted_date = datetime.strptime(n_date, '%Y-%m-%d %H:%M:%S.%f').strftime('%d %b %Y, %I:%M %p')
                st.markdown(f"<span style='color: #d35400; font-size: 14px; font-weight: bold;'>{n_cat}</span> <span style='color: gray; font-size: 12px;'>| {formatted_date}</span>", unsafe_allow_html=True)
                
                # টাইটেলে ক্লিক করার বাটন
                if st.button(n_title, key=f"title_{n_id}", use_container_width=True):
                    st.session_state.selected_news = news
                    st.session_state.view = 'details'
                    st.rerun()
            st.write("---")

        # পেজ নাম্বার নিচে দেখানো
        st.write("### পেইজ:")
        cols = st.columns(total_pages if total_pages < 10 else 10)
        for p in range(1, total_pages + 1):
            with cols[p-1]:
                if st.button(str(p), key=f"page_{p}"):
                    st.session_state.page_num = p
                    st.rerun()

# --- ২. সিঙ্গেল নিউজ পেইজ (সম্পূর্ণ খবর) ---
elif st.session_state.view == 'details':
    news = st.session_state.selected_news
    if st.button("⬅️ খবরের তালিকায় ফিরে যান"):
        st.session_state.view = 'home'
        st.rerun()
    
    st.write("")
    # খবরের টাইটেল
    st.markdown(f"<h2 style='line-height: 1.4;'>{news[1]}</h2>", unsafe_allow_html=True)
    
    # মেটা ডাটা
    formatted_date = datetime.strptime(news[4], '%Y-%m-%d %H:%M:%S.%f').strftime('%d %b %Y, %I:%M %p')
    st.markdown(f"<p style='color: gray; font-size: 15px;'>বিভাগ: <b>{news[3]}</b> | আপডেট: {formatted_date}</p>", unsafe_allow_html=True)
    
    # মূল ছবি (মার্জিত সাইজ)
    if news[2]: 
        st.markdown(f'''
            <div style="border-radius: 10px; overflow: hidden; margin-bottom: 20px;">
                <img src="{news[2]}" style="width: 100%; height: auto;">
            </div>
        ''', unsafe_allow_html=True)
    
    # সম্পূর্ণ খবরের টেক্সট (justify করা)
    st.markdown(f"<div style='font-size: 18px; color: #333;'>{news[5]}</div>", unsafe_allow_html=True)
    
    st.write("---")
    st.markdown(f"**[🔗 মূল খবরটি ইংরেজিতে পড়তে এখানে ক্লিক করুন]({news[6]})**")
