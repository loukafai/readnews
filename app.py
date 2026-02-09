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


# --- UI 介面 ---
st.title("🇲🇴 澳門日報全版面下載器 v.0.2")
st.info("您可以手動輸入網址，或點擊下方按鈕直接抓取今天的報紙。")

# 1. 建立兩欄佈局，讓按鈕看起來更整齊
col1, col2 = st.columns([1, 1])

with col1:
    # 獲取今天日期的邏輯
    today = datetime.date.today()
    # 格式化為網址要求的樣式：YYYY-MM/DD
    formatted_date = today.strftime("%Y-%m/%d")
    today_url = f"https://www.macaodaily.com/html/{formatted_date}/node_1.htm"
    
    if st.button("📅 下載當天新聞", use_container_width=True):
        url_input = today_url # 重寫 url_input
        st.session_state['run_url'] = today_url # 存入 session 觸發執行

with col2:
    if st.button("🧹 清除輸入", use_container_width=True):
        st.session_state.pop('run_url', None)

# 2. 手動輸入框（給予預設值或顯示自動生成的網址）
default_val = st.session_state.get('run_url', today_url)
url_to_process = st.text_input("版面網址:", value=default_val)

# 3. 執行邏輯
# 如果點擊了「下載當天新聞」或者手動點擊「開始分析」
if st.button("🚀 開始分析並生成合輯", type="primary"):
    if url_to_process:
        with st.spinner(f'正在搬運 {url_to_process} 的內容...'):
            result_html = start_full_crawler(url_to_process)
            
            if result_html:
                st.balloons() # 成功後噴花特效
                html_bytes = result_html.encode('utf-8')
                st.download_button(
                    label="📥 點我儲存 HTML 合輯檔案",
                    data=html_bytes,
                    file_name=f"MacaoDaily_{today.strftime('%Y%m%d')}.html",
                    mime="text/html"
                )
    else:
        st.warning("請先輸入網址或點擊當天按鈕")
