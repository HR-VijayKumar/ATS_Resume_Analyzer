import streamlit as st
from streamlit_extras.add_vertical_space import add_vertical_space
import os
import json
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.colors import black, red, green, orange, blue, grey
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from datetime import datetime
import io
from ats_analyser import (
    configure_genai, 
    get_gemini_response, 
    extract_pdf_text, 
    prepare_prompt,
    process_ats_results,
    generate_action_plan
)

def init_session_state():
    """Initialize session state variables."""
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    if 'show_detailed_view' not in st.session_state:
        st.session_state.show_detailed_view = False

def display_score_card(match_score, ats_score):
    """Display score cards with color coding."""
    col1, col2 = st.columns(2)
    
    with col1:
        # Extract numeric value from match score
        match_num = int(''.join(filter(str.isdigit, str(match_score).split()[0]))) if match_score != "N/A" else 0
        match_color = "green" if match_num >= 70 else "orange" if match_num >= 50 else "red"
        st.metric(
            label="📊 Job Match Score", 
            value=f"{match_num}%",
            help="Overall compatibility with job requirements"
        )
    
    with col2:
        # Extract numeric value from ATS score
        ats_num = int(''.join(filter(str.isdigit, str(ats_score).split()[0]))) if ats_score != "N/A" else 0
        ats_color = "green" if ats_num >= 80 else "orange" if ats_num >= 60 else "red"
        st.metric(
            label="🤖 ATS Optimization Score", 
            value=f"{ats_num}%",
            help="How well your resume will be parsed by ATS systems"
        )

def display_skills_analysis(skills_data):
    """Display detailed skills alignment analysis."""
    st.subheader("🎯 Skills Analysis")
    
    if isinstance(skills_data, dict):
        # Matched Skills
        matched_skills = skills_data.get("MatchedSkills", [])
        if matched_skills:
            st.success("✅ **Well-Matched Skills:**")
            st.write(", ".join(matched_skills))
        
        add_vertical_space(1)
        
        # Partially Matched Skills
        partial_skills = skills_data.get("PartiallyMatched", [])
        if partial_skills:
            st.warning("⚠️ **Partially Matched Skills:**")
            st.write(", ".join(partial_skills))
        
        add_vertical_space(1)
        
        # Gap Analysis
        gap_analysis = skills_data.get("GapAnalysis", "")
        if gap_analysis:
            st.info("📋 **Skill Gap Analysis:**")
            st.write(gap_analysis)
    else:
        st.write("Skills analysis data not available")

def display_experience_match(experience_data):
    """Display experience matching analysis."""
    st.subheader("💼 Experience Analysis")
    
    if isinstance(experience_data, dict):
        col1, col2 = st.columns(2)
        
        with col1:
            relevant_exp = experience_data.get("RelevantExperience", "Not specified")
            st.info(f"**Relevant Experience:** {relevant_exp}")
            
            level_alignment = experience_data.get("LevelAlignment", "Not specified")
            st.info(f"**Level Match:** {level_alignment}")
        
        with col2:
            industry_fit = experience_data.get("IndustryFit", "Not specified")
            st.info(f"**Industry Fit:** {industry_fit}")
    else:
        st.write("Experience analysis data not available")

def display_recommendations(recommendations_data):
    """Display prioritized recommendations."""
    st.subheader("🚀 Improvement Recommendations")
    
    if isinstance(recommendations_data, dict):
        # High Priority Recommendations
        high_priority = recommendations_data.get("HighPriority", [])
        if high_priority:
            st.error("🔥 **High Priority Actions:**")
            for i, rec in enumerate(high_priority, 1):
                st.write(f"{i}. {rec}")
        
        add_vertical_space(1)
        
        # Medium Priority Recommendations
        medium_priority = recommendations_data.get("MediumPriority", [])
        if medium_priority:
            st.warning("📈 **Medium Priority Improvements:**")
            for i, rec in enumerate(medium_priority, 1):
                st.write(f"{i}. {rec}")
        
        add_vertical_space(1)
        
        # Keyword Optimization
        keyword_opt = recommendations_data.get("KeywordOptimization", [])
        if keyword_opt:
            st.info("🔍 **Keyword Optimization Tips:**")
            for i, tip in enumerate(keyword_opt, 1):
                st.write(f"{i}. {tip}")
        
        add_vertical_space(1)
        
        # Quantification Opportunities
        quant_ops = recommendations_data.get("QuantificationOpportunities", [])
        if quant_ops:
            st.success("📊 **Add Numbers & Metrics:**")
            for i, opp in enumerate(quant_ops, 1):
                st.write(f"{i}. {opp}")
    else:
        st.write("Recommendations data not available")

def display_red_flags(red_flags):
    """Display potential red flags."""
    if red_flags:
        st.subheader("⚠️ Red Flags to Address")
        st.error("**Issues that might cause automatic rejection:**")
        for i, flag in enumerate(red_flags, 1):
            st.write(f"{i}. {flag}")

def display_competitive_advantage(advantage):
    """Display competitive advantages."""
    if advantage:
        st.subheader("💪 Your Competitive Edge")
        st.success(f"**Unique Strengths:** {advantage}")

def display_action_plan(action_plan):
    """Display the generated action plan."""
    st.subheader("📋 Your Action Plan")
    
    # Immediate Actions
    immediate = action_plan.get("immediate_actions", [])
    if immediate:
        st.error("🚨 **Do This First:**")
        for action in immediate:
            st.write(f"• {action}")
    
    add_vertical_space(1)
    
    # Missing Keywords
    missing_kw = action_plan.get("missing_keywords", [])
    if missing_kw:
        st.warning("🔑 **Keywords to Add:**")
        st.write(", ".join(missing_kw))
    
    add_vertical_space(1)
    
    # Red Flags
    red_flags = action_plan.get("red_flags_to_fix", [])
    if red_flags:
        st.error("🛑 **Fix These Issues:**")
        for flag in red_flags:
            st.write(f"• {flag}")

def generate_pdf_report(results, action_plan=None):
    """Generate a well-structured PDF report from analysis results."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, 
                           topMargin=72, bottomMargin=18)
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=blue,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=black,
        leftIndent=0
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=14,
        spaceAfter=8,
        textColor=blue,
        leftIndent=0
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8,
        alignment=TA_JUSTIFY
    )
    
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=4,
        leftIndent=20,
        bulletIndent=10
    )
    
    # Build PDF content
    story = []
    
    # Header
    story.append(Paragraph("ATS Resume Analysis Report", title_style))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", 
                          styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Executive Summary
    story.append(Paragraph("Executive Summary", heading_style))
    profile_summary = results.get("Profile Summary", "No summary available")
    story.append(Paragraph(profile_summary, body_style))
    story.append(Spacer(1, 15))
    
    # Score Summary Table
    story.append(Paragraph("Score Summary", heading_style))
    
    # Extract numeric scores
    match_score = results.get("JD Match", "N/A")
    ats_score = results.get("ATSScore", "N/A")
    
    match_num = int(''.join(filter(str.isdigit, str(match_score).split()[0]))) if match_score != "N/A" else 0
    ats_num = int(''.join(filter(str.isdigit, str(ats_score).split()[0]))) if ats_score != "N/A" else 0
    
    score_data = [
        ['Metric', 'Score', 'Status'],
        ['Job Description Match', f'{match_num}%', 'Excellent' if match_num >= 70 else 'Good' if match_num >= 50 else 'Needs Improvement'],
        ['ATS Optimization Score', f'{ats_num}%', 'Excellent' if ats_num >= 80 else 'Good' if ats_num >= 60 else 'Needs Improvement']
    ]
    
    score_table = Table(score_data, colWidths=[2.5*inch, 1*inch, 1.5*inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), 'white'),
        ('GRID', (0, 0), (-1, -1), 1, black)
    ]))
    
    story.append(score_table)
    story.append(Spacer(1, 20))
    
    # Skills Analysis
    skills_data = results.get("SkillsAlignment", {})
    if isinstance(skills_data, dict):
        story.append(Paragraph("Skills Analysis", heading_style))
        
        matched_skills = skills_data.get("MatchedSkills", [])
        if matched_skills:
            story.append(Paragraph("Well-Matched Skills:", subheading_style))
            story.append(Paragraph(", ".join(matched_skills), body_style))
            story.append(Spacer(1, 8))
        
        partial_skills = skills_data.get("PartiallyMatched", [])
        if partial_skills:
            story.append(Paragraph("Partially Matched Skills:", subheading_style))
            story.append(Paragraph(", ".join(partial_skills), body_style))
            story.append(Spacer(1, 8))
        
        gap_analysis = skills_data.get("GapAnalysis", "")
        if gap_analysis:
            story.append(Paragraph("Skill Gap Analysis:", subheading_style))
            story.append(Paragraph(gap_analysis, body_style))
        
        story.append(Spacer(1, 15))
    
    # Experience Analysis
    experience_data = results.get("ExperienceMatch", {})
    if isinstance(experience_data, dict):
        story.append(Paragraph("Experience Analysis", heading_style))
        
        # Create table data with proper text wrapping
        exp_data = [
            ['Aspect', 'Assessment'],
            [Paragraph('Relevant Experience', bullet_style), 
             Paragraph(experience_data.get("RelevantExperience", "Not specified"), body_style)],
            [Paragraph('Level Alignment', bullet_style), 
             Paragraph(experience_data.get("LevelAlignment", "Not specified"), body_style)],
            [Paragraph('Industry Fit', bullet_style), 
             Paragraph(experience_data.get("IndustryFit", "Not specified"), body_style)]
        ]
        
        exp_table = Table(exp_data, colWidths=[1.8*inch, 3.7*inch])
        exp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), 'white'),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('WORDWRAP', (0, 0), (-1, -1), 'LTR')
        ]))
        
        story.append(exp_table)
        story.append(Spacer(1, 15))
    
    # Missing Keywords
    missing_keywords = results.get("MissingKeywords", [])
    if missing_keywords:
        story.append(Paragraph("Missing Keywords", heading_style))
        story.append(Paragraph("The following keywords should be added to improve your resume's ATS compatibility:", body_style))
        for keyword in missing_keywords:
            story.append(Paragraph(f"• {keyword}", bullet_style))
        story.append(Spacer(1, 15))
    
    # Recommendations
    recommendations_data = results.get("Recommendations", {})
    if isinstance(recommendations_data, dict):
        story.append(Paragraph("Improvement Recommendations", heading_style))
        
        # High Priority
        high_priority = recommendations_data.get("HighPriority", [])
        if high_priority:
            story.append(Paragraph("High Priority Actions:", subheading_style))
            for i, rec in enumerate(high_priority, 1):
                story.append(Paragraph(f"{i}. {rec}", bullet_style))
            story.append(Spacer(1, 10))
        
        # Medium Priority
        medium_priority = recommendations_data.get("MediumPriority", [])
        if medium_priority:
            story.append(Paragraph("Medium Priority Improvements:", subheading_style))
            for i, rec in enumerate(medium_priority, 1):
                story.append(Paragraph(f"{i}. {rec}", bullet_style))
            story.append(Spacer(1, 10))
        
        # Keyword Optimization
        keyword_opt = recommendations_data.get("KeywordOptimization", [])
        if keyword_opt:
            story.append(Paragraph("Keyword Optimization Tips:", subheading_style))
            for i, tip in enumerate(keyword_opt, 1):
                story.append(Paragraph(f"{i}. {tip}", bullet_style))
            story.append(Spacer(1, 10))
        
        # Quantification Opportunities
        quant_ops = recommendations_data.get("QuantificationOpportunities", [])
        if quant_ops:
            story.append(Paragraph("Quantification Opportunities:", subheading_style))
            for i, opp in enumerate(quant_ops, 1):
                story.append(Paragraph(f"{i}. {opp}", bullet_style))
        
        story.append(Spacer(1, 15))
    
    # Red Flags
    red_flags = results.get("RedFlags", [])
    if red_flags:
        story.append(Paragraph("Red Flags to Address", heading_style))
        story.append(Paragraph("The following issues might cause automatic rejection and should be addressed immediately:", body_style))
        for flag in red_flags:
            story.append(Paragraph(f"• {flag}", bullet_style))
        story.append(Spacer(1, 15))
    
    # Competitive Advantage
    advantage = results.get("CompetitiveAdvantage", "")
    if advantage:
        story.append(Paragraph("Your Competitive Edge", heading_style))
        story.append(Paragraph(advantage, body_style))
        story.append(Spacer(1, 15))
    
    # Action Plan
    if action_plan:
        story.append(PageBreak())
        story.append(Paragraph("Action Plan", heading_style))
        
        immediate_actions = action_plan.get("immediate_actions", [])
        if immediate_actions:
            story.append(Paragraph("Immediate Actions (Do This First):", subheading_style))
            for action in immediate_actions:
                story.append(Paragraph(f"• {action}", bullet_style))
            story.append(Spacer(1, 10))
        
        missing_kw = action_plan.get("missing_keywords", [])
        if missing_kw:
            story.append(Paragraph("Keywords to Integrate:", subheading_style))
            story.append(Paragraph(", ".join(missing_kw), body_style))
            story.append(Spacer(1, 10))
        
        red_flags_fix = action_plan.get("red_flags_to_fix", [])
        if red_flags_fix:
            story.append(Paragraph("Critical Issues to Fix:", subheading_style))
            for flag in red_flags_fix:
                story.append(Paragraph(f"• {flag}", bullet_style))
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("This report was generated by Smart ATS Resume Analyzer", 
                          styles['Normal']))
    story.append(Paragraph("For best results, implement recommendations systematically and re-analyze your updated resume.", 
                          styles['Normal']))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

def main():
    # Set page config
    st.set_page_config(
        page_title="ATS Resume Analyzer",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Load environment variables
    load_dotenv()
    
    # Initialize session state
    init_session_state()
    
    # Configure Generative AI
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("⚠️ Please set the GOOGLE_API_KEY in your .env file")
        return
        
    try:
        configure_genai(api_key)
    except Exception as e:
        st.error(f"❌ Failed to configure API: {str(e)}")
        return

    # Sidebar
    with st.sidebar:
        st.title("🎯ATS Resume Analyzer")
        st.markdown("---")
        
        st.subheader("📊 Features")
        st.markdown("""
        1. **Comprehensive Analysis** - Deep dive into resume-job fit
        2. **ATS Optimization** - Improve parsing scores
        3. **Skills Alignment** - Gap analysis & recommendations
        4. **Keyword Optimization** - Strategic keyword placement
        6. **Action Plans** - Prioritized improvement roadmap
        7. **Red Flag Detection** - Avoid automatic rejection
        """)
        
        add_vertical_space(2)
        
        st.subheader("💡 Tips for Best Results")
        st.markdown("""
        1. **Complete Job Description** - Include all requirements
        2. **Clear PDF Resume** - Ensure text is selectable
        3. **Updated Content** - Use your latest resume version
        4. **Specific Role Focus** - Analyze for one role at a time
        """)
        
        add_vertical_space(2)
        
        if st.session_state.analysis_results:
            st.success("✅ Analysis Complete!")
            if st.button("🔄 New Analysis"):
                st.session_state.analysis_results = None
                st.session_state.show_detailed_view = False
                st.rerun()

    # Main content
    st.title("🚀 ATS Resume Analyzer")
    st.markdown("**Optimize your resume for Applicant Tracking Systems and get hired faster!**")
    
    add_vertical_space(1)
    
    # Input sections
    if not st.session_state.analysis_results:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📝 Job Description")
            jd = st.text_area(
                "Paste the complete job description here:",
                placeholder="Copy and paste the full job posting including requirements, responsibilities, and qualifications...",
                height=300,
                help="Include all details for accurate analysis"
            )
        
        with col2:
            st.subheader("📄 Your Resume")
            uploaded_file = st.file_uploader(
                "Upload your resume (PDF format):",
                type="pdf",
                help="Make sure your PDF contains selectable text, not scanned images"
            )
            
            if uploaded_file:
                st.success(f"✅ File uploaded: {uploaded_file.name}")

        add_vertical_space(2)

        # Analysis button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔍 Analyze My Resume", 
                        type="primary", 
                        disabled=st.session_state.processing,
                        use_container_width=True):
                
                if not jd.strip():
                    st.warning("⚠️ Please provide a job description.")
                    return
                    
                if not uploaded_file:
                    st.warning("⚠️ Please upload your resume in PDF format.")
                    return
                    
                st.session_state.processing = True
                
                try:
                    with st.spinner("🔄 Analyzing your resume... This may take 30-60 seconds"):
                        # Progress bar for better UX
                        progress_bar = st.progress(0)
                        
                        # Extract text from PDF
                        progress_bar.progress(25)
                        resume_text = extract_pdf_text(uploaded_file)
                        
                        # Prepare prompt
                        progress_bar.progress(50)
                        input_prompt = prepare_prompt(resume_text, jd)
                        
                        # Get response
                        progress_bar.progress(75)
                        response = get_gemini_response(input_prompt)
                        
                        # Process results
                        progress_bar.progress(100)
                        response_json = process_ats_results(response)
                        
                        # Store results in session state
                        st.session_state.analysis_results = response_json
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Analysis failed: {str(e)}")
                    st.info("💡 Try simplifying the job description or check if your PDF is text-selectable")
                    
                finally:
                    st.session_state.processing = False

    # Display results
    if st.session_state.analysis_results:
        results = st.session_state.analysis_results
        
        st.success("🎉 **Analysis Complete!** Here's your comprehensive resume evaluation:")
        
        add_vertical_space(1)
        
        # Score Cards
        display_score_card(
            results.get("JD Match", "N/A"),
            results.get("ATSScore", "N/A")
        )
        
        add_vertical_space(2)
        
        # Profile Summary
        st.subheader("📋 Executive Summary")
        profile_summary = results.get("Profile Summary", "No summary available")
        st.info(profile_summary)
        
        add_vertical_space(2)
        
        # Toggle for detailed view
        if st.checkbox("🔍 Show Detailed Analysis", value=st.session_state.show_detailed_view):
            st.session_state.show_detailed_view = True
            
            # Skills Analysis
            display_skills_analysis(results.get("SkillsAlignment", {}))
            
            add_vertical_space(2)
            
            # Experience Analysis
            display_experience_match(results.get("ExperienceMatch", {}))
            
            add_vertical_space(2)
            
            # Missing Keywords
            st.subheader("🔑 Missing Keywords")
            missing_keywords = results.get("MissingKeywords", [])
            if missing_keywords:
                st.warning("**Add these keywords to improve your match:**")
                # Display as tags
                keyword_html = " ".join([f'<span style="background-color: #ff6b6b; color: white; padding: 2px 8px; border-radius: 12px; margin: 2px; display: inline-block;">{kw}</span>' for kw in missing_keywords])
                st.markdown(keyword_html, unsafe_allow_html=True)
            else:
                st.success("✅ No critical missing keywords found!")
            
            add_vertical_space(2)
            
            # Recommendations
            display_recommendations(results.get("Recommendations", {}))
            
            add_vertical_space(2)
            
            # Red Flags
            display_red_flags(results.get("RedFlags", []))
            
            add_vertical_space(2)
            
            # Competitive Advantage
            display_competitive_advantage(results.get("CompetitiveAdvantage", ""))
        
        add_vertical_space(2)
        
        # Action Plan Section
        st.subheader("🎯 Quick Action Plan")
        try:
            action_plan = generate_action_plan(results)
            display_action_plan(action_plan)
        except Exception as e:
            st.error(f"Could not generate action plan: {str(e)}")
        
        add_vertical_space(2)
        
        # Download results as PDF
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            try:
                action_plan = generate_action_plan(results)
                pdf_buffer = generate_pdf_report(results, action_plan)
                
                st.download_button(
                    label="📥 Download Complete Analysis Report",
                    data=pdf_buffer.getvalue(),
                    file_name=f"ATS_Analysis_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Could not generate PDF report: {str(e)}")
                # Fallback to JSON download
                st.download_button(
                    label="📥 Download Analysis (JSON)",
                    data=json.dumps(results, indent=2),
                    file_name="ats_analysis.json",
                    mime="application/json",
                    use_container_width=True
                )

if __name__ == "__main__":
    main()