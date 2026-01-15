import streamlit as st
import requests
from openai import OpenAI

# 1. 密钥初始化
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    TIAN_API_KEY = st.secrets["TIAN_API_KEY"]
except Exception as e:
    st.error("密钥配置未就绪，请在 Streamlit Secrets 中检查。")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# 页面设置
st.set_page_config(page_title="实时全域新闻内参系统", layout="wide")
st.title("🗞️ 实时全域新闻内参系统")

# 2. 侧边栏配置
with st.sidebar:
    st.header("检索设置")
    search_mode = st.radio(
        "检索源路径选择", 
        ["全网风向(全网热搜)", "垂直地区(地区新闻)", "全域深度(互联网资讯)", "综合门户(综合新闻)"]
    )
    
    word = ""
    area = ""
    if search_mode == "全网风向(全网热搜)":
        st.success("🔥 实时热搜模式：已自动连接全网热榜。")
    elif search_mode == "垂直地区(地区新闻)":
        area = st.text_input("指定地区", "新疆")
        word = st.text_input("在结果中筛选(可选)", "")
    else:
        word = st.text_input("输入核心关键词", "马斯克")

    num_limit = st.slider("展示篇数", 1, 20, 10)
    btn = st.button("获取实时资讯", type="primary")

# 3. 核心检索函数（优化参数逻辑）
def get_tian_api_data(mode, kw, ar):
    endpoints = {
        "全网风向(全网热搜)": "https://apis.tianapi.com/networkhot/index",
        "垂直地区(地区新闻)": "https://apis.tianapi.com/areanews/index",
        "全域深度(互联网资讯)": "https://apis.tianapi.com/internet/index",
        "综合门户(综合新闻)": "https://apis.tianapi.com/generalnews/index"
    }
    api_url = endpoints.get(mode)
    params = {"key": TIAN_API_KEY, "num": 50} # 获取较大数据池
    
    # 策略：针对不同接口严格限制参数，防止 250 错误
    if mode == "全网风向(全网热搜)":
        pass # 热搜不需要任何参数
    elif mode == "垂直地区(地区新闻)":
        params["areaname"] = ar # 仅传递地区名，不传递关键词，提高成功率
    else:
        params["word"] = kw
        
    try:
        return requests.get(api_url, params=params, timeout=10).json()
    except:
        return {"code": 500, "msg": "网络请求超时"}

# 4. 主渲染逻辑
if btn:
    status = st.empty()
    status.info(f"正在调取『{search_mode}』实时数据...")
    
    # 执行初次检索
    res = get_tian_api_data(search_mode, word, area)
    
    # 保底机制：如果精准检索无结果，尝试宽泛检索
    if res.get("code") == 250 and word:
        status.warning(f"精准检索未匹配，正在为您扩大扫描范围...")
        # 提取关键词的首个词进行保底尝试（例如“马斯克 访谈”变为“马斯克”）
        base_word = word.split()[0] if " " in word else word
        res = get_tian_api_data(search_mode, base_word, area)

    if res.get("code") == 200:
        raw_list = res.get("result", {}).get("newslist", [])
        
        # 本地筛选逻辑（仅在用户输入了过滤词时启用）
        if search_mode == "垂直地区(地区新闻)" and word:
            display_list = [n for n in raw_list if word.lower() in str(n).lower()][:num_limit]
            if not display_list: display_list = raw_list[:num_limit] # 筛选无果则显示全部
        else:
            display_list = raw_list[:num_limit]

        if not display_list:
            st.warning("接口数据暂时为空，请换个关键词或稍后再试。")
        else:
            status.success(f"实时数据获取成功（共 {len(display_list)} 条）")
            for news in display_list:
                with st.container(border=True):
                    # 字段自适应适配
                    title = news.get('title') or news.get('keyword') or "实时动态"
                    source = news.get('source') or "实时热榜"
                    content = news.get('description') or news.get('digest') or f"关注：{title}"
                    ctime = news.get('ctime') or "刚刚"
                    
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.write(f"**{source}**")
                        st.caption(ctime)
                    with col2:
                        # AI 处理逻辑
                        try:
                            # 仅对有内容的新闻进行简报，热搜词直接显示
                            if search_mode == "全网风向(全网热搜)":
                                st.markdown(f"### {title}")
                            else:
                                prompt = f"请根据素材写12字内标题和80字内内参总结：\n标题：{title}\n素材：{content}"
                                completion = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
                                st.markdown(f"**{title}**")
                                st.info(completion.choices[0].message.content)
                        except:
                            st.markdown(f"**{title}**")
                            st.write(content)
                        
                        if news.get('url'):
                            st.markdown(f"🔗 [查看详情]({news['url']})")
    else:
        st.error(f"接口获取失败。状态码：{res.get('code')}，原因：{res.get('msg')}")
