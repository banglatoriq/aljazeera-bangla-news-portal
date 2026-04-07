import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# --- পেইজ সেটআপ ---
st.set_page_config(page_title="বাংলা নিউজ পোর্টাল", page_icon="📰", layout="wide")

# --- ডাটাবেস তৈরি (নতুন ভার্সন) ---
@st.cache_resource
def init_db():
    # নতুন ডাটাবেস তৈরি করছি যাতে আগেরটার সাথে ক্ল্যাশ না করে
    conn = sqlite3.connect('news_database_v2.db', check_same_thread=False)
    c = conn.cursor()
    # 'translated_details' নামে নতুন কলাম যোগ করা হয়েছে
    c.execute('''CREATE TABLE IF NOT EXISTS news_v2
                 (title TEXT, link TEXT, translated_title TEXT, translated_details TEXT, date TIMESTAMP)''')
    conn.commit()
    return conn, c

conn, c = init_db()

# --- বিস্তারিত খবরসহ স্ক্র্যাপিং এবং অনুবাদের ফাংশন ---
def scrape_and_translate():
    url = "https://www.aljazeera.com/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
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
            c.execute("SELECT * FROM news_v2 WHERE link=?", (link,))
            if not c.fetchone():
                try:
                    # ১. টাইটেল অনুবাদ
                    translated_title = translator.translate(title)
                    
                    # ২. বিস্তারিত খবর আনতে লিংকে প্রবেশ করা
                    article_response = requests.get(link, headers=headers)
                    article_soup = BeautifulSoup(article_response.content, 'html.parser')
                    
                    # খবরের ভেতরের প্যারাগ্রাফগুলো (<p> ট্যাগ) খুঁজে বের করা
                    paragraphs = article_soup.find_all('p')
                    
                    # প্রথম ৩-৪ টি প্যারাগ্রাফ মিলিয়ে একটি সারাংশ তৈরি করা (যাতে অনুবাদ দ্রুত হয়)
                    details_text = " ".join([p.text for p in paragraphs[1:5]]) 
                    
                    if not details_text.strip():
                        translated_details = "বিস্তারিত খবর ওয়েবসাইটের মূল লিংকে দেখুন।"
                    else:
                        # গুগলের ফ্রি ট্রান্সলেটরে একসাথে অনেক বড় লেখা দিলে সমস্যা হতে পারে, 
                        # তাই আমরা প্রথম ৪০০০ অক্ষর নিচ্ছি
                        translated_details = translator.translate(details_text[:4000])
                    
                    # ডাটাবেসে সেভ করা (বিস্তারিত খবরসহ)
                    c.execute("INSERT INTO news_v2 VALUES (?, ?, ?, ?, ?)", 
                              (title, link, translated_title, translated_details, datetime.now()))
                    conn.commit()
                    new_news_count += 1
                except Exception as e:
                    print(f"অনুবাদে সমস্যা: {e}") # কোনো একটি নিউজে সমস্যা হলে যেন পুরো সিস্টেম বন্ধ না হয়
                
        return True, f"{new_news_count} টি নতুন খবর বিস্তারিতসহ যোগ করা হয়েছে!"
    except Exception as e:
        return False, f"খবর আনতে সমস্যা হয়েছে: {e}"

# --- পুরনো খবর ডিলিট করার ফাংশন ---
def delete_old_news():
    seven_days_ago = datetime.now() - timedelta(days=7)
    c.execute("DELETE FROM news_v2 WHERE date < ?", (seven_days_ago,))
    deleted_count = c.rowcount
    conn.commit()
    return deleted_count

# ==========================================
# Frontend ও UI ডিজাইন
# ==========================================

# সাইডবার - অ্যাডমিন প্যানেল
st.sidebar.title("⚙️ অ্যাডমিন প্যানেল")
admin_password = st.sidebar.text_input("পাসওয়ার্ড দিন", type="password")

if admin_password == "admin123": 
    st.sidebar.success("লগইন সফল!")
    st.sidebar.write("---")
    
    if st.sidebar.button("🔄 নতুন খবর নিয়ে আসুন"):
        with st.spinner("Al Jazeera থেকে খবর আনা হচ্ছে... এতে কিছুটা সময় লাগতে পারে!"):
            success, message = scrape_and_translate()
            if success:
                st.sidebar.success(message)
            else:
                st.sidebar.error(message)
                
    if st.sidebar.button("🗑️ ৭ দিনের পুরনো খবর মুছুন"):
        deleted = delete_old_news()
        st.sidebar.warning(f"{deleted} টি পুরনো খবর মুছে ফেলা হয়েছে।")

elif admin_password != "":
    st.sidebar.error("ভুল পাসওয়ার্ড!")

# মূল পেইজ - পাঠকের জন্য
st.title("📰 তাজা খবর (Al Jazeera থেকে)")
st.write("স্বয়ংক্রিয়ভাবে বাংলায় অনূদিত নিউজ পোর্টাল")
st.write("---")

# ডাটাবেস থেকে খবর দেখানো
c.execute("SELECT translated_title, link, translated_details, date FROM news_v2 ORDER BY date DESC")
all_news = c.fetchall()

if not all_news:
    st.info("এখনো কোনো খবর নেই। অ্যাডমিন প্যানেল থেকে খবর আপডেট করুন।")
else:
    for news in all_news:
        bn_title = news[0]
        news_link = news[1]
        news_details = news[2]
        
        # সময় ফরম্যাট করা
        raw_date = datetime.strptime(news[3], '%Y-%m-%d %H:%M:%S.%f')
        formatted_date = raw_date.strftime("%d %B %Y, %I:%M %p")
        
        # Expander ব্যবহার করা (ক্লিক করলে বিস্তারিত দেখাবে)
        with st.expander(f"🔹 {bn_title}"):
            st.caption(f"🕒 সংগৃহীত সময়: {formatted_date}")
            st.write(news_details)
            st.write("---")
            st.markdown(f"**[🔗 মূল খবরটি ইংরেজিতে পড়তে এখানে ক্লিক করুন]({news_link})**")
