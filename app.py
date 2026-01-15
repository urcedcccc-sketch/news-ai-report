import streamlit as st
import requests
from openai import OpenAI

# 1. 密钥读取与安全检查
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    TIAN_API_KEY = st.secrets["TIAN_API_KEY"]
except Exception as e:
    st.error("密钥配置未就绪，请在 Streamlit Secrets 中检查。")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# 页面设置
st.set_page_config(page_title="高级新闻内参系统", layout="wide")
st.title("🗞️ 智能新闻检索与内参系统")

# 2. 侧边栏配置
with st.sidebar:
    st.header("检索设置")
    word = st.text_input("请输入核心关键词", "人工智能")
    num_limit = st.slider("最大生成篇数", 1, 10, 5)
    st.divider()
    st.caption("注：系统优先筛选新华社、澎湃等主流媒体。")
    btn = st.button("开始深度检索", type="primary")

# 3. 主逻辑
if btn:
    status_text = st.empty()
    status_text.info(f"正在全网扫描关于『{word}』的权威报道...")
    
    # 定义主流媒体关键词，用于排序筛选
    mainstream_keywords = ["新华", "澎湃", "人民网", "央视", "界面", "财新", "经济日报", "中国新闻网", "中国证券报"]
    
    # 请求天行“综合新闻”接口
    url = "https://apis.tianapi.com/generalnews/index"
    params = {"key": TIAN_API_KEY, "word": word, "num": 20} # 采样20篇以便筛选
    
    try:
        res = requests.get(url, params=params, timeout=15).json()
        
        # --- 保底逻辑：如果报错250（没搜到），自动获取今日国内热点 ---
        if res.get("code") == 250:
            st.warning(f"主流媒体暂无关于『{word}』的直接报道。已为您切换至今日最新权威内参：")
            res = requests.get("https://apis.tianapi.com/guonei/index", params={"key": TIAN_API_KEY, "num": num_limit}).json()

        if res.get("code") == 200:
            all_news = res["result"]["newslist"]
            
            # 分类：权威媒体排在前面
            high_quality_news = [n for n in all_news if any(m in n['source'] for m in mainstream_keywords)]
            other_news = [n for n in all_news if n not in high_quality_news]
            final_display_list = (high_quality_news + other_news)[:num_limit]

            status_text.success(f"精选总结已完成，以下为针对性分析：")

            for news in final_display_list:
                with st.container(border=True):
                    # 判别标签
                    is_mainstream = any(m in news['source'] for m in mainstream_keywords)
                    tag = "🔴【权威主流】" if is_mainstream else "⚪【门户转播】"
                    
                    # 调用 AI 编写内参
                    prompt = f"""
                    你现在是新华社资深编辑。请根据以下素材撰写一份内参简报。
                    要求：
                    1. 主标题：12字以内，需体现专业性。
                    2. 副标题：15字以内，点明核心事实（时间、地点、人物）。
                    3. 深度总结：100字左右，语言干练，像新闻通稿。
                    
                    素材内容：
                    标题：{news['title']}
                    来源：{news['source']}
                    描述：{news['description']}
                    """
                    
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3
                    )
                    
                    # 界面展示
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.write(f"**{news['source']}**")
                        st.caption(f"{news['ctime']}")
                        st.caption(tag)
                    with col2:
                        st.markdown(response.choices[0].message.content)
                        st.markdown(f"🔗 [查看原发报道]({news['url']})")
            
            status_text.empty()
        else:
            st.error(f"接口连接失败，请检查天行后台状态。错误信息：{res.get('msg')}")
            
    except Exception as e:
        st.error(f"系统运行超时，请尝试减少篇数或刷新页面。详情: {e}")
