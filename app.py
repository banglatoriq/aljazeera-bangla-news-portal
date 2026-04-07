import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# --- পেইজ সেটআপ ---
st.set_page_config(page_title="বাংলা নিউজ পোর্টাল", page_icon="📰", layout="wide")

# --- ডাটাবেস তৈরি এবং সেটআপ ---
@st.cache_resource
def init_db():
    conn = sqlite3.connect('news_database.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news
                 (title TEXT, link TEXT, translated_title TEXT, date TIMESTAMP)''')
    conn.commit()
    return conn, c

conn, c = init_db()

# --- স্ক্র্যাপিং এবং অনুবাদের ফাংশন ---
def scrape_and_translate():
    url = "https://www.aljazeera.com/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Al Jazeera-র হেডলাইনগুলো খুঁজে বের করা
        articles = soup.find_all('h3', class_='gc__title')[:10] # ১০টি নিউজ নিচ্ছি
        
        new_news_count = 0
        translator = GoogleTranslator(source='en', target='bn')
        
        for article in articles:
            title = article.text.strip()
            link_tag = article.find('a')
            if link_tag:
                link = link_tag['href']
                if not link.startswith('http'):
                    link = "https://www.aljazeera.com" + link
            else:
                link = url
            
            # ডাটাবেসে নিউজটি আগে থেকেই আছে কি না চেক করা
            c.execute("SELECT * FROM news WHERE link=?", (link,))
            if not c.fetchone():
                # অনুবাদ করা
                translated_title = translator.translate(title)
                
                # ডাটাবেসে সেভ করা
                c.execute("INSERT INTO news VALUES (?, ?, ?, ?)", (title, link, translated_title, datetime.now()))
                conn.commit()
                new_news_count += 1
                
        return True, f"{new_news_count} টি নতুন খবর সফলভাবে যোগ করা হয়েছে!"
    except Exception as e:
        return False, f"খবর আনতে সমস্যা হয়েছে: {e}"

# --- পুরনো খবর ডিলিট করার ফাংশন ---
def delete_old_news():
    seven_days_ago = datetime.now() - timedelta(days=7)
    c.execute("DELETE FROM news WHERE date < ?", (seven_days_ago,))
    deleted_count = c.rowcount
    conn.commit()
    return deleted_count

# ==========================================
# Frontend ও UI ডিজাইন
# ==========================================

# সাইডবার - অ্যাডমিন প্যানেল
st.sidebar.title("⚙️ অ্যাডমিন প্যানেল")
st.sidebar.write("খবর আপডেট করতে লগইন করুন")
admin_password = st.sidebar.text_input("পাসওয়ার্ড দিন", type="password")

# সিকিউরিটির জন্য একটি সাধারণ পাসওয়ার্ড (এটি আপনার ইচ্ছেমতো পরিবর্তন করে নিন)
if admin_password == "admin123": 
    st.sidebar.success("লগইন সফল!")
    
    st.sidebar.write("---")
    if st.sidebar.button("🔄 নতুন খবর নিয়ে আসুন"):
        with st.spinner("Al Jazeera থেকে খবর আনা হচ্ছে এবং অনুবাদ করা হচ্ছে..."):
            success, message = scrape_and_translate()
            if success:
                st.sidebar.success(message)
            else:
                st.sidebar.error(message)
                
    if st.sidebar.button("🗑️ ৭ দিনের পুরনো খবর মুছুন"):
        deleted = delete_old_news()
        st.sidebar.warning(f"{deleted} টি পুরনো খবর ডাটাবেস থেকে মুছে ফেলা হয়েছে।")

elif admin_password != "":
    st.sidebar.error("ভুল পাসওয়ার্ড!")

# মূল পেইজ - পাঠকের জন্য
st.title("📰 তাজা খবর (Al Jazeera থেকে)")
st.write("স্বয়ংক্রিয়ভাবে বাংলায় অনূদিত নিউজ পোর্টাল")
st.write("---")

# ডাটাবেস থেকে খবর দেখানো
c.execute("SELECT translated_title, link, date FROM news ORDER BY date DESC")
all_news = c.fetchall()

if not all_news:
    st.info("এখনো কোনো খবর নেই। অ্যাডমিন প্যানেল থেকে খবর আপডেট করুন।")
else:
    # খবরগুলো সুন্দর করে সাজিয়ে দেখানো
    for news in all_news:
        bn_title = news[0]
        news_link = news[1]
        
        # সময় ফরম্যাট করা
        raw_date = datetime.strptime(news[2], '%Y-%m-%d %H:%M:%S.%f')
        formatted_date = raw_date.strftime("%d %B %Y, %I:%M %p")
        
        st.markdown(f"### 🔹 {bn_title}")
        st.caption(f"🕒 সংগৃহীত সময়: {formatted_date}")
        st.markdown(f"[🔗 মূল খবরটি ইংরেজিতে পড়ুন]({news_link})")
        st.write("---")