import os
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from pypdf import PdfReader
# --- REMOVED: from langchain_openai import ChatOpenAI ---
from langchain_google_genai import ChatGoogleGenerativeAI # <-- ADD THIS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# ... (Pydantic models remain unchanged) ...
class ContactInfo(BaseModel):
    name: str = Field(description="The full name of the person.")
    address: str = Field(description="The city, state, and country.")
    email: str = Field(description="The email address.")
    phone: str = Field(description="The phone number.")
    linkedin: str = Field(description="The full LinkedIn profile URL.")
    github: str = Field(description="The full GitHub profile URL.")
    portfolio: Optional[str] = Field(description="The URL of a personal portfolio, if available.")

class Skills(BaseModel):
    programming_languages: List[str] = Field(description="List of programming languages like Python, Java, etc.")
    technologies: List[str] = Field(description="List of technologies, frameworks, and databases like Scikit-learn, PostgreSQL, AWS, etc.")
    methodologies: List[str] = Field(description="List of methodologies and concepts like Agile, Supervised Learning, RAG, etc.")

class Accomplishment(BaseModel):
    project_name: str = Field(description="A descriptive name for the project or initiative, inferred from the bullet point.")
    description: str = Field(description="A 1-2 sentence high-level description of the project's goal. If not present, create one based on the context.")
    technologies_used: List[str] = Field(description="A list of specific technologies used in this accomplishment, extracted from the text.")
    my_responsibilities: List[str] = Field(description="A list of actions or responsibilities taken by the person for this accomplishment.")
    impact: str = Field(description="The quantifiable outcome or result of the work. If not quantified, describe the qualitative impact.")

class WorkExperience(BaseModel):
    company: str
    role: str
    dates: str
    location: str
    accomplishments: List[Accomplishment] = Field(description="A list of detailed accomplishments for this role.")

class Project(BaseModel):
    name: str
    description: str
    technologies_used: List[str]
    bullet_points: List[str]
    link: Optional[str]

class EducationEntry(BaseModel):
    institution: str
    degree: str
    dates: str
    gpa: Optional[str]
    relevant_courses: Optional[List[str]]

class MasterProfile(BaseModel):
    contact_info: ContactInfo
    professional_summary: str = Field(description="The professional summary or objective statement from the resume.")
    skills: Skills
    work_experience: List[WorkExperience]
    projects: List[Project]
    education: List[EducationEntry]
    accomplishments_and_awards: List[str] = Field(description="A list of certifications, publications, or awards.")


def _extract_text_from_pdf(pdf_path: str) -> str:
    # ... (This function remains unchanged) ...
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"The file '{pdf_path}' was not found.")
    
    print(f"Reading text from '{pdf_path}'...")
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
    return ' '.join(text.split())


def _generate_structured_profile(resume_text: str) -> MasterProfile:
    """Uses an LLM to parse resume text into a structured MasterProfile object."""
    # --- CHANGE: Use Gemini instead of OpenAI ---
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.4)
    parser = PydanticOutputParser(pydantic_object=MasterProfile)

    prompt_template = """
    You are an expert HR analyst and data extraction specialist. Your task is to parse the raw text from a resume and convert it into a highly structured JSON format. Pay close attention to the instructions for each field.

    **Resume Text:**
    ---
    {resume_text}
    ---

    **Instructions:**
    1.  **Parse all sections:** Carefully extract information for contact info, summary, skills, work experience, education, projects, and awards.
    2.  **Work Experience -> Accomplishments:** This is the most important part. For each job listed under 'Work Experience', do not just copy bullet points. Instead, for each bullet point or described project, create a detailed `accomplishment` object.
        -   `project_name`: Infer a logical name for the initiative (e.g., "Automated Quotation System").
        -   `description`: Briefly describe the project's goal.
        -   `my_responsibilities`: Detail what the person *did* (e.g., "Architected the system," "Developed the model").
        -   `impact`: Extract the quantifiable result (e.g., "Reduced costs by 15%"). If not present, state the qualitative impact (e.g., "Improved system efficiency").
        -   `technologies_used`: List only the technologies mentioned for that specific accomplishment.
    3.  **Skills:** Categorize all skills found into `programming_languages`, `technologies`, and `methodologies`.
    4.  **Empty Fields:** If you cannot find information for a specific field (e.g., `gpa` or a `portfolio` URL), you must return an empty string or an empty list as specified in the schema. Do not invent data.

    {format_instructions}
    """
    
    prompt = ChatPromptTemplate.from_template(
        template=prompt_template,
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    chain = prompt | llm | parser

    print("Analyzing resume text with Google Gemini to generate master profile...")
    structured_profile = chain.invoke({"resume_text": resume_text})
    return structured_profile


def create_master_profile_from_pdf(source_folder: str = "profile_source"):
    # ... (This function remains unchanged) ...
    print("--- Master Profile Generator ---")
    print("`master_profile.json` not found.")
    
    pdf_files = [f for f in os.listdir(source_folder) if f.lower().endswith('.pdf')]

    if len(pdf_files) == 0:
        print(f"\nERROR: No PDF resume found in the '{source_folder}' directory.")
        print(f"Please add your resume (as a PDF) to the '{source_folder}' folder and run the script again.")
        exit()

    if len(pdf_files) > 1:
        print(f"\nERROR: Multiple PDF files found in the '{source_folder}' directory:")
        for f in pdf_files:
            print(f" - {f}")
        print("Please ensure there is only one resume PDF in that folder and run the script again.")
        exit()

    resume_pdf_path = os.path.join(source_folder, pdf_files[0])
    print(f"Found resume: '{resume_pdf_path}'")
    
    choice = input("Would you like to generate `master_profile.json` from this file? (y/n): ").lower()
    if choice != 'y':
        print("Exiting. Please create `master_profile.json` manually.")
        exit()

    try:
        raw_text = _extract_text_from_pdf(resume_pdf_path)
        master_profile_data = _generate_structured_profile(raw_text)
        
        output_path = 'master_profile.json'
        with open(output_path, 'w') as f:
            f.write(master_profile_data.model_dump_json(indent=2))
        
        print("\n\n" + "="*50)
        print(f"✅ Success! `master_profile.json` has been created at: {output_path}")
        print("IMPORTANT: The generated profile is a starting point.")
        print("Please review the file and add/edit any details for maximum accuracy.")
        print("="*50 + "\n")

    except Exception as e:
        print(f"\nAn error occurred during profile generation: {e}")
        exit()