import json
from utils.input_handler import get_job_description_text
from agents.job_analyzer_agent import analyze_job_description
from agents.content_selector_agent import select_and_tailor_content
from agents.resume_generator_agent import generate_resume_docx, generate_resume_from_template_docx

# --- Main Execution Block ---
if __name__ == '__main__':
    # --- CONTROL PANEL ---
    # To use your own template, provide the path here. e.g., "my_resume_template.docx"
    # To use the default generator, set this to None.
    USER_TEMPLATE_PATH = None

    # --- Job Input ---
    # You can change these values to test different inputs.
    source_type = 'url'
    source_value = "https://www.linkedin.com/jobs/collections/recommended/?currentJobId=4272093518" # Replace with a fresh, valid job URL

    try:
        # --- PREP: Load Master Profile ---
        print("--- Step 0: Loading Master Profile ---")
        with open('master_profile.json', 'r') as f:
            master_profile_data = json.load(f)
        
        # --- PHASE 1: Get Raw Job Description Text ---
        print("\n--- Step 1: Fetching Job Description ---")
        raw_jd_text = get_job_description_text(source_type, source_value)
        
        # --- PHASE 2: Analyze the Text with LLM ---
        print("\n--- Step 2: Analyzing Job Description ---")
        structured_analysis = analyze_job_description(raw_jd_text)
        print("--- Analysis Complete! ---")
        print(structured_analysis.model_dump_json(indent=2))
        
        # --- PHASE 3: Select and Tailor Content ---
        print("\n--- Step 3: Selecting and Tailoring Content ---")
        tailored_content = select_and_tailor_content(structured_analysis, master_profile_data)
        print("--- Content Tailoring Complete! ---")
        print(tailored_content.model_dump_json(indent=2))
        
        # --- PHASE 4: Dual-Path Resume Generation ---
        print("\n--- Step 4: Generating Final Resume ---")
        
        if USER_TEMPLATE_PATH:
            final_resume_path = generate_resume_from_template_docx(
                tailored_content=tailored_content,
                contact_info=master_profile_data['contact_info'],
                template_path=USER_TEMPLATE_PATH
            )
        else:
            final_resume_path = generate_resume_docx(
                tailored_content=tailored_content,
                contact_info=master_profile_data['contact_info']
            )
        
        print(f"\n\n>>> ALL DONE! Your resume is ready at: {final_resume_path} <<<")

    except Exception as e:
        print(f"\nAn error occurred in the pipeline: {e}")