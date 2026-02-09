import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import time
import io
import datetime

# 設定網頁資訊
st.set_page_config(page_title="澳門日報下載器", page_icon="🇲🇴")

def start_full_crawler(target_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0"
    }

    try:
        res = requests.get(target_url, headers=headers, timeout=15)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 提取文章連結
        links = []
        for a in soup.find_all('a', href=True):
            if 'content_' in a['href']:
                links.append(urljoin(target_url, a['href']))
        
        article_links = list(dict.fromkeys(links))
        total = len(article_links)
        
        if total == 0:
            st.error("❌ 找不到文章連結，請檢查網址。")
            return None

        # 準備進度條
        progress_bar = st.progress(0)
        status_text = st.empty()

        # 檔名處理
        date_match = re.search(r'(\d{4}-\d{2}/\d{2})', target_url)
        date_id = date_match.group(1).replace('-', '').replace('/', '') if date_match else "Archive"

        # HTML 模板
        html_start = f"""<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="UTF-8">
        <style>
            body {{ font-family: sans-serif; line-height: 1.8; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f4; }}
            .article-card {{ background: white; padding: 30px; margin-bottom: 30px; border-radius: 8px; shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .news-title {{ color: #aa0000; font-size: 1.8em; font-weight: bold; }}
            .news-image {{ max-width: 100%; display: block; margin: 20px auto; border-radius: 4px; }}
            #toc {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #ddd; }}
        </style></head><body><h1>澳門日報合輯 ({date_id})</h1><div id="toc"><h3>📋 目錄</h3>"""

        toc_html = ""
        articles_body = ""

        for i, link in enumerate(article_links):
            try:
                status_text.text(f"正在處理 ({i+1}/{total}): {link.split('/')[-1]}")
                r = requests.get(link, headers=headers, timeout=10)
                r.encoding = 'utf-8'
                raw_html = r.text

                # 方正標籤提取標題
                title_match = re.search(r'<founder-title>(.*?)</founder-title>', raw_html, re.DOTALL)
                final_title = title_match.group(1).strip() if title_match else "無標題"
                final_title = final_title.replace('<![CDATA[', '').replace(']]>', '')

                a_soup = BeautifulSoup(raw_html, 'html.parser')
                
                imgs_html = ""
                for img in a_soup.find_all('img'):
                    src = img.get('src')
                    if src and '/res/' in src:
                        full_img_url = urljoin(link, src)
                        imgs_html += f'<img src="{full_img_url}" class="news-image">'

                content_div = a_soup.find(id="ozoom")
                content_html = str(content_div) if content_div else "<p>（內文擷取失敗）</p>"

                anchor_id = f"news_{i}"
                toc_html += f'<a href="#{anchor_id}" style="display:block;margin:5px 0;text-decoration:none;color:#0056b3;">{i+1}. {final_title}</a>'
                articles_body += f'<div class="article-card" id="{anchor_id}"><div class="news-title">{final_title}</div><hr>{imgs_html}<div>{content_html}</div></div>'
                
                progress_bar.progress((i + 1) / total)
                time.sleep(0.1)
            except:
                continue

        status_text.text("✨ 處理完成！請點擊下方按鈕下載。")
        return html_start + toc_html + "</div>" + articles_body + "</body></html>"

    except Exception as e:
        st.error(f"崩潰: {e}")
        return None



# --- 1. 時間處理 (UTC+8) ---
utc_now = datetime.datetime.utcnow()
local_now = utc_now + datetime.timedelta(hours=8)
today = local_now.date()
formatted_date = today.strftime("%Y-%m/%d")
today_url = f"https://www.macaodaily.com/html/{formatted_date}/node_1.htm"

# --- 2. UI 介面 ---
st.title("🇲🇴 澳門日報全版面下載器 v0.3")
st.caption(f"📅 伺服器偵測日期：{today} (UTC+8)")

# 建立按鈕欄位
col1, col2 = st.columns(2)
target_url = "" 
trigger_start = False 

with col1:
    # 使用大紅色的按鈕吸引注意
    if st.button("🔴 下載當天新聞", type="primary", use_container_width=True):
        target_url = today_url
        trigger_start = True

with col2:
    # 讓用戶也可以手動輸入其他日期或版面
    manual_url = st.text_input("輸入其他版面網址:", placeholder="https://...", label_visibility="collapsed")
    if st.button("🔍 開始分析手動網址", use_container_width=True):
        target_url = manual_url
        trigger_start = True

# --- 3. 執行邏輯 ---
if trigger_start:
    if target_url:
        with st.spinner(f'正在爬取: {target_url}'):
            # 這裡調用你之前的 start_full_crawler 函數
            result_html = start_full_crawler(target_url)
            
            if result_html:
                st.success(f"✅ {today} 報紙生成完成！")
                st.balloons()
                
                st.download_button(
                    label="💾 點我下載 HTML 存檔",
                    data=result_html.encode('utf-8'),
                    file_name=f"MacaoDaily_{today.strftime('%Y%m%d')}.html",
                    mime="text/html",
                    use_container_width=True
                )
    else:
        st.warning("請輸入網址或點擊下載按鈕。")
