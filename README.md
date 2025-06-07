# ATS_Resume_Analyzer
🎯 ATS Resume Analyzer is an AI-driven tool that compares your resume with job descriptions to enhance ATS compatibility. It identifies skill gaps, optimizes keywords, detects red flags, and provides a personalized improvement plan—helping job seekers increase their chances of getting shortlisted by making their resumes more relevant and impactful.

---

## ✨ Features

- 🔍 **Resume vs Job Match**: Calculates match score and skills alignment  
- ⚙️ **ATS Optimization**: Detects formatting and keyword issues  
- 📌 **Actionable Suggestions**: High-impact recommendations  
- 📄 **Reports**: Downloadable PDF and JSON outputs  
- 💻 **Simple Interface**: Built with Gradio for easy interaction

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- [Google AI API Key](https://makersuite.google.com/app/apikey)

### Installation

```bash
git clone https://github.com/HR-VijayKumar/ATS_Resume_Analyzer.git
cd ATS_Resume_Analyzer
pip install -r requirements.txt
```

## Setup .env

Create a .env file in the project root with your API key:

```bash
GOOGLE_API_KEY=your_google_api_key_here
```

## Run App

```bash
streamlit run app.py
```

## 📥 Usage

- Upload your PDF resume
- Paste a job description
- Click Analyze My Resume
- Download the PDF report or export JSON

