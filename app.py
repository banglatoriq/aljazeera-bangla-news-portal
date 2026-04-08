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
# থিম এবং ফন্ট সেটআপ (বইয়ের পাতার রঙ)
# ==========================================
bg_color = "#FDF6E3"       
text_color = "#111827"     # একদম গাঢ় কালো (পড়তে সুবিধা হবে)
card_bg = "#FFFBF0"        
meta_color = "#4B5563"     # গাঢ় ছাই রঙ
accent_color = "#D35400"   

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&display=swap');
html, body, h1, h2, h3, h4, h5, h6, p, button, a {{ font-family: 'Hind Siliguri', sans-serif !important; color: {text_color} !important; }}
.stApp {{ background-color: {bg_color}; }}
.news-card {{ background-color: {card_bg}; border-radius: 12px; overflow: hidden; height: 180px; margin-bottom: 12px; border: 1px solid #E5E0D5; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
.news-meta {{ color: {meta_color} !important; font-size: 13.5px; margin-top: 5px; margin-bottom: 10px; font-weight: 600; }}
.category-badge {{ color: {accent_color} !important; font-weight: 800; text-transform: uppercase; }}
</style>
""", unsafe_allow_html=True)

def show_logo():
    st.markdown("""
    <div style="text-align: center; margin-bottom: 40px; padding-top: 20px;">
        <span style="font-family: 'Arial', sans-serif; font-size: 48px; font-weight: 900; color: #D35400; letter-spacing: -1px;">আলজাজিরা</span>
        <span style="font-family: 'Arial', sans-serif; font-size: 48px; font-weight: 300; color: #111827;"> বাংলা</span>
        <br><span style="font-size: 17px; color: #4B5563; font-weight: 600; letter-spacing: 1px;">এবং অন্যান্য আন্তর্জাতিক সংবাদ</span>
    </div>
    """, unsafe_allow_html=True)

# --- ডাটাবেস সেটআপ ---
@st.cache_resource
def init_db():
    conn = sqlite3.connect('news_db_multi.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news_table
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, link TEXT, translated_title TEXT, 
                  full_text TEXT, image_url TEXT, category TEXT, source TEXT, date TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS update_meta (last_update TIMESTAMP)''')
    conn.commit()
    return conn, c

conn, c = init_db()

# --- অনুবাদ ফাংশন ---
def safe_translate(text):
    if not text: return ""
    try:
        translator = GoogleTranslator(source='en', target='bn')
        if len(text) > 3000:
            chunks = text.split('. ')
            translated_chunks = []
            for chunk in chunks:
                if chunk.strip():
                    try:
                        translated_chunks.append(translator.translate(chunk.strip()))
                    except:
                        translated_chunks.append(chunk) 
            return "। ".join(translated_chunks)
        else:
            return translator.translate(text)
    except:
        return text 

# --- ন্যাচারাল অডিও জেনারেটর (Edge TTS) ---
def generate_audio(text):
    clean_text = BeautifulSoup(text, "html.parser").get_text(separator=' ')
    clean_text = clean_text[:4000]
    
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
    except Exception as e:
        tts = gTTS(text=clean_text, lang='bn') 
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()

# --- স্বয়ংক্রিয় স্ক্র্যাপিং ---
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
            for entry in feed.entries[:3]:
                title = entry.title
                link = entry.link
                
                c.execute("SELECT * FROM news_table WHERE link=? OR title=?", (link, title))
                if not c.fetchone():
                    try:
                        art_resp = requests.get(link, headers=headers, timeout=10)
                        art_soup = BeautifulSoup(art_resp.content, 'html.parser')
                        
                        img_tag = art_soup.find('meta', property='og:image')
                        image_url = img_tag['content'] if img_tag else "https://via.placeholder.com/600x400?text=News"
                        category = "বিশ্ব সংবাদ"
                        
                        paragraphs = art_soup.find_all('p')
                        full_eng_text = "\n\n".join([p.text.strip() for p in paragraphs if len(p.text.split()) > 10])
                        
                        if not full_eng_text:
                            continue
                            
                        bn_title = safe_translate(title)
                        
                        bn_full_text = ""
                        for p in full_eng_text.split('\n\n')[:12]: 
                            if p.strip():
                                trans_p = safe_translate(p.strip())
                                bn_full_text += f"<p>{trans_p}</p>"
                        
                        c.execute('''INSERT INTO news_table (title, link, translated_title, full_text, image_url, category, source, date) 
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                                  (title, link, bn_title, bn_full_text, image_url, category, source_name, datetime.now()))
                        conn.commit()
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
    should_update = False
    
    if not row:
        should_update = True
    else:
        last_update = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f')
        if datetime.now() - last_update > timedelta(hours=2): 
            should_update = True
            
    if should_update:
        auto_delete_old()
        success, count = scrape_news()
        if success and count > 0:
            st.toast(f"✅ {count}টি নতুন খবর অটো-আপডেট হয়েছে!", icon="🔄")
            time.sleep(1)
            st.rerun()

check_for_auto_update()

# ==========================================
# Frontend UI
# ==========================================

st.sidebar.title("⚙️ এডমিন প্যানেল")
if st.sidebar.button("🔄 খবর আপডেট করুন"):
    with st.spinner("নতুন খবর সংগ্রহ ও অনুবাদ করা হচ্ছে..."):
        auto_delete_old()
        success, count = scrape_news()
        st.sidebar.success(f"{count}টি নতুন খবর পাওয়া গেছে!")
        time.sleep(1)
        st.rerun()

if 'page_num' not in st.session_state: st.session_state.page_num = 1
if 'view' not in st.session_state: st.session_state.view = 'home'
if 'selected_news_id' not in st.session_state: st.session_state.selected_news_id = None

# --- ১. হোম পেইজ ---
if st.session_state.view == 'home':
    show_logo()
    
    c.execute("SELECT DISTINCT source FROM news_table")
    sources = ["সব সোর্স"] + [s[0] for s in c.fetchall() if s[0]]
    
    col_filter, _ = st.columns([1, 3])
    with col_filter:
        selected_source = st.selectbox("📰 সোর্স নির্বাচন করুন:", sources)
    st.write("")

    query = "SELECT id, translated_title, image_url, source, date FROM news_table "
    query += "ORDER BY date DESC" if selected_source == "সব সোর্স" else f"WHERE source='{selected_source}' ORDER BY date DESC"
    c.execute(query)
    all_news = c.fetchall()

    if not all_news:
        st.info("কোনো খবর পাওয়া যায়নি। বাম পাশ থেকে 'খবর আপডেট করুন' বাটনে ক্লিক করুন।")
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
                        st.markdown(f'<div class="news-card"><img src="{n[2]}" style="width:100%;height:100%;object-fit:cover;"></div>', unsafe_allow_html=True)
                        formatted_date = datetime.strptime(n[4], '%Y-%m-%d %H:%M:%S.%f').strftime('%b %d, %Y')
                        st.markdown(f"<div class='news-meta'><span class='category-badge'>{n[3]}</span> | {formatted_date}</div>", unsafe_allow_html=True)
                        if st.button(n[1], key=f"btn_{n[0]}", use_container_width=True):
                            st.session_state.selected_news_id = n[0]
                            st.session_state.view = 'details'
                            st.rerun()
            st.write("")

        st.write("---")
        if total_pages > 1:
            spacer_ratio = 4
            page_cols = st.columns([spacer_ratio] + [1]*total_pages + [spacer_ratio])
            
            for p in range(1, total_pages + 1):
                with page_cols[p]:
                    btn_type = "primary" if p == st.session_state.page_num else "secondary"
                    if st.button(str(p), key=f"page_{p}", type=btn_type, use_container_width=True):
                        st.session_state.page_num = p
                        st.rerun()

# --- ২. বিস্তারিত পেইজ ---
elif st.session_state.view == 'details':
    c.execute("SELECT translated_title, image_url, source, date, full_text, link FROM news_table WHERE id=?", (st.session_state.selected_news_id,))
    news = c.fetchone()
    
    # টপ বার (ব্যাক বাটন)
    col_back, _ = st.columns([1, 6])
    with col_back:
        if st.button("⬅️ হোম পেজে যান", use_container_width=True):
            st.session_state.view = 'home'
            st.rerun()
    
    st.write("")
    formatted_date = datetime.strptime(news[3], '%Y-%m-%d %H:%M:%S.%f').strftime('%B %d, %Y - %I:%M %p')
    img_html = f"""<div style="text-align: center; margin: 30px 0;"><img src="{news[1]}" style="max-width: 100%; width: 100%; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);"></div>""" if news[1] else ""
    
    # 🔴 সম্পূর্ণ নতুন এবং হাই-কন্ট্রাস্ট ডিজাইনের আর্টিকেল কন্টেইনার
    article_html = f"""
    <div style="background-color: #FFFBF0; padding: 50px; border-radius: 16px; border: 1px solid #E5E0D5; box-shadow: 0 10px 25px rgba(0,0,0,0.05); max-width: 850px; margin: 0 auto;">
        
        <h1 style='line-height: 1.5; color: #000000 !important; text-align: center; margin-bottom: 20px; font-weight: 800; font-size: 34px;'>{news[0]}</h1>
        
        <p style='text-align: center; font-size: 16px; color: #555555 !important; font-weight: 500; border-bottom: 1px solid #E5E0D5; padding-bottom: 25px;'>
            সোর্স: <span style="color: #D35400; font-weight: 800; text-transform: uppercase;">{news[2]}</span> &nbsp;|&nbsp; প্রকাশ: {formatted_date}
        </p>
        
        {img_html}
        
        <div style="color: #1A1A1A !important; font-size: 21px; line-height: 1.9; text-align: justify; margin-top: 30px; font-weight: 400;">
            {news[4]}
        </div>
        
        <hr style="border-top: 2px dashed #E5E0D5; margin-top: 50px; margin-bottom: 30px;">
        
        <div style="text-align: center;">
            <a href="{news[5]}" target="_blank" style="background-color: #D35400; color: #FFFFFF !important; padding: 12px 25px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 18px; display: inline-block; box-shadow: 0 4px 6px rgba(211,84,0,0.3);">🔗 মূল ইংরেজি খবরটি পড়ুন</a>
        </div>
        
    </div>
    """
    
    # 🔴 অডিও বাটনটি একদম মাঝখানে সুন্দরভাবে বসানো হয়েছে
    st.write("")
    col_audio1, col_audio2, col_audio3 = st.columns([1, 2, 1])
    with col_audio2:
        if st.button("🎧 সংবাদটি বাংলায় শুনুন (Smart Voice)", use_container_width=True):
            with st.spinner("ন্যাচারাল অডিও তৈরি হচ্ছে, একটু অপেক্ষা করুন..."):
                try:
                    audio_bytes = generate_audio(news[4])
                    st.audio(audio_bytes, format='audio/mp3')
                except Exception as e:
                    st.error("অডিও তৈরি করতে সমস্যা হয়েছে।")
    
    st.write("")
    st.markdown(article_html, unsafe_allow_html=True)
