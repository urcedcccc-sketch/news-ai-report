import streamlit as st
import requests
from openai import OpenAI

# 密钥读取
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    TIAN_API_KEY = st.secrets["TIAN_API_KEY"]
except:
    st.error("请在 Streamlit 后台配置密钥")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

st.set_page_config(page_title="高级新闻内参", layout="wide")
st.title("🗞️ 智能新闻检索与编辑系统")

with st.sidebar:
    word = st.text_input("请输入核心关键词", "贺蛟龙")
    num = st.slider("获取篇数", 1, 10, 5)
    btn = st.button("全网深度检索", type="primary")

if btn:
    with st.spinner(f"正在深度检索关于『{word}』的高质量新闻..."):
        # 切换到天行数据中权限最高、范围最广的“互联网资讯”或“综合新闻”接口
        # 建议在天行后台同时申请“互联网资讯”接口，它的范围更偏向主流报道
        url = "https://apis.tianapi.com/generalnews/index" 
        params = {"key": TIAN_API_KEY, "word": word, "num": num}
        
        try:
            res = requests.get(url, params=params).json()
            
            if res.get("code") == 200:
                news_list = res["result"]["newslist"]
                for news in news_list:
                    # 提示词强化：要求 AI 模仿主流媒体编辑风格
                    prompt = f"""
                    你现在是新华社的资深新闻编辑。请阅读以下素材，撰写一份内参简报。
                    要求：
                    1. 主标题：10字左右，极具专业感。
                    2. 副标题：15字左右，点出核心事实（时间、地点、人物）。
                    3. 总结段落：80-100字，客观、干练，像新闻通稿。
                    
                    新闻素材：
                    标题：{news['title']}
                    来源：{news['source']}
                    摘要：{news['description']}
                    """
                    
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3 # 降低随机性，确保严谨
                    )
                    
                    # 页面呈现
                    with st.container():
                        col1, col2 = st.columns([1, 4])
                        with col1:
                            st.caption(f"📅 {news['ctime']}")
                            st.caption(f"📍 {news['source']}")
                        with col2:
                            st.markdown(response.choices[0].message.content)
                            st.markdown(f"🔗 [阅读原发报道]({news['url']})")
                        st.divider()
            else:
                st.warning(f"当前接口未找到相关深度报道，错误信息：{res.get('msg')}")
                st.info("提示：如果关键词非常冷门，建议尝试搜索其关联的机构或大事件名称。")
        except Exception as e:
            st.error(f"系统运行异常: {e}")
