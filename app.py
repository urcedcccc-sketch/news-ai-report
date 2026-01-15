import streamlit as st
import requests
from openai import OpenAI

# 1. 密钥初始化
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    TIAN_API_KEY = st.secrets["TIAN_API_KEY"]
except Exception as e:
    st.error("密钥配置错误，请检查 Secrets。")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# 页面配置
st.set_page_config(page_title="实时全域新闻内参系统", layout="wide")
st.title("🗞️ 实时全域新闻内参系统")

# 2. 侧边栏配置
with st.sidebar:
    st.header("检索设置")
    search_mode = st.radio(
        "检索源路径选择", 
        ["全网风向(全网热搜)", "垂直地区(地区新闻)", "全域深度(互联网资讯)", "综合门户(综合新闻)"]
    )
    
    # 初始化变量
    word = ""
    area = ""
    
    if search_mode == "全网风向(全网热搜)":
        st.success("🔥 实时模式：自动连接全网热点。")
    elif search_mode == "垂直地区(地区新闻)":
        area = st.text_input("指定地区", "新疆")
        word = st.text_input("在结果中筛选(可选)", "")
    else:
        word = st.text_input("输入核心关键词", "马斯克")

    num_limit = st.slider("展示篇数", 1, 20, 10)
    btn = st.button("同步实时数据", type="primary")

# 3. 核心检索函数：严格物理隔离参数
def get_clean_data(mode, kw, ar):
    # 接口地址映射
    endpoints = {
        "全网风向(全网热搜)": "https://apis.tianapi.com/networkhot/index",
        "垂直地区(地区新闻)": "https://apis.tianapi.com/areanews/index",
        "全域深度(互联网资讯)": "https://apis.tianapi.com/internet/index",
        "综合门户(综合新闻)": "https://apis.tianapi.com/generalnews/index"
    }
    api_url = endpoints.get(mode)
    
    # 基础参数：只包含 Key 和数量
    base_params = {"key": TIAN_API_KEY, "num": 50}
    
    # --- 关键修复：根据模式严格构建参数字典，不留空键 ---
    if mode == "全网风向(全网热搜)":
        final_params = base_params # 绝对不传 word 或 areaname
    elif mode == "垂直地区(地区新闻)":
        final_params = base_params
        final_params["areaname"] = ar.strip() # 仅传地区
        # 即使有 kw 也不传给接口，留在本地代码过滤，防止接口报 250
    else:
        final_params = base_params
        final_params["word"] = kw.strip()
        
    try:
        response = requests.get(api_url, params=final_params, timeout=10)
        return response.json()
    except:
        return {"code": 500, "msg": "网络请求异常"}

# 4. 主渲染逻辑
if btn:
    status = st.empty()
    status.info(f"正在调取『{search_mode}』实时底层数据...")
    
    res = get_clean_data(search_mode, word, area)
    
    # 逻辑分流处理
    if res.get("code") == 200:
        raw_news = res.get("result", {}).get("newslist", [])
        
        # 本地二次过滤（仅针对有筛选需求的场景）
        if search_mode == "垂直地区(地区新闻)" and word:
            display_list = [n for n in raw_news if word.lower() in str(n).lower()]
            if not display_list: display_list = raw_news # 没搜到就给全部，不留白
        else:
            display_list = raw_news
            
        display_list = display_list[:num_limit]

        if not display_list:
            st.warning("接口返回数据为空。可能原因：该地区暂无新闻或天行库延迟。")
        else:
            status.success(f"同步成功：获取到 {len(display_list)} 条实时资讯")
            for news in display_list:
                with st.container(border=True):
                    # 字段兼容性适配
                    title = news.get('title') or news.get('keyword') or "实时动态"
                    source = news.get('source') or ("实时热搜" if search_mode == "全网风向(全网热搜)" else "资讯快报")
                    desc = news.get('description') or news.get('digest') or f"关键词: {title}"
                    
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.write(f"**{source}**")
                        st.caption(news.get('ctime', '刚刚'))
                    with col2:
                        # 只有在非热搜模式下且有描述时，才调用 AI，提高加载速度
                        if search_mode != "全网风向(全网热搜)" and len(desc) > 20:
                            try:
                                prompt = f"撰写12字内标题和80字内简报：\n标题：{title}\n素材：{desc}"
                                ai_res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
                                st.markdown(f"**{title}**")
                                st.info(ai_res.choices[0].message.content)
                            except:
                                st.markdown(f"**{title}**")
                                st.write(desc)
                        else:
                            st.markdown(f"### {title}")
                            st.write(desc)
                        
                        if news.get('url'): st.markdown(f"🔗 [阅读原文]({news['url']})")
    else:
        st.error(f"调取失败。代码：{res.get('code')}，信息：{res.get('msg')}")
