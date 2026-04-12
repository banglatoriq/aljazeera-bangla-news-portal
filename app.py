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
import urllib.parse

# --- পেইজ সেটআপ ---
st.set_page_config(page_title="আন্তর্জাতিক সংবাদ - বাংলা", page_icon="📰", layout="wide")

# ==========================================
# থিম এবং ফন্ট সেটআপ
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

.news-image-container {{ width: 100%; overflow: hidden; border-radius: 10px; margin-bottom: 10px; background-color: #E5E0D5; }}
.news-image-container img {{ width: 100%; height: auto; display: block; object-fit: contain; }}
p {{ color: #000000 !important; font-family: 'Hind Siliguri', sans-serif !important; }}

.stButton > button {{ 
    background-color: transparent !important; 
    color: #111827 !important; 
    border: none !important; 
    font-family: 'Hind Siliguri', sans-serif !important; 
    font-size: 18px !important; 
    font-weight: 600 !important;
    text-align: left !important;
    line-height: 1.4 !important;
    padding: 0 !important;
    white-space: normal !important;
    display: block !important;
}}

.stButton > button:hover {{ color: {accent_color} !important; }}
.article-title {{ line-height: 1.3; color: #000000 !important; text-align: center; margin-bottom: 20px; font-weight: 800; font-size: 36px; }}

.share-btn {{
    display: inline-flex; align-items: center; justify-content: center;
    padding: 8px 15px; border-radius: 5px; color: white !important;
    text-decoration: none; font-size: 14px; font-weight: 600; margin-right: 10px;
}}
.fb {{ background-color: #1877F2; }}
.wa {{ background-color: #25D366; }}
</style>
""", unsafe_allow_html=True)

def show_logo():
    st.markdown("""
    <div style="text-align: center; margin-bottom: 40px; padding-top: 20px;">
        <span style="font-family: 'Arial', sans-serif; font-size: 48px; font-weight: 900; color: #D35400;">হাওয়া</span>
        <span style="font-family: 'Arial', sans-serif; font-size: 48px; font-weight: 300; color: #111827;"> বাংলা</span>
        <br><span style="font-size: 17px; color: #4B5563; font-weight: 600;">এবং অন্যান্য আন্তর্জাতিক সংবাদ</span>
    </div>
    """, unsafe_allow_html=True)

# --- ডাটাবেস সেটআপ ---
@st.cache_resource
def init_db():
    conn = sqlite3.connect('news_db_free_v7.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news_table
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, link TEXT, translated_title TEXT, 
                  full_text TEXT, image_url TEXT, video_url TEXT, source TEXT, date TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS update_meta (last_update TIMESTAMP)''')
    conn.commit()
    return conn, c

conn, c = init_db()

def safe_translate(text):
    if not text: return ""
    try:
        translator = GoogleTranslator(source='en', target='bn')
        if len(text) > 1500:
            sentences = text.split('. ')
            translated = [translator.translate(s) for s in sentences if s.strip()]
            return "। ".join(translated)
        return translator.translate(text)
    except:
        return text

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
        return None

def scrape_news():
    news_feeds = {
        "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
        "TRT World": "https://www.trtworld.com/rss.xml",
        "RT News": "https://www.rt.com/rss/",
        "Dawn": "https://www.dawn.com/feeds/home/"
    }
    headers = {'User-Agent': 'Mozilla/5.0'}
    for source_name, feed_url in news_feeds.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                c.execute("SELECT * FROM news_table WHERE link=?", (entry.link,))
                if not c.fetchone():
                    try:
                        art_resp = requests.get(entry.link, headers=headers, timeout=10)
                        art_soup = BeautifulSoup(art_resp.content, 'html.parser')
                        img = art_soup.find('meta', property='og:image')['content'] if art_soup.find('meta', property='og:image') else ""
                        
                        video_link = None
                        iframe = art_soup.find('iframe')
                        if iframe and iframe.get('src'):
                            video_link = iframe.get('src')
                        
                        paragraphs = art_soup.find_all('p')
                        full_eng_text = "\n\n".join([p.text.strip() for p in paragraphs if len(p.text.split()) > 10])
                        if not full_eng_text: continue
                        
                        bn_title = safe_translate(entry.title)
                        bn_full_text = "".join([f"<p>{safe_translate(p.strip())}</p>" for p in full_eng_text.split('\n\n')[:12] if p.strip()])
                        
                        c.execute('''INSERT INTO news_table (title, link, translated_title, full_text, image_url, video_url, source, date) 
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                                  (entry.title, entry.link, bn_title, bn_full_text, img, video_link, source_name, datetime.now()))
                        conn.commit()
                    except: continue
        except: continue
    
    c.execute("DELETE FROM update_meta")
    c.execute("INSERT INTO update_meta (last_update) VALUES (?)", (datetime.now(),))
    conn.commit()

def check_for_auto_update():
    c.execute("SELECT last_update FROM update_meta")
    row = c.fetchone()
    if not row or (datetime.now() - datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f') > timedelta(hours=2)):
        scrape_news()

check_for_auto_update()

if 'view' not in st.session_state: st.session_state.view = 'home'
if 'page_num' not in st.session_state: st.session_state.page_num = 1

if st.sidebar.button("🔄 খবর আপডেট করুন"):
    scrape_news()
    st.rerun()

if st.session_state.view == 'home':
    show_logo()
    c.execute("SELECT id, translated_title, image_url, source, date FROM news_table ORDER BY date DESC LIMIT 15")
    all_news = c.fetchall()

    if all_news:
        for i in range(0, len(all_news), 3):
            cols = st.columns(3)
            for j in range(3):
                if i+j < len(all_news):
                    n = all_news[i+j]
                    with cols[j]:
                        st.markdown(f'<div class="news-image-container"><img src="{n[2]}"></div>', unsafe_allow_html=True)
                        st.markdown(f"<div class='news-meta'><b>{n[3]}</b> | {n[4][:10]}</div>", unsafe_allow_html=True)
                        if st.button(n[1], key=f"btn_{n[0]}", use_container_width=True):
                            st.session_state.selected_news_id = n[0]
                            st.session_state.view = 'details'
                            st.rerun()

elif st.session_state.view == 'details':
    c.execute("SELECT translated_title, image_url, source, date, full_text, link, video_url FROM news_table WHERE id=?", (st.session_state.selected_news_id,))
    news = c.fetchone()
    
    if st.button("⬅️ হোম পেজে যান"):
        st.session_state.view = 'home'
        st.rerun()

    encoded_title = urllib.parse.quote(news[0])
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 20px;">
        <a class="share-btn fb" href="https://www.facebook.com/sharer/sharer.php?u={news[5]}" target="_blank">Facebook</a>
        <a class="share-btn wa" href="https://api.whatsapp.com/send?text={encoded_title}%20{news[5]}" target="_blank">WhatsApp</a>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🎧 সংবাদটি বাংলায় শুনুন"):
        audio = generate_audio(news[4])
        if audio: st.audio(audio)

if news[6]:
    st.write("---")
    # কালো রঙের টাইটেল
    st.markdown('<h3 style="color: #000000; font-family: \'Hind Siliguri\', sans-serif;">📺 ভিডিও / সোশ্যাল এমবেড</h3>', unsafe_allow_html=True)
    
    # ভিডিও কন্টেইনার (এটি ভিডিওকে ছোট এবং মাঝখানে রাখবে)
    col_vid1, col_vid2, col_vid3 = st.columns([1, 4, 1]) # মাঝখানের কলামটি বড়
    with col_vid2:
        if "youtube" in news[6] or "vimeo" in news[6]:
            st.video(news[6])
        else:
            # আইফ্রেম ভিডিও ছোট করার জন্য স্টাইলসহ
            st.markdown(f'''
                <div style="display: flex; justify-content: center;">
                    <iframe src="{news[6]}" width="100%" height="350" frameborder="0" style="border-radius: 12px; max-width: 600px;"></iframe>
                </div>
            ''', unsafe_allow_html=True)

    article_html = f"""<div style="background-color: #FFFBF0; padding: 40px; border-radius: 16px; border: 1px solid #E5E0D5; max-width: 850px; margin: 0 auto;">
<h1 class="article-title">{news[0]}</h1>
<p style='text-align: center; color: #4B5563; font-weight: 600;'>সোর্স: {news[2]} | {news[3][:10]}</p>
<div style="text-align: center; margin: 30px 0;"><img src="{news[1]}" style="max-width: 100%; border-radius: 12px;"></div>
<div style="color: #111827; font-size: 21px; line-height: 1.8; text-align: justify;">{news[4]}</div>
<hr>
<center><a href="{news[5]}" target="_blank" style="color: #D35400; font-weight: 700; text-decoration: none;">🔗 মূল ইংরেজি খবরটি পড়ুন</a></center>
</div>"""
    st.markdown(article_html, unsafe_allow_html=True)
