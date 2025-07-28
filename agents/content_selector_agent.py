import json
from typing import List, Dict
from pydantic import BaseModel, Field
from .job_analyzer_agent import JobAnalysis
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

class TailoredWorkExperience(BaseModel):
    company: str = Field(description="Name of the company.")
    role: str = Field(description="Job title or role at the company.")
    dates: str = Field(description="The dates of employment.")
    rewritten_bullet_points: List[str] = Field(description="Bulleted list of achievements, rewritten to align with the target job's keywords and responsibilities.")

class TailoredProject(BaseModel):
    name: str = Field(description="The name of the project.")
    rewritten_description: str = Field(description="A 1-2 sentence description of the project, rewritten to highlight its relevance to the target job.")
    link: str = Field(description="URL to the project or its source code.")

class TailoredResumeContent(BaseModel):
    professional_summary: str = Field(description="A 2-3 sentence professional summary, rewritten to be highly specific and compelling for the target job.")
    selected_experience: List[TailoredWorkExperience] = Field(description="The top 2-3 most relevant work experiences, with bullet points tailored to the job.")
    selected_projects: List[TailoredProject] = Field(description="The 1-2 most relevant projects, with descriptions tailored to the job. If no projects are relevant, return an empty list.")
    relevant_skills: Dict[str, List[str]] = Field(description="A dictionary of skill categories and a list of skills from the master profile that are most relevant to the job.")
    education: List[Dict] = Field(description="A list of education entries (institution, degree, dates) from the master profile.")
    accomplishments: List[str] = Field(description="A list of 1-3 key accomplishments or awards from the master profile that are relevant to the job. If none are relevant, return an empty list.")

def select_and_tailor_content(job_analysis: JobAnalysis, master_profile: Dict) -> TailoredResumeContent:
    llm = ChatOpenAI(model="gpt-4-turbo", temperature=0.2)
    parser = PydanticOutputParser(pydantic_object=TailoredResumeContent)
    job_analysis_json = job_analysis.model_dump_json(indent=2)
    master_profile_json = json.dumps(master_profile, indent=2)

    prompt_template = """
    You are an expert career coach and professional resume writer. Your task is to create tailored resume content for a specific job application by comparing a user's master profile against a detailed job analysis.

    **Job Analysis:**
    ```json
    {job_analysis}
    ```

    **User's Master Profile:**
    ```json
    {master_profile}
    ```

    **Your Instructions:**
    1.  **Professional Summary:** Write a new, 2-3 sentence professional summary. It must be highly specific, incorporating the `job_title` from the analysis and highlighting the user's most relevant skills and experience from their profile.
    2.  **Work Experience:** Select the 2 most relevant work experiences from the master profile that best match the job analysis. For EACH selected experience, DO NOT change the company, role, or dates. **REWRITE the bullet points.** Infuse them with keywords from the job analysis's `key_skills` and `core_responsibilities`. Rephrase accomplishments to directly address what the job is looking for.
    3.  **Projects:** Select the 1-2 most relevant projects. If no projects from the master profile seem relevant, return an empty list for this field. For EACH selected project, **REWRITE the description** to highlight technologies and outcomes relevant to the target job.
    4.  **Skills:** From the master profile's skills, create a new list of skills that are most relevant to the `key_skills` required by the job. Maintain the original categories.
    5.  **Education:** Extract the user's complete education history from the master profile exactly as it is.
    6.  **Accomplishments:** Review the user's accomplishments/awards in the master profile. Select the 1-3 that are most impressive or relevant to the job analysis. If none are relevant, return an empty list.

    Please provide your final output in the required structured format.
    {format_instructions}
    """
    prompt = ChatPromptTemplate.from_template(
        template=prompt_template,
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    chain = prompt | llm | parser
    print("Selecting and tailoring content with LLM...")
    tailored_content = chain.invoke({
        "job_analysis": job_analysis_json,
        "master_profile": master_profile_json
    })
    return tailored_content