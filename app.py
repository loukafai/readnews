import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

# 設定網頁標題
st.set_page_config(page_title="澳門日報下載器", page_icon="🇲🇴")

def start_crawler(target_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0"
    }

    try:
        res = requests.get(target_url, headers=headers)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
    except Exception as e:
        st.error(f"❌ 連線失敗: {e}")
        return None

    article_links = []
    for a in soup.find_all('a', href=True):
        if 'content_' in a['href']:
            article_links.append(urljoin(target_url, a['href']))
    
    article_links = list(dict.fromkeys(article_links))
    
    if not article_links:
        st.warning("❌ 找不到文章，請檢查網址。")
        return None

    total = len(article_links)
    
    # --- Streamlit 進度條 ---
    progress_bar = st.progress(0)
    status_text = st.empty()

    html_header = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>澳門日報合輯</title>
    <style>
        body { font-family: sans-serif; max-width: 850px; margin: 0 auto; padding: 30px; background: #f0f2f5; color: #1c1e21; }
        .article { background: white; padding: 35px; margin-bottom: 50px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
        .post-title { color: #aa0000; font-size: 1.8em; margin-bottom: 10px; }
        .source-link { background: #fff8f8; border: 1px solid #ffebeb; padding: 10px; border-radius: 6px; font-size: 0.85em; margin-bottom: 25px; }
        .source-link a { color: #0066cc; text-decoration: none; word-break: break-all; }
        .news-img { max-width: 100%; display: block; margin: 25px auto; border-radius: 4px; }
        .img-caption { text-align: center; font-size: 0.9em; color: #666; background: #f9f9f9; padding: 8px; margin-top: -20px; margin-bottom: 25px; border-bottom: 2px solid #eee; }
        .content-text { line-height: 1.8; font-size: 1.15em; color: #333; }
        #toc { background: white; padding: 25px; border-radius: 12px; margin-bottom: 40px; border: 1px solid #ddd; }
    </style></head><body><h1>新聞合輯備份</h1><div id="toc"><h3>📋 本頁文章清單</h3>"""

    toc_html = ""
    articles_body = ""

    for i, link in enumerate(article_links):
        try:
            status_text.text(f"正在擷取 ({i+1}/{total}): {link.split('/')[-1]}")
            r = requests.get(link, headers=headers)
            r.encoding = 'utf-8'
            a_soup = BeautifulSoup(r.text, 'html.parser')

            title = a_soup.find('title').text.replace("-澳門日報電子版", "").strip()
            
            news_images_html = ""
            for img in a_soup.find_all('img'):
                src = img.get('src')
                if src and '/res/' in src:
                    full_src = urljoin(link, src)
                    news_images_html += f'<img src="{full_src}" class="news-img">'
                    parent_td = img.find_parent('td')
                    if parent_td:
                        caption = parent_td.get_text(strip=True)
                        if caption and len(caption) < 150:
                            news_images_html += f'<p class="img-caption">▲ {caption}</p>'

            content_div = a_soup.find(id="ozoom")
            content_text = str(content_div) if content_div else "（未能擷取內文）"

            anchor_id = f"news_{i}"
            toc_html += f'<a href="#{anchor_id}" style="display:block; margin:8px 0; color:#0056b3; text-decoration:none;">{i+1}. {title}</a>'
            articles_body += f"""<div class="article" id="{anchor_id}"><div class="post-title">{title}</div>
            <div class="source-link"><b>🔗 原文連結：</b><a href="{link}" target="_blank">{link}</a></div>
            <div class="images-area">{news_images_html}</div><div class="content-text">{content_text}</div></div>"""
            
            progress_bar.progress((i + 1) / total)
            time.sleep(0.1)
        except:
            continue

    status_text.text("✅ 擷取完成！")
    return html_header + toc_html + "</div>" + articles_body + "</body></html>"

# --- UI 介面 ---
st.title("🇲🇴 澳門日報合併下載器")
st.write("輸入版面網址（Node 頁面），程式將自動抓取該版所有文章並合併為一個 HTML。")

input_url = st.text_input("請輸入網址:", placeholder="https://www.macaodaily.com/html/2026-02-02/node_1.htm")

if st.button("開始處理"):
    if input_url:
        final_html = start_crawler(input_url)
        if final_html:
            st.download_button(
                label="📥 下載合輯 HTML",
                data=final_html,
                file_name="MacaoDaily_Archive.html",
                mime="text/html"
            )
    else:
        st.warning("請先輸入有效網址")
