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
    
    # 权威媒体白名单
    mainstream_keywords = ["新华", "澎湃", "人民网", "央视", "界面", "财新", "经济日报", "中国新闻网", "光明网", "中国证券报"]
    
    res = get_news_data(word, search_mode, area)
    
    # 1. 结构化检查：确保 res 是字典且包含 code
    if isinstance(res, dict) and res.get("code") == 250:
        st.warning(f"当前路径未检索到『{word}』相关深度结果，已为您切换至全局即时资讯...")
        res = get_news_data(word, "即时热点(国内新闻)")

    # 2. 核心修复：安全地提取数据，防止 KeyError
    if isinstance(res, dict) and res.get("code") == 200:
        # 使用 .get() 方式安全获取 result，如果不存在则返回空字典
        result_data = res.get("result", {})
        all_news = result_data.get("newslist", [])
        
        if not all_news:
            st.warning("接口连接成功，但暂无相关资讯内容，请稍后再试。")
            st.stop()
        
        # 筛选与重排逻辑
        high_quality_news = [n for n in all_news if any(m in n.get('source', '') for m in mainstream_keywords)]
        other_news = [n for n in all_news if n not in high_quality_news]
        final_list = (high_quality_news + other_news)[:num_limit]

        status_text.success(f"检索完成，正在生成分析简报：")

        for news in final_list:
            with st.container(border=True):
                # 兼容不同接口的字段名（解决地区新闻和热搜的差异）
                title = news.get('title') or news.get('keyword') or "无标题资讯"
                source = news.get('source') or "权威资讯源"
                content = news.get('description') or news.get('digest') or f"关键词『{title}』当前热度极高，正在全网发酵中。"
                ctime = news.get('ctime') or "实时"
                
                is_mainstream = any(m in source for m in mainstream_keywords)
                tag = "🔴【权威主流】" if is_mainstream else "⚪【动态资讯】"
                
                # AI 总结生成
                try:
                    prompt = f"你是一位新闻编辑。请根据以下素材写10字主标题、15字副标题和100字总结：\n来源：{source}\n标题：{title}\n内容：{content}"
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
                except Exception as ai_err:
                    st.error(f"AI 生成失败：{ai_err}")
        
        status_text.empty()
    else:
        # 处理接口明确报错的情况
        error_msg = res.get("msg") if isinstance(res, dict) else "未知连接错误"
        st.error(f"路径请求异常：{error_msg} (请检查该接口是否已在天行后台申请)")
