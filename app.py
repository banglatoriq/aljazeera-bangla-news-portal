import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import math
import time

# --- Auto Refresh Error Handling ---
try:
    from streamlit_autorefresh import st_autorefresh
    # 30 মিনিট পর পর রিফ্রেশ
    st_autorefresh(interval=30 * 60 * 1000, key="news_update_timer")
except ImportError:
    st.warning("Auto-refresh module missing. Please add 'streamlit-autorefresh' to requirements.txt")

# --- Page Setup (Wide Layout for 3 Columns) ---
st.set_page_config(page_title="Al Jazeera News Updates", page_icon="🌐", layout="wide")

# --- Database Setup ---
@st.cache_resource
def init_db():
    conn = sqlite3.connect('news_db_grid.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news_table
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  title TEXT, link TEXT, translated_title TEXT, 
                  full_text TEXT, image_url TEXT, category TEXT, date TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS metadata (last_scrape TIMESTAMP)''')
    conn.commit()
    return conn, c

conn, c = init_db()

# --- Scraping Logic ---
def scrape_news():
    url = "https://www.aljazeera.com/" 
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        articles = []
        for heading in soup.find_all(['h3', 'h2']):
            a_tag = heading.find('a')
            if a_tag and 'href' in a_tag.attrs:
                articles.append(heading)
                if len(articles) >= 15: 
                    break
        
        translator = GoogleTranslator(source='en', target='bn')
        new_items = 0
        
        for article in articles:
            title = article.text.strip()
            link_tag = article.find('a')
            link = link_tag['href']
            if not link.startswith('http'):
                link = "https://www.aljazeera.com" + link
                
            c.execute("SELECT * FROM news_table WHERE link=?", (link,))
            if not c.fetchone():
                try:
                    art_resp = requests.get(link, headers=headers, timeout=10)
                    art_soup = BeautifulSoup(art_resp.content, 'html.parser')
                    
                    og_image = art_soup.find('meta', property='og:image')
                    image_url = og_image['content'] if og_image else "https://via.placeholder.com/600x400?text=News+Image"
                    
                    # Category in English for filtering
                    try: category = link.split('/')[3].capitalize()
                    except: category = "Latest"
                        
                    paragraphs = art_soup.find_all('p')
                    valid_paragraphs = [p.text.strip() for p in paragraphs if len(p.text.split()) > 10]
                    
                    translated_paragraphs = []
                    for p_text in valid_paragraphs[:10]: 
                        try:
                            bn_p = translator.translate(p_text)
                            translated_paragraphs.append(f"<p style='margin-bottom: 12px; line-height: 1.8; text-align: justify;'>{bn_p}</p>")
                        except: pass
                    
                    bn_title = translator.translate(title)
                    bn_full_text = "".join(translated_paragraphs) if translated_paragraphs else "No content available."
                    
                    c.execute('''INSERT INTO news_table (title, link, translated_title, full_text, image_url, category, date) 
                                 VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                              (title, link, bn_title, bn_full_text, image_url, category, datetime.now()))
                    conn.commit()
                    new_items += 1
                except: continue
        
        c.execute("DELETE FROM metadata")
        c.execute("INSERT INTO metadata VALUES (?)", (datetime.now(),))
        conn.commit()
        return True, f"Successfully fetched {new_items} new articles!"
    except Exception as e:
        return False, f"Scraping Error: {e}"

def auto_delete_old():
    limit = datetime.now() - timedelta(days=7)
    c.execute("DELETE FROM news_table WHERE date < ?", (limit,))
    conn.commit()

c.execute("SELECT last_scrape FROM metadata")
last_time = c.fetchone()
if last_time is None or (datetime.now() - datetime.strptime(last_time[0], '%Y-%m-%d %H:%M:%S.%f')) > timedelta(minutes=30):
    scrape_news()
    auto_delete_old()

# ==========================================
# Frontend UI (English Headers, Grid Layout)
# ==========================================

if 'page_num' not in st.session_state: st.session_state.page_num = 1
if 'view' not in st.session_state: st.session_state.view = 'home'
if 'selected_news' not in st.session_state: st.session_state.selected_news = None

# --- Admin Sidebar ---
st.sidebar.title("⚙️ Admin Panel")
if st.sidebar.button("🔄 Force Refresh News"):
    with st.spinner("Fetching latest news..."):
        success, msg = scrape_news()
        if success: st.sidebar.success(msg)
        else: st.sidebar.error(msg)
        time.sleep(2)
        st.rerun()

# --- Main Page Header ---
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>Al Jazeera News Updates</h1>", unsafe_allow_html=True)
st.write("---")

if st.session_state.view == 'home':
    # --- Category Filter (Isotope Style) ---
    c.execute("SELECT DISTINCT category FROM news_table")
    db_categories = c.fetchall()
    categories = ["All News"] + [cat[0] for cat in db_categories]
    
    # Horizontal Radio Buttons for Filtering
    selected_category = st.radio("🏷️ Filter by Category:", categories, horizontal=True)
    st.write("")

    # Fetch News based on Filter
    if selected_category == "All News":
        c.execute("SELECT id, translated_title, image_url, category, date, full_text, link FROM news_table ORDER BY date DESC")
    else:
        c.execute("SELECT id, translated_title, image_url, category, date, full_text, link FROM news_table WHERE category=? ORDER BY date DESC", (selected_category,))
    
    all_news = c.fetchall()

    if not all_news:
        st.info("No news available in this category. Please click 'Force Refresh News' from the sidebar.")
    else:
        # --- Pagination Setup (12 items per page) ---
        items_per_page = 12
        total_pages = math.ceil(len(all_news) / items_per_page)
        
        # Reset page to 1 if user clicks a new category and current page > total pages
        if st.session_state.page_num > total_pages:
            st.session_state.page_num = 1
            
        start_idx = (st.session_state.page_num - 1) * items_per_page
        end_idx = start_idx + items_per_page
        current_page_news = all_news[start_idx:end_idx]
        
        # --- Grid Layout (3 Columns per Row) ---
        for i in range(0, len(current_page_news), 3):
            cols = st.columns(3) # Create 3 columns
            
            for j in range(3):
                if i + j < len(current_page_news):
                    news = current_page_news[i + j]
                    n_id, n_title, n_img, n_cat, n_date, n_full, n_link = news
                    
                    with cols[j]:
                        # Card Design
                        st.markdown(f'''
                            <div style="border-radius: 8px; overflow: hidden; height: 180px; margin-bottom: 10px; background-color: #f0f2f6;">
                                <img src="{n_img}" style="width: 100%; height: 100%; object-fit: cover;">
                            </div>
                        ''', unsafe_allow_html=True)
                        
                        formatted_date = datetime.strptime(n_date, '%Y-%m-%d %H:%M:%S.%f').strftime('%b %d, %Y - %I:%M %p')
                        st.markdown(f"<span style='color: #EA580C; font-size: 13px; font-weight: bold;'>{n_cat}</span> <span style='color: gray; font-size: 12px;'>| {formatted_date}</span>", unsafe_allow_html=True)
                        
                        # News Title (in Bengali) acts as the button
                        if st.button(n_title, key=f"btn_{n_id}", use_container_width=True):
                            st.session_state.selected_news = news
                            st.session_state.view = 'details'
                            st.rerun()
            st.write("---") # Line separator after each row

        # --- Pagination Buttons ---
        if total_pages > 1:
            st.write("### Page:")
            page_cols = st.columns(total_pages if total_pages < 15 else 15)
            for p in range(1, total_pages + 1):
                with page_cols[p-1]:
                    # Highlight current page
                    btn_type = "primary" if p == st.session_state.page_num else "secondary"
                    if st.button(str(p), key=f"page_{p}", type=btn_type):
                        st.session_state.page_num = p
                        st.rerun()

# --- Single News Page ---
elif st.session_state.view == 'details':
    news = st.session_state.selected_news
    
    if st.button("⬅️ Back to News List"):
        st.session_state.view = 'home'
        st.rerun()
    
    st.write("")
    # Title (Bengali)
    st.markdown(f"<h2 style='line-height: 1.4;'>{news[1]}</h2>", unsafe_allow_html=True)
    
    # Meta Data (English)
    formatted_date = datetime.strptime(news[4], '%Y-%m-%d %H:%M:%S.%f').strftime('%b %d, %Y - %I:%M %p')
    st.markdown(f"<p style='color: gray; font-size: 14px;'>Category: <b>{news[3]}</b> | Published: {formatted_date}</p>", unsafe_allow_html=True)
    
    if news[2]: 
        st.markdown(f'''
            <div style="border-radius: 10px; overflow: hidden; margin-bottom: 20px;">
                <img src="{news[2]}" style="width: 100%; height: auto; max-height: 500px; object-fit: cover;">
            </div>
        ''', unsafe_allow_html=True)
    
    # Full News Text (Bengali)
    st.markdown(f"<div style='font-size: 18px; color: #333;'>{news[5]}</div>", unsafe_allow_html=True)
    
    st.write("---")
    st.markdown(f"**[🔗 Read the original article on Al Jazeera]({news[6]})**")
