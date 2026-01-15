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
st.set_page_config(page_title="智能全域新闻内参系统", layout="wide")
st.title("🗞️ 智能全域新闻检索系统")

# 2. 侧边栏配置
with st.sidebar:
    st.header("检索设置")
    
    # 模式选择
    search_mode = st.radio(
        "检索源路径选择", 
        ["全网风向(全网热搜)", "垂直地区(地区新闻)", "全域深度(互联网资讯)", "综合门户(综合新闻)", "即时热点(国内新闻)"]
    )
    
    # 根据模式动态显示输入框
    word = ""
    area = ""
    if search_mode == "全网风向(全网热搜)":
        st.info("💡 该模式下无需输入关键词，将直接获取全网最新热议话题。")
    elif search_mode == "垂直地区(地区新闻)":
        area = st.text_input("指定地区(如: 新疆/广东/上海)", "新疆")
        word = st.text_input("关键词过滤(可选，留空则显示全地区新闻)", "")
    else:
        word = st.text_input("请输入核心关键词", "人工智能")

    num_limit = st.slider("页面展示篇数", 1, 10, 5)
    st.divider()
    st.caption("系统优化：针对热搜与地区新闻已开启‘直接透传’模式。")
    btn = st.button("开始执行检索", type="primary")

# 3. 核心检索函数
def get_news_data(api_word, mode, area_name=""):
    endpoints = {
        "全网风向(全网热搜)": "https://apis.tianapi.com/networkhot/index",
        "垂直地区(地区新闻)": "https://apis.tianapi.com/areanews/index",
        "全域深度(互联网资讯)": "https://apis.tianapi.com/internet/index",
        "综合门户(综合新闻)": "https://apis.tianapi.com/generalnews/index",
        "即时热点(国内新闻)": "https://apis.tianapi.com/guonei/index"
    }
    api_url = endpoints.get(mode)
    params = {"key": TIAN_API_KEY, "num": 50} # 统一缓存50篇
    
    # 参数分流
    if mode == "全网风向(全网热搜)":
        pass # 热搜不需要额外参数
    elif mode == "垂直地区(地区新闻)":
        params["areaname"] = area_name # 必须使用 areaname 参数
        if api_word: params["word"] = api_word
    elif "国内新闻" in mode:
        pass
    else:
        params["word"] = api_word
        
    try:
        response = requests.get(api_url, params=params, timeout=15).json()
        return response
    except Exception as e:
        return {"code": 500, "msg": f"网络异常: {str(e)}"}

# 4. 主逻辑
if btn:
    # 彻底修复变量未定义问题：在逻辑开始前赋予初始值
    res = None 
    status_text = st.empty()
    status_text.info(f"正在通过『{search_mode}』路径调取数据...")
    
    # 执行请求
    res = get_news_data(word, search_mode, area)
    
    # 5. 数据处理
    if isinstance(res, dict) and res.get("code") == 200:
        result_data = res.get("result", {})
        all_raw_news = result_data.get("newslist", [])
        
        # 针对热搜和地区新闻的“透传”逻辑
        if search_mode == "全网风向(全网热搜)":
            final_pool = all_raw_news # 不进行关键词过滤
        elif search_mode == "垂直地区(地区新闻)" and not word:
            final_pool = all_raw_news # 如果关键词为空，直接透传地区新闻
        elif word:
            # 仅在输入了关键词的情况下执行本地二次过滤
            final_pool = [n for n in all_raw_news if word.lower() in n.get('title', '').lower() or word.lower() in n.get('description', '').lower()]
            if not final_pool: final_pool = all_raw_news # 过滤太死则保底
        else:
            final_pool = all_raw_news

        # 权威媒体高亮名单
        mainstream = ["新华", "澎湃", "人民网", "央视", "环球", "界面", "财新", "石榴", "日报"]
        
        # 权重重排
        high_quality = [n for n in final_pool if any(m in n.get('source', '') for m in mainstream)]
        others = [n for n in final_pool if n not in high_quality]
        display_list = (high_quality + others)[:num_limit]

        if not display_list:
            st.warning("接口调取成功，但当前路径下暂无相关内容，请尝试其他检索源。")
        else:
            status_text.success("数据获取成功，已为您生成内参分析：")
            for news in display_list:
                with st.container(border=True):
                    # 字段兼容性处理
                    title = news.get('title') or news.get('keyword') or "无标题资讯"
                    source = news.get('source') or ("实时热搜" if search_mode == "全网风向(全网热搜)" else "权威资讯源")
                    content = news.get('description') or news.get('digest') or f"关键词『{title}』当前热度极高，正在持续发酵。"
                    ctime = news.get('ctime') or "实时更新"
                    
                    is_mainstream = any(m in source for m in mainstream)
                    tag = "🔴【权威主流】" if is_mainstream else "⚪【动态资讯】"
                    
                    # AI 分析生成
                    try:
                        prompt = f"你是一位新闻编辑。请写12字内主标题、15字内副标题和100字简洁总结：\n来源：{source}\n标题：{title}\n内容：{content}"
                        completion = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
                        
                        col1, col2 = st.columns([1, 4])
                        with col1:
                            st.write(f"**{source}**")
                            st.caption(ctime)
                            st.caption(tag)
                        with col2:
                            st.markdown(completion.choices[0].message.content)
                            if news.get('url'): st.markdown(f"🔗 [阅读原文]({news['url']})")
                    except:
                        st.write(f"**{title}** (总结生成服务繁忙)")
            status_text.empty()
    else:
        # 处理接口错误或数据为空
        error_msg = res.get("msg") if isinstance(res, dict) else "接口通讯故障"
        st.error(f"检索失败：{error_msg} (代码: {res.get('code') if isinstance(res, dict) else 'Unknown'})")
