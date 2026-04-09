# AI简历分析助手

一键上传简历，AI自动生成候选人画像、匹配度评估和定制化面试问题。

## 在线体验
https://resume-assistant.streamlit.app

## 功能
- 支持 PDF/Word/TXT 格式
- 自动提取姓名、工作年限、关键技能
- 评估优势、待提升点
- 生成5个定制化面试问题
- 用户自己输入 API Key，保护隐私

## 技术栈
- Streamlit（前端）
- LangChain（文档解析）
- DeepSeek API（大模型）
- FAISS（向量检索）

## 本地运行
pip install -r requirements.txt
streamlit run resume_assistant.py
