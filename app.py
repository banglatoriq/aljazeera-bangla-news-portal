import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import math
import time

# --- পেইজ সেটআপ (Wide Layout) ---
st.set_page_config(page_title="Al Jazeera News Updates", page_icon="🌐", layout="wide")

# ==========================================
# থিম এবং ফন্ট সেটআপ (Light / Dark Mode)
# ==========================================
st.sidebar.title("⚙️ Admin Panel")
theme = st.sidebar.radio("🎨 Website Theme", ["Light Mode", "Dark Mode"], horizontal=True)

# কালার প্যালেট নির্বাচন
if theme == "Dark Mode":
    bg_color, text_color, card_bg, meta_color = "#0E1117", "#F8FAFC", "#1E293B", "#94A3B8"
    accent_color = "#38BDF8"
else:
    bg_color, text_color, card_bg, meta_color = "#F8FAFC", "#0F172A", "#FFFFFF", "#64748B"
    accent_color = "#0284C7"

# সিএসএস (CSS) - ওভারল্যাপিং এড়াতে স্পেসিফিক ট্যাগ ব্যবহার করা হয়েছে
st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&display=swap');
        
        html, body, h1, h2, h3, h4, h5, h6, p, button, a {{
            font-family: 'Hind Siliguri', sans-serif !important;
        }}
        
        .stApp {{
            background-color: {bg_color};
        }}
        
        .news-card {{
            background-color: {card_bg};
            border-radius: 12px;
            overflow: hidden;
            height: 180px;
            margin-bottom: 12px;
            border: 1px solid {meta_color}33;
        }}
        
        .news-meta {{
            color: {meta_color};
            font-size: 13.5px;
            margin-top: 5px;
            margin-bottom: 10px;
        }}
        
        .category-badge {{
            color: {accent_color};
            font-weight: 700;
            text-transform: uppercase;
        }}
        
        .article-container {{
            max-width: 800px;
            margin: 0 auto;
            background-color: {card_bg};
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.05);
            border: 1px solid {meta_color}22;
        }}
        
        .article-text p {{
            font-size: 19px;
            line-height: 1.8;
            color: {text_color};
            text-align: justify;
            margin-bottom: 15px;
        }}
    </style>
""", unsafe_allow_html=True)

# --- ডাটাবেস সেটআপ ---
@st.cache_resource
def init_db():
    conn = sqlite3.connect('news_db_safe.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news_table
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  title TEXT, link TEXT, translated_title TEXT, 
                  full_text TEXT, image_url TEXT, category TEXT, date TIMESTAMP)''')
    conn.commit()
    return conn, c

conn, c = init_db()

# --- স্ক্র্যাপিং লজিক ---
def scrape_news():
    url = "https://www.aljazeera.com/" 
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        articles = []
        for heading in soup.find_all(['h3', 'h2']):
            a_tag = heading.find('a')
            if a_tag and 'href' in a_tag.attrs:
                articles.append(heading)
                if len(articles) >= 15: break
        
        translator = GoogleTranslator(source='en', target='bn')
        new_items = 0
        
        for article in articles:
            title = article.text.strip()
            link_tag = article.find('a')
            link = link_tag['href']
            if not link.startswith('http'): link = "https://www.aljazeera.com" + link
                
            c.execute("SELECT * FROM news_table WHERE link=?", (link,))
            if not c.fetchone():
                try:
                    art_resp = requests.get(link, headers=headers, timeout=10)
                    art_soup = BeautifulSoup(art_resp.content, 'html.parser')
                    
                    og_image = art_soup.find('meta', property='og:image')
                    image_url = og_image['content'] if og_image else "https://via.placeholder.com/600x400?text=News"
                    
                    try: category = link.split('/')[3].capitalize()
                    except: category = "Latest"
                        
                    paragraphs = art_soup.find_all('p')
                    valid_paragraphs = [p.text.strip() for p in paragraphs if len(p.text.split()) > 10]
                    
                    translated_paragraphs = []
                    for p_text in valid_paragraphs[:10]: 
                        try:
                            bn_p = translator.translate(p_text)
                            translated_paragraphs.append(f"<p>{bn_p}</p>")
                        except: pass
                    
                    bn_title = translator.translate(title)
                    bn_full_text = "".join(translated_paragraphs) if translated_paragraphs else "No content available."
                    
                    c.execute('''INSERT INTO news_table (title, link, translated_title, full_text, image_url, category, date) 
                                 VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                              (title, link, bn_title, bn_full_text, image_url, category, datetime.now()))
                    conn.commit()
                    new_items += 1
                except: continue
        
        return True, f"Successfully fetched {new_items} new articles!"
    except Exception as e:
        return False, f"Scraping Error: {e}"

# ==========================================
# Frontend UI
# ==========================================

if 'page_num' not in st.session_state: st.session_state.page_num = 1
if 'view' not in st.session_state: st.session_state.view = 'home'
if 'selected_news' not in st.session_state: st.session_state.selected_news = None

if st.sidebar.button("🔄 Fetch Latest News"):
    with st.spinner("Fetching and translating news..."):
        success, msg = scrape_news()
        if success: st.sidebar.success(msg)
        else: st.sidebar.error(msg)
        time.sleep(2)
        st.rerun()

# --- ১. হোম / আর্কাইভ পেইজ ---
if st.session_state.view == 'home':
    st.markdown(f"<h1 style='text-align: center; color: {text_color}; font-weight: 700; margin-bottom: 30px;'>Al Jazeera News Updates</h1>", unsafe_allow_html=True)

    c.execute("SELECT DISTINCT category FROM news_table")
    db_categories = c.fetchall()
    categories = ["All News"] + [cat[0] for cat in db_categories]
    
    # রেডিও বাটনের বদলে সুন্দর ড্রপডাউন (Selectbox)
    col_filter, _ = st.columns([1, 3])
    with col_filter:
        selected_category = st.selectbox("🏷️ Filter by Category:", categories)
    st.write("")

    if selected_category == "All News":
        c.execute("SELECT id, translated_title, image_url, category, date, full_text, link FROM news_table ORDER BY date DESC")
    else:
        c.execute("SELECT id, translated_title, image_url, category, date, full_text, link FROM news_table WHERE category=? ORDER BY date DESC", (selected_category,))
    
    all_news = c.fetchall()

    if not all_news:
        st.info("No news available. Please click 'Fetch Latest News' from the sidebar to start.")
    else:
        items_per_page = 12
        total_pages = math.ceil(len(all_news) / items_per_page)
        if st.session_state.page_num > total_pages: st.session_state.page_num = 1
            
        start_idx = (st.session_state.page_num - 1) * items_per_page
        end_idx = start_idx + items_per_page
        current_page_news = all_news[start_idx:end_idx]
        
        for i in range(0, len(current_page_news), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(current_page_news):
                    news = current_page_news[i + j]
                    with cols[j]:
                        st.markdown(f'''
                            <div class="news-card">
                                <img src="{news[2]}" style="width: 100%; height: 100%; object-fit: cover;">
                            </div>
                        ''', unsafe_allow_html=True)
                        
                        formatted_date = datetime.strptime(news[4], '%Y-%m-%d %H:%M:%S.%f').strftime('%b %d, %Y')
                        st.markdown(f"<div class='news-meta'><span class='category-badge'>{news[3]}</span> &nbsp;|&nbsp; {formatted_date}</div>", unsafe_allow_html=True)
                        
                        if st.button(news[1], key=f"btn_{news[0]}", use_container_width=True):
                            st.session_state.selected_news = news
                            st.session_state.view = 'details'
                            st.rerun()
            st.write("")

        st.write("---")
        if total_pages > 1:
            page_cols = st.columns(total_pages if total_pages < 15 else 15)
            for p in range(1, total_pages + 1):
                with page_cols[p-1]:
                    btn_type = "primary" if p == st.session_state.page_num else "secondary"
                    if st.button(str(p), key=f"page_{p}", type=btn_type):
                        st.session_state.page_num = p
                        st.rerun()

# --- ২. সিঙ্গেল নিউজ পেইজ ---
elif st.session_state.view == 'details':
    news = st.session_state.selected_news
    
    if st.button("⬅️ Back to News List"):
        st.session_state.view = 'home'
        st.rerun()
    
    st.write("")
    
    formatted_date = datetime.strptime(news[4], '%Y-%m-%d %H:%M:%S.%f').strftime('%B %d, %Y - %I:%M %p')
    
    img_html = f'''
<div style="text-align: center; margin: 30px 0;">
    <img src="{news[2]}" style="max-width: 100%; width: 600px; height: auto; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
</div>
''' if news[2] else ""
    
    # ইনডেন্টেশন (খালি স্পেস) পুরোপুরি সরিয়ে দেওয়া হয়েছে, যাতে কোড ব্লক হিসেবে না দেখায়
    article_html = f"""
<div class="article-container">
    <h1 style='line-height: 1.4; color: {text_color}; text-align: center; margin-bottom: 15px; font-weight: 700;'>
        {news[1]}
    </h1>
    <p style='text-align: center; font-size: 15px; color: {meta_color};'>
        Category: <span class="category-badge" style="font-size: 15px;">{news[3]}</span> | Published: {formatted_date}
    </p>
    {img_html}
    <div class="article-text">
        {news[5]}
    </div>
    <hr style="border-top: 1px solid {meta_color}; opacity: 0.2; margin-top: 40px; margin-bottom: 20px;">
    <div style="text-align: center;">
        <a href="{news[6]}" target="_blank" style="color: {accent_color}; text-decoration: none; font-weight: 600; font-size: 16px;">🔗 Read the original article on Al Jazeera</a>
    </div>
</div>
"""
    
    st.markdown(article_html, unsafe_allow_html=True)
