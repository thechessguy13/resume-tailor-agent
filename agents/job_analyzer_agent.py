from typing import List
from pydantic import BaseModel, Field

class JobAnalysis(BaseModel):
    """Structured analysis of a job description."""
    
    job_title: str = Field(description="The official title of the job position.")
    company: str = Field(description="The name of the company hiring for the position.")
    key_skills: List[str] = Field(description="A list of the most important technical skills, tools, or programming languages mentioned.")
    core_responsibilities: List[str] = Field(description="A list of key responsibilities or daily tasks for the role.")
    experience_level: str = Field(description="The required level of experience, e.g., 'Entry-level', '3-5 years', 'Senior', 'Lead'.")


from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

def analyze_job_description(text: str) -> JobAnalysis:
    """
    Analyzes the raw text of a job description using an LLM.

    Args:
        text (str): The raw text scraped from the job posting.

    Returns:
        JobAnalysis: A Pydantic object containing the structured analysis.
    """
    llm = ChatOpenAI(model="gpt-4o-mini-2024-07-18", temperature=0)

    # 2. Create an output parser that will enforce the JobAnalysis schema.
    parser = PydanticOutputParser(pydantic_object=JobAnalysis)

    prompt_template = """
    You are an expert recruitment analyst. Your task is to analyze the following job description text and extract key information in a structured format.

    Here is the job description text:
    ---
    {job_description_text}
    ---

    Please extract the information according to the following schema.
    {format_instructions}
    """

    prompt = ChatPromptTemplate.from_template(
        template=prompt_template,
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    chain = prompt | llm | parser

    print("Analyzing job description with LLM...")

    analysis_result = chain.invoke({"job_description_text": text})
    
    return analysis_result