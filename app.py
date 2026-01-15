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
st.set_page_config(page_title="精选周度内参系统", layout="wide")
st.title("🗞️ 精选周度新闻内参系统")
st.caption("专注核心四大路径 | 严格锁定 7 天内时效")

# 2. 侧边栏配置
with st.sidebar:
    st.header("内参源设置")
    search_mode = st.radio(
        "选择新闻路径", 
        [
            "全球动态(国际新闻)", 
            "综合门户(综合新闻)", 
            "全域深度(互联网资讯)", 
            "即时热点(国内新闻)"
        ]
    )
    
    word = st.text_input("输入核心关键词", "委内瑞拉")
    num_limit = st.slider("最大展示篇数", 1, 15, 5)
    
    st.divider()
    st.warning("⏱️ 时效过滤：ON (仅保留7天内讯息)")
    btn = st.button("开始同步内参", type="primary")

# 3. 核心工具函数
def is_within_a_week(date_str):
    """检查日期是否在7天内"""
    if not date_str: return False
    try:
        # 兼容 %Y-%m-%d %H:%M:%S 或 %Y-%m-%d
        fmt = "%Y-%m-%d %H:%M:%S" if ":" in date_str else "%Y-%m-%d"
        news_date = datetime.strptime(date_str[:19], fmt)
        return datetime.now() - news_date <= timedelta(days=7)
    except:
        return True # 解析失败则默认显示

def fetch_core_news(mode, kw):
    # 映射天行 API 接口地址
    endpoints = {
        "全球动态(国际新闻)": "https://apis.tianapi.com/world/index",
        "综合门户(综合新闻)": "https://apis.tianapi.com/generalnews/index",
        "全域深度(互联网资讯)": "https://apis.tianapi.com/internet/index",
        "即时热点(国内新闻)": "https://apis.tianapi.com/guonei/index"
    }
    params = {
        "key": TIAN_API_KEY,
        "num": 40, # 抓取较多数据进行本地时间过滤
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
        st.warning("⚠️ 请输入关键词后再执行检索。")
        st.stop()

    status = st.empty()
    status.info(f"正在全网扫描关于『{word}』的最新报道...")
    
    res = fetch_core_news(search_mode, word)
    
    if res.get("code") == 200:
        raw_list = res.get("result", {}).get("newslist", [])
        
        # --- 时效性过滤：核心拦截 ---
        # 仅保留最近 7 天内的新闻
        display_list = [n for n in raw_list if is_within_a_week(n.get('ctime'))][:num_limit]

        if not display_list:
            if not raw_list:
                st.error("❌ 未找到相关结果。建议简化关键词或切换路径。")
            else:
                st.warning(f"💡 检索到相关信息，但其发布时间已超过 7 天，根据规则已自动过滤。")
                with st.expander("查看历史存档（一周前）"):
                    for n in raw_list[:3]:
                        st.write(f"- {n.get('title')} ({n.get('ctime')})")
        else:
            status.success(f"✅ 同步成功：已提炼 {len(display_list)} 条本周深度资讯")
            for news in display_list:
                with st.container(border=True):
                    title = news.get('title', '无标题')
                    source = news.get('source', '权威源')
                    ctime = news.get('ctime', '刚刚')
                    desc = news.get('description') or news.get('digest') or "暂无详细描述"
                    
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.markdown(f"**{source}**")
                        st.caption(f"📅 {ctime}")
                    with col2:
                        try:
                            # 强化 AI 的内参编写风格
                            prompt = f"你是资深新闻内参编辑。请针对下述素材，撰写一个12字内的震撼标题，并提供一段100字左右的专业深度总结（包含背景、现状及影响）：\n来源：{source}\n素材：{desc}"
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
        # 错误处理
        err_code = res.get("code")
        if err_code == 250:
            st.error("🔍 未找到相关新闻。请尝试以下操作：\n1. 检查关键词是否有误；\n2. 尝试更宽泛的词（如‘美国伊朗’改为‘伊朗’）。")
        else:
            st.error(f"📡 接口连接异常 (代码: {err_code})")
