import streamlit as st
import requests
from openai import OpenAI

# 1. 密钥读取与初始化
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    TIAN_API_KEY = st.secrets["TIAN_API_KEY"]
except Exception as e:
    st.error("密钥配置未就绪，请在 Streamlit Secrets 中检查。")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# 页面设置
st.set_page_config(page_title="高级全域新闻内参系统", layout="wide")
st.title("🗞️ 智能全域新闻检索系统")

# 2. 侧边栏配置
with st.sidebar:
    st.header("检索设置")
    word = st.text_input("请输入核心关键词", "贺蛟龙")
    
    search_mode = st.radio(
        "检索源路径选择", 
        ["全域深度(互联网资讯)", "综合门户(综合新闻)", "即时热点(国内新闻)", "垂直地区(地区新闻)", "全网风向(全网热搜)"]
    )
    
    area = ""
    if search_mode == "垂直地区(地区新闻)":
        area = st.text_input("指定地区(如: 新疆/广东/上海)", "新疆")

    num_limit = st.slider("页面展示篇数", 1, 10, 5)
    st.divider()
    st.caption("系统优化：单次扫描50篇，支持本地二次精准匹配。")
    btn = st.button("开始深度跨路径检索", type="primary")

# 3. 核心检索函数
def get_news_data(api_word, mode, area_name=""):
    endpoints = {
        "全域深度(互联网资讯)": "https://apis.tianapi.com/internet/index",
        "综合门户(综合新闻)": "https://apis.tianapi.com/generalnews/index",
        "即时热点(国内新闻)": "https://apis.tianapi.com/guonei/index",
        "垂直地区(地区新闻)": "https://apis.tianapi.com/areanews/index",
        "全网风向(全网热搜)": "https://apis.tianapi.com/networkhot/index"
    }
    api_url = endpoints.get(mode)
    params = {"key": TIAN_API_KEY, "num": 50}
    
    # 针对不同模式适配参数
    if mode == "垂直地区(地区新闻)":
        params["areaname"] = area_name # 关键修复：地区新闻必须使用 areaname
        if api_word and api_word != area_name:
            params["word"] = api_word
    elif mode == "全网风向(全网热搜)" or "国内新闻" in mode:
        pass
    else:
        params["word"] = api_word
        
    try:
        response = requests.get(api_url, params=params, timeout=15).json()
        return response
    except:
        return {"code": 500, "msg": "请求超时"}

# 4. 主逻辑
if btn:
    status_text = st.empty()
    status_text.info(f"正在全域扫描关于『{word}』的最新报道...")
    
    # 提前初始化 res 变量，防止 NameError
    res = {"code": 0, "msg": "未执行请求"}
    
    # 获取数据
    res = get_news_data(word, search_mode, area)
    
    # 如果特定搜索无结果，保底逻辑
    if isinstance(res, dict) and res.get("code") == 250:
        status_text.warning("当前路径未匹配到深度结果，正在尝试即时热点...")
        res = get_news_data(word, "即时热点(国内新闻)")

    # 处理结果
    if isinstance(res, dict) and res.get("code") == 200:
        all_raw_news = res.get("result", {}).get("newslist", [])
        
        # 二次筛选逻辑：如果输入了关键词且不等于地区名，则进行标题匹配
        if word and word != area:
            final_pool = [n for n in all_raw_news if word.lower() in n.get('title', '').lower() or word.lower() in n.get('description', '').lower()]
            if not final_pool: # 如果筛选后为空，展示原始前几条作为保底
                final_pool = all_raw_news
        else:
            final_pool = all_raw_news

        # 权威媒体白名单
        mainstream = ["新华", "澎湃", "人民网", "央视", "环球", "界面", "财新", "石榴", "新疆日报"]
        
        high_quality = [n for n in final_pool if any(m in n.get('source', '') for m in mainstream)]
        others = [n for n in final_pool if n not in high_quality]
        display_list = (high_quality + others)[:num_limit]

        if not display_list:
            st.warning("接口连接成功，但当前资讯流中暂无匹配内容。")
        else:
            status_text.success("精选内参生成完毕：")
            for news in display_list:
                with st.container(border=True):
                    title = news.get('title') or news.get('keyword') or "无标题"
                    source = news.get('source') or "权威资讯源"
                    content = news.get('description') or news.get('digest') or f"关键词『{title}』动态。"
                    
                    is_mainstream = any(m in source for m in mainstream)
                    tag = "🔴【权威/主流】" if is_mainstream else "⚪【动态资讯】"
                    
                    try:
                        prompt = f"撰写12字主标题、15字副标题和100字总结：\n来源：{source}\n标题：{title}\n内容：{content}"
                        completion = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
                        
                        col1, col2 = st.columns([1, 4])
                        with col1:
                            st.write(f"**{source}**")
                            st.caption(tag)
                        with col2:
                            st.markdown(completion.choices[0].message.content)
                            if news.get('url'): st.markdown(f"🔗 [查看原文]({news['url']})")
                    except:
                        st.write(f"**{title}** (总结生成失败)")
            status_text.empty()
    else:
        st.error(f"路径请求异常：{res.get('msg', '未知错误')}")
