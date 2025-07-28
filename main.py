import json
import os 
# --- RENAMED IMPORT ---
from utils.input_handler import get_job_data
from agents.job_analyzer_agent import analyze_job_description
from agents.content_selector_agent import select_and_tailor_content
from agents.resume_generator_agent import generate_resume_docx
from utils.profile_generator import create_master_profile_from_pdf

# --- Main Execution Block ---
if __name__ == '__main__':
    # --- CONTROL PANEL ---
    PROFILE_SOURCE_FOLDER = "input" 

    # --- Job Input ---
    source_type = 'url'
    # Replace with a fresh, valid job URL for testing
    source_value = "https://www.linkedin.com/jobs/collections/recommended/?currentJobId=4263346390&start=24" 

    try:
        # --- Check for master_profile.json and generate if needed ---
        os.makedirs(PROFILE_SOURCE_FOLDER, exist_ok=True) 
        if not os.path.exists('master_profile.json'):
            create_master_profile_from_pdf(source_folder=PROFILE_SOURCE_FOLDER)
        
        # --- PREP: Load Master Profile ---
        print("--- Step 0: Loading Master Profile ---")
        with open('master_profile.json', 'r') as f:
            master_profile_data = json.load(f)
        
        # --- PHASE 1: Get Raw Job Data (Name and Text) ---
        print("\n--- Step 1: Fetching Job Data ---")
        scraped_data = get_job_data(source_type, source_value)
        
        # --- PHASE 2: Analyze the Text with LLM ---
        print("\n--- Step 2: Analyzing Job Description ---")
        structured_analysis = analyze_job_description(scraped_data.job_description_text)

        # --- NEW: Override company name with reliably scraped data ---
        # This ensures the company name is always correct, even if the LLM fails to extract it.
        print(f"Overriding LLM-analyzed company name ('{structured_analysis.company}') with scraped name ('{scraped_data.company_name}').")
        structured_analysis.company = scraped_data.company_name
        
        print("--- Analysis Complete! ---")
        print(structured_analysis.model_dump_json(indent=2))
        
        # --- PHASE 3: Select and Tailor Content ---
        print("\n--- Step 3: Selecting and Tailoring Content ---")
        tailored_content = select_and_tailor_content(structured_analysis, master_profile_data)
        print("--- Content Tailoring Complete! ---")
        print(tailored_content.model_dump_json(indent=2))
        
        # --- PHASE 4: Simplified Resume Generation ---
        print("\n--- Step 4: Generating Final Resume ---")
        
        # The generator will now receive the corrected company name via structured_analysis
        final_resume_path = generate_resume_docx(
            tailored_content=tailored_content,
            contact_info=master_profile_data['contact_info'],
            job_analysis=structured_analysis 
        )
        
        print(f"\n\n>>> ALL DONE! Your resume is ready at: {final_resume_path} <<<")

    except Exception as e:
        print(f"\nAn error occurred in the pipeline: {e}")