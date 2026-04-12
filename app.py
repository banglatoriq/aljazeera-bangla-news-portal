import streamlit as st
import sqlite3
import math
import asyncio
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from gtts import gTTS
import edge_tts
import feedparser
import io
import tempfile
import time
import os



# --- পেইজ সেটআপ ---
st.set_page_config(page_title="আন্তর্জাতিক সংবাদ - বাংলা", page_icon="📰", layout="wide")



# ==========================================
# থিম এবং ফন্ট সেটআপ (বইয়ের পাতার রঙ ও উন্নত ডিজাইন)
# ==========================================
bg_color = "#FDF6E3"       
card_bg = "#FFFBF0"        
text_color = "#111827"
accent_color = "#D35400"



st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&display=swap');
html, body, [class*="css"] {{ font-family: 'Hind Siliguri', sans-serif !important; color: {text_color} !important; }}
.stApp {{ background-color: {bg_color}; }}



/* ছবি যেন না কাটে তার সমাধান */
.news-image-container {{
    width: 100%;
    overflow: hidden;
    border-radius: 10px;
    margin-bottom: 10px;
    background-color: #E5E0D5;
}}
.news-image-container img {{
    width: 100%;
    height: auto;
    display: block;
    object-fit: contain;
}}
p{{color:#000000 !important}}



/* এই কোডটি Streamlit-এর ডিফল্ট কোডকে ওভাররাইড (Override) করবে */
.stButton > button {{ 
    font-family: 'Hind Siliguri', sans-serif !important; 
    font-size: 18px !important; 
    font-weight: 600 !important;
}}



/* নিউজ মেটা তথ্য */
.news-meta {{ color: #4B5563 !important; font-size: 13px; margin-top: 8px; font-weight: 600; }}
.category-badge {{ color: {accent_color} !important; font-weight: 800; }}



/* 🔴 টাইটেল বাটনটি বড় এবং বোল্ড করার জন্য চূড়ান্ত ফিক্স */
.stButton > button {{ 
    background-color: transparent !important; 
    color: #111827 !important; 
    border: none !important; 
    font-weight: 800 !important; 
    font-size: 22px !important; /* সাইজ বাড়ানো হয়েছে */
    text-align: left !important;
    line-height: 1.3 !important;
    padding: 0 !important;
    margin-top: 5px !important;
    white-space: normal !important;
    display: block !important;
}}
.stButton > button:hover {{ color: {accent_color} !important; }}



/* সিঙ্গেল নিউজ পেজ ডিজাইন */
.article-title {{ 
    line-height: 1.3; 
    color: #000000 !important; 
    text-align: center; 
    margin-bottom: 20px; 
    font-weight: 800; 
    font-size: 36px; 
}}
</style>
""", unsafe_allow_html=True)



def show_logo():
    st.markdown("""
    <div style="text-align: center; margin-bottom: 40px; padding-top: 20px;">
        <span style="font-family: 'Arial', sans-serif; font-size: 48px; font-weight: 900; color: #D35400;">হাওয়া</span>
        <span style="font-family: 'Arial', sans-serif; font-size: 48px; font-weight: 300; color: #111827;"> বাংলা</span>
        <br><span style="font-size: 17px; color: #4B5563; font-weight: 600;">এবং অন্যান্য আন্তর্জাতিক সংবাদ</span>
    </div>
    """, unsafe_allow_html=True)



# --- ডাটাবেস সেটআপ ---
@st.cache_resource
def init_db():
    conn = sqlite3.connect('news_db_v4.db', check_same_thread=False) # ডাটাবেস ভার্সন আপডেট করা হয়েছে
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news_table
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, link TEXT, translated_title TEXT, 
                  full_text TEXT, image_url TEXT, category TEXT, source TEXT, date TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS update_meta (last_update TIMESTAMP)''')
    conn.commit()
    return conn, c



conn, c = init_db()



# --- 🔴 উন্নত অনুবাদ ফাংশন (পুরো খবর নিশ্চিত করার জন্য) ---
def safe_translate(text):
    if not text: return ""
    try:
        translator = GoogleTranslator(source='en', target='bn')
        # টেক্সটকে ৫০০০ অক্ষরের ছোট ছোট ভাগে ভাগ করে অনুবাদ
        max_chars = 1500
        if len(text) > max_chars:
            chunks = [text[i:i+max_chars] for i in range(0, len(text), max_chars)]
            translated_chunks = [translator.translate(ch) for ch in chunks if ch.strip()]
            return " ".join(translated_chunks)
        return translator.translate(text)
    except:
        return text



# --- অডিও জেনারেটর ---
def generate_audio(text):
    clean_text = BeautifulSoup(text, "html.parser").get_text(separator=' ')[:4000]
    try:
        async def _main():
            communicate = edge_tts.Communicate(clean_text, "bn-BD-NabanitaNeural")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_path = fp.name
            await communicate.save(temp_path)
            return temp_path
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_file = loop.run_until_complete(_main())
        with open(audio_file, "rb") as f:
            audio_data = f.read()
        os.remove(audio_file)
        return audio_data
    except:
        tts = gTTS(text=clean_text, lang='bn')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()



# --- উন্নত স্ক্র্যাপিং (ডুপ্লিকেট নিউজ ফিল্টার সহ) ---
def scrape_news():
    news_feeds = {
        "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
        "TRT World": "https://www.trtworld.com/rss.xml",
        "RT News": "https://www.rt.com/rss/",
        "Dawn": "https://www.dawn.com/feeds/home/"
    }
    new_items = 0
    headers = {'User-Agent': 'Mozilla/5.0'}
    for source_name, feed_url in news_feeds.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                title = entry.title
                link = entry.link
                
                # 🔴 ডুপ্লিকেট চেকার: লিংক এবং মূল টাইটেল চেক
                c.execute("SELECT * FROM news_table WHERE link=? OR title=?", (link, title))
                if not c.fetchone():
                    try:
                        art_resp = requests.get(link, headers=headers, timeout=10)
                        art_soup = BeautifulSoup(art_resp.content, 'html.parser')
                        img = art_soup.find('meta', property='og:image')['content'] if art_soup.find('meta', property='og:image') else "https://via.placeholder.com/600x400"
                        
                        paragraphs = art_soup.find_all('p')
                        full_eng_text = "\n\n".join([p.text.strip() for p in paragraphs if len(p.text.split()) > 10])
                        if not full_eng_text: continue
                        
                        bn_title = safe_translate(title)
                        
                        # প্যারাগ্রাফ ধরে ধরে অনুবাদ নিশ্চিত করা
                        bn_full_text = ""
                        for p in full_eng_text.split('\n\n')[:15]: 
                            if p.strip():
                                bn_full_text += f"<p>{safe_translate(p.strip())}</p>"
                        
                        c.execute('''INSERT INTO news_table (title, link, translated_title, full_text, image_url, category, source, date) 
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                                  (title, link, bn_title, bn_full_text, img, "বিশ্ব সংবাদ", source_name, datetime.now()))
                        new_items += 1
                        time.sleep(1)
                    except: continue
        except: continue
    
    c.execute("DELETE FROM update_meta")
    c.execute("INSERT INTO update_meta (last_update) VALUES (?)", (datetime.now(),))
    conn.commit()
    return True, new_items



def auto_delete_old():
    limit = datetime.now() - timedelta(days=7)
    c.execute("DELETE FROM news_table WHERE date < ?", (limit,))
    conn.commit()



def check_for_auto_update():
    c.execute("SELECT last_update FROM update_meta")
    row = c.fetchone()
    if not row or (datetime.now() - datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f') > timedelta(hours=2)):
        auto_delete_old()
        scrape_news()
        st.rerun()



check_for_auto_update()



# ==========================================
# Frontend UI
# ==========================================



st.sidebar.title("⚙️ এডমিন প্যানেল")
if st.sidebar.button("🔄 খবর আপডেট করুন"):
    with st.spinner("নিউজ লোড হচ্ছে..."):
        auto_delete_old()
        success, count = scrape_news()
        st.sidebar.success(f"{count}টি নতুন খবর পাওয়া গেছে!")
        st.rerun()



if 'page_num' not in st.session_state: st.session_state.page_num = 1
if 'view' not in st.session_state: st.session_state.view = 'home'



# --- ১. হোম পেইজ ---
if st.session_state.view == 'home':
    show_logo()
    c.execute("SELECT DISTINCT source FROM news_table")
    sources = ["সব সোর্স"] + [s[0] for s in c.fetchall() if s[0]]
    selected_source = st.selectbox("📰 সোর্স নির্বাচন করুন:", sources)
    
    query = "SELECT id, translated_title, image_url, source, date FROM news_table "
    query += "ORDER BY date DESC" if selected_source == "সব সোর্স" else f"WHERE source='{selected_source}' ORDER BY date DESC"
    c.execute(query)
    all_news = c.fetchall()



    if not all_news:
        st.info("খবর লোড হচ্ছে, অনুগ্রহ করে অপেক্ষা করুন...")
    else:
        items_per_page = 12
        total_pages = math.ceil(len(all_news) / items_per_page)
        start_idx = (st.session_state.page_num - 1) * items_per_page
        current_news = all_news[start_idx : start_idx + items_per_page]
        
        for i in range(0, len(current_news), 3):
            cols = st.columns(3)
            for j in range(3):
                if i+j < len(current_news):
                    n = current_news[i+j]
                    with cols[j]:
                        st.markdown(f'<div class="news-image-container"><img src="{n[2]}"></div>', unsafe_allow_html=True)
                        formatted_date = datetime.strptime(n[4], '%Y-%m-%d %H:%M:%S.%f').strftime('%b %d, %Y')
                        st.markdown(f"<div class='news-meta'><span class='category-badge'>{n[3]}</span> | {formatted_date}</div>", unsafe_allow_html=True)
                        if st.button(n[1], key=f"btn_{n[0]}", use_container_width=True):
                            st.session_state.selected_news_id = n[0]
                            st.session_state.view = 'details'
                            st.rerun()
            st.write("")



        st.write("---")
        if total_pages > 1:
            page_cols = st.columns([4] + [1]*total_pages + [4])
            for p in range(1, total_pages + 1):
                with page_cols[p]:
                    if st.button(str(p), key=f"p_{p}", type="primary" if p == st.session_state.page_num else "secondary"):
                        st.session_state.page_num = p
                        st.rerun()



# --- ২. বিস্তারিত পেইজ ---
elif st.session_state.view == 'details':
    c.execute("SELECT translated_title, image_url, source, date, full_text, link FROM news_table WHERE id=?", (st.session_state.selected_news_id,))
    news = c.fetchone()
    
    if st.button("⬅️ হোম পেজে যান"):
        st.session_state.view = 'home'
        st.rerun()



    st.write("")
    col_a1, col_a2, col_a3 = st.columns([1, 2, 1])
    with col_a2:
        if st.button("🎧 সংবাদটি বাংলায় শুনুন", use_container_width=True):
            with st.spinner("অডিও তৈরি হচ্ছে..."):
                audio_bytes = generate_audio(news[4])
                st.audio(audio_bytes, format='audio/mp3')



    # 🔴 বিস্তারিত পেজে টাইটেল এবং টেক্সট ফরম্যাটিং
    article_html = f"""<div style="background-color: #FFFBF0; padding: 40px; border-radius: 16px; border: 1px solid #E5E0D5; max-width: 850px; margin: 0 auto;">
<h1 class="article-title">{news[0]}</h1>
<p style='text-align: center; color: #4B5563; font-weight: 600; border-bottom: 1px solid #E5E0D5; padding-bottom: 20px;'>সোর্স: {news[2]} | {datetime.strptime(news[3], '%Y-%m-%d %H:%M:%S.%f').strftime('%B %d, %Y')}</p>
<div style="text-align: center; margin: 30px 0;"><img src="{news[1]}" style="max-width: 100%; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);"></div>
<div style="color: #111827; font-size: 21px; line-height: 1.8; text-align: justify;">{news[4]}</div>
<hr style="border-top: 2px dashed #E5E0D5; margin-top: 40px; margin-bottom: 20px;">
<center><a href="{news[5]}" target="_blank" style="color: #D35400; font-weight: 700; text-decoration: none; font-size: 18px;">🔗 মূল ইংরেজি খবরটি পড়ুন</a></center>
</div>"""
    
    st.markdown(article_html, unsafe_allow_html=True)
 
