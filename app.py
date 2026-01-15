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
    status_text = st.empty()
    status_text.info(f"正在全网检索关于『{word}』的主流媒体报道...")
    
    # 1. 增加搜索深度，一次抓取20篇，方便我们从中筛选主流媒体
    url = "https://apis.tianapi.com/generalnews/index"
    params = {"key": TIAN_API_KEY, "word": word, "num": 20}
    
    try:
        res = requests.get(url, params=params, timeout=15).json()
        
        if res.get("code") == 200:
            all_news = res["result"]["newslist"]
            
            # 2. 定义你想看到的主流媒体白名单
            mainstream_keywords = ["新华", "澎湃", "人民网", "央视", "界面", "财新", "经济日报", "中国新闻网"]
            
            # 将新闻分类：主流媒体排在前面，其他排在后面
            high_quality_news = [n for n in all_news if any(m in n['source'] for m in mainstream_keywords)]
            other_news = [n for n in all_news if n not in high_quality_news]
            
            # 合并结果，只取前 num_limit 篇展示
            final_list = (high_quality_news + other_news)[:num_limit]

            status_text.success(f"已深度检索{len(all_news)}篇资讯，正在为您精选总结...")

            for news in final_list:
                with st.container(border=True):
                    # 标记来源是否为权威媒体
                    source_tag = "🔴【权威主流媒体】" if news in high_quality_news else "⚪【门户转播】"
                    
                    # AI 提示词强化：要求模仿新华社/澎湃的社论风格
                    prompt = f"""
                    你是一位资深时政编辑。请根据以下素材撰写内参：
                    1. 主标题：12字以内，严肃专业。
                    2. 副标题：18字以内，包含核心人物/地点/事件。
                    3. 总结：100字左右，客观干练，体现新闻深度。
                    
                    素材来源：{news['source']}
                    素材标题：{news['title']}
                    素材内容：{news['description']}
                    """
                    
                    completion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3
                    )
                    
                    st.markdown(f"#### {news['title']}")
                    st.caption(f"{source_tag} | 来源：{news['source']} | 时间：{news['ctime']}")
                    st.write(completion.choices[0].message.content)
                    st.markdown(f"🔗 [阅读原发报道]({news['url']})")
            
            status_text.empty()
        else:
            st.error(f"检索失败：{res.get('msg')} (代码: {res.get('code')})")
            
    except Exception as e:
        st.error(f"深度检索超时，请稍后重试: {e}")
