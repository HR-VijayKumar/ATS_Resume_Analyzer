import google.generativeai as genai
import PyPDF2 as pdf
import json

def configure_genai(api_key):
    """Configure the Generative AI API with error handling."""
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        raise Exception(f"Failed to configure Generative AI: {str(e)}")
    

def get_gemini_response(prompt):
    """Generate a response using Gemini with enhanced error handling and response validation."""
    try:
        model = genai.GenerativeModel('models/gemini-2.0-flash-lite-preview')
        response = model.generate_content(prompt)
        
        # Ensure response is not empty
        if not response or not response.text:
            raise Exception("Empty response received from Gemini")
            
        # Try to parse the response as JSON
        try:
            response_json = json.loads(response.text)
            
            # Validate required fields
            required_fields = ["JD Match", "MissingKeywords", "Profile Summary", 
                             "SkillsAlignment", "ExperienceMatch", "Recommendations", "ATSScore"]
            for field in required_fields:
                if field not in response_json:
                    raise ValueError(f"Missing required field: {field}")
                    
            return response.text
            
        except json.JSONDecodeError:
            # If response is not valid JSON, try to extract JSON-like content
            import re
            json_pattern = r'\{.*\}'
            match = re.search(json_pattern, response.text, re.DOTALL)
            if match:
                return match.group()
            else:
                raise Exception("Could not extract valid JSON response")
                
    except Exception as e:
        raise Exception(f"Error generating response: {str(e)}")

def extract_pdf_text(uploaded_file):
    """Extract text from PDF with enhanced error handling."""
    try:
        reader = pdf.PdfReader(uploaded_file)
        if len(reader.pages) == 0:
            raise Exception("PDF file is empty")
            
        text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
                
        if not text:
            raise Exception("No text could be extracted from the PDF")
            
        return " ".join(text)
        
    except Exception as e:
        raise Exception(f"Error extracting PDF text: {str(e)}")
    

def prepare_prompt(resume_text, job_description):
    """Prepare the input prompt with improved structure and validation."""
    if not resume_text or not job_description:
        raise ValueError("Resume text and job description cannot be empty")
        
    prompt_template = """
    Act as a senior ATS (Applicant Tracking System) specialist and career consultant with 15+ years of experience in:
    - Technical recruitment and talent acquisition
    - Software engineering, DevOps, and cloud technologies
    - Data science, machine learning, and AI
    - Data analysis and business intelligence
    - Big data engineering and distributed systems
    - Product management and technical leadership
    
    You understand how modern ATS systems work, including keyword matching algorithms, 
    semantic analysis, and ranking mechanisms used by companies like Google, Amazon, Microsoft, and Fortune 500 firms.
    
    ANALYSIS TASK:
    Perform a comprehensive evaluation of the following resume against the job description. 
    Consider the highly competitive job market and provide actionable insights for optimization.
    
    RESUME CONTENT:
    {resume_text}
    
    JOB DESCRIPTION:
    {job_description}
    
    EVALUATION CRITERIA:
    1. Keyword density and relevance matching
    2. Skills alignment with job requirements
    3. Experience level and domain expertise
    4. Education and certification relevance
    5. ATS-friendliness (formatting, structure, parsing)
    6. Achievement quantification and impact demonstration
    7. Industry-specific terminology usage
    8. Role progression and career trajectory
    
    Provide your analysis in the following JSON format ONLY (no additional text):
    {{
        "JD Match": "percentage score between 0-100 with brief justification",
        "ATSScore": "ATS parsing and keyword optimization score (0-100)",
        "MissingKeywords": [
            "critical technical keywords not found in resume",
            "include both hard and soft skills",
            "prioritize by importance to the role"
        ],
        "SkillsAlignment": {{
            "MatchedSkills": ["skills that align well with JD"],
            "PartiallyMatched": ["skills with some relevance"],
            "GapAnalysis": "detailed analysis of skill gaps"
        }},
        "ExperienceMatch": {{
            "RelevantExperience": "assessment of relevant experience years and domains",
            "LevelAlignment": "junior/mid/senior level match analysis",
            "IndustryFit": "industry background compatibility assessment"
        }},
        "Profile Summary": "comprehensive 3-4 sentence analysis covering overall match quality, strongest selling points, and competitive positioning",
        "Recommendations": {{
            "HighPriority": [
                "most critical improvements for immediate implementation",
                "focus on top 3-5 actionable items"
            ],
            "MediumPriority": [
                "important enhancements for better positioning",
                "include formatting and structure improvements"
            ],
            "KeywordOptimization": [
                "specific phrases and terms to incorporate naturally",
                "suggest placement strategies (summary, skills, experience)"
            ],
            "QuantificationOpportunities": [
                "areas where metrics and numbers should be added",
                "suggest specific types of achievements to highlight"
            ]
        }},
        "RedFlags": [
            "potential issues that might cause automatic rejection",
            "formatting or content problems for ATS parsing"
        ],
        "CompetitiveAdvantage": "unique strengths and differentiators to emphasize"
    }}
    
    IMPORTANT NOTES:
    - Be specific and actionable in recommendations
    - Consider both ATS optimization and human reviewer appeal
    - Focus on realistic improvements rather than complete rewrites
    - Prioritize changes that provide maximum impact
    - Consider current market trends and in-demand skills
    """
    
    return prompt_template.format(
        resume_text=resume_text.strip(),
        job_description=job_description.strip()
    )

# Additional utility function for post-processing results
def process_ats_results(response_json):
    """Process and validate ATS analysis results."""
    try:
        data = json.loads(response_json) if isinstance(response_json, str) else response_json
        
        # Validate score ranges
        for score_field in ['JD Match', 'ATSScore']:
            if score_field in data:
                # Extract numeric value if it's a string with description
                score_text = str(data[score_field])
                score_value = int(''.join(filter(str.isdigit, score_text.split()[0])))
                if not 0 <= score_value <= 100:
                    raise ValueError(f"{score_field} must be between 0-100")
        
        return data
        
    except Exception as e:
        raise Exception(f"Error processing ATS results: {str(e)}")

# Function to generate improvement action plan
def generate_action_plan(ats_results):
    """Generate a prioritized action plan based on ATS analysis."""
    try:
        data = json.loads(ats_results) if isinstance(ats_results, str) else ats_results
        
        action_plan = {
            "immediate_actions": data.get("Recommendations", {}).get("HighPriority", []),
            "keyword_integration": data.get("Recommendations", {}).get("KeywordOptimization", []),
            "missing_keywords": data.get("MissingKeywords", []),
            "skill_gaps": data.get("SkillsAlignment", {}).get("GapAnalysis", ""),
            "red_flags_to_fix": data.get("RedFlags", []),
            "competitive_edge": data.get("CompetitiveAdvantage", "")
        }
        
        return action_plan
        
    except Exception as e:
        raise Exception(f"Error generating action plan: {str(e)}")