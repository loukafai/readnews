import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import time
import datetime
import base64  # 必須加入這個導入
import streamlit.components.v1 as components # 確保導入此套件
from concurrent.futures import ThreadPoolExecutor, as_completed

# 設定網頁資訊
st.set_page_config(page_title="澳門日報多線程下載器", page_icon="⚡")

def fetch_single_article(i, link, headers):
    """單篇文章抓取邏輯，供線程池調用"""
    try:
        r = requests.get(link, headers=headers, timeout=15)
        r.encoding = 'utf-8'
        raw_html = r.text

        # 提取標題 (Founder Tag)
        title_match = re.search(r'<founder-title>(.*?)</founder-title>', raw_html, re.DOTALL)
        final_title = title_match.group(1).strip() if title_match else "無標題"
        final_title = final_title.replace('<![CDATA[', '').replace(']]>', '')

        a_soup = BeautifulSoup(raw_html, 'html.parser')
        
        # 處理圖片
        imgs_html = ""
        for img in a_soup.find_all('img'):
            src = img.get('src')
            if src and '/res/' in src:
                full_img_url = urljoin(link, src)
                imgs_html += f'<img src="{full_img_url}" class="news-image">'

        # 處理正文
        content_div = a_soup.find(id="ozoom")
        content_html = str(content_div) if content_div else "<p>（內文擷取失敗）</p>"

        # 組裝該篇 HTML 片段
        anchor_id = f"news_{i}"
        article_piece = f"""
        <div class="article-card" id="{anchor_id}">
            <div class="news-title">{final_title}</div>
            <div class="source-url">
                <b>🔗 來源連結：</b><a href="{link}" target="_blank">{link}</a>
            </div>
            <hr>
            {imgs_html}
            <div class="content-body">{content_html}</div>
        </div>
        """
        # 返回索引、標題、片段，以便後續按順序排序
        return (i, final_title, anchor_id, article_piece)
    except Exception as e:
        return (i, f"抓取失敗: {link}", f"error_{i}", f"<p>錯誤: {str(e)}</p>")

def start_multi_threaded_crawler(target_url, num_threads):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0"
    }

    try:
        res = requests.get(target_url, headers=headers, timeout=15)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. 提取所有文章連結
        links = []
        for a in soup.find_all('a', href=True):
            if 'content_' in a['href']:
                links.append(urljoin(target_url, a['href']))
        
        article_links = list(dict.fromkeys(links))
        total = len(article_links)
        
        if total == 0:
            st.error("❌ 找不到文章連結。")
            return None

        # 2. 開始併發抓取
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text(f"🚀 啟動 {num_threads} 線程處理中...")

        results = []
        # 使用 ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            # 提交任務
            future_to_url = {executor.submit(fetch_single_article, i, link, headers): i for i, link in enumerate(article_links)}
            
            completed_count = 0
            for future in as_completed(future_to_url):
                res_data = future.result()
                results.append(res_data)
                completed_count += 1
                progress_bar.progress(completed_count / total)
                status_text.text(f"已完成: {completed_count}/{total}")

        # 3. 按原始順序排序（線程返回順序是亂的，需按索引排序）
        results.sort(key=lambda x: x[0])

        # 4. 組合 HTML
        date_match = re.search(r'(\d{4}-\d{2}/\d{2})', target_url)
        date_id = date_match.group(1).replace('-', '').replace('/', '') if date_match else "Archive"

        html_start = f"""<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="UTF-8">
        <style>
            body {{ font-family: sans-serif; line-height: 1.8; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f4; }}
            .article-card {{ background: white; padding: 30px; margin-bottom: 30px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .news-title {{ color: #aa0000; font-size: 1.8em; font-weight: bold; margin-bottom: 10px; }}
            .source-url {{ background: #f9f9f9; padding: 10px; border-radius: 4px; font-size: 0.85em; color: #666; margin-bottom: 20px; border: 1px solid #eee; word-break: break-all; }}
            .source-url a {{ color: #0056b3; text-decoration: none; }}
            .news-image {{ max-width: 100%; display: block; margin: 20px auto; border-radius: 4px; }}
            #toc {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #ddd; }}
        </style></head><body><h1>澳門日報合輯 ({date_id})</h1><div id="toc"><h3>📋 目錄</h3>"""

        toc_html = "".join([f'<a href="#{r[2]}" style="display:block;margin:5px 0;text-decoration:none;color:#0056b3;">{r[0]+1}. {r[1]}</a>' for r in results])
        articles_body = "".join([r[3] for r in results])

        status_text.text("✨ 多線程抓取完成！")
        return html_start + toc_html + "</div>" + articles_body + "</body></html>"

    except Exception as e:
        st.error(f"崩潰: {e}")
        return None

# --- UI 介面 ---
st.title("🇲🇴 澳門日報⚡極速下載器 v0.6.1")
st.info("💡 **提示：** 澳門日報網址通常為 https://www.macaodaily.com/html/2026-02/10/node_1.htm ")

# 線程數選擇
thread_count = st.slider("選擇並發線程數 (建議 4-8)", min_value=1, max_value=15, value=6)

local_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
formatted_date = local_now.strftime("%Y-%m/%d")
today_url = f"https://www.macaodaily.com/html/{formatted_date}/node_1.htm"

col1, col2 = st.columns(2)
target_url = "" 
trigger_start = False 

with col1:
    if st.button("🔴 下載當天新聞", type="primary", use_container_width=True):
        target_url = today_url
        trigger_start = True

with col2:
    manual_url = st.text_input("輸入版面網址:", placeholder="https://...", label_visibility="collapsed")
    if st.button("🔍 開始分析", use_container_width=True):
        target_url = manual_url
        trigger_start = True

if trigger_start:
    if target_url:
        with st.spinner('極速抓取中...'):
            result_html = start_multi_threaded_crawler(target_url, thread_count)
            if result_html:
                st.success(f"✅ 生成完成！")
                
                # 1. 下載按鈕
                st.download_button(
                    label="💾 點我下載 HTML 存檔",
                    data=result_html.encode('utf-8'),
                    file_name=f"MacaoDaily_{local_now.strftime('%Y%m%d')}.html",
                    mime="text/html",
                    use_container_width=True
                )

                # --- 修正後的預覽邏輯：使用 JavaScript Blob ---
                # 轉義 HTML 中的引號以避免 JS 報錯
                escaped_html = result_html.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
                
                js_code = f"""
                <script>
                function openInNewTab() {{
                    const htmlContent = `{escaped_html}`;
                    const blob = new Blob([htmlContent], {{ type: 'text/html' }});
                    const url = URL.createObjectURL(blob);
                    window.open(url, '_blank');
                }}
                </script>
                <button onclick="openInNewTab()" style="
                    width: 100%;
                    background-color: white;
                    color: #ff4b4b;
                    border: 1px solid #ff4b4b;
                    padding: 10px 20px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-weight: 500;
                    margin-top: 10px;
                    font-size: 16px;
                ">
                    🌐 直接在新分頁開啟查看 (免下載)
                </button>
                """
                # 使用 components.html 嵌入這個按鈕
                components.html(js_code, height=70)
