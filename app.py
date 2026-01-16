import streamlit as st
import requests
from openai import OpenAI
from datetime import datetime, timedelta

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
st.caption("多源并发检索 | 自动聚合提炼 | 严格 7 天时效")

# 2. 侧边栏配置 (UI 极简优化)
with st.sidebar:
    st.header("检索设置")
    word = st.text_input("请输入核心关键词", "伊朗")
    num_limit = st.slider("最大展示总篇数", 1, 30, 10)
    
    st.divider()
    st.info("📌 系统已开启‘全源联动’：点击同步后，后台将自动检索国际、国内、互联网及综合新闻。")
    btn = st.button("开始同步全域内参", type="primary")

# 3. 核心工具函数
def is_within_a_week(date_str):
    """时效拦截：确保只有7天内的新闻能通过"""
    if not date_str: return False
    try:
        fmt = "%Y-%m-%d %H:%M:%S" if ":" in date_str else "%Y-%m-%d"
        news_date = datetime.strptime(date_str[:19], fmt)
        return datetime.now() - news_date <= timedelta(days=7)
    except:
        return True

def fetch_all_sources(kw):
    """核心：后台并发检索四大接口"""
    endpoints = {
        "国际新闻": "https://apis.tianapi.com/world/index",
        "国内新闻": "https://apis.tianapi.com/guonei/index",
        "互联网资讯": "https://apis.tianapi.com/internet/index",
        "综合新闻": "https://apis.tianapi.com/generalnews/index"
    }
    
    aggregated_news = []
    
    # 逐一请求接口并打上来源标签
    for name, url in endpoints.items():
        params = {"key": TIAN_API_KEY, "num": 30, "word": kw.strip()}
        try:
            res = requests.get(url, params=params, timeout=8).json()
            if res.get("code") == 200:
                news_list = res.get("result", {}).get("newslist", [])
                for n in news_list:
                    n["source_tag"] = name # 标记数据来自哪个接口
                aggregated_news.extend(news_list)
        except:
            continue
            
    # 按时间倒序排列 (最新的在前)
    aggregated_news.sort(key=lambda x: x.get('ctime', ''), reverse=True)
    return aggregated_news

# 4. 主渲染逻辑
if btn:
    if not word:
        st.warning("⚠️ 请输入关键词后再执行同步。")
        st.stop()

    status = st.empty()
    status.info(f"正在跨源同步关于『{word}』的全域数据并进行 AI 提炼...")
    
    # 聚合数据获取
    all_data = fetch_all_sources(word)
    
    # 时效性过滤 + 篇数截取
    final_list = [n for n in all_data if is_within_a_week(n.get('ctime'))][:num_limit]

    if not final_list:
        st.error(f"🔍 全域检索完毕，未发现最近 7 天内关于『{word}』的有效报道。")
    else:
        status.success(f"✅ 全域同步成功：已从四大源中提炼出 {len(final_list)} 条本周高价值内参")
        
        for news in final_list:
    with st.container(border=True):
        title = news.get('title', '无标题')
        source = news.get('source', '权威媒体')
        tag = news.get('source_tag', '未知分类')
        ctime = news.get('ctime', '刚刚')
        
        # 优化点 1：获取真实素材，如果为空则使用标题兜底
        desc = news.get('description') or news.get('digest')
        raw_desc = desc if desc and len(desc) > 10 else "暂无详细正文"
        
        col1, col2 = st.columns([1, 4])
        with col1:
            st.write(f"**{source}**")
            st.caption(f"📅 {ctime}")
            st.caption(f"📂 分类：{tag}")
        with col2:
            # 优化点 2：只有当素材字数足够时才调用 AI
            if desc and len(desc) > 20:
                try:
                    # 改进的提示词：强调严谨性，减少误导
                    prompt = (
                        f"你是一名称职的新闻编辑。请针对以下素材进行提炼：\n"
                        f"【标题】：{title}\n"
                        f"【正文】：{desc}\n"
                        f"要求：严格基于正文，写一段100字以内的深度总结，要求包含事件核心和潜在影响。若正文内容不足，请直接概括标题。"
                    )
                    
                    completion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.2 # 调低随机性，减少幻觉
                    )
                    st.markdown(f"### {title}")
                    st.info(completion.choices[0].message.content)
                except:
                    st.markdown(f"### {title}")
                    st.write(raw_desc)
            else:
                # 素材太少，直接显示标题和原文摘要，不浪费 Token 且更准确
                st.markdown(f"### {title}")
                st.write(f"⚠️ 原始素材过短，请点击下方链接查看原文详情。")
                st.caption(f"内容简述：{raw_desc}")
            
            if news.get('url'):
                st.markdown(f"🔗 [阅读原发报道]({news['url']})")
    
    status.empty()
