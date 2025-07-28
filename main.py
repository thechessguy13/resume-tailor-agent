import json
from utils.input_handler import get_job_description_text
from agents.job_analyzer_agent import analyze_job_description
from agents.content_selector_agent import select_and_tailor_content

# --- Main Execution Block ---
if __name__ == '__main__':
    source_type = 'url'
    source_value = "https://www.linkedin.com/jobs/collections/recommended/?currentJobId=4270824847" # Use a fresh, valid job URL

    try:
        # --- PREP: Load Master Profile ---
        print("--- Step 0: Loading Master Profile ---")
        with open('master_profile.json', 'r') as f:
            master_profile_data = json.load(f)
        print("Master profile loaded successfully.\n")

        # --- PHASE 1: Get Raw Job Description Text ---
        print("--- Step 1: Fetching Job Description ---")
        raw_jd_text = get_job_description_text(
            source_type=source_type, 
            source_value=source_value
        )
        print("Successfully fetched raw text.\n")
        
        # --- PHASE 2: Analyze the Text with LLM ---
        print("--- Step 2: Analyzing Job Description ---")
        structured_analysis = analyze_job_description(raw_jd_text)
        print("\n--- Analysis Complete! ---")
        print(structured_analysis.model_dump_json(indent=2))
        print("\n")

        # --- PHASE 3: Select and Tailor Content ---
        print("--- Step 3: Selecting and Tailoring Content ---")
        tailored_content = select_and_tailor_content(
            job_analysis=structured_analysis,
            master_profile=master_profile_data
        )
        print("\n--- Content Tailoring Complete! ---")
        print(tailored_content.model_dump_json(indent=2))


    except Exception as e:
        print(f"\nAn error occurred in the pipeline: {e}")