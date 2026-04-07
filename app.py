import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import time

# --- পেইজ সেটআপ ---
st.set_page_config(page_title="বাংলা নিউজ পোর্টাল", page_icon="📰", layout="wide")

# --- ডাটাবেস তৈরি (Pro Version) ---
@st.cache_resource
def init_db():
    conn = sqlite3.connect('news_db_pro.db', check_same_thread=False)
    c = conn.cursor()
    # নতুন কলাম: category, image_url, full_text
    c.execute('''CREATE TABLE IF NOT EXISTS news_pro
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  title TEXT, link TEXT, translated_title TEXT, 
                  full_text TEXT, image_url TEXT, category TEXT, date TIMESTAMP)''')
    conn.commit()
    return conn, c

conn, c = init_db()

# --- সেশন স্টেট (সিঙ্গেল পেইজ কন্ট্রোল করার জন্য) ---
if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'current_news_id' not in st.session_state:
    st.session_state.current_news_id = None

def go_to_home():
    st.session_state.page = 'home'
    st.session_state.current_news_id = None

def go_to_article(news_id):
    st.session_state.page = 'article'
    st.session_state.current_news_id = news_id

# --- স্ক্র্যাপিং এবং অনুবাদের ফাংশন ---
def scrape_and_translate():
    url = "https://www.aljazeera.com/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        articles = soup.find_all('h3', class_='gc__title')[:8] # দ্রুত হওয়ার জন্য ৮টি নিলাম
        
        new_news_count = 0
        translator = GoogleTranslator(source='en', target='bn')
        
        for article in articles:
            title = article.text.strip()
            link_tag = article.find('a')
            if not link_tag: continue
            
            link = link_tag['href']
            link = "https://www.aljazeera.com" + link if not link.startswith('http') else link
            
            # ডাটাবেসে আছে কি না চেক
            c.execute("SELECT * FROM news_pro WHERE link=?", (link,))
            if not c.fetchone():
                try:
                    # মূল খবরে প্রবেশ
                    art_resp = requests.get(link, headers=headers)
                    art_soup = BeautifulSoup(art_resp.content, 'html.parser')
                    
                    # ১. মেটা ডাটা: ছবি (Featured Image)
                    og_image = art_soup.find('meta', property='og:image')
                    image_url = og_image['content'] if og_image else "https://via.placeholder.com/800x400?text=No+Image+Found"
                    
                    # ২. ক্যাটাগরি (URL থেকে বের করা)
                    try:
                        category_raw = link.split('/')[3].capitalize()
                        category = translator.translate(category_raw)
                    except:
                        category = "খবর"
                        
                    # ৩. পুরো খবর সংগ্রহ ও অনুবাদ (প্যারাগ্রাফগুলো)
                    paragraphs = art_soup.find_all('p')
                    full_english_text = " ".join([p.text for p in paragraphs[1:-2]]) # প্রথম ও শেষের কিছু অপ্রয়োজনীয় লেখা বাদ
                    
                    # অনেক বড় লেখা একসাথে অনুবাদ করলে Error আসতে পারে, তাই ৪০০০ অক্ষরে কাটছি
                    if len(full_english_text) > 4000:
                        full_english_text = full_english_text[:4000] + "..."
                        
                    translated_title = translator.translate(title)
                    translated_text = translator.translate(full_english_text) if full_english_text.strip() else "খবরটি পড়ার জন্য মূল ওয়েবসাইটে যান।"
                    
                    # ডাটাবেসে সেভ
                    c.execute('''INSERT INTO news_pro (title, link, translated_title, full_text, image_url, category, date) 
                                 VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                              (title, link, translated_title, translated_text, image_url, category, datetime.now()))
                    conn.commit()
                    new_news_count += 1
                except Exception as e:
                    print(f"Error in single article: {e}")
                
        return True, f"{new_news_count} টি নতুন খবর ছবি ও বিস্তারিতসহ যোগ করা হয়েছে!"
    except Exception as e:
        return False, f"সমস্যা হয়েছে: {e}"

# ==========================================
# Frontend ও UI ডিজাইন
# ==========================================

# --- সাইডবার (অ্যাডমিন) ---
st.sidebar.title("⚙️ অ্যাডমিন প্যানেল")
admin_pass = st.sidebar.text_input("পাসওয়ার্ড দিন", type="password")

if admin_pass == "admin123":
    st.sidebar.success("লগইন সফল!")
    if st.sidebar.button("🔄 তাজা খবর নিয়ে আসুন (Scrape)"):
        with st.spinner("Al Jazeera থেকে ছবি এবং পুরো খবর আনা হচ্ছে... দয়া করে অপেক্ষা করুন।"):
            success, msg = scrape_and_translate()
            if success: st.sidebar.success(msg)
            else: st.sidebar.error(msg)
            time.sleep(2)
            st.rerun()

# --- মূল পেইজ কন্ট্রোলার ---

if st.session_state.page == 'home':
    # ১. হোম পেইজ / আর্কাইভ পেইজ (Al Jazeera লেআউট)
    st.title("📰 তাজা খবর পোর্টাল")
    st.markdown("*আন্তর্জাতিক খবরের নির্ভরযোগ্য বাংলা অনুবাদ*")
    st.write("---")
    
    c.execute("SELECT id, translated_title, image_url, category, date, full_text FROM news_pro ORDER BY date DESC")
    all_news = c.fetchall()
    
    if not all_news:
        st.info("এখনো কোনো খবর নেই। অ্যাডমিন প্যানেল থেকে খবর আপডেট করুন।")
    else:
        # গ্রিড লেআউট (২ কলামে খবর দেখানোর জন্য)
        for i in range(0, len(all_news), 2):
            cols = st.columns(2) # দুটি কলাম তৈরি
            
            for j in range(2):
                if i + j < len(all_news):
                    news = all_news[i + j]
                    news_id = news[0]
                    title = news[1]
                    img_url = news[2]
                    cat = news[3]
                    date_str = datetime.strptime(news[4], '%Y-%m-%d %H:%M:%S.%f').strftime("%d %b %Y, %I:%M %p")
                    excerpt = news[5][:150] + "..." if news[5] else ""
                    
                    with cols[j]:
                        # ছবির নিচে ক্যাটাগরি ও টাইটেল
                        st.image(img_url, use_container_width=True)
                        st.caption(f"**{cat}** • 🕒 {date_str}")
                        st.subheader(title)
                        st.write(excerpt)
                        
                        # "বিস্তারিত পড়ুন" বাটন (ক্লিক করলে সিঙ্গেল পেইজে যাবে)
                        if st.button("বিস্তারিত পড়ুন ➔", key=f"btn_{news_id}"):
                            go_to_article(news_id)
                            st.rerun()
            st.write("---") # প্রতিটি রো-এর পর একটি দাগ

elif st.session_state.page == 'article':
    # ২. সিঙ্গেল নিউজ পেইজ
    news_id = st.session_state.current_news_id
    c.execute("SELECT translated_title, image_url, category, date, full_text, link FROM news_pro WHERE id=?", (news_id,))
    news_data = c.fetchone()
    
    if news_data:
        # ব্যাক বাটন
        if st.button("⬅️ ফিরে যান"):
            go_to_home()
            st.rerun()
            
        st.write("---")
        
        # মূল খবর
        title, img_url, cat, raw_date, full_text, original_link = news_data
        date_str = datetime.strptime(raw_date, '%Y-%m-%d %H:%M:%S.%f').strftime("%d %b %Y, %I:%M %p")
        
        st.caption(f"**ক্যাটাগরি:** {cat} | **প্রকাশিত:** {date_str}")
        st.header(title)
        st.image(img_url, use_container_width=True)
        
        st.write("---")
        # পুরো খবরের প্যারাগ্রাফগুলো সুন্দর করে দেখানো
        st.markdown(f"<div style='text-align: justify; font-size: 18px; line-height: 1.6;'>{full_text}</div>", unsafe_allow_html=True)
        
        st.write("---")
        st.markdown(f"*[মূল খবরটি ইংরেজিতে পড়তে এখানে ক্লিক করুন]({original_link})*")
