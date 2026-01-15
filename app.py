import streamlit as st
import requests
from openai import OpenAI

# 1. 密钥配置
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    TIAN_API_KEY = st.secrets["TIAN_API_KEY"]
except Exception as e:
    st.error("密钥配置未就绪，请在 Streamlit Secrets 中检查。")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# 页面设置
st.set_page_config(page_title="实时全域内参系统", layout="wide")
st.title("🗞️ 实时全域新闻内参系统")

# 2. 侧边栏配置
with st.sidebar:
    st.header("检索路径选择")
    search_mode = st.radio(
        "选择数据源", 
        ["全网风向(全网热搜)", "垂直地区(地区新闻)", "全域深度(互联网资讯)", "综合门户(综合新闻)"]
    )
    
    word = ""
    area = ""
    if search_mode == "全网风向(全网热搜)":
        st.success("🔥 实时模式：将直接调取全网最热话题，无需输入。")
    elif search_mode == "垂直地区(地区新闻)":
        area = st.text_input("指定地区", "新疆")
        word = st.text_input("过滤关键词(可选，留空则看全部)", "")
    else:
        word = st.text_input("输入核心关键词", "人工智能")

    num_limit = st.slider("展示条数", 1, 20, 10)
    st.button("获取实时资讯", type="primary", key="run_btn")

# 3. 接口调用函数
def fetch_tian_data(mode, kw="", ar=""):
    endpoints = {
        "全网风向(全网热搜)": "https://apis.tianapi.com/networkhot/index",
        "垂直地区(地区新闻)": "https://apis.tianapi.com/areanews/index",
        "全域深度(互联网资讯)": "https://apis.tianapi.com/internet/index",
        "综合门户(综合新闻)": "https://apis.tianapi.com/generalnews/index"
    }
    params = {"key": TIAN_API_KEY, "num": 50}
    
    if mode == "垂直地区(地区新闻)":
        params["areaname"] = ar
        if kw: params["word"] = kw
    elif mode != "全网风向(全网热搜)":
        params["word"] = kw
        
    try:
        res = requests.get(endpoints[mode], params=params, timeout=10).json()
        return res
    except:
        return {"code": 500, "msg": "网络超时"}

# 4. 主逻辑渲染
if st.session_state.get("run_btn"):
    res = fetch_tian_data(search_mode, word, area)
    
    if res and res.get("code") == 200:
        news_list = res.get("result", {}).get("newslist", [])
        
        # --- 零过滤逻辑 ---
        # 如果是热搜或未设关键词的地区新闻，直接全量显示，不筛任何白名单
        display_list = news_list[:num_limit]
        
        if not display_list:
            st.warning("接口调取成功，但该路径暂无实时更新内容。")
        else:
            st.subheader(f"📍 当前路径：{search_mode}")
            for news in display_list:
                with st.container(border=True):
                    # 针对热搜接口的字段适配
                    title = news.get('title') or news.get('keyword') or "未知标题"
                    source = news.get('source') or ("全网实时热榜" if search_mode == "全网风向(全网热搜)" else "地方媒体")
                    desc = news.get('description') or news.get('digest') or f"实时关注关键词：{title}"
                    time = news.get('ctime') or "刚刚"
                    
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.write(f"**{source}**")
                        st.caption(time)
                        if search_mode == "全网风向(全网热搜)":
                            st.write("📈 **实时热度**")
                    with col2:
                        # 只有非热搜模式下才动用 AI 总结，节省资源且保持原汁原味
                        if search_mode == "全网风向(全网热搜)":
                            st.markdown(f"### {title}")
                            st.write(desc)
                        else:
                            try:
                                # AI 仅做极简提炼
                                summary = client.chat.completions.create(
                                    model="gpt-4o-mini",
                                    messages=[{"role": "user", "content": f"请用一句话概括：{title}。内容：{desc}"}]
                                ).choices[0].message.content
                                st.markdown(f"**{title}**")
                                st.info(summary)
                            except:
                                st.markdown(f"**{title}**")
                                st.write(desc)
                        
                        if news.get('url'):
                            st.markdown(f"🔗 [查看详情]({news['url']})")
    else:
        st.error(f"接口获取失败。错误码：{res.get('code')}，原因：{res.get('msg')}")
