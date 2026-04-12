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
import re
import streamlit.components.v1 as components

# --- পেইজ সেটআপ ---
st.set_page_config(page_title="আন্তর্জাতিক সংবাদ - বাংলা", page_icon="📰", layout="wide")

# ==========================================
# থিম এবং ফন্ট সেটআপ
# ==========================================
bg_color = "#FDF6E3"
card_bg = "#FFFBF0"
text_color = "#111827"
accent_color = "#D35400"

if 'font_size' not in st.session_state:
    st.session_state.font_size = 20

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&display=swap');
html, body, [class*="css"] {{ font-family: 'Hind Siliguri', sans-serif !important; color: {text_color} !important; }}
.stApp {{ background-color: {bg_color}; }}

.news-image-container {{ width: 100%; overflow: hidden; border-radius: 10px; margin-bottom: 10px; background-color: #E5E0D5; }}
.news-image-container img {{ width: 100%; height: auto; display: block; object-fit: contain; }}
p {{ color: #000000 !important; font-family: 'Hind Siliguri', sans-serif !important; }}

.stButton > button {{ 
    background-color: transparent !important; color: #111827 !important; border: none !important; 
    font-family: 'Hind Siliguri', sans-serif !important; font-size: 18px !important; font-weight: 600 !important;
    text-align: left !important; line-height: 1.4 !important; padding: 0 !important; white-space: normal !important; display: block !important;
}}
.stButton > button:hover {{ color: {accent_color} !important; }}
.article-title {{ line-height: 1.3; color: #000000 !important; text-align: center; margin-bottom: 10px; font-weight: 800; font-size: 36px; }}

.share-btn {{ display: inline-flex; align-items: center; justify-content: center; padding: 8px 15px; border-radius: 5px; color: white !important; text-decoration: none; font-size: 14px; font-weight: 600; margin-right: 10px; }}
.fb {{ background-color: #1877F2; }}
.wa {{ background-color: #25D366; }}

.read-time-badge {{ background-color: #E5E0D5; color: #4B5563; padding: 4px 12px; border-radius: 20px; font-size: 14px; font-weight: 600; display: inline-block; margin-bottom: 20px; }}
.content-box {{ background-color: #FFFBF0; padding: 30px; border-radius: 16px; border: 1px solid #E5E0D5; margin-bottom: 20px; max-width: 850px; margin-left: auto; margin-right: auto; }}
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

@st.cache_resource
def init_db():
    conn = sqlite3.connect('news_db_free_v9.db', check_same_thread=False, timeout=30)
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
        with open(audio_file, "rb") as f: audio_data = f.read()
        os.remove(audio_file)
        return audio_data
    except: return None

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
                        
                        # 🔴 ভিডিও এবং টুইট লিঙ্ক খোঁজার উন্নত পদ্ধতি (সাদা বক্স বন্ধ করার জন্য)
                        video_link = None
                        
                        # ১. প্রথমে বৈধ ভিডিও আইফ্রেম খুঁজবে
                        for iframe in art_soup.find_all('iframe'):
                            src = iframe.get('src', '')
                            # শুধুমাত্র আসল ভিডিও প্ল্যাটফর্ম হলে নিবে (এডস বা ট্র্যাকার বাদ)
                            if any(platform in src for platform in ['youtube', 'vimeo', 'dailymotion', 'rt.com']):
                                if src.startswith('//'): src = 'https:' + src
                                video_link = src
                                break
                        
                        # ২. ভিডিও না পেলে টুইটারের এমবেড খুঁজবে
                        if not video_link:
                            tweet = art_soup.find('blockquote', class_='twitter-tweet')
                            if tweet:
                                a_tags = tweet.find_all('a')
                                if a_tags: video_link = a_tags[-1].get('href') # টুইটের লিংক নিবে
                        
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
    try:
        c.execute("DELETE FROM update_meta")
        c.execute("INSERT INTO update_meta (last_update) VALUES (?)", (datetime.now(),))
        conn.commit()
    except: pass

def check_for_auto_update():
    try:
        c.execute("SELECT last_update FROM update_meta")
        row = c.fetchone()
        if not row or (datetime.now() - datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f') > timedelta(hours=2)):
            scrape_news()
    except: pass

check_for_auto_update()

# ==========================================
# Frontend UI
# ==========================================
if 'view' not in st.session_state: st.session_state.view = 'home'
if 'page_num' not in st.session_state: st.session_state.page_num = 1

if st.sidebar.button("🔄 খবর আপডেট করুন"):
    with st.spinner("খবর আপডেট হচ্ছে..."):
        scrape_news()
        st.rerun()

# --- ১. হোম পেইজ ---
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

# --- ২. বিস্তারিত পেইজ ---
elif st.session_state.view == 'details':
    c.execute("SELECT translated_title, image_url, source, date, full_text, link, video_url FROM news_table WHERE id=?", (st.session_state.selected_news_id,))
    news = c.fetchone()
    
    t1, t2, t3 = st.columns([1, 2, 1])
    with t1:
        if st.button("⬅️ হোম পেজে যান"):
            st.session_state.view = 'home'
            st.rerun()
    with t2:
        st.session_state.font_size = st.select_slider("📖 ফন্ট সাইজ:", options=[18, 20, 22, 24, 26], value=st.session_state.font_size)

    col_a1, col_a2, col_a3 = st.columns([1, 2, 1])
    with col_a2:
        if st.button("🎧 সংবাদটি বাংলায় শুনুন", use_container_width=True):
            with st.spinner("অডিও তৈরি হচ্ছে..."):
                audio = generate_audio(news[4])
                if audio: st.audio(audio)

    encoded_title = urllib.parse.quote(news[0])
    st.markdown(f"""
        <div style="text-align: center; margin: 20px 0;">
            <a class="share-btn fb" href="https://www.facebook.com/sharer/sharer.php?u={news[5]}" target="_blank">Facebook</a>
            <a class="share-btn wa" href="https://api.whatsapp.com/send?text={encoded_title}%20{news[5]}" target="_blank">WhatsApp</a>
        </div>
    """, unsafe_allow_html=True)

    word_count = len(BeautifulSoup(news[4], "html.parser").get_text().split())
    read_time = max(1, word_count // 150)

    # 🔴 পার্ট ১: টাইটেল এবং প্রথম ছবি
    st.markdown(f"""
        <div class="content-box">
            <div style="text-align: center;">
                <h1 class="article-title">{news[0]}</h1>
                <div class="read-time-badge">⏱️ পড়তে সময় লাগবে প্রায় {read_time} মিনিট</div>
                <p style='color: #4B5563; font-weight: 600;'>সোর্স: {news[2]} | {news[3][:10]}</p>
                <img src="{news[1]}" style="width: 100%; border-radius: 12px; margin-top: 15px;">
            </div>
        </div>
    """, unsafe_allow_html=True)

    paragraphs = [p for p in news[4].split('</p>') if p.strip()]
    
    # 🔴 পার্ট ২: প্রথম প্যারাগ্রাফ
    if len(paragraphs) > 0:
        # টুইটার লিংক ফিক্স করা (যদি টেক্সটের ভেতর pic.twitter থাকে)
        para1 = re.sub(r'(pic\.twitter\.com/\w+)', r'<a href="https://\1" target="_blank" style="color:#1DA1F2;">\1</a>', paragraphs[0])
        st.markdown(f'<div class="content-box" style="font-size: {st.session_state.font_size}px; line-height: 1.8; text-align: justify;">{para1}</p></div>', unsafe_allow_html=True)

    # 🔴 পার্ট ৩: ভিডিও বা টুইট এমবেড (HTML ব্রেক ছাড়া, তাই আর সাদা বক্স আসবে না)
    if news[6] and news[6].startswith('http'):
        st.markdown("<br>", unsafe_allow_html=True)
        col_vid1, col_vid2, col_vid3 = st.columns([1, 6, 1])
        with col_vid2:
            if 'twitter.com' in news[6]:
                # টুইটার আসল এমবেড
                tweet_html = f'''<blockquote class="twitter-tweet" data-theme="light"><a href="{news[6]}"></a></blockquote> <script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>'''
                components.html(tweet_html, height=500, scrolling=True)
            elif "youtube" in news[6] or "vimeo" in news[6]:
                st.video(news[6])
            else:
                st.markdown(f'<iframe src="{news[6]}" width="100%" height="400" frameborder="0" style="border-radius: 12px;"></iframe>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # 🔴 পার্ট ৪: বাকি নিউজ এবং সোর্স লিঙ্ক
    if len(paragraphs) > 1:
        rest_of_news = "</p>".join(paragraphs[1:]) + "</p>"
        # টেক্সটের ভেতরের টুইটার লিংক ফিক্স
        rest_of_news = re.sub(r'(pic\.twitter\.com/\w+)', r'<a href="https://\1" target="_blank" style="color:#1DA1F2;">\1 (টুইটটি দেখুন)</a>', rest_of_news)
        
        st.markdown(f'''
            <div class="content-box" style="font-size: {st.session_state.font_size}px; line-height: 1.8; text-align: justify;">
                {rest_of_news}
                <hr style="border-top: 2px dashed #E5E0D5; margin-top: 30px;">
                <center><a href="{news[5]}" target="_blank" style="color: #D35400; font-weight: 700; text-decoration: none; font-size: 18px;">🔗 মূল ইংরেজি খবরটি পড়ুন</a></center>
            </div>
        ''', unsafe_allow_html=True)
