import streamlit as st
import tempfile
import os
import json
import re
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.document_loaders import Docx2txtLoader
from langchain_openai import ChatOpenAI

# 页面配置
st.set_page_config(
    page_title="AI简历分析助手",
    page_icon="📄",
    layout="wide"
)

# 标题
st.title("📄 AI简历分析助手")
st.markdown("上传简历PDF/Word，AI将自动提取关键信息、生成面试问题并给出评估建议")

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 配置")
    api_key = st.text_input("DeepSeek API Key", type="password", help="输入你的DeepSeek API Key")
    model_name = st.selectbox("模型", ["deepseek-chat", "deepseek-coder"], index=0)
    st.markdown("---")
    st.markdown("### 使用说明")
    st.markdown("""
    1. 输入DeepSeek API Key
    2. 上传简历（支持PDF/Word/TXT）
    3. 点击「开始分析」
    4. 查看候选人画像、匹配度评估和定制化面试问题
    """)

# 文件上传
uploaded_file = st.file_uploader(
    "选择简历文件",
    type=["pdf", "docx", "txt"],
    help="支持PDF、Word、TXT格式"
)

# 更简化的Prompt模板（让模型更容易遵循）
RESUME_ANALYSIS_PROMPT = """
你是一位资深招聘专家。请分析以下简历，并按要求输出。

【简历内容】
{resume_text}

【输出要求】
请用中文输出，严格按照以下格式，不要输出任何其他内容：

候选人姓名：xxx
工作年限：x年
当前职位：xxx
最高学历：xxx
关键技能：技能1、技能2、技能3、技能4、技能5

优势：
- 优势1
- 优势2
- 优势3

待提升点：
- 待提升点1
- 待提升点2

综合评分：xx/100
技术匹配度：xxx
经验匹配度：xxx

面试问题：
1. xxx
2. xxx
3. xxx
4. xxx
5. xxx

综合建议：xxx
"""

def extract_text_from_file(uploaded_file):
    """从上传的文件中提取文本"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        if uploaded_file.name.endswith('.pdf'):
            loader = PyPDFLoader(tmp_path)
            pages = loader.load()
            text = "\n".join([page.page_content for page in pages])
        elif uploaded_file.name.endswith('.docx'):
            loader = Docx2txtLoader(tmp_path)
            docs = loader.load()
            text = "\n".join([doc.page_content for doc in docs])
        else:
            loader = TextLoader(tmp_path, encoding='utf-8')
            docs = loader.load()
            text = "\n".join([doc.page_content for doc in docs])
    finally:
        os.unlink(tmp_path)
    
    return text

def analyze_resume(resume_text, api_key, model_name):
    """调用大模型分析简历"""
    llm = ChatOpenAI(
        openai_api_key=api_key,
        openai_api_base="https://api.deepseek.com/v1",
        model_name=model_name,
        temperature=0.3,
        max_tokens=4096
    )
    
    prompt = RESUME_ANALYSIS_PROMPT.format(resume_text=resume_text[:20000])
    
    response = llm.invoke(prompt)
    return response.content

def parse_analysis_result(text):
    """解析模型返回的文本，提取结构化信息"""
    result = {
        "candidate_profile": {
            "name": "未知",
            "years_of_experience": "未知",
            "current_title": "未知",
            "education": "未知",
            "key_skills": []
        },
        "strengths": [],
        "weaknesses_or_gaps": [],
        "match_assessment": {
            "overall_score": "未知",
            "technical_match": "未知",
            "experience_match": "未知"
        },
        "interview_questions": [],
        "recommendation": "未知"
    }
    
    # 提取姓名
    name_match = re.search(r'候选人姓名[：:]\s*(.+?)(?:\n|$)', text)
    if name_match:
        result["candidate_profile"]["name"] = name_match.group(1).strip()
    
    # 提取工作年限
    exp_match = re.search(r'工作年限[：:]\s*(\d+)', text)
    if exp_match:
        result["candidate_profile"]["years_of_experience"] = exp_match.group(1)
    
    # 提取当前职位
    title_match = re.search(r'当前职位[：:]\s*(.+?)(?:\n|$)', text)
    if title_match:
        result["candidate_profile"]["current_title"] = title_match.group(1).strip()
    
    # 提取最高学历
    edu_match = re.search(r'最高学历[：:]\s*(.+?)(?:\n|$)', text)
    if edu_match:
        result["candidate_profile"]["education"] = edu_match.group(1).strip()
    
    # 提取关键技能
    skills_match = re.search(r'关键技能[：:]\s*(.+?)(?:\n|$)', text)
    if skills_match:
        skills_str = skills_match.group(1).strip()
        result["candidate_profile"]["key_skills"] = [s.strip() for s in re.split(r'[、，,]', skills_str) if s.strip()]
    
    # 提取优势
    strengths_section = re.search(r'优势[：:]\s*(.*?)(?=待提升点|$)', text, re.DOTALL)
    if strengths_section:
        strengths_text = strengths_section.group(1)
        result["strengths"] = [s.strip().lstrip('-•*').strip() for s in strengths_text.strip().split('\n') if s.strip() and not s.strip().startswith('待提升')]
    
    # 提取待提升点
    weaknesses_section = re.search(r'待提升点[：:]\s*(.*?)(?=综合评分|面试问题|$)', text, re.DOTALL)
    if weaknesses_section:
        weaknesses_text = weaknesses_section.group(1)
        result["weaknesses_or_gaps"] = [w.strip().lstrip('-•*').strip() for w in weaknesses_text.strip().split('\n') if w.strip()]
    
    # 提取综合评分
    score_match = re.search(r'综合评分[：:]\s*(\d+)', text)
    if score_match:
        result["match_assessment"]["overall_score"] = score_match.group(1)
    
    # 提取技术匹配度
    tech_match = re.search(r'技术匹配度[：:]\s*(.+?)(?:\n|$)', text)
    if tech_match:
        result["match_assessment"]["technical_match"] = tech_match.group(1).strip()
    
    # 提取经验匹配度
    exp_match = re.search(r'经验匹配度[：:]\s*(.+?)(?:\n|$)', text)
    if exp_match:
        result["match_assessment"]["experience_match"] = exp_match.group(1).strip()
    
    # 提取面试问题
    questions_section = re.search(r'面试问题[：:]\s*(.*?)(?=综合建议|$)', text, re.DOTALL)
    if questions_section:
        questions_text = questions_section.group(1)
        questions = []
        for line in questions_text.strip().split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                q = re.sub(r'^\d+[\.、]\s*', '', line)
                q = q.lstrip('-•*').strip()
                if q:
                    questions.append(q)
        result["interview_questions"] = questions[:5]
    
    # 提取综合建议
    rec_match = re.search(r'综合建议[：:]\s*(.+?)(?:\n|$)', text, re.DOTALL)
    if rec_match:
        result["recommendation"] = rec_match.group(1).strip()
    
    return result

# 分析按钮
if uploaded_file is not None and api_key:
    if st.button("🚀 开始分析", type="primary"):
        with st.spinner("正在解析简历..."):
            resume_text = extract_text_from_file(uploaded_file)
            st.success(f"✅ 文本提取成功，共 {len(resume_text)} 字符")
        
        with st.spinner("AI正在分析中...（可能需要10-20秒）"):
            raw_result = analyze_resume(resume_text, api_key, model_name)
            result = parse_analysis_result(raw_result)
        
        # 展示结果
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("👤 候选人画像")
            profile = result.get("candidate_profile", {})
            st.markdown(f"""
            - **姓名**：{profile.get('name', '未知')}
            - **工作年限**：{profile.get('years_of_experience', '未知')}年
            - **当前职位**：{profile.get('current_title', '未知')}
            - **教育背景**：{profile.get('education', '未知')}
            """)
            
            skills = profile.get('key_skills', [])
            if skills:
                st.markdown("**关键技能**：" + "、".join(skills))
            else:
                st.markdown("**关键技能**：暂无")
            
            st.subheader("✅ 优势")
            for s in result.get("strengths", []):
                if s:
                    st.markdown(f"- {s}")
            
            st.subheader("⚠️ 待提升点")
            for w in result.get("weaknesses_or_gaps", []):
                if w:
                    st.markdown(f"- {w}")
        
        with col2:
            st.subheader("📊 匹配度评估")
            assessment = result.get("match_assessment", {})
            score = assessment.get('overall_score', '?')
            st.metric("综合评分", f"{score}/100")
            st.markdown(f"**技术匹配**：{assessment.get('technical_match', '暂无')}")
            st.markdown(f"**经验匹配**：{assessment.get('experience_match', '暂无')}")
            
            st.subheader("💡 综合建议")
            st.info(result.get("recommendation", "暂无"))
        
        st.subheader("🎯 定制化面试问题")
        questions = result.get("interview_questions", [])
        if questions:
            for i, q in enumerate(questions, 1):
                if q:
                    st.markdown(f"**{i}.** {q}")
        else:
            st.info("暂无面试问题，请检查简历内容是否完整")
        
        # 可选：显示原始返回内容（用于调试）
        with st.expander("查看AI原始返回内容"):
            st.text(raw_result)
            
elif uploaded_file and not api_key:
    st.warning("请先在侧边栏输入DeepSeek API Key")
elif not uploaded_file:
    st.info("请上传一份简历文件开始体验")

st.markdown("---")
st.markdown("💡 **提示**：本工具适用于简历初筛阶段，建议结合人工判断使用")