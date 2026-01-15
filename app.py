import streamlit as st
import requests
from openai import OpenAI

# 1. 密钥读取
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    TIAN_API_KEY = st.secrets["TIAN_API_KEY"]
except:
    st.error("请在 Streamlit 后台 Secrets 中配置 OPENAI_API_KEY 和 TIAN_API_KEY")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

st.title("🗞️ 智能新闻剪报 (天行版)")

# 2. 侧边栏配置
with st.sidebar:
    word = st.text_input("搜索关键词", "人工智能")
    num = st.slider("篇数", 1, 10, 5)
    btn = st.button("开始生成")

if btn:
    with st.spinner("正在获取并总结新闻..."):
        # 使用“综合新闻”接口，支持关键词搜索
        url = "https://apis.tianapi.com/generalnews/index"
        params = {
            "key": TIAN_API_KEY,
            "word": word,
            "num": num
        }
        
        try:
            res = requests.get(url, params=params).json()
            if res.get("code") == 200:
                for item in res["result"]["newslist"]:
                    # AI 总结逻辑
                    prompt = f"请为以下新闻写一个10字主标题、15字副标题和100字以内的专业总结：\n标题：{item['title']}\n内容：{item['description']}"
                    
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    
                    # 展示结果
                    st.subheader(item['title'])
                    st.write(response.choices[0].message.content)
                    st.markdown(f"[🔗 阅读全文]({item['url']})")
                    st.divider()
            else:
                st.error(f"接口报错：{res.get('msg')}")
        except Exception as e:
            st.error(f"发生错误：{e}")
