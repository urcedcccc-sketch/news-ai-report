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
st.set_page_config(page_title="精选周度新闻内参", layout="wide")
st.title("🗞️ 精选周度新闻内参系统")
st.caption("专注核心资讯 | 严格限定一周内时效")

# 2. 侧边栏配置
with st.sidebar:
    st.header("检索设置")
    search_mode = st.radio(
        "检索源路径", 
        ["综合门户(综合新闻)", "全域深度(互联网资讯)", "即时热点(国内新闻)"]
    )
    
    word = st.text_input("输入核心关键词", "马斯克")
    num_limit = st.slider("最大展示篇数", 1, 15, 5)
    
    st.divider()
    st.info("📌 系统已开启‘时效围栏’：仅展示最近 7 天内的报道。")
    btn = st.button("开始同步内参", type="primary")

# 3. 核心工具函数
def is_within_a_week(date_str):
    """检查日期是否在7天内"""
    if not date_str: return False
    try:
        # 兼容多种日期格式
        fmt = "%Y-%m-%d %H:%M:%S" if ":" in date_str else "%Y-%m-%d"
        news_date = datetime.strptime(date_str[:19], fmt)
        return datetime.now() - news_date <= timedelta(days=7)
    except:
        return True # 解析失败则保底显示

def fetch_core_news(mode, kw):
    endpoints = {
        "综合门户(综合新闻)": "https://apis.tianapi.com/generalnews/index",
        "全域深度(互联网资讯)": "https://apis.tianapi.com/internet/index",
        "即时热点(国内新闻)": "https://apis.tianapi.com/guonei/index"
    }
    params = {
        "key": TIAN_API_KEY,
        "num": 50, # 初始抓取50篇用于时效筛选
        "word": kw.strip()
    }
    try:
        res = requests.get(endpoints[mode], params=params, timeout=10).json()
        return res
    except:
        return {"code": 500}

# 4. 主渲染逻辑
if btn:
    if not word:
        st.warning("请输入关键词后再执行检索。")
        st.stop()

    status = st.empty()
    status.info(f"正在深度扫描『{word}』的一周内相关报道...")
    
    res = fetch_core_news(search_mode, word)
    
    if res.get("code") == 200:
        raw_list = res.get("result", {}).get("newslist", [])
        
        # --- 时效性过滤：核心逻辑 ---
        valid_news = [n for n in raw_list if is_within_a_week(n.get('ctime'))]
        display_list = valid_news[:num_limit]

        if not display_list:
            st.warning(f"检索成功，但在最近 7 天内未发现关于『{word}』的高质量报道。")
            if raw_list:
                with st.expander("查看 7 天前的历史报道（仅供参考）"):
                    st.write(raw_list[:3])
        else:
            status.success(f"同步成功：已为您提炼 {len(display_list)} 条本周深度资讯")
            for news in display_list:
                with st.container(border=True):
                    title = news.get('title', '无标题')
                    source = news.get('source', '权威源')
                    ctime = news.get('ctime', '刚刚')
                    desc = news.get('description') or news.get('digest') or "暂无摘要"
                    
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.markdown(f"**{source}**")
                        st.caption(f"📅 {ctime}")
                    with col2:
                        try:
                            prompt = f"你是资深内参编辑。请根据素材写12字标题和100字深度总结，必须客观专业：\n来源：{source}\n素材：{desc}"
                            completion = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0.3
                            )
                            st.markdown(f"### {title}")
                            st.info(completion.choices[0].message.content)
                        except:
                            st.markdown(f"### {title}")
                            st.write(desc)
                        
                        if news.get('url'):
                            st.markdown(f"🔗 [阅读原发报道]({news['url']})")
    else:
        # 处理 250 错误
        if res.get("code") == 250:
            st.error("未找到相关结果。建议：1. 缩短关键词（如‘美国伊朗’改‘伊朗’）2. 换个路径试试。")
        else:
            st.error(f"同步失败。错误代码：{res.get('code')}")
