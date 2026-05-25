import streamlit as st
import sqlite3
import math
import asyncio
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import edge_tts
import feedparser
import tempfile
import time
import os
import urllib.parse
import re
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
if 'font_size' not in st.session_state:    st.session_state.font_size = 20
if 'view' not in st.session_state:         st.session_state.view = 'home'
if 'page_num' not in st.session_state:     st.session_state.page_num = 1
if 'bookmarks' not in st.session_state:    st.session_state.bookmarks = []
if 'category_filter' not in st.session_state: st.session_state.category_filter = 'General'
if 'dark_mode' not in st.session_state:    st.session_state.dark_mode = False
if 'search_query' not in st.session_state: st.session_state.search_query = ''
if 'search_active' not in st.session_state: st.session_state.search_active = False

# ==========================================
# থিম — ডার্ক / লাইট
# ==========================================
if st.session_state.dark_mode:
    bg_color    = "#0F172A"
    card_bg     = "#1E293B"
    text_color  = "#F1F5F9"
    meta_color  = "#94A3B8"
    border_col  = "#334155"
    input_bg    = "#1E293B"
    accent_color = "#F97316"
else:
    bg_color    = "#FDF6E3"
    card_bg     = "#FFFBF0"
    text_color  = "#111827"
    meta_color  = "#4B5563"
    border_col  = "#E5E0D5"
    input_bg    = "#FFFFFF"
    accent_color = "#D35400"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&display=swap');

html, body, .stApp {{
    font-family: 'Hind Siliguri', sans-serif !important;
    scroll-behavior: smooth;
    background-color: {bg_color} !important;
}}
header[data-testid="stHeader"] {{ display: none !important; }}
.block-container {{ padding-top: 1.5rem !important; padding-bottom: 2rem !important; margin-top: 0 !important; }}
.main {{ color: {text_color} !important; background-color: {bg_color} !important; }}
section[data-testid="stSidebar"] {{ background-color: {card_bg} !important; }}
p {{ color: {text_color} !important; font-family: 'Hind Siliguri', sans-serif !important; }}
h1,h2,h3,h4 {{ color: {text_color} !important; }}

/* ── ticker ── */
.ticker-wrap {{
    width: 100%; background: {accent_color}; padding: 8px 0;
    overflow: hidden; border-radius: 8px; margin-bottom: 18px;
}}
.ticker-label {{
    display: inline-block; background: #111827; color: #fff;
    padding: 2px 14px; font-weight: 700; font-size: 14px;
    border-radius: 4px; margin-left: 12px; margin-right: 10px; vertical-align: middle;
}}
.ticker-content {{
    display: inline-block; white-space: nowrap;
    animation: ticker-scroll 90s linear infinite;
    color: #fff; font-size: 15px; font-weight: 600; vertical-align: middle;
}}
@keyframes ticker-scroll {{
    0%   {{ transform: translateX(60vw); }}
    100% {{ transform: translateX(-100%); }}
}}

/* ── breaking badge ── */
.breaking-badge {{
    background: #EF4444; color: #fff; font-size: 11px; font-weight: 700;
    padding: 2px 8px; border-radius: 4px; margin-right: 6px;
    display: inline-block;
}}

/* ── trending badge ── */
.trending-badge {{
    background: #F59E0B; color: #fff; font-size: 11px; font-weight: 700;
    padding: 2px 8px; border-radius: 4px; margin-right: 6px; display: inline-block;
}}

/* ── cards ── */
.news-image-container {{
    width: 100%; overflow: hidden; border-radius: 10px;
    margin-bottom: 10px; background-color: {border_col}; position: relative;
}}
.news-image-container img {{ width: 100%; height: 200px; display: block; object-fit: cover; }}
.news-meta {{ color: {meta_color} !important; font-size: 13px; margin-top: 4px; font-weight: 600; }}
.view-count {{ color: {meta_color} !important; font-size: 12px; }}

/* ── buttons ── */
.stButton > button, div[data-testid="stButton"] > button {{
    background-color: transparent !important; color: {text_color} !important;
    border: none !important; box-shadow: none !important; outline: none !important;
    font-family: 'Hind Siliguri', sans-serif !important; font-size: 17px !important;
    font-weight: 600 !important; text-align: left !important; line-height: 1.4 !important;
    padding: 0 !important; white-space: normal !important; display: block !important; transition: 0.2s;
}}
.stButton > button:hover {{ color: {accent_color} !important; transform: translateX(3px); }}
.nav-btn > button {{
    background-color: {border_col} !important; padding: 10px !important;
    border-radius: 8px !important; text-align: center !important; transform: none !important;
    color: {text_color} !important;
}}
.nav-btn > button:hover {{ background-color: {accent_color} !important; color: white !important; transform: none !important; }}
.top-home-btn > button {{
    background-color: #111827 !important; color: white !important;
    padding: 5px 15px !important; border-radius: 6px !important;
    font-size: 16px !important; text-align: center !important;
}}
.top-home-btn > button:hover {{ background-color: {accent_color} !important; }}
.refresh-btn > button {{
    background-color: #22C55E !important; color: white !important;
    padding: 10px !important; border-radius: 8px !important;
    text-align: center !important; font-size: 16px !important;
}}
.refresh-btn > button:hover {{ background-color: #16A34A !important; transform: none !important; }}
.cat-btn button {{
    background-color: {border_col} !important; color: {text_color} !important;
    padding: 10px !important; border-radius: 8px !important; text-align: center !important;
}}
.cat-btn button:hover {{ background-color: {accent_color} !important; color: white !important; }}
.cat-btn-active button {{
    background-color: {accent_color} !important; color: white !important;
    padding: 10px !important; border-radius: 8px !important; text-align: center !important;
}}

/* ── article detail ── */
.article-title {{
    line-height: 1.3; color: {text_color} !important; text-align: center;
    margin-bottom: 10px; font-weight: 800; font-size: 32px;
}}
.share-btn {{
    display: inline-flex; align-items: center; justify-content: center;
    padding: 8px 15px; border-radius: 5px; color: white !important;
    text-decoration: none; font-size: 14px; font-weight: 600;
    margin-right: 8px; transition: 0.2s;
}}
.share-btn:hover {{ opacity: 0.8; transform: translateY(-2px); }}
.fb {{ background-color: #1877F2; }}
.wa {{ background-color: #25D366; }}
.tw {{ background-color: #1DA1F2; }}
.cp {{ background-color: #6B7280; }}
.read-time-badge {{
    background-color: {border_col}; color: {meta_color}; padding: 4px 12px;
    border-radius: 20px; font-size: 14px; font-weight: 600; display: inline-block; margin-bottom: 20px;
}}
.content-box {{
    background-color: {card_bg}; padding: 30px; border-radius: 16px;
    border: 1px solid {border_col}; margin-bottom: 20px;
    max-width: 850px; margin-left: auto; margin-right: auto;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.08);
}}
.tldr-box {{
    background-color: {'#0F2A1A' if st.session_state.dark_mode else '#F0FDF4'};
    border-left: 5px solid #22C55E; padding: 15px 20px;
    border-radius: 0 10px 10px 0; margin-bottom: 25px;
}}
.tldr-title {{ color: {'#4ADE80' if st.session_state.dark_mode else '#166534'}; font-weight: 700; font-size: 18px; margin-bottom: 5px; }}
.translate-badge {{
    background-color: {'#1E3A5F' if st.session_state.dark_mode else '#EFF6FF'};
    border: 1px solid {'#3B82F6' if st.session_state.dark_mode else '#BFDBFE'};
    color: {'#93C5FD' if st.session_state.dark_mode else '#1D4ED8'};
    padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 600;
    display: inline-block; margin-bottom: 8px;
}}

/* ── search box ── */
.stTextInput > div > div > input {{
    background-color: {input_bg} !important; color: {text_color} !important;
    border: 2px solid {border_col} !important; border-radius: 10px !important;
    font-family: 'Hind Siliguri', sans-serif !important; font-size: 16px !important;
}}

/* ── font size controls ── */
.font-ctrl > button {{
    background-color: {border_col} !important; color: {text_color} !important;
    padding: 6px 14px !important; border-radius: 6px !important;
    font-size: 18px !important; text-align: center !important;
}}
.font-ctrl > button:hover {{ background-color: {accent_color} !important; color: white !important; }}

/* ── trending sidebar ── */
.trending-item {{
    background-color: {card_bg}; border: 1px solid {border_col};
    border-radius: 10px; padding: 10px 12px; margin-bottom: 8px;
    cursor: pointer; transition: 0.2s;
}}
.trending-item:hover {{ border-color: {accent_color}; }}
</style>
""", unsafe_allow_html=True)


# ==========================================
# লোগো
# ==========================================
def show_logo():
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 18px;">
        <span style="font-size: 46px; font-weight: 900; color: {accent_color};">হাওয়া</span>
        <span style="font-size: 46px; font-weight: 300; color: {text_color};"> বাংলা</span>
        <br><span style="font-size: 16px; color: {meta_color}; font-weight: 600;">আন্তর্জাতিক সংবাদ | AI অনুবাদ</span>
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# ইংরেজি সংখ্যা → বাংলায়
# ==========================================
def eng_to_bn_num(text):
    if text is None: return ""
    bn_digits = {'0':'০','1':'১','2':'২','3':'৩','4':'৪','5':'৫','6':'৬','7':'৭','8':'৮','9':'৯'}
    text = str(text)
    twitter_links = re.findall(r'pic\.twitter\.com/\w+', text)
    for i, link in enumerate(twitter_links):
        text = text.replace(link, f"__TW_{i}__")
    converted = ''.join(bn_digits.get(ch, ch) for ch in text)
    for i, link in enumerate(twitter_links):
        converted = converted.replace(f"__TW_{i}__", link)
    return converted


# ==========================================
# বাংলা তারিখ
# ==========================================
def get_bengali_date(date_str):
    try:
        fmt = '%Y-%m-%d %H:%M:%S.%f' if '.' in str(date_str) else '%Y-%m-%d %H:%M:%S'
        dt = datetime.strptime(str(date_str), fmt)
        months = {1:'জানুয়ারি',2:'ফেব্রুয়ারি',3:'মার্চ',4:'এপ্রিল',5:'মে',6:'জুন',
                  7:'জুলাই',8:'আগস্ট',9:'সেপ্টেম্বর',10:'অক্টোবর',11:'নভেম্বর',12:'ডিসেম্বর'}
        return f"{eng_to_bn_num(dt.day)} {months[dt.month]}, {eng_to_bn_num(dt.year)}"
    except:
        return eng_to_bn_num(str(date_str)[:10])


def is_breaking(date_str):
    """২ ঘণ্টার মধ্যে যোগ হলে ব্রেকিং"""
    try:
        s = str(date_str).strip()
        if not s or s == 'None':
            return False
        fmt = '%Y-%m-%d %H:%M:%S.%f' if '.' in s else '%Y-%m-%d %H:%M:%S'
        dt = datetime.strptime(s, fmt)
        diff = datetime.now() - dt
        # শুধুমাত্র ০ থেকে ২ ঘণ্টার মধ্যে হলে ব্রেকিং
        return timedelta(0) <= diff <= timedelta(hours=2)
    except:
        return False


# ==========================================
# ডাটাবেস সেটআপ
# ==========================================
@st.cache_resource
def init_db():
    conn = sqlite3.connect('news_hawabangla.db', check_same_thread=False, timeout=30)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news_table
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT, link TEXT UNIQUE, translated_title TEXT,
                  full_text TEXT, image_url TEXT, video_url TEXT,
                  source TEXT, category TEXT, date TIMESTAMP,
                  translation_method TEXT DEFAULT 'google',
                  view_count INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS update_meta (last_update TIMESTAMP)''')
    # পুরনো DB-তে নতুন কলাম যোগ
    for col_sql in [
        "ALTER TABLE news_table ADD COLUMN translation_method TEXT DEFAULT 'google'",
        "ALTER TABLE news_table ADD COLUMN view_count INTEGER DEFAULT 0",
    ]:
        try:
            c.execute(col_sql)
            conn.commit()
        except:
            pass
    conn.commit()
    return conn, c

conn, c = init_db()


def increment_view(news_id):
    try:
        c.execute("UPDATE news_table SET view_count = view_count + 1 WHERE id=?", (news_id,))
        conn.commit()
    except:
        pass


# ==========================================
# অনুবাদ
# ==========================================
def _chunk_text(text, max_chars=4500):
    if len(text) <= max_chars:
        return [text]
    chunks, current = [], ""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    for sentence in sentences:
        if len(current) + len(sentence) + 1 < max_chars:
            current += sentence + " "
        else:
            if current.strip(): chunks.append(current.strip())
            if len(sentence) >= max_chars:
                words, sub = sentence.split(), ""
                for w in words:
                    if len(sub) + len(w) + 1 < max_chars: sub += w + " "
                    else:
                        if sub.strip(): chunks.append(sub.strip())
                        sub = w + " "
                if sub.strip(): chunks.append(sub.strip())
                current = ""
            else:
                current = sentence + " "
    if current.strip(): chunks.append(current.strip())
    return chunks


def google_translate(text, retries=3):
    if not text or not text.strip(): return text
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source='auto', target='bn')
        chunks = _chunk_text(text.strip())
        parts = []
        for chunk in chunks:
            for attempt in range(retries):
                try:
                    result = translator.translate(chunk)
                    parts.append(result if result else chunk)
                    break
                except Exception:
                    if attempt < retries - 1: time.sleep(1.5)
                    else: parts.append(chunk)
            time.sleep(0.4)
        return eng_to_bn_num(" ".join(parts))
    except Exception:
        return text


def safe_translate(text, is_title=False):
    if not text or not text.strip(): return "", "none"
    return google_translate(text), "google"


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
        # আন্তর্জাতিক
        "Al Jazeera":         {"url": "https://www.aljazeera.com/xml/rss/all.xml",                     "category": "General"},
        "TRT World":          {"url": "https://www.trtworld.com/rss.xml",                              "category": "General"},
        "RT News":            {"url": "https://www.rt.com/rss/",                                       "category": "General"},
        "Reuters World":      {"url": "https://feeds.reuters.com/reuters/worldNews",                   "category": "General"},
        "BBC World":          {"url": "https://feeds.bbci.co.uk/news/world/rss.xml",                   "category": "General"},
        "DW News":            {"url": "https://rss.dw.com/rdf/rss-en-all",                             "category": "General"},
        "France 24":          {"url": "https://www.france24.com/en/rss",                               "category": "General"},
        "The Guardian World": {"url": "https://www.theguardian.com/world/rss",                         "category": "General"},
        "Sky News":           {"url": "https://feeds.skynews.com/feeds/rss/world.xml",                 "category": "General"},
        "Euronews":           {"url": "https://www.euronews.com/rss?format=mrss&level=theme&name=news","category": "General"},
        # প্রযুক্তি
        "TechCrunch":         {"url": "https://techcrunch.com/feed/",                                  "category": "Technology"},
        "The Verge":          {"url": "https://www.theverge.com/rss/index.xml",                        "category": "Technology"},
        "Ars Technica":       {"url": "http://feeds.arstechnica.com/arstechnica/index",                "category": "Technology"},
        "Space.com":          {"url": "https://www.space.com/feeds/all",                               "category": "Technology"},
        "Wired":              {"url": "https://www.wired.com/feed/rss",                                "category": "Technology"},
        "MIT Tech Review":    {"url": "https://www.technologyreview.com/feed/",                        "category": "Technology"},
        "Engadget":           {"url": "https://www.engadget.com/rss.xml",                              "category": "Technology"},
        "ZDNet":              {"url": "https://www.zdnet.com/news/rss.xml",                            "category": "Technology"},
        # বাণিজ্য
        "Reuters Business":   {"url": "https://feeds.reuters.com/reuters/businessNews",                "category": "Business"},
        "BBC Business":       {"url": "https://feeds.bbci.co.uk/news/business/rss.xml",                "category": "Business"},
        "Forbes":             {"url": "https://www.forbes.com/business/feed/",                         "category": "Business"},
        "CNBC":               {"url": "https://www.cnbc.com/id/100003114/device/rss/rss.html",         "category": "Business"},
        # বিজ্ঞান
        "NASA":               {"url": "https://www.nasa.gov/rss/dyn/breaking_news.rss",                "category": "Science"},
        "New Scientist":      {"url": "https://www.newscientist.com/feed/home/",                       "category": "Science"},
        "Science Daily":      {"url": "https://www.sciencedaily.com/rss/all.xml",                      "category": "Science"},
        # খেলাধুলা
        "BBC Sport":          {"url": "https://feeds.bbci.co.uk/sport/rss.xml",                        "category": "Sports"},
        "ESPN":               {"url": "https://www.espn.com/espn/rss/news",                            "category": "Sports"},
        "Sky Sports":         {"url": "https://www.skysports.com/rss/12040",                           "category": "Sports"},
    }
    headers = {'User-Agent': 'Mozilla/5.0'}
    new_count = 0

    for source_name, feed_info in news_feeds.items():
        try:
            feed = feedparser.parse(feed_info["url"])
        except:
            continue
        for entry in feed.entries[:4]:
            c.execute("SELECT id FROM news_table WHERE link=?", (entry.link,))
            if c.fetchone():
                continue
            try:
                art_resp = requests.get(entry.link, headers=headers, timeout=10)
                art_soup = BeautifulSoup(art_resp.content, 'html.parser')
                img_tag  = art_soup.find('meta', property='og:image')
                img_url  = img_tag['content'] if img_tag else \
                    "https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=800&auto=format&fit=crop"
                video_link = ""
                for iframe in art_soup.find_all('iframe'):
                    src = iframe.get('src', '')
                    if src and any(d in src.lower() for d in ['youtube','vimeo','dailymotion','twitter','rt.com']):
                        if src.startswith('//'): src = 'https:' + src
                        video_link = src; break
                if not video_link:
                    vid_tag = art_soup.find('video')
                    if vid_tag:
                        src = vid_tag.get('src') or (vid_tag.find('source').get('src') if vid_tag.find('source') else None)
                        if src: video_link = src
                paragraphs   = art_soup.find_all('p')
                full_eng_text = "\n\n".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True).split()) > 10])
                if not full_eng_text: continue
                bn_title, _ = safe_translate(entry.title, is_title=True)
                para_list   = [p.strip() for p in full_eng_text.split('\n\n') if p.strip()][:10]
                bn_combined, body_method = safe_translate("\n\n".join(para_list))
                bn_paras    = [p for p in bn_combined.split('\n\n') if p.strip()] if bn_combined else para_list
                bn_full_text = "".join([f"<p>{p.strip()}</p>" for p in bn_paras if p.strip()])
                c.execute(
                    '''INSERT OR IGNORE INTO news_table
                       (title,link,translated_title,full_text,image_url,video_url,source,category,date,translation_method,view_count)
                       VALUES (?,?,?,?,?,?,?,?,?,?,0)''',
                    (entry.title, entry.link, bn_title, bn_full_text,
                     img_url, video_link, source_name, feed_info["category"],
                     datetime.now(), body_method)
                )
                conn.commit()
                new_count += 1
            except Exception:
                continue

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
            fmt  = '%Y-%m-%d %H:%M:%S.%f' if '.' in row[0] else '%Y-%m-%d %H:%M:%S'
            last = datetime.strptime(row[0], fmt)
            if datetime.now() - last > timedelta(hours=3):
                scrape_news()
    except:
        pass

check_for_auto_update()


# ==========================================
# হেডলাইন টিকার
# ==========================================
def show_ticker():
    try:
        c.execute("SELECT translated_title FROM news_table ORDER BY date DESC LIMIT 10")
        rows = c.fetchall()
        if not rows: return
        headlines = "  ◆  ".join([r[0] for r in rows if r[0]])
        st.markdown(f"""
        <div class="ticker-wrap">
            <span class="ticker-label">🔴 সর্বশেষ</span>
            <span class="ticker-content">{headlines}</span>
        </div>
        """, unsafe_allow_html=True)
    except:
        pass


# ==========================================
# সাইডবার
# ==========================================
st.sidebar.markdown(f"<h2 style='text-align:center;color:{accent_color};'>মেনু</h2>", unsafe_allow_html=True)

# ডার্ক মোড টগল
dm_label = "☀️ লাইট মোড" if st.session_state.dark_mode else "🌙 ডার্ক মোড"
if st.sidebar.button(dm_label, use_container_width=True, key="dark_toggle"):
    st.session_state.dark_mode = not st.session_state.dark_mode
    st.rerun()

st.sidebar.markdown("---")
nav_selection = st.sidebar.radio("নেভিগেশন",
    ["🏠 হোম পেজ", "🔍 খবর খুঁজুন", "🔥 ট্রেন্ডিং", "🔖 সেভ করা খবর"],
    label_visibility="collapsed")
st.sidebar.markdown("---")

# ফন্ট সাইজ কন্ট্রোল
st.sidebar.markdown(f"<div style='color:{meta_color};font-size:13px;font-weight:600;margin-bottom:6px;'>🔤 লেখার আকার</div>", unsafe_allow_html=True)
fs_col1, fs_col2, fs_col3 = st.sidebar.columns([1, 1, 1])
with fs_col1:
    st.markdown('<div class="font-ctrl">', unsafe_allow_html=True)
    if st.button("A−", key="fs_down"):
        st.session_state.font_size = max(14, st.session_state.font_size - 2)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with fs_col2:
    st.sidebar.markdown(f"<div style='text-align:center;font-weight:700;padding-top:6px;color:{text_color};'>{st.session_state.font_size}px</div>", unsafe_allow_html=True)
with fs_col3:
    st.markdown('<div class="font-ctrl">', unsafe_allow_html=True)
    if st.button("A+", key="fs_up"):
        st.session_state.font_size = min(32, st.session_state.font_size + 2)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 খবর আপডেট করুন", use_container_width=True):
    with st.spinner("AI দিয়ে খবর অনুবাদ হচ্ছে..."):
        count = scrape_news()
        st.sidebar.success(f"✅ {count}টি নতুন খবর যোগ হয়েছে!")
        st.session_state.view = 'home'
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<div style='font-size:12px;color:{meta_color};text-align:center;'>
🌐 <b>Google Translate চালু</b><br>বিনামূল্যে প্রাকৃতিক বাংলা অনুবাদ
</div>""", unsafe_allow_html=True)


# ==========================================
# ক্যাটাগরি বাটন হেলপার
# ==========================================
def show_category_buttons():
    cats = [
        ('General',    '🌍 আন্তর্জাতিক', 'cat_pol'),
        ('Technology', '💻 প্রযুক্তি',   'cat_tech'),
        ('Business',   '📈 বাণিজ্য',     'cat_bus'),
        ('Science',    '🔬 বিজ্ঞান',     'cat_sci'),
        ('Sports',     '⚽ খেলাধুলা',    'cat_spo'),
        ('All',        '📰 সব খবর',      'cat_all'),
    ]
    cols = st.columns(len(cats))
    for col, (cat_key, cat_label, btn_key) in zip(cols, cats):
        with col:
            cls = "cat-btn-active" if st.session_state.category_filter == cat_key else "cat-btn"
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(cat_label, key=btn_key, use_container_width=True):
                st.session_state.category_filter = cat_key
                st.session_state.page_num = 1
                st.session_state.search_active = False
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


# ==========================================
# নিউজ কার্ড গ্রিড
# ==========================================
def show_news_grid(news_list):
    for i in range(0, len(news_list), 3):
        cols = st.columns(3)
        for j in range(3):
            if i + j < len(news_list):
                n = news_list[i + j]
                # n = (id, translated_title, image_url, source, date, view_count)
                with cols[j]:
                    breaking = is_breaking(n[4])
                    badge_html = '<span class="breaking-badge">🔴 ব্রেকিং</span>' if breaking else ''
                    views = eng_to_bn_num(n[5] if n[5] else 0)
                    st.markdown(
                        f'<div class="news-image-container"><img src="{n[2]}" loading="lazy"></div>'
                        f'<div class="news-meta">{badge_html}{n[3]} | {get_bengali_date(n[4])}</div>'
                        f'<div class="view-count">👁️ {views} বার পড়া হয়েছে</div>',
                        unsafe_allow_html=True
                    )
                    if st.button(n[1], key=f"btn_{n[0]}_{i}_{j}", use_container_width=True):
                        st.session_state.selected_news_id = n[0]
                        st.session_state.view = 'details'
                        increment_view(n[0])
                        st.rerun()


# ==========================================
# ১–৪. নেভিগেশন পেইজ (details view-এ দেখাবে না)
# ==========================================
items_per_page = 15

if st.session_state.view != 'details':

    # ── হোম পেইজ ──────────────────────────────────────────────────────────
    if nav_selection == "🏠 হোম পেজ":
        st.session_state.search_active = False
        show_logo()
        show_ticker()

        rc1, rc2, rc3 = st.columns([2, 1, 2])
        with rc2:
            st.markdown('<div class="refresh-btn">', unsafe_allow_html=True)
            if st.button("🔄 নতুন খবর লোড করুন", use_container_width=True, key="home_refresh_btn"):
                with st.spinner("নতুন খবর আনা হচ্ছে..."):
                    count = scrape_news()
                    st.success(f"✅ {count}টি নতুন খবর যোগ হয়েছে!" if count > 0 else "ℹ️ কোনো নতুন খবর নেই।")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        st.write("")

        show_category_buttons()
        st.write("---")

        cat_title_map = {
            'General':    "সর্বশেষ আন্তর্জাতিক ও রাজনীতি সংবাদ",
            'Technology': "সর্বশেষ প্রযুক্তি সংবাদ",
            'Business':   "সর্বশেষ বাণিজ্য ও মার্কেট সংবাদ",
            'Science':    "সর্বশেষ বিজ্ঞান সংবাদ",
            'Sports':     "সর্বশেষ খেলাধুলার সংবাদ",
            'All':        "সর্বশেষ সকল সংবাদ",
        }
        st.markdown(f"<h3 style='color:{text_color};'>{cat_title_map.get(st.session_state.category_filter,'সর্বশেষ সংবাদ')}</h3>", unsafe_allow_html=True)

        if st.session_state.category_filter == 'All':
            c.execute("SELECT COUNT(*) FROM news_table")
            total_items = c.fetchone()[0]
            total_pages = max(1, math.ceil(total_items / items_per_page))
            offset = (st.session_state.page_num - 1) * items_per_page
            c.execute("SELECT id,translated_title,image_url,source,date,view_count FROM news_table ORDER BY date DESC LIMIT ? OFFSET ?",
                      (items_per_page, offset))
        else:
            c.execute("SELECT COUNT(*) FROM news_table WHERE category=?", (st.session_state.category_filter,))
            total_items = c.fetchone()[0]
            total_pages = max(1, math.ceil(total_items / items_per_page))
            offset = (st.session_state.page_num - 1) * items_per_page
            c.execute("SELECT id,translated_title,image_url,source,date,view_count FROM news_table WHERE category=? ORDER BY date DESC LIMIT ? OFFSET ?",
                      (st.session_state.category_filter, items_per_page, offset))
        all_news = c.fetchall()

        if all_news:
            show_news_grid(all_news)
            if total_pages > 1:
                st.write("---")
                pc1, pc2, pc3 = st.columns([1, 2, 1])
                with pc2:
                    bc1, tc, bc2 = st.columns([1, 1, 1])
                    with bc1:
                        if st.session_state.page_num > 1:
                            if st.button("⬅️ আগের পাতা", use_container_width=True):
                                st.session_state.page_num -= 1; st.rerun()
                    with tc:
                        st.markdown(f"<div style='text-align:center;margin-top:8px;font-weight:bold;color:{meta_color};'>পৃষ্ঠা {eng_to_bn_num(st.session_state.page_num)} / {eng_to_bn_num(total_pages)}</div>", unsafe_allow_html=True)
                    with bc2:
                        if st.session_state.page_num < total_pages:
                            if st.button("পরের পাতা ➡️", use_container_width=True):
                                st.session_state.page_num += 1; st.rerun()
        else:
            st.info("এই মুহূর্তে কোনো খবর নেই। সাইডবার থেকে 'খবর আপডেট করুন' বাটনে ক্লিক করুন।")

    # ── সার্চ পেইজ ────────────────────────────────────────────────────────
    elif nav_selection == "🔍 খবর খুঁজুন":
        show_logo()
        st.markdown(f"<h3 style='color:{text_color};text-align:center;'>🔍 খবর খুঁজুন</h3>", unsafe_allow_html=True)

        search_input = st.text_input("বাংলা বা ইংরেজিতে কীওয়ার্ড লিখুন...",
                                      value=st.session_state.search_query,
                                      placeholder="যেমন: ফিলিস্তিন, AI, cricket...",
                                      key="search_box", label_visibility="collapsed")
        sc1, sc2, sc3 = st.columns([2, 1, 2])
        with sc2:
            st.markdown('<div class="refresh-btn">', unsafe_allow_html=True)
            search_clicked = st.button("🔍 খুঁজুন", use_container_width=True, key="search_btn")
            st.markdown('</div>', unsafe_allow_html=True)

        if search_clicked and search_input.strip():
            st.session_state.search_query  = search_input.strip()
            st.session_state.search_active = True

        if st.session_state.search_active and st.session_state.search_query:
            q = f"%{st.session_state.search_query}%"
            c.execute("""SELECT id,translated_title,image_url,source,date,view_count
                         FROM news_table
                         WHERE translated_title LIKE ? OR title LIKE ?
                         ORDER BY date DESC LIMIT 30""", (q, q))
            results = c.fetchall()
            st.markdown(f"<p style='color:{meta_color};'>'{st.session_state.search_query}' — {eng_to_bn_num(len(results))}টি ফলাফল পাওয়া গেছে</p>", unsafe_allow_html=True)
            if results:
                show_news_grid(results)
            else:
                st.warning("কোনো ফলাফল পাওয়া যায়নি। অন্য কীওয়ার্ড দিয়ে চেষ্টা করুন।")

    # ── ট্রেন্ডিং পেইজ ───────────────────────────────────────────────────
    elif nav_selection == "🔥 ট্রেন্ডিং":
        show_logo()
        st.markdown(f"<h3 style='color:{accent_color};text-align:center;'>🔥 সবচেয়ে বেশি পড়া খবর</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center;color:{meta_color};'>পাঠকদের পছন্দের শীর্ষ সংবাদ</p>", unsafe_allow_html=True)
        st.write("---")

        c.execute("""SELECT id,translated_title,image_url,source,date,view_count
                     FROM news_table ORDER BY view_count DESC, date DESC LIMIT 15""")
        trending = c.fetchall()

        if trending:
            for rank, n in enumerate(trending, 1):
                tc1, tc2 = st.columns([1, 5])
                with tc1:
                    st.markdown(f"""
                    <div style='text-align:center;background:{accent_color};color:white;
                         border-radius:50%;width:48px;height:48px;line-height:48px;
                         font-size:22px;font-weight:900;margin:auto;'>
                         {eng_to_bn_num(rank)}
                    </div>""", unsafe_allow_html=True)
                with tc2:
                    views = eng_to_bn_num(n[5] if n[5] else 0)
                    st.markdown(f'<span class="trending-badge">🔥 {views} ভিউ</span>', unsafe_allow_html=True)
                    if st.button(n[1], key=f"trend_{n[0]}", use_container_width=True):
                        st.session_state.selected_news_id = n[0]
                        st.session_state.view = 'details'
                        increment_view(n[0])
                        st.rerun()
                    st.markdown(f"<div class='news-meta'>{n[3]} | {get_bengali_date(n[4])}</div>", unsafe_allow_html=True)
                st.write("---")
        else:
            st.info("এখনো কোনো ট্রেন্ডিং ডেটা নেই। কিছু খবর পড়লে এখানে দেখা যাবে।")

    # ── সেভ করা খবর ──────────────────────────────────────────────────────
    elif nav_selection == "🔖 সেভ করা খবর":
        show_logo()
        st.markdown(f"<h3 style='color:{text_color};'>🔖 আপনার সেভ করা খবরগুলো</h3>", unsafe_allow_html=True)
        if st.session_state.bookmarks:
            placeholders = ','.join(['?'] * len(st.session_state.bookmarks))
            c.execute(f"SELECT id,translated_title,image_url,source,date,view_count FROM news_table WHERE id IN ({placeholders}) ORDER BY date DESC",
                      st.session_state.bookmarks)
            saved_news = c.fetchall()
            show_news_grid(saved_news)
        else:
            st.info("আপনি এখনও কোনো খবর সেভ করেননি। খবর পড়ার সময় 'সেভ করুন' বাটনে ক্লিক করুন।")


# ==========================================
# ৫. বিস্তারিত পেইজ (যেকোনো ভিউ থেকে)
# ==========================================
if st.session_state.view == 'details':
    c.execute(
        "SELECT id,translated_title,image_url,source,date,full_text,link,video_url,category,translation_method,view_count FROM news_table WHERE id=?",
        (st.session_state.selected_news_id,)
    )
    news = c.fetchone()
    if not news:
        st.error("সংবাদটি খুঁজে পাওয়া যায়নি।")
        st.session_state.view = 'home'
        st.rerun()

    news_id   = news[0]
    category  = news[8]
    views     = eng_to_bn_num(news[10] if news[10] else 0)

    # ── শীর্ষ নেভিগেশন ──
    t1, t2, t3 = st.columns([1, 2, 1])
    with t1:
        st.markdown('<div class="top-home-btn">', unsafe_allow_html=True)
        if st.button("⬅️ হোম পেজ", use_container_width=True, key="back_home"):
            st.session_state.view = 'home'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with t3:
        is_saved = news_id in st.session_state.bookmarks
        if st.button("🔖 সেভড (রিমুভ)" if is_saved else "🔖 সেভ করে রাখুন",
                     use_container_width=True, key="save_btn"):
            if is_saved: st.session_state.bookmarks.remove(news_id)
            else:        st.session_state.bookmarks.append(news_id)
            st.rerun()

    # ── অডিও বাটন ──
    ac1, ac2, ac3 = st.columns([1, 2, 1])
    with ac2:
        if st.button("🎧 সংবাদটি বাংলায় শুনুন", use_container_width=True, key="audio_btn"):
            with st.spinner("অডিও তৈরি হচ্ছে..."):
                audio = generate_audio(news[5])
                if audio: st.audio(audio)
                else:     st.warning("অডিও তৈরি করা সম্ভব হয়নি।")

    # ── শেয়ার বাটন ──
    encoded_title = urllib.parse.quote(news[1])
    encoded_url   = urllib.parse.quote(news[6])
    copy_js = f"navigator.clipboard.writeText('{news[6]}')"
    st.markdown(f"""
    <div style="text-align:center;margin:18px 0;">
        <a class="share-btn fb" href="https://www.facebook.com/sharer/sharer.php?u={news[6]}" target="_blank">📘 Facebook</a>
        <a class="share-btn wa" href="https://api.whatsapp.com/send?text={encoded_title}%20{news[6]}" target="_blank">💬 WhatsApp</a>
        <a class="share-btn tw" href="https://twitter.com/intent/tweet?text={encoded_title}&url={encoded_url}" target="_blank">🐦 Twitter</a>
        <a class="share-btn cp" href="javascript:void(0)" onclick="{copy_js};alert('লিংক কপি হয়েছে!')">🔗 লিংক কপি</a>
    </div>
    """, unsafe_allow_html=True)

    # ── আর্টিকেল হেডার ──
    word_count   = len(BeautifulSoup(news[5], "html.parser").get_text().split())
    read_time    = max(1, word_count // 150)
    bn_read_time = eng_to_bn_num(read_time)
    bn_date      = get_bengali_date(news[4])
    breaking     = is_breaking(news[4])
    breaking_html = '<span class="breaking-badge">🔴 ব্রেকিং নিউজ</span>' if breaking else ''

    cat_badge_map = {
        "General":    "🌍 আন্তর্জাতিক",
        "Technology": "💻 প্রযুক্তি",
        "Business":   "📈 বাণিজ্য",
        "Science":    "🔬 বিজ্ঞান",
        "Sports":     "⚽ খেলাধুলা",
    }
    cat_badge = cat_badge_map.get(category, "📰 সংবাদ")

    st.markdown(f"""
    <div class="content-box">
        <div style="text-align:center;">
            {breaking_html}
            <span style="background:{accent_color};color:white;padding:3px 10px;border-radius:4px;font-size:12px;font-weight:bold;display:inline-block;margin-bottom:10px;">{cat_badge}</span>
            &nbsp;<span class="translate-badge">🌐 Google অনুবাদ</span>
            <h1 class="article-title">{news[1]}</h1>
            <div class="read-time-badge">⏱️ পড়তে সময় লাগবে প্রায় {bn_read_time} মিনিট &nbsp;|&nbsp; 👁️ {views} বার পড়া হয়েছে</div>
            <p style='color:{meta_color};font-weight:600;'>সোর্স: {news[3]} | {bn_date}</p>
            <img src="{news[2]}" style="width:100%;border-radius:12px;margin-top:15px;max-height:450px;object-fit:cover;">
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── TL;DR ──
    paragraphs = [p for p in news[5].split('</p>') if p.strip()]
    if paragraphs:
        summary_text = BeautifulSoup(paragraphs[0], "html.parser").get_text()
        st.markdown(f'''
        <div class="content-box" style="padding-top:10px;padding-bottom:10px;">
            <div class="tldr-box">
                <div class="tldr-title">📝 এক নজরে</div>
                <p style="margin:0;font-size:17px;">{summary_text}</p>
            </div>
        </div>''', unsafe_allow_html=True)

    # ── ভিডিও ──
    video_url = str(news[7]) if news[7] else ""
    valid_domains = ['youtube.com','youtu.be','vimeo.com','twitter.com','x.com','rt.com','.mp4']
    if video_url and len(video_url.strip()) > 10 and any(d in video_url.lower() for d in valid_domains):
        if 'twitter.com' in video_url or 'x.com' in video_url:
            tweet_html = f'<div style="display:flex;justify-content:center;"><blockquote class="twitter-tweet"><a href="{video_url}"></a></blockquote></div><script async src="https://platform.twitter.com/widgets.js"></script>'
            components.html(tweet_html, height=600, scrolling=True)
        else:
            vc1, vc2, vc3 = st.columns([1, 6, 1])
            with vc2: st.video(video_url)

    # ── বডি টেক্সট ──
    if paragraphs:
        body_html = "</p>".join(paragraphs) + "</p>"
        body_html = re.sub(
            r'(pic\.twitter\.com/\w+)',
            r'<a href="https://\1" target="_blank" style="color:#1DA1F2;">\1</a>',
            body_html
        )
        st.markdown(f'''
        <div class="content-box" style="font-size:{st.session_state.font_size}px;line-height:1.9;text-align:justify;">
            {body_html}
            <hr style="border-top:2px dashed {border_col};margin-top:30px;">
            <center><a href="{news[6]}" target="_blank" style="color:{accent_color};font-weight:700;text-decoration:none;font-size:18px;">🔗 মূল ইংরেজি খবরটি পড়ুন</a></center>
        </div>''', unsafe_allow_html=True)

    # ── নিচের নেভিগেশন ──
    st.markdown("<hr style='margin-top:30px;'>", unsafe_allow_html=True)
    bc1, bc2 = st.columns(2)
    with bc1:
        st.markdown('<div class="nav-btn">', unsafe_allow_html=True)
        if st.button("🏠 হোম পেজে ফেরত যান", key="home_btn_bottom", use_container_width=True):
            st.session_state.view = 'home'; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with bc2:
        c.execute("SELECT id FROM news_table WHERE id < ? AND category=? ORDER BY id DESC LIMIT 1", (news_id, category))
        next_news = c.fetchone()
        if next_news:
            st.markdown('<div class="nav-btn">', unsafe_allow_html=True)
            if st.button("পরবর্তী সংবাদ পড়ুন ➡️", key="next_btn_bottom", use_container_width=True):
                st.session_state.selected_news_id = next_news[0]
                increment_view(next_news[0])
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # ── সম্পর্কিত খবর ──
    st.markdown(f"<h3 style='text-align:center;margin-top:50px;margin-bottom:20px;color:{accent_color};'>⚡ এই সম্পর্কিত আরও খবর</h3>", unsafe_allow_html=True)
    c.execute("SELECT id,translated_title,image_url,source,date,view_count FROM news_table WHERE category=? AND id!=? ORDER BY date DESC LIMIT 3",
              (category, news_id))
    related = c.fetchall()
    if related:
        rc = st.columns(3)
        for j, rel in enumerate(related):
            with rc[j]:
                st.markdown(f'<div style="width:100%;height:160px;overflow:hidden;border-radius:10px;margin-bottom:8px;"><img src="{rel[2]}" style="width:100%;height:100%;object-fit:cover;"></div>', unsafe_allow_html=True)
                if st.button(rel[1][:55] + "…", key=f"rel_{rel[0]}", use_container_width=True):
                    st.session_state.selected_news_id = rel[0]
                    increment_view(rel[0])
                    st.rerun()
