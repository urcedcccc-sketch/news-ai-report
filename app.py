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
        # 强制使用“综合新闻”接口，请确保你在天行后台已申请该接口
        url = "https://apis.tianapi.com/generalnews/index"
        params = {
            "key": TIAN_API_KEY,
            "word": word,
            "num": num
        }
        
        try:
            response = requests.get(url, params=params)
            res_data = response.json()
            
            if res_data.get("code") == 200:
                news_list = res_data["result"]["newslist"]
                for news in news_list:
                    # AI 提示词优化
                    prompt = f"你是一位资深编辑。请根据以下内容生成：1.主标题(10字) 2.副标题(15字) 3.总结段落(100字以内)。内容如下：\n标题：{news['title']}\n描述：{news['description']}"
                    
                    completion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    
                    # 结果呈现
                    st.markdown(f"### {news['title']}") # 原标题作为备选
                    st.info(completion.choices[0].message.content)
                    st.markdown(f"🔗 [查看新闻原文]({news['url']})")
                    st.divider()
            else:
                # 这里会打印出天行返回的具体错误代码
                st.error(f"天行接口返回错误：{res_data.get('msg')} (代码: {res_data.get('code')})")
                st.warning("提示：请确认你已在天行后台申请了『综合新闻』接口，而不仅仅是『国内新闻』。")
        except Exception as e:
            st.error(f"程序运行异常: {e}")
