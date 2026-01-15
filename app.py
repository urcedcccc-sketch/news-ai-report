import streamlit as st
import requests
from openai import OpenAI

# 1. 密钥读取与初始化
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    TIAN_API_KEY = st.secrets["TIAN_API_KEY"]
except Exception as e:
    st.error("密钥配置错误，请检查 Streamlit Secrets")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

st.set_page_config(page_title="智能新闻专业版", layout="centered")
st.title("🗞️ 智能新闻检索系统")

# 2. 侧边栏配置
with st.sidebar:
    st.header("搜索设置")
    word = st.text_input("关键词", "贺蛟龙")
    num_limit = st.slider("篇数", 1, 5, 3) # 限制在5篇以内，防止超时白屏
    btn = st.button("生成简报", type="primary")

# 3. 主逻辑
if btn:
    status_text = st.empty() # 创建一个动态显示状态的占位符
    status_text.info(f"正在全网检索『{word}』相关资讯...")
    
    url = "https://apis.tianapi.com/generalnews/index"
    params = {"key": TIAN_API_KEY, "word": word, "num": num_limit}
    
    try:
        res = requests.get(url, params=params, timeout=10).json()
        
        # 关键词未搜到则自动切换到热点资讯
        if res.get("code") == 250:
            st.warning(f"暂无『{word}』的高匹配度新闻，为您推送今日热点资讯：")
            res = requests.get("https://apis.tianapi.com/guonei/index", params={"key": TIAN_API_KEY, "num": num_limit}).json()

        if res.get("code") == 200:
            status_text.success("数据获取成功，AI 正在编辑总结...")
            
            for news in res["result"]["newslist"]:
                # 使用带容器的排版，防止渲染白屏
                with st.container(border=True):
                    # AI 生成部分
                    prompt = f"请为以下新闻写一个10字主标题、15字副标题和80字以内专业总结：\n标题：{news['title']}\n来源：{news['source']}"
                    
                    try:
                        completion = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=300
                        )
                        ai_content = completion.choices[0].message.content
                        
                        # 结果展示
                        st.markdown(f"#### {news['title']}")
                        st.caption(f"来源：{news['source']} | 时间：{news['ctime']}")
                        st.write(ai_content)
                        st.markdown(f"[🔗 阅读全文]({news['url']})")
                    except Exception as ai_err:
                        st.error("AI 总结超时，请稍后重试")
            
            status_text.empty() # 完成后清除状态提示
        else:
            st.error(f"接口异常: {res.get('msg')}")
            
    except Exception as e:
        st.error(f"连接超时或系统异常: {e}")
