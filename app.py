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
# সেশন স্টেট (Session State) ইনিশিয়ালাইজেশন
# ==========================================
if 'font_size' not in st.session_state: st.session_state.font_size = 20
if 'view' not in st.session_state: st.session_state.view = 'home'
if 'page_num' not in st.session_state: st.session_state.page_num = 1
if 'bookmarks' not in st.session_state: st.session_state.bookmarks = [] # বুকমার্ক লিস্ট

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
html, body, [class*="css"] {{ font-family: 'Hind Siliguri', sans-serif !important; color: {text_color} !important; scroll-behavior: smooth; }}
.stApp {{ background-color: {bg_color}; }}

.news-image-container {{ width: 100%; overflow: hidden; border-radius: 10px; margin-bottom: 10px; background-color: #E5E0D5; position: relative; }}
.news-image-container img {{ width: 100%; height: 200px; display: block; object-fit: cover; }}
p {{ color: #000000 !important; font-family: 'Hind Siliguri', sans-serif !important; }}

.stButton > button, div[data-testid="stButton"] > button {{ 
    background-color: transparent !important; color: #111827 !important; border: none !important; box-shadow: none !important; outline: none !important;
    font-family: 'Hind Siliguri', sans-serif !important; font-size: 18px !important; font-weight: 600 !important;
    text-align: left !important; line-height: 1.4 !important; padding: 0 !important; white-space: normal !important; display: block !important; transition: 0.2s;
}}
.stButton > button:hover, div[data-testid="stButton"] > button:hover {{ color: {accent_color} !important; transform: translateX(5px); }}

.article-title {{ line-height: 1.3; color: #000000 !important; text-align: center; margin-bottom: 10px; font-weight: 800; font-size: 36px; }}
.share-btn {{ display: inline-flex; align-items: center; justify-content: center; padding: 8px 15px; border-radius: 5px; color: white !important; text-decoration: none; font-size: 14px; font-weight: 600; margin-right: 10px; transition: 0.2s; }}
.share-btn:hover {{ opacity: 0.8; transform: translateY(-2px); }}
.fb {{ background-color: #1877F2; }}
.wa {{ background-color: #25D366; }}

.read-time-badge {{ background-color: #E5E0D5; color: #4B5563; padding: 4px 12px; border-radius: 20px; font-size: 14px; font-weight: 600; display: inline-block; margin-bottom: 20px; }}
.content-box {{ background-color: #FFFBF0; padding: 30px; border-radius: 16px; border: 1px solid #E5E0D5; margin-bottom: 20px; max-width: 850px; margin-left: auto; margin-right: auto; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
.tldr-box {{ background-color: #F0FDF4; border-left: 5px solid #22C55E; padding: 15px 20px; border-radius: 0 10px 10px 0; margin-bottom: 25px; }}
.tldr-title {{ color: #166534; font-weight: 700; font-size: 18px; margin-bottom: 5px; display: flex; align-items: center; gap: 5px; }}
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
    conn = sqlite3.connect('news_db_pro_v1.db', check_same_thread=False, timeout=30)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news_table
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, link TEXT, translated_title TEXT, 
                  full_text TEXT, image_url TEXT, video_url TEXT, source TEXT, date TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS update_meta (last_update TIMESTAMP)''')
    conn.commit()
    return conn, c

conn, c = init_db()

# --- ফ্রি অনুবাদ ফাংশন ---
def safe_translate(text):
    if not text: return ""
    try:
        translator = GoogleTranslator(source='en', target='bn')
        if len(text) > 1500:
            sentences = text.split('. ')
            translated = [translator.translate(s) for s in sentences if s.strip()]
            return "। ".join(translated)
        return translator.translate(text)
    except: return text

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
        with open(audio_file, "rb") as f: audio_data = f.read()
        os.remove(audio_file)
        return audio_data
    except: return None

# --- স্ক্র্যাপিং লজিক ---
def scrape_news():
    news_feeds = {
        "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
        "TRT World": "https://www.trtworld.com/rss.xml",
        "RT News": "https://www.rt.com/rss/"
    }
    headers = {'User-Agent': 'Mozilla/5.0'}
    for source_name, feed_url in news_feeds.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:4]: # একটু দ্রুত করার জন্য প্রতি সাইট থেকে ৪টি
                c.execute("SELECT * FROM news_table WHERE link=?", (entry.link,))
                if not c.fetchone():
                    try:
                        art_resp = requests.get(entry.link, headers=headers, timeout=10)
                        art_soup = BeautifulSoup(art_resp.content, 'html.parser')
                        
                        # ফলব্যাক ইমেজ লজিক
                        img = art_soup.find('meta', property='og:image')
                        img_url = img['content'] if img else "https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=800&auto=format&fit=crop"
                        
                        video_link = None
                        for iframe in art_soup.find_all('iframe'):
                            src = iframe.get('src', '')
                            if src and 'ad' not in src.lower() and 'banner' not in src.lower():
                                if src.startswith('//'): src = 'https:' + src
                                video_link = src
                                break
                        
                        if not video_link:
                            vid_tag = art_soup.find('video')
                            if vid_tag:
                                src = vid_tag.get('src') or (vid_tag.find('source').get('src') if vid_tag.find('source') else None)
                                if src: video_link = src
                        
                        if not video_link:
                            tweet = art_soup.find('blockquote', class_='twitter-tweet')
                            if tweet and tweet.find_all('a'): video_link = tweet.find_all('a')[-1].get('href')
                        
                        paragraphs = art_soup.find_all('p')
                        full_eng_text = "\n\n".join([p.text.strip() for p in paragraphs if len(p.text.split()) > 10])
                        if not full_eng_text: continue
                        
                        bn_title = safe_translate(entry.title)
                        bn_full_text = "".join([f"<p>{safe_translate(p.strip())}</p>" for p in full_eng_text.split('\n\n')[:10] if p.strip()])
                        
                        c.execute('''INSERT INTO news_table (title, link, translated_title, full_text, image_url, video_url, source, date) 
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                                  (entry.title, entry.link, bn_title, bn_full_text, img_url, video_link, source_name, datetime.now()))
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
        if not row or (datetime.now() - datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f') > timedelta(hours=3)):
            scrape_news()
    except: pass

check_for_auto_update()

# ==========================================
# Sidebar Navigation (নতুন UI)
# ==========================================
st.sidebar.markdown("<h2 style='text-align: center; color: #D35400;'>মেনু</h2>", unsafe_allow_html=True)
nav_selection = st.sidebar.radio("", ["🏠 হোম পেজ", "🔖 সেভ করা খবর"])

if st.sidebar.button("🔄 খবর আপডেট করুন"):
    with st.spinner("খবর আপডেট হচ্ছে..."):
        scrape_news()
        st.session_state.view = 'home'
        st.rerun()

# --- ১. হোম পেইজ বা সেভ করা পেইজ ---
if st.session_state.view == 'home':
    show_logo()
    
    if nav_selection == "🏠 হোম পেজ":
        c.execute("SELECT id, translated_title, image_url, source, date FROM news_table ORDER BY date DESC LIMIT 15")
        st.subheader("সর্বশেষ সংবাদ")
    else:
        # সেভ করা খবর দেখানোর লজিক
        if st.session_state.bookmarks:
            placeholders = ','.join(['?'] * len(st.session_state.bookmarks))
            c.execute(f"SELECT id, translated_title, image_url, source, date FROM news_table WHERE id IN ({placeholders}) ORDER BY date DESC", st.session_state.bookmarks)
            st.subheader("আপনার সেভ করা খবরগুলো")
        else:
            st.info("আপনি এখনও কোনো খবর সেভ করেননি। খবর পড়ার সময় 'সেভ করুন' বাটনে ক্লিক করুন।")
            c.execute("SELECT id FROM news_table WHERE id=-1") # Empty query
            
    all_news = c.fetchall()

    if all_news:
        st.write("---")
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
    c.execute("SELECT id, translated_title, image_url, source, date, full_text, link, video_url FROM news_table WHERE id=?", (st.session_state.selected_news_id,))
    news = c.fetchone()
    news_id = news[0]
    
    # টপ কন্ট্রোল বার
    t1, t2, t3 = st.columns([1, 1.5, 1])
    with t1:
        if st.button("⬅️ ফিরে যান"):
            st.session_state.view = 'home'
            st.rerun()
    with t2:
        st.session_state.font_size = st.select_slider("📖 ফন্ট সাইজ:", options=[18, 20, 22, 24, 26], value=st.session_state.font_size, label_visibility="collapsed")
    with t3:
        # 🔴 বুকমার্ক বাটন
        is_saved = news_id in st.session_state.bookmarks
        if st.button("🔖 সেভড (রিমুভ)" if is_saved else "🔖 সেভ করে রাখুন"):
            if is_saved: st.session_state.bookmarks.remove(news_id)
            else: st.session_state.bookmarks.append(news_id)
            st.rerun()

    # অডিও বাটন
    col_a1, col_a2, col_a3 = st.columns([1, 2, 1])
    with col_a2:
        if st.button("🎧 সংবাদটি বাংলায় শুনুন", use_container_width=True):
            with st.spinner("অডিও তৈরি হচ্ছে..."):
                audio = generate_audio(news[5])
                if audio: st.audio(audio)

    # সোশ্যাল শেয়ার
    encoded_title = urllib.parse.quote(news[1])
    st.markdown(f"""
        <div style="text-align: center; margin: 20px 0;">
            <a class="share-btn fb" href="https://www.facebook.com/sharer/sharer.php?u={news[6]}" target="_blank">Facebook</a>
            <a class="share-btn wa" href="https://api.whatsapp.com/send?text={encoded_title}%20{news[6]}" target="_blank">WhatsApp</a>
        </div>
    """, unsafe_allow_html=True)

    word_count = len(BeautifulSoup(news[5], "html.parser").get_text().split())
    read_time = max(1, word_count // 150)

    # 🔴 পার্ট ১: টাইটেল এবং ছবি
    st.markdown(f"""
        <div class="content-box">
            <div style="text-align: center;">
                <h1 class="article-title">{news[1]}</h1>
                <div class="read-time-badge">⏱️ পড়তে সময় লাগবে প্রায় {read_time} মিনিট</div>
                <p style='color: #4B5563; font-weight: 600;'>সোর্স: {news[3]} | {news[4][:10]}</p>
                <img src="{news[2]}" style="width: 100%; border-radius: 12px; margin-top: 15px; max-height: 450px; object-fit: cover;">
            </div>
        </div>
    """, unsafe_allow_html=True)

    paragraphs = [p for p in news[5].split('</p>') if p.strip()]
    
    # 🔴 পার্ট ২: TL;DR (এক নজরে)
    if len(paragraphs) > 0:
        summary_text = BeautifulSoup(paragraphs[0], "html.parser").get_text()
        st.markdown(f'''
            <div class="content-box" style="padding-top: 10px; padding-bottom: 10px;">
                <div class="tldr-box">
                    <div class="tldr-title">📝 এক নজরে</div>
                    <p style="margin: 0; color: #064E3B; font-size: 17px;">{summary_text}</p>
                </div>
            </div>
        ''', unsafe_allow_html=True)

    # 🔴 পার্ট ৩: ভিডিও বা টুইট
    if news[7]:
        st.markdown("<br>", unsafe_allow_html=True)
        if 'twitter.com' in news[7] or 'x.com' in news[7]:
            tweet_html = f'''<div style="display: flex; justify-content: center; width: 100%;"><blockquote class="twitter-tweet" data-theme="light"><a href="{news[7]}"></a></blockquote></div><script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>'''
            components.html(tweet_html, height=600, scrolling=True)
        elif "youtube" in news[7] or "vimeo" in news[7] or news[7].endswith('.mp4'):
            col_vid1, col_vid2, col_vid3 = st.columns([1, 6, 1])
            with col_vid2: st.video(news[7])
        else:
            col_vid1, col_vid2, col_vid3 = st.columns([1, 6, 1])
            with col_vid2: st.markdown(f'<iframe src="{news[7]}" width="100%" height="400" frameborder="0" style="border-radius: 12px;"></iframe>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # 🔴 পার্ট ৪: বিস্তারিত নিউজ
    if len(paragraphs) > 0:
        rest_of_news = "</p>".join(paragraphs) + "</p>"
        rest_of_news = re.sub(r'(pic\.twitter\.com/\w+)', r'<a href="https://\1" target="_blank" style="color:#1DA1F2;">\1 (টুইটটি দেখুন)</a>', rest_of_news)
        
        st.markdown(f'''
            <div class="content-box" style="font-size: {st.session_state.font_size}px; line-height: 1.8; text-align: justify;">
                {rest_of_news}
                <hr style="border-top: 2px dashed #E5E0D5; margin-top: 30px;">
                <center><a href="{news[6]}" target="_blank" style="color: #D35400; font-weight: 700; text-decoration: none; font-size: 18px;">🔗 মূল ইংরেজি খবরটি পড়ুন</a></center>
            </div>
        ''', unsafe_allow_html=True)

    # 🔴 পার্ট ৫: সম্পর্কিত খবর (Related News)
    st.markdown("<h3 style='text-align: center; margin-top: 40px; margin-bottom: 20px;'>⚡ এই সম্পর্কিত আরও খবর</h3>", unsafe_allow_html=True)
    c.execute("SELECT id, translated_title, image_url, source, date FROM news_table WHERE source=? AND id!=? ORDER BY date DESC LIMIT 3", (news[3], news_id))
    related = c.fetchall()
    
    if related:
        cols = st.columns(3)
        for j, rel in enumerate(related):
            with cols[j]:
                st.markdown(f'<div class="news-image-container"><img src="{rel[2]}" style="height: 150px;"></div>', unsafe_allow_html=True)
                if st.button(rel[1][:60] + "...", key=f"rel_{rel[0]}", use_container_width=True):
                    st.session_state.selected_news_id = rel[0]
                    st.rerun()
    else:
        st.info("আপাতত এই সম্পর্কিত আর কোনো খবর নেই।")
