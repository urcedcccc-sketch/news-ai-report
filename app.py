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
st.set_page_config(page_title="高级全网内参系统", layout="wide")
st.title("🗞️ 智能全域新闻检索系统")

# 2. 侧边栏配置
with st.sidebar:
    st.header("检索设置")
    word = st.text_input("请输入核心关键词", "贺蛟龙")
    
    # 允许用户选择检索模式，利用你拥有的不同接口
    search_mode = st.radio("检索源选择", ["全域深度(互联网资讯)", "综合门户(综合新闻)", "即时热点(国内新闻)"])
    
    num_limit = st.slider("最大生成篇数", 1, 10, 5)
    st.divider()
    st.caption("系统将优先筛选：新华社、澎湃新闻、人民网、央视新闻等。")
    btn = st.button("开始跨平台检索", type="primary")

# 3. 核心检索函数：根据你的 Key 权限动态切换接口
def get_news_data(api_word, mode):
    # 映射你的天行接口权限
    endpoints = {
        "全域深度(互联网资讯)": "https://apis.tianapi.com/internet/index",
        "综合门户(综合新闻)": "https://apis.tianapi.com/generalnews/index",
        "即时热点(国内新闻)": "https://apis.tianapi.com/guonei/index"
    }
    api_url = endpoints.get(mode)
    
    # 增加 num 到 30 篇，扩大筛选池以确保能筛出新华社/澎湃
    params = {"key": TIAN_API_KEY, "word": api_word, "num": 30}
    
    # 如果是国内新闻接口，不支持 word 参数，需特殊处理
    if "国内新闻" in mode:
        params.pop("word")
        
    try:
        response = requests.get(api_url, params=params, timeout=15).json()
        return response
    except:
        return {"code": 500, "msg": "网络连接超时"}

# 4. 主逻辑
if btn:
    status_text = st.empty()
    status_text.info(f"正在通过『{search_mode}』接口检索关于『{word}』的权威报道...")
    
    # 定义主流权威媒体关键词
    mainstream_keywords = ["新华", "澎湃", "人民网", "央视", "界面", "财新", "经济日报", "中国新闻网", "光明网", "中国证券报"]
    
    res = get_news_data(word, search_mode)
    
    # 保底逻辑：如果当前接口没搜到，自动尝试其他接口或返回热搜
    if res.get("code") == 250:
        st.warning(f"当前接口暂无『{word}』深度报道，正在为您检索全网即时热点...")
        res = get_news_data(word, "即时热点(国内新闻)")

    if res.get("code") == 200:
        all_news = res["result"]["newslist"]
        
        # 核心筛选逻辑：优先提取白名单中的媒体
        high_quality_news = [n for n in all_news if any(m in n['source'] for m in mainstream_keywords)]
        other_news = [n for n in all_news if n not in high_quality_news]
        
        # 重新组合：主流媒体置顶
        final_list = (high_quality_news + other_news)[:num_limit]

        status_text.success(f"已为您精选主流媒体报道：")

        for news in final_list:
            with st.container(border=True):
                is_mainstream = any(m in news['source'] for m in mainstream_keywords)
                tag = "🔴【权威主流】" if is_mainstream else "⚪【门户转播】"
                
                # AI 编写内参
                prompt = f"""
                你是一位资深时政编辑。请根据以下素材撰写一份专业内参。
                1. 主标题：12字以内，严肃客观。
                2. 副标题：15字以内，点明核心要素。
                3. 深度总结：100字左右，通稿风格。
                
                素材来源：{news['source']}
                素材标题：{news['title']}
                素材内容：{news['description']}
                """
                
                try:
                    completion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3
                    )
                    
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.write(f"**{news['source']}**")
                        st.caption(f"{news['ctime']}")
                        st.caption(tag)
                    with col2:
                        st.markdown(completion.choices[0].message.content)
                        st.markdown(f"🔗 [查看原发报道]({news['url']})")
                except:
                    st.error("AI 总结服务暂时繁忙")
        
        status_text.empty()
    else:
        st.error(f"接口报错：{res.get('msg')} (代码: {res.get('code')})")
