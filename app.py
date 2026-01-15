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

# 2. 侧边栏配置：增加“地区新闻”和“全网热搜”
with st.sidebar:
    st.header("检索设置")
    word = st.text_input("请输入核心关键词", "贺蛟龙")
    
    # 增加更多接口路径
    search_mode = st.radio(
        "检索源路径选择", 
        [
            "全域深度(互联网资讯)", 
            "综合门户(综合新闻)", 
            "即时热点(国内新闻)", 
            "垂直地区(地区新闻)", 
            "全网风向(全网热搜)"
        ]
    )
    
    # 如果选择地区新闻，增加一个省份/城市输入框
    area = ""
    if search_mode == "垂直地区(地区新闻)":
        area = st.text_input("指定地区(如: 广东/上海/深圳)", "北京")

    num_limit = st.slider("最大生成篇数", 1, 10, 5)
    st.divider()
    st.caption("系统已集成：互联网/综合/国内/地区/热搜 五大接口路径。")
    btn = st.button("开始跨路径检索", type="primary")

# 3. 核心检索函数：动态匹配你的所有天行接口
def get_news_data(api_word, mode, area_name=""):
    # 映射你拥有的所有天行接口
    endpoints = {
        "全域深度(互联网资讯)": "https://apis.tianapi.com/internet/index",
        "综合门户(综合新闻)": "https://apis.tianapi.com/generalnews/index",
        "即时热点(国内新闻)": "https://apis.tianapi.com/guonei/index",
        "垂直地区(地区新闻)": "https://apis.tianapi.com/areanews/index",
        "全网风向(全网热搜)": "https://apis.tianapi.com/networkhot/index"
    }
    api_url = endpoints.get(mode)
    
    # 基础参数
    params = {"key": TIAN_API_KEY, "num": 30} # 保持高采样率
    
    # 根据不同模式调整参数
    if mode == "垂直地区(地区新闻)":
        params["areaname"] = area_name
        # 地区新闻通常是展示该地区最新消息，有些版本不支持 word 过滤
    elif mode == "全网风向(全网热搜)":
        # 热搜接口通常不需要 word，返回的是当前全网最热列表
        pass
    elif "国内新闻" in mode:
        pass
    else:
        params["word"] = api_word
        
    try:
        response = requests.get(api_url, params=params, timeout=15).json()
        return response
    except:
        return {"code": 500, "msg": "网络连接超时"}

# 4. 主逻辑
if btn:
    status_text = st.empty()
    status_text.info(f"正在通过『{search_mode}』路径检索相关资讯...")
    
    # 定义主流权威媒体关键词
    mainstream_keywords = ["新华", "澎湃", "人民网", "央视", "界面", "财新", "经济日报", "中国新闻网", "光明网", "中国证券报"]
    
    res = get_news_data(word, search_mode, area)
    
    # 自动保底：如果特定搜索无结果，自动转为国内热点
    if res.get("code") == 250:
        st.warning(f"当前路径未检索到『{word}』深度结果，已为您切换至全局即时资讯...")
        res = get_news_data(word, "即时热点(国内新闻)")

    if res.get("code") == 200:
        all_news = res["result"]["newslist"]
        
        # 筛选逻辑
        high_quality_news = [n for n in all_news if any(m in n.get('source', '') for m in mainstream_keywords)]
        other_news = [n for n in all_news if n not in high_quality_news]
        final_list = (high_quality_news + other_news)[:num_limit]

        status_text.success(f"检索完成，正在生成内参简报：")

        for news in final_list:
            with st.container(border=True):
                # 处理不同接口字段名不一致的问题
                title = news.get('title') or news.get('keyword') or "无标题"
                source = news.get('source') or "全网热搜"
                content = news.get('description') or news.get('digest') or f"当前全网热议关键词：{title}"
                ctime = news.get('ctime') or "实时更新"
                
                is_mainstream = any(m in source for m in mainstream_keywords)
                tag = "🔴【权威主流】" if is_mainstream else "⚪【动态资讯】"
                
                # AI 提示词（针对不同来源自适应）
                prompt = f"""
                你是一位资深时政编辑。请根据以下素材撰写一份专业内参。
                1. 主标题：12字以内，严肃客观。
                2. 副标题：15字以内，点明事实。
                3. 总结：100字左右，通稿风格，逻辑清晰。
                
                素材来源：{source}
                素材标题：{title}
                素材内容：{content}
                """
                
                try:
                    completion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3
                    )
                    
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.write(f"**{source}**")
                        st.caption(ctime)
                        st.caption(tag)
                    with col2:
                        st.markdown(completion.choices[0].message.content)
                        if news.get('url'):
                            st.markdown(f"🔗 [查看原发报道]({news['url']})")
                except:
                    st.error("AI 总结服务暂时繁忙")
        
        status_text.empty()
    else:
        st.error(f"接口报错：{res.get('msg')} (代码: {res.get('code')})")
