import streamlit as st
import requests
from openai import OpenAI

# 密钥读取
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    TIAN_API_KEY = st.secrets["TIAN_API_KEY"]
except:
    st.error("请在 Streamlit 后台 Secrets 中配置密钥")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

st.title("🗞️ 智能新闻剪报 (正式版)")

with st.sidebar:
    word = st.text_input("输入检索关键词", "科技")
    num = st.sidebar.slider("生成篇数", 1, 5, 3)
    btn = st.button("开始生成报告", type="primary")

if btn:
    with st.spinner("正在检索并撰写总结..."):
        # 尝试使用综合新闻接口
        url = "https://apis.tianapi.com/generalnews/index"
        params = {"key": TIAN_API_KEY, "word": word, "num": num}
        
        try:
            res = requests.get(url, params=params).json()
            
            # 如果关键词搜不到(250)，我们自动切换到“国内新闻”列表，保证页面不空白
            if res.get("code") == 250:
                st.warning(f"未找到关于『{word}』的特定新闻，已为您转为获取最新热点资讯。")
                url = "https://apis.tianapi.com/guonei/index" # 切换到国内新闻接口
                res = requests.get(url, params={"key": TIAN_API_KEY, "num": num}).json()

            if res.get("code") == 200:
                for news in res["result"]["newslist"]:
                    prompt = f"请为以下新闻写一个10字主标题、15字副标题和100字以内的专业总结：\n标题：{news['title']}\n内容：{news['description']}"
                    
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    
                    st.subheader(news['title'])
                    st.info(response.choices[0].message.content)
                    st.markdown(f"🔗 [查看原文]({news['url']})")
                    st.divider()
            else:
                st.error(f"接口报错：{res.get('msg')} (代码: {res.get('code')})")
        except Exception as e:
            st.error(f"发生错误：{e}")
