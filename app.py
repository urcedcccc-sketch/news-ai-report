import streamlit as st
import requests
from openai import OpenAI
from datetime import datetime, timedelta
from newspaper import Article  # 新增：用于抓取网页正文

# 1. 密钥初始化
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    TIAN_API_KEY = st.secrets["TIAN_API_KEY"]
except Exception as e:
    st.error("密钥配置错误，请检查 Streamlit Secrets。")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# 页面设置
st.set_page_config(page_title="全域智能内参系统", layout="wide")
st.title("🗞️ 全域智能内参系统")
st.caption("多源并发检索 | 实时正文抓取 | AI 深度提炼")

# 2. 侧边栏配置
with st.sidebar:
    st.header("检索设置")
    word = st.text_input("请输入核心关键词", "伊朗")
    num_limit = st.slider("最大展示总篇数", 1, 30, 8)
    st.divider()
    btn = st.button("开始同步全域内参", type="primary")

# 3. 核心工具函数
def get_full_text(url):
    """新增：给定URL，抓取并返回网页正文"""
    try:
        article = Article(url, language='zh')
        article.download()
        article.parse()
        return article.text
    except:
        return None

def is_within_a_week(date_str):
    if not date_str: return False
    try:
        fmt = "%Y-%m-%d %H:%M:%S" if ":" in date_str else "%Y-%m-%d"
        news_date = datetime.strptime(date_str[:19], fmt)
        return datetime.now() - news_date <= timedelta(days=7)
    except: return True

def fetch_all_sources(kw):
    endpoints = {
        "国际新闻": "https://apis.tianapi.com/world/index",
        "国内新闻": "https://apis.tianapi.com/guonei/index",
        "互联网资讯": "https://apis.tianapi.com/internet/index",
        "综合新闻": "https://apis.tianapi.com/generalnews/index"
    }
    aggregated_news = []
    for name, url in endpoints.items():
        params = {"key": TIAN_API_KEY, "num": 30, "word": kw.strip()}
        try:
            res = requests.get(url, params=params, timeout=8).json()
            if res.get("code") == 200:
                news_list = res.get("result", {}).get("newslist", [])
                for n in news_list:
                    n["source_tag"] = name 
                aggregated_news.extend(news_list)
        except: continue
    aggregated_news.sort(key=lambda x: x.get('ctime', ''), reverse=True)
    return aggregated_news

# 4. 主渲染逻辑
if btn:
    if not word:
        st.warning("⚠️ 请输入关键词")
        st.stop()

    status = st.empty()
    status.info(f"正在跨源同步『{word}』并实时解析正文...")
    
    all_data = fetch_all_sources(word)
    final_list = [n for n in all_data if is_within_a_week(n.get('ctime'))][:num_limit]

    if not final_list:
        st.error(f"🔍 未发现最近 7 天内关于『{word}』的有效报道。")
    else:
        for news in final_list:
            with st.container(border=True):
                title = news.get('title', '无标题')
                source = news.get('source', '权威媒体')
                url = news.get('url')
                
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.write(f"**{source}**")
                    st.caption(f"📅 {news.get('ctime')}")
                    st.caption(f"📂 {news.get('source_tag')}")
                
                with col2:
                    st.markdown(f"### {title}")
                    
                    # 第一步：尝试抓取网页真实正文
                    full_content = None
                    if url:
                        with st.spinner('正在深度解析原文...'):
                            full_content = get_full_text(url)
                    
                    # 第二步：确定交给 AI 的素材（抓取的正文 > API摘要 > 标题）
                    content_for_ai = full_content or news.get('description') or news.get('digest')
                    
                    if content_for_ai and len(content_for_ai) > 20:
                        try:
                            prompt = (
                                f"你是一名专业的政经分析师。请针对以下新闻素材进行深度提炼：\n"
                                f"【标题】：{title}\n"
                                f"【素材内容】：{content_for_ai[:1500]}\n\n" # 截取前1500字防止超长
                                f"要求：请写一段150字以内的深度总结。要求：\n"
                                f"1. 概括事件核心事实；\n"
                                f"2. 分析该事件背后的潜在影响或重要性；\n"
                                f"3. 语气保持严谨、客观、专业。不要出现'根据素材'等废话。"
                            )
                            
                            completion = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0.3
                            )
                            st.info(completion.choices[0].message.content)
                        except:
                            st.write(content_for_ai[:200] + "...")
                    else:
                        st.warning("🚨 无法提取有效正文，AI 总结跳过。")
                    
                    if url:
                        st.markdown(f"🔗 [阅读原发报道]({url})")
    status.empty()
