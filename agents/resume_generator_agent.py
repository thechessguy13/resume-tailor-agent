import os
from datetime import datetime # Added for date formatting
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from .content_selector_agent import TailoredResumeContent
from .job_analyzer_agent import JobAnalysis # Added to get job analysis data
from typing import Dict

def add_bottom_border_to_paragraph(paragraph):
    """
    This function directly manipulates the paragraph's XML to add a
    bottom border, mimicking the user's working document.
    """
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '12')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), 'auto')
    
    pBdr.append(bottom)
    pPr.append(pBdr)

# --- Default Generator (Now the ONLY generator) ---
def generate_resume_docx(
    tailored_content: TailoredResumeContent,
    contact_info: Dict,
    job_analysis: JobAnalysis, # Added to get target company name
    output_folder: str = "output"
) -> str:
    print("Generating .docx resume using XML-derived styling...")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    doc = Document()
    
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(10)

    for section in doc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)
    
    # --- HEADER ---
    p_name = doc.add_paragraph()
    p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_name.paragraph_format.space_before = Pt(0)
    p_name.paragraph_format.space_after = Pt(0)
    run_name = p_name.add_run(contact_info.get('name', ''))
    run_name.font.size = Pt(14)
    run_name.font.bold = True
    
    p_contact = doc.add_paragraph()
    p_contact.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_contact.paragraph_format.space_after = Pt(8)
    p_contact.add_run(contact_info.get('address', ''))
    p_contact.add_run().add_break()
    p_contact.add_run(f"{contact_info.get('email', '')} | {contact_info.get('phone', '')} | {contact_info.get('linkedin', '')}")
    
    def add_section_heading(text, first_section=False):
        p = doc.add_paragraph()
        if not first_section:
            p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(text)
        run.bold = True
        run.font.size = Pt(10)
        add_bottom_border_to_paragraph(p)

    # --- BUILD DOCUMENT SECTIONS ---
    add_section_heading('PROFESSIONAL SUMMARY', first_section=True)
    doc.add_paragraph(tailored_content.professional_summary)

    add_section_heading('EXPERIENCE')
    for job in tailored_content.selected_experience:
        p_job_title = doc.add_paragraph()
        p_job_title.paragraph_format.space_before = Pt(6)
        run_job = p_job_title.add_run(f"{job.role} – {job.company}")
        run_job.bold = True
        p_job_title.paragraph_format.tab_stops.add_tab_stop(Inches(7.0), alignment=WD_ALIGN_PARAGRAPH.RIGHT)
        run_date = p_job_title.add_run('\t' + job.dates)
        run_date.bold = True
        for point in job.rewritten_bullet_points:
            p_bullet = doc.add_paragraph(point, style='List Bullet')
            p_bullet.paragraph_format.space_before = Pt(6)

    add_section_heading('SKILLS')
    for category, skills_list in tailored_content.relevant_skills.items():
        p_skill = doc.add_paragraph(style='List Bullet')
        p_skill.add_run(f"{category.replace('_', ' ').title()}: ").bold = True
        p_skill.add_run(', '.join(skills_list))

    if tailored_content.selected_projects:
        add_section_heading('PROJECTS')
        for project in tailored_content.selected_projects:
            doc.add_paragraph(f"{project.name} - {project.rewritten_description}", style='List Bullet')
    
    if tailored_content.education:
        add_section_heading('EDUCATION')
        for edu in tailored_content.education:
            p_inst = doc.add_paragraph()
            p_inst.paragraph_format.space_before = Pt(6)
            p_inst.paragraph_format.space_after = Pt(0)
            p_inst.add_run(edu['institution']).bold = True
            p_inst.paragraph_format.tab_stops.add_tab_stop(Inches(7.0), alignment=WD_ALIGN_PARAGRAPH.RIGHT)
            run_edu_date = p_inst.add_run('\t' + edu['dates'])
            run_edu_date.bold = True
            
            p_degree = doc.add_paragraph()
            p_degree.paragraph_format.space_after = Pt(0)
            p_degree.add_run(edu['degree']).italic = True
            if edu.get('gpa'): p_degree.add_run(f" (GPA: {edu.get('gpa')})")
            
            if edu.get('relevant_courses'):
                p_courses = doc.add_paragraph()
                p_courses.paragraph_format.space_after = Pt(8)
                p_courses.add_run("Relevant Courses: ").bold = True
                p_courses.add_run(', '.join(edu['relevant_courses']))
            else:
                p_degree.paragraph_format.space_after = Pt(8)

    if tailored_content.accomplishments_and_awards:
        add_section_heading('ACCOMPLISHMENTS & AWARDS')
        for acc in tailored_content.accomplishments_and_awards:
            doc.add_paragraph(acc, style='List Bullet')

    # --- CORRECTED FILENAME LOGIC ---
    # Get the company name directly from the job analysis object.
    company_name = job_analysis.company
    
    # Sanitize the company name for use in a filename.
    sanitized_company_name = company_name.lower().replace(' ', '-').replace('/', '-')
    
    # Get today's date in YYYY-MM-DD format.
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Create the new, correct filename.
    output_filename = f"resume-{sanitized_company_name}-{today_str}.docx"
    output_path = os.path.join(output_folder, output_filename)
    
    doc.save(output_path)
    print(f"Successfully generated resume: {output_path}")
    return output_path