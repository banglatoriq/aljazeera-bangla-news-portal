import streamlit as st
import sqlite3
import math
import asyncio
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import edge_tts
import feedparser
import io
import tempfile
import time
import os
import urllib.parse
import re
import json
import streamlit.components.v1 as components

# ==========================================
# পেইজ সেটআপ
# ==========================================
st.set_page_config(
    page_title="হাওয়া বাংলা - আন্তর্জাতিক সংবাদ",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# সেশন স্টেট ইনিশিয়ালাইজেশন
# ==========================================
if 'font_size' not in st.session_state: st.session_state.font_size = 20
if 'view' not in st.session_state: st.session_state.view = 'home'
if 'page_num' not in st.session_state: st.session_state.page_num = 1
if 'bookmarks' not in st.session_state: st.session_state.bookmarks = []
if 'category_filter' not in st.session_state: st.session_state.category_filter = 'General'

# ==========================================
# থিম এবং স্টাইল
# ==========================================
bg_color = "#FDF6E3"
card_bg = "#FFFBF0"
text_color = "#111827"
accent_color = "#D35400"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&display=swap');

html, body, .stApp {{ font-family: 'Hind Siliguri', sans-serif !important; scroll-behavior: smooth; background-color: {bg_color}; }}
header[data-testid="stHeader"] {{ display: none !important; }}
.block-container {{ padding-top: 1.5rem !important; padding-bottom: 2rem !important; margin-top: 0 !important; }}
.main {{ color: {text_color} !important; }}
p {{ color: #111827 !important; font-family: 'Hind Siliguri', sans-serif !important; }}

.news-image-container {{ width: 100%; overflow: hidden; border-radius: 10px; margin-bottom: 10px; background-color: #E5E0D5; position: relative; }}
.news-image-container img {{ width: 100%; height: 325px; display: block; object-fit: cover; }}
.news-meta {{ color: #4B5563 !important; font-size: 14px; margin-top: 5px; font-weight: 600; }}

.stButton > button, div[data-testid="stButton"] > button {{ 
    background-color: transparent !important; color: #111827 !important; border: none !important; box-shadow: none !important; outline: none !important;
    font-family: 'Hind Siliguri', sans-serif !important; font-size: 18px !important; font-weight: 600 !important;
    text-align: left !important; line-height: 1.4 !important; padding: 0 !important; white-space: normal !important; display: block !important; transition: 0.2s;
}}
.stButton > button:hover, div[data-testid="stButton"] > button:hover {{ color: {accent_color} !important; transform: translateX(3px); }}
.nav-btn > button {{ background-color: #E5E0D5 !important; padding: 10px !important; border-radius: 8px !important; text-align: center !important; transform: none !important; }}
.nav-btn > button:hover {{ background-color: {accent_color} !important; color: white !important; transform: none !important; }}
.top-home-btn > button {{ background-color: #111827 !important; color: white !important; padding: 5px 15px !important; border-radius: 6px !important; font-size: 16px !important; text-align: center !important; }}
.top-home-btn > button:hover {{ background-color: {accent_color} !important; }}
button[kind="secondary"][data-testid*="home_refresh_btn"] {{ background-color: #22C55E !important; color: white !important; }}
div[data-testid="stButton"]:has(button[key="home_refresh_btn"]) > button {{ background-color: #22C55E !important; color: white !important; border-radius: 8px !important; padding: 10px !important; font-size: 16px !important; text-align: center !important; }}
.refresh-btn > button {{ background-color: #22C55E !important; color: white !important; padding: 10px !important; border-radius: 8px !important; text-align: center !important; font-size: 16px !important; }}
.refresh-btn > button:hover {{ background-color: #16A34A !important; transform: none !important; }}
.article-title {{ line-height: 1.3; color: #000000 !important; text-align: center; margin-bottom: 10px; font-weight: 800; font-size: 34px; }}
.share-btn {{ display: inline-flex; align-items: center; justify-content: center; padding: 8px 15px; border-radius: 5px; color: white !important; text-decoration: none; font-size: 14px; font-weight: 600; margin-right: 10px; transition: 0.2s; }}
.share-btn:hover {{ opacity: 0.8; transform: translateY(-2px); }}
.fb {{ background-color: #1877F2; }}
.wa {{ background-color: #25D366; }}
.read-time-badge {{ background-color: #E5E0D5; color: #4B5563; padding: 4px 12px; border-radius: 20px; font-size: 14px; font-weight: 600; display: inline-block; margin-bottom: 20px; }}
.content-box {{ background-color: #FFFBF0; padding: 30px; border-radius: 16px; border: 1px solid #E5E0D5; margin-bottom: 20px; max-width: 850px; margin-left: auto; margin-right: auto; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
.tldr-box {{ background-color: #F0FDF4; border-left: 5px solid #22C55E; padding: 15px 20px; border-radius: 0 10px 10px 0; margin-bottom: 25px; }}
.tldr-title {{ color: #166534; font-weight: 700; font-size: 18px; margin-bottom: 5px; display: flex; align-items: center; gap: 5px; }}
.cat-btn button {{ background-color: #E5E0D5 !important; color: #111827 !important; padding: 10px !important; border-radius: 8px !important; text-align: center !important; transition: 0.3s; }}
.cat-btn button:hover {{ background-color: {accent_color} !important; color: white !important; }}
.cat-btn-active button {{ background-color: {accent_color} !important; color: white !important; padding: 10px !important; border-radius: 8px !important; text-align: center !important; }}

/* অনুবাদ স্ট্যাটাস ব্যাজ */
.translate-badge {{ background-color: #EFF6FF; border: 1px solid #BFDBFE; color: #1D4ED8; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; display: inline-block; margin-bottom: 8px; }}
.translate-badge.ai {{ background-color: #F0FDF4; border-color: #BBF7D0; color: #15803D; }}
</style>
""", unsafe_allow_html=True)


# ==========================================
# লোগো
# ==========================================
def show_logo():
    st.markdown("""
    <div style="text-align: center; margin-bottom: 25px;">
        <span style="font-family: 'Arial', sans-serif; font-size: 48px; font-weight: 900; color: #D35400;">হাওয়া</span>
        <span style="font-family: 'Arial', sans-serif; font-size: 48px; font-weight: 300; color: #111827;"> বাংলা</span>
        <br><span style="font-size: 17px; color: #4B5563; font-weight: 600;">আন্তর্জাতিক সংবাদ | AI অনুবাদ</span>
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# ইংরেজি সংখ্যা → বাংলায়
# ==========================================
def eng_to_bn_num(text):
    if text is None: return ""
    bn_digits = {'0': '০', '1': '১', '2': '২', '3': '৩', '4': '৪', '5': '৫', '6': '৬', '7': '৭', '8': '৮', '9': '৯'}
    text = str(text)
    twitter_links = re.findall(r'pic\.twitter\.com/\w+', text)
    for i, link in enumerate(twitter_links):
        text = text.replace(link, f"__TWITTER_{i}__")
    converted = ''.join(bn_digits.get(char, char) for char in text)
    for i, link in enumerate(twitter_links):
        converted = converted.replace(f"__TWITTER_{i}__", link)
    return converted


# ==========================================
# বাংলা তারিখ
# ==========================================
def get_bengali_date(date_str):
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f') if '.' in date_str else datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        months = {1: 'জানুয়ারি', 2: 'ফেব্রুয়ারি', 3: 'মার্চ', 4: 'এপ্রিল', 5: 'মে', 6: 'জুন',
                  7: 'জুলাই', 8: 'আগস্ট', 9: 'সেপ্টেম্বর', 10: 'অক্টোবর', 11: 'নভেম্বর', 12: 'ডিসেম্বর'}
        return f"{eng_to_bn_num(dt.day)} {months[dt.month]}, {eng_to_bn_num(dt.year)}"
    except:
        return eng_to_bn_num(date_str[:10])


# ==========================================
# ডাটাবেস সেটআপ
# ==========================================
@st.cache_resource
def init_db():
    conn = sqlite3.connect('news_hawabangla.db', check_same_thread=False, timeout=30)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news_table
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, link TEXT UNIQUE, translated_title TEXT,
                  full_text TEXT, image_url TEXT, video_url TEXT, source TEXT, category TEXT,
                  date TIMESTAMP, translation_method TEXT DEFAULT 'google')''')
    c.execute('''CREATE TABLE IF NOT EXISTS update_meta (last_update TIMESTAMP)''')
    # নতুন কলাম যোগ করা (পুরনো DB এর জন্য)
    try:
        c.execute("ALTER TABLE news_table ADD COLUMN translation_method TEXT DEFAULT 'google'")
        conn.commit()
    except:
        pass
    conn.commit()
    return conn, c

conn, c = init_db()


# ==========================================
# � বিনামূল্যে প্রাকৃতিক বাংলা অনুবাদ
# ==========================================

def _chunk_text(text, max_chars=4500):
    """
    টেক্সটকে বাক্যের সীমানায় ভেঙে চাংক তৈরি করে।
    এতে অনুবাদ আরও প্রাকৃতিক হয়।
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    current = ""
    # বাক্যের শেষে (., !, ?) ভাঙো
    sentences = re.split(r'(?<=[.!?])\s+', text)
    for sentence in sentences:
        if len(current) + len(sentence) + 1 < max_chars:
            current += sentence + " "
        else:
            if current.strip():
                chunks.append(current.strip())
            # একটি বাক্য নিজেই অনেক বড় হলে শব্দে ভাঙো
            if len(sentence) >= max_chars:
                words = sentence.split()
                sub = ""
                for w in words:
                    if len(sub) + len(w) + 1 < max_chars:
                        sub += w + " "
                    else:
                        if sub.strip():
                            chunks.append(sub.strip())
                        sub = w + " "
                if sub.strip():
                    chunks.append(sub.strip())
                current = ""
            else:
                current = sentence + " "
    if current.strip():
        chunks.append(current.strip())
    return chunks


def google_translate(text, retries=3):
    """
    deep_translator → Google Translate দিয়ে প্রাকৃতিক বাংলা অনুবাদ।
    সম্পূর্ণ বিনামূল্যে। বাক্য-স্তরে অনুবাদ করে, শব্দ-স্তরে নয়।
    """
    if not text or not text.strip():
        return text

    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source='auto', target='bn')
        chunks = _chunk_text(text.strip())
        translated_parts = []

        for chunk in chunks:
            for attempt in range(retries):
                try:
                    result = translator.translate(chunk)
                    translated_parts.append(result if result else chunk)
                    break
                except Exception:
                    if attempt < retries - 1:
                        time.sleep(1.5)
                    else:
                        translated_parts.append(chunk)
            time.sleep(0.4)  # Google rate limit এড়াতে

        return eng_to_bn_num(" ".join(translated_parts))
    except Exception:
        return text


def safe_translate(text, is_title=False):
    """
    মূল অনুবাদ ফাংশন — Google Translate (বিনামূল্যে, প্রাকৃতিক বাংলা)।
    শিরোনাম ও বডি উভয়ের জন্য একই পদ্ধতি, তবে শিরোনামে ছোট ইনপুট।
    """
    if not text or not text.strip():
        return "", "none"
    result = google_translate(text)
    return result, "google"


# ==========================================
# অডিও জেনারেশন
# ==========================================
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


# ==========================================
# নিউজ স্ক্র্যাপিং
# ==========================================
def scrape_news():
    news_feeds = {
        # ── আন্তর্জাতিক ও রাজনীতি ──────────────────────────────────────────
        "Al Jazeera":        {"url": "https://www.aljazeera.com/xml/rss/all.xml",                    "category": "General"},
        "TRT World":         {"url": "https://www.trtworld.com/rss.xml",                             "category": "General"},
        "RT News":           {"url": "https://www.rt.com/rss/",                                      "category": "General"},
        "Reuters World":     {"url": "https://feeds.reuters.com/reuters/worldNews",                  "category": "General"},
        "BBC World":         {"url": "https://feeds.bbci.co.uk/news/world/rss.xml",                  "category": "General"},
        "DW News":           {"url": "https://rss.dw.com/rdf/rss-en-all",                            "category": "General"},
        "France 24":         {"url": "https://www.france24.com/en/rss",                              "category": "General"},
        "The Guardian World":{"url": "https://www.theguardian.com/world/rss",                        "category": "General"},
        "Sky News":          {"url": "https://feeds.skynews.com/feeds/rss/world.xml",                "category": "General"},
        "Euronews":          {"url": "https://www.euronews.com/rss?format=mrss&level=theme&name=news","category": "General"},
        # ── প্রযুক্তি ────────────────────────────────────────────────────────
        "TechCrunch":        {"url": "https://techcrunch.com/feed/",                                 "category": "Technology"},
        "The Verge":         {"url": "https://www.theverge.com/rss/index.xml",                       "category": "Technology"},
        "Ars Technica":      {"url": "http://feeds.arstechnica.com/arstechnica/index",               "category": "Technology"},
        "Space.com":         {"url": "https://www.space.com/feeds/all",                              "category": "Technology"},
        "Wired":             {"url": "https://www.wired.com/feed/rss",                               "category": "Technology"},
        "MIT Tech Review":   {"url": "https://www.technologyreview.com/feed/",                       "category": "Technology"},
        "Engadget":          {"url": "https://www.engadget.com/rss.xml",                             "category": "Technology"},
        "ZDNet":             {"url": "https://www.zdnet.com/news/rss.xml",                           "category": "Technology"},
        # ── বাণিজ্য ──────────────────────────────────────────────────────────
        "Pandaily":          {"url": "https://pandaily.com/feed/",                                   "category": "Business"},
        "TechNode":          {"url": "https://technode.com/feed/",                                   "category": "Business"},
        "Reuters Business":  {"url": "https://feeds.reuters.com/reuters/businessNews",               "category": "Business"},
        "BBC Business":      {"url": "https://feeds.bbci.co.uk/news/business/rss.xml",               "category": "Business"},
        "Forbes":            {"url": "https://www.forbes.com/business/feed/",                        "category": "Business"},
        "CNBC":              {"url": "https://www.cnbc.com/id/100003114/device/rss/rss.html",        "category": "Business"},
    }
    headers = {'User-Agent': 'Mozilla/5.0'}
    new_count = 0

    for source_name, feed_info in news_feeds.items():
        feed_url  = feed_info["url"]
        category  = feed_info["category"]
        try:
            feed = feedparser.parse(feed_url)
        except:
            continue

        for entry in feed.entries[:4]:
            # ইতিমধ্যে ডাটাবেসে থাকলে বাদ
            c.execute("SELECT id FROM news_table WHERE link=?", (entry.link,))
            if c.fetchone():
                continue

            try:
                art_resp = requests.get(entry.link, headers=headers, timeout=10)
                art_soup = BeautifulSoup(art_resp.content, 'html.parser')

                # ছবি
                img_tag = art_soup.find('meta', property='og:image')
                img_url = img_tag['content'] if img_tag else \
                    "https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=800&auto=format&fit=crop"

                # ভিডিও
                video_link = ""
                for iframe in art_soup.find_all('iframe'):
                    src = iframe.get('src', '')
                    if src and any(d in src.lower() for d in ['youtube', 'vimeo', 'dailymotion', 'twitter', 'rt.com']):
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
                    if tweet and tweet.find_all('a'):
                        video_link = tweet.find_all('a')[-1].get('href', '')

                # আর্টিকেলের টেক্সট
                paragraphs = art_soup.find_all('p')
                full_eng_text = "\n\n".join(
                    [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True).split()) > 10]
                )
                if not full_eng_text:
                    continue

                # ===== Google Translate দিয়ে প্রাকৃতিক বাংলা অনুবাদ =====
                bn_title, title_method = safe_translate(entry.title, is_title=True)

                # বডি টেক্সট: প্রথম ১০টি প্যারাগ্রাফ একসাথে অনুবাদ
                para_list = [p.strip() for p in full_eng_text.split('\n\n') if p.strip()][:10]
                combined_eng = "\n\n".join(para_list)
                bn_combined, body_method = safe_translate(combined_eng)
                bn_paras = [p for p in bn_combined.split('\n\n') if p.strip()] if bn_combined else para_list

                bn_full_text = "".join([f"<p>{p.strip()}</p>" for p in bn_paras if p.strip()])

                c.execute(
                    '''INSERT OR IGNORE INTO news_table
                       (title, link, translated_title, full_text, image_url, video_url, source, category, date, translation_method)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (entry.title, entry.link, bn_title, bn_full_text,
                     img_url, video_link, source_name, category,
                     datetime.now(), body_method)
                )
                conn.commit()
                new_count += 1

            except Exception:
                continue

    # আপডেট মেটা সেভ
    try:
        c.execute("DELETE FROM update_meta")
        c.execute("INSERT INTO update_meta (last_update) VALUES (?)", (datetime.now(),))
        conn.commit()
    except:
        pass

    return new_count


def check_for_auto_update():
    try:
        c.execute("SELECT last_update FROM update_meta")
        row = c.fetchone()
        if not row:
            scrape_news()
        else:
            fmt = '%Y-%m-%d %H:%M:%S.%f' if '.' in row[0] else '%Y-%m-%d %H:%M:%S'
            last = datetime.strptime(row[0], fmt)
            if datetime.now() - last > timedelta(hours=3):
                scrape_news()
    except:
        pass


check_for_auto_update()


# ==========================================
# সাইডবার নেভিগেশন
# ==========================================
st.sidebar.markdown("<h2 style='text-align: center; color: #D35400;'>মেনু</h2>", unsafe_allow_html=True)
nav_selection = st.sidebar.radio("নেভিগেশন", ["🏠 হোম পেজ", "🔖 সেভ করা খবর"], label_visibility="collapsed")
st.sidebar.markdown("---")

if st.sidebar.button("🔄 খবর আপডেট করুন"):
    with st.spinner("AI দিয়ে খবর অনুবাদ হচ্ছে... একটু অপেক্ষা করুন"):
        count = scrape_news()
        st.sidebar.success(f"✅ {count}টি নতুন খবর যোগ হয়েছে!")
        st.session_state.view = 'home'
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style='font-size: 12px; color: #6B7280; text-align: center;'>
🌐 <b>Google Translate চালু</b><br>
বিনামূল্যে প্রাকৃতিক বাংলা অনুবাদ<br>
সম্পূর্ণ ফ্রি সার্ভিস
</div>
""", unsafe_allow_html=True)


# ==========================================
# ১. হোম পেইজ
# ==========================================
if st.session_state.view == 'home':
    show_logo()
    items_per_page = 15

    if nav_selection == "🏠 হোম পেজ":

        # ── রিফ্রেশ বাটন (হোম পেজের শীর্ষে) ──────────────────────────────
        refresh_col1, refresh_col2, refresh_col3 = st.columns([2, 1, 2])
        with refresh_col2:
            st.markdown('<div class="refresh-btn">', unsafe_allow_html=True)
            if st.button("🔄 নতুন খবর লোড করুন", use_container_width=True, key="home_refresh_btn"):
                with st.spinner("নতুন খবর আনা হচ্ছে এবং বাংলায় অনুবাদ হচ্ছে..."):
                    count = scrape_news()
                    if count > 0:
                        st.success(f"✅ {count}টি নতুন খবর যোগ হয়েছে!")
                    else:
                        st.info("ℹ️ এই মুহূর্তে কোনো নতুন খবর নেই।")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        st.write("")

        # ক্যাটাগরি বাটন
        cat_cols = st.columns(4)
        cats = [
            ('General',    '🌍 আন্তর্জাতিক ও রাজনীতি', 'cat_pol'),
            ('Technology', '💻 প্রযুক্তি সংবাদ',       'cat_tech'),
            ('Business',   '📈 বাণিজ্য ও মার্কেট',     'cat_bus'),
            ('All',        '📰 সব খবর',                'cat_all'),
        ]
        for col, (cat_key, cat_label, btn_key) in zip(cat_cols, cats):
            with col:
                cls = "cat-btn-active" if st.session_state.category_filter == cat_key else "cat-btn"
                st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
                if st.button(cat_label, key=btn_key, use_container_width=True):
                    st.session_state.category_filter = cat_key
                    st.session_state.page_num = 1
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        st.write("---")

        cat_title_map = {
            'General':    "সর্বশেষ আন্তর্জাতিক ও রাজনীতি সংবাদ",
            'Technology': "সর্বশেষ প্রযুক্তি সংবাদ",
            'Business':   "সর্বশেষ বাণিজ্য ও মার্কেট সংবাদ",
            'All':        "সর্বশেষ সকল সংবাদ",
        }
        st.markdown(f"<h3 style='color:#111827;'>{cat_title_map.get(st.session_state.category_filter, 'সর্বশেষ সংবাদ')}</h3>", unsafe_allow_html=True)

        if st.session_state.category_filter == 'All':
            c.execute("SELECT COUNT(*) FROM news_table")
            total_items = c.fetchone()[0]
            total_pages = max(1, math.ceil(total_items / items_per_page))
            offset = (st.session_state.page_num - 1) * items_per_page
            c.execute("SELECT id, translated_title, image_url, source, date FROM news_table ORDER BY date DESC LIMIT ? OFFSET ?",
                      (items_per_page, offset))
        else:
            c.execute("SELECT COUNT(*) FROM news_table WHERE category=?", (st.session_state.category_filter,))
            total_items = c.fetchone()[0]
            total_pages = max(1, math.ceil(total_items / items_per_page))
            offset = (st.session_state.page_num - 1) * items_per_page
            c.execute("SELECT id, translated_title, image_url, source, date FROM news_table WHERE category=? ORDER BY date DESC LIMIT ? OFFSET ?",
                      (st.session_state.category_filter, items_per_page, offset))

        all_news = c.fetchall()

    else:  # সেভ করা খবর
        if st.session_state.bookmarks:
            st.markdown("<h3 style='color:#111827;'>আপনার সেভ করা খবরগুলো</h3>", unsafe_allow_html=True)
            placeholders = ','.join(['?'] * len(st.session_state.bookmarks))
            c.execute(f"SELECT id, translated_title, image_url, source, date FROM news_table WHERE id IN ({placeholders}) ORDER BY date DESC",
                      st.session_state.bookmarks)
            all_news = c.fetchall()
            total_pages = 1
        else:
            st.info("আপনি এখনও কোনো খবর সেভ করেননি। খবর পড়ার সময় 'সেভ করুন' বাটনে ক্লিক করুন।")
            all_news = []
            total_pages = 1

    if all_news:
        st.write("---")
        for i in range(0, len(all_news), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(all_news):
                    n = all_news[i + j]
                    with cols[j]:
                        st.markdown(f'<div class="news-image-container"><img src="{n[2]}"></div>', unsafe_allow_html=True)
                        bn_date = get_bengali_date(n[4])
                        st.markdown(f"<div class='news-meta'>{n[3]} | {bn_date}</div>", unsafe_allow_html=True)
                        if st.button(n[1], key=f"btn_{n[0]}", use_container_width=True):
                            st.session_state.selected_news_id = n[0]
                            st.session_state.view = 'details'
                            st.rerun()

        if nav_selection == "🏠 হোম পেজ" and total_pages > 1:
            st.write("---")
            p_col1, p_col2, p_col3 = st.columns([1, 2, 1])
            with p_col2:
                btn_col1, txt_col, btn_col2 = st.columns([1, 1, 1])
                with btn_col1:
                    if st.session_state.page_num > 1:
                        if st.button("⬅️ আগের পাতা", use_container_width=True):
                            st.session_state.page_num -= 1
                            st.rerun()
                with txt_col:
                    st.markdown(f"<div style='text-align: center; margin-top: 8px; font-weight: bold; color: #4B5563;'>পৃষ্ঠা {eng_to_bn_num(st.session_state.page_num)} / {eng_to_bn_num(total_pages)}</div>", unsafe_allow_html=True)
                with btn_col2:
                    if st.session_state.page_num < total_pages:
                        if st.button("পরের পাতা ➡️", use_container_width=True):
                            st.session_state.page_num += 1
                            st.rerun()
    else:
        if nav_selection == "🏠 হোম পেজ":
            st.info("এই মুহূর্তে কোনো খবর পাওয়া যাচ্ছে না। সাইডবার থেকে 'খবর আপডেট করুন' বাটনে ক্লিক করুন।")


# ==========================================
# ২. বিস্তারিত পেইজ
# ==========================================
elif st.session_state.view == 'details':
    c.execute(
        "SELECT id, translated_title, image_url, source, date, full_text, link, video_url, category, translation_method FROM news_table WHERE id=?",
        (st.session_state.selected_news_id,)
    )
    news = c.fetchone()
    if not news:
        st.error("সংবাদটি খুঁজে পাওয়া যায়নি।")
        st.session_state.view = 'home'
        st.rerun()

    news_id          = news[0]
    category         = news[8]
    translation_meth = news[9] if len(news) > 9 else "google"

    t1, t2, t3 = st.columns([1, 2, 1])
    with t1:
        st.markdown('<div class="top-home-btn">', unsafe_allow_html=True)
        if st.button("⬅️ হোম পেজ", use_container_width=True):
            st.session_state.view = 'home'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with t3:
        is_saved = news_id in st.session_state.bookmarks
        if st.button("🔖 সেভড (রিমুভ)" if is_saved else "🔖 সেভ করে রাখুন", use_container_width=True):
            if is_saved:
                st.session_state.bookmarks.remove(news_id)
            else:
                st.session_state.bookmarks.append(news_id)
            st.rerun()

    col_a1, col_a2, col_a3 = st.columns([1, 2, 1])
    with col_a2:
        if st.button("🎧 সংবাদটি বাংলায় শুনুন", use_container_width=True):
            with st.spinner("অডিও তৈরি হচ্ছে..."):
                audio = generate_audio(news[5])
                if audio:
                    st.audio(audio)

    encoded_title = urllib.parse.quote(news[1])
    st.markdown(f"""
        <div style="text-align: center; margin: 20px 0;">
            <a class="share-btn fb" href="https://www.facebook.com/sharer/sharer.php?u={news[6]}" target="_blank">Facebook</a>
            <a class="share-btn wa" href="https://api.whatsapp.com/send?text={encoded_title}%20{news[6]}" target="_blank">WhatsApp</a>
        </div>
    """, unsafe_allow_html=True)

    word_count = len(BeautifulSoup(news[5], "html.parser").get_text().split())
    read_time = max(1, word_count // 150)
    bn_read_time = eng_to_bn_num(read_time)
    bn_date_details = get_bengali_date(news[4])

    cat_badge_map = {"General": "আন্তর্জাতিক", "Technology": "প্রযুক্তি", "Business": "বাণিজ্য"}
    cat_badge = cat_badge_map.get(category, "সংবাদ")

    # অনুবাদ পদ্ধতির ব্যাজ
    method_badge = '<span class="translate-badge ai">🌐 Google অনুবাদ</span>'

    st.markdown(f"""
        <div class="content-box">
            <div style="text-align: center;">
                <span style="background-color: {accent_color}; color: white; padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-bottom: 10px; display: inline-block;">{cat_badge}</span>
                &nbsp;{method_badge}
                <h1 class="article-title">{news[1]}</h1>
                <div class="read-time-badge">⏱️ পড়তে সময় লাগবে প্রায় {bn_read_time} মিনিট</div>
                <p style='color: #4B5563; font-weight: 600;'>সোর্স: {news[3]} | {bn_date_details}</p>
                <img src="{news[2]}" style="width: 100%; border-radius: 12px; margin-top: 15px; max-height: 450px; object-fit: cover;">
            </div>
        </div>
    """, unsafe_allow_html=True)

    paragraphs = [p for p in news[5].split('</p>') if p.strip()]

    if paragraphs:
        summary_text = BeautifulSoup(paragraphs[0], "html.parser").get_text()
        st.markdown(f'''
            <div class="content-box" style="padding-top: 10px; padding-bottom: 10px;">
                <div class="tldr-box">
                    <div class="tldr-title">📝 এক নজরে</div>
                    <p style="margin: 0; color: #064E3B; font-size: 17px;">{summary_text}</p>
                </div>
            </div>
        ''', unsafe_allow_html=True)

    # ভিডিও
    video_url = str(news[7]) if news[7] else ""
    valid_vid_domains = ['youtube.com', 'youtu.be', 'vimeo.com', 'twitter.com', 'x.com', 'rt.com', '.mp4']
    if video_url and len(video_url.strip()) > 10 and any(d in video_url.lower() for d in valid_vid_domains):
        st.markdown("<br>", unsafe_allow_html=True)
        if 'twitter.com' in video_url or 'x.com' in video_url:
            tweet_html = f'''<div style="display: flex; justify-content: center; width: 100%;"><blockquote class="twitter-tweet" data-theme="light"><a href="{video_url}"></a></blockquote></div><script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>'''
            components.html(tweet_html, height=600, scrolling=True)
        elif "youtube" in video_url or "vimeo" in video_url or video_url.endswith('.mp4'):
            col_vid1, col_vid2, col_vid3 = st.columns([1, 6, 1])
            with col_vid2: st.video(video_url)
        else:
            col_vid1, col_vid2, col_vid3 = st.columns([1, 6, 1])
            with col_vid2:
                st.markdown(f'<iframe src="{video_url}" width="100%" height="400" frameborder="0" style="border-radius: 12px;"></iframe>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # আর্টিকেলের বডি
    if paragraphs:
        rest_of_news = "</p>".join(paragraphs) + "</p>"
        rest_of_news = re.sub(
            r'(pic\.twitter\.com/\w+)',
            r'<a href="https://\1" target="_blank" style="color:#1DA1F2;">\1 (টুইটটি দেখুন)</a>',
            rest_of_news
        )
        st.markdown(f'''
            <div class="content-box" style="font-size: {st.session_state.font_size}px; line-height: 1.8; text-align: justify;">
                {rest_of_news}
                <hr style="border-top: 2px dashed #E5E0D5; margin-top: 30px;">
                <center><a href="{news[6]}" target="_blank" style="color: #D35400; font-weight: 700; text-decoration: none; font-size: 18px;">🔗 মূল ইংরেজি খবরটি পড়ুন</a></center>
            </div>
        ''', unsafe_allow_html=True)

    st.markdown("<hr style='margin-top: 30px; border-top: 2px solid #E5E0D5;'>", unsafe_allow_html=True)
    bottom_col1, bottom_col2 = st.columns(2)
    with bottom_col1:
        st.markdown('<div class="nav-btn">', unsafe_allow_html=True)
        if st.button("🏠 হোম পেজে ফেরত যান", key="home_btn_bottom", use_container_width=True):
            st.session_state.view = 'home'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with bottom_col2:
        c.execute("SELECT id FROM news_table WHERE id < ? AND category=? ORDER BY id DESC LIMIT 1", (news_id, category))
        next_news = c.fetchone()
        if next_news:
            st.markdown('<div class="nav-btn">', unsafe_allow_html=True)
            if st.button("পরবর্তী সংবাদ পড়ুন ➡️", key="next_btn_bottom", use_container_width=True):
                st.session_state.selected_news_id = next_news[0]
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # সম্পর্কিত খবর
    st.markdown("<h3 style='text-align: center; margin-top: 50px; margin-bottom: 20px; color: #D35400;'>⚡ এই সম্পর্কিত আরও খবর</h3>", unsafe_allow_html=True)
    c.execute("SELECT id, translated_title, image_url, source, date FROM news_table WHERE category=? AND id!=? ORDER BY date DESC LIMIT 3",
              (category, news_id))
    related = c.fetchall()

    if related:
        cols = st.columns(3)
        for j, rel in enumerate(related):
            with cols[j]:
                st.markdown(f'<div style="width:100%; height:180px; overflow:hidden; border-radius:10px; margin-bottom:10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);"><img src="{rel[2]}" style="width:100%; height:100%; object-fit:cover;"></div>', unsafe_allow_html=True)
                if st.button(rel[1][:50] + "...", key=f"rel_{rel[0]}", use_container_width=True):
                    st.session_state.selected_news_id = rel[0]
                    st.rerun()
