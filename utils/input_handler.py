from datetime import datetime
from pathlib import Path
import shutil
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pypdf import PdfReader
from playwright.sync_api import sync_playwright
import os
import time

env_path = Path(__file__).parent.parent / '.env' 
load_dotenv(dotenv_path=env_path)

class ScrapedJobData(BaseModel):
    """Holds the data scraped directly from the job posting page."""
    company_name: str
    job_description_text: str

def get_daily_session_path() -> Path:
    today_str = datetime.now().strftime("%Y-%m-%d")
    base_dir = Path(".linkedin")
    session_dir = base_dir / f"session_{today_str}"

    # Ensure both base_dir and session_dir exist
    session_dir.mkdir(parents=True, exist_ok=True)

    return session_dir

def clear_old_sessions():
    base_dir = Path(".linkedin")
    today_session = get_daily_session_path()

    if not base_dir.exists():
        return

    for session_path in base_dir.glob("session_*"):
        if session_path != today_session and session_path.is_dir():
            print(f"Deleting old session: {session_path}")
            shutil.rmtree(session_path)

def login_and_scrape(url: str):
    session_path = get_daily_session_path()
    clear_old_sessions()  # Clean up old sessions

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(session_path),
            headless=False,
        )

def get_job_data(source_type: str, source_value: str) -> ScrapedJobData:
    """
    Retrieves the job data (company name, description) from a given source.

    Args:
        source_type (str): The type of source. One of ['text', 'url', 'pdf'].
        source_value (str): The actual text, URL, or file path.

    Returns:
        ScrapedJobData: An object containing the scraped company name and job description text.
        
    Raises:
        ValueError: If the source_type is invalid.
        Exception: For issues with URL fetching or file reading.
    """
    print(f"Processing job description from source: {source_type}")

    if source_type == 'url':
        if 'linkedin.com' not in source_value:
            # For non-LinkedIn URLs, we can try the simple method first
            print("Non-LinkedIn URL detected, using simple fetch.")
            try:
                response = requests.get(source_value, headers={'User-Agent': 'Mozilla/5.0'})
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                # For simple fetch, we can't reliably get the company name, so we default it.
                return ScrapedJobData(
                    company_name="Unknown Company", 
                    job_description_text=' '.join(soup.body.get_text(separator=' ').split())
                )
            except Exception as e:
                print(f"Simple fetch failed: {e}. Falling back to Playwright.")
        
        # For LinkedIn or failed simple fetches, use the full login method
        print("Using Playwright to fetch dynamic content with login...")
        
        email = os.getenv("LINKEDIN_EMAIL")
        password = os.getenv("LINKEDIN_PASSWORD")

        print("--- DEBUGGING CREDENTIALS ---")
        print(f"Loaded Email: {email}")
        print(f"Loaded Password: {'*' * len(password) if password else None}") # Don't print the actual password
        
        if not email or not password:
            print("ERROR: Credentials not found in environment variables. Stopping.")
            raise ValueError("LINKEDIN_EMAIL and LINKEDIN_PASSWORD must be set in the .env file")
        
        print("--- CREDENTIALS LOADED SUCCESSFULLY ---")
        
        try:
            session_path = get_daily_session_path()
            clear_old_sessions()  # Clean up old sessions

            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(session_path),
                    headless=False,
                )
                page = browser.new_page()
                page.goto('https://www.linkedin.com/login', timeout=60000)

                print("Checking if already logged in...")
                try:
                    # If this element appears, the user is already logged in
                    page.wait_for_selector('input.search-global-typeahead__input', timeout=10000)
                    print("Session valid. Already logged in.")
                except:
                    print("Session not valid or login required. Proceeding with login...")  
                
                    page.goto('https://www.linkedin.com/login', timeout=60000)
                    print("Waiting for login form to be ready...")
                    
                    email_field_selector = 'input#username'
                    page.wait_for_selector(email_field_selector, timeout=30000)

                    print("Filling email...")
                    page.fill(email_field_selector, email)

                    password_field_selector = 'input#password'
                    page.wait_for_selector(password_field_selector, timeout=30000)

                    print("Filling password...")
                    page.fill(password_field_selector, password)

                    print("Signing in...")
                    page.click('button[data-litms-control-urn="login-submit"]')
                    
                    print("Waiting for login confirmation (main search bar)...")
                    login_confirmation_selector = 'input.search-global-typeahead__input'
                    page.wait_for_selector(login_confirmation_selector, timeout=60000)
                    print("Login successful!")

                print(f"Navigating to job URL: {source_value}")
                page.goto(source_value, timeout=60000)

                # --- START OF FIX ---
                # Wait for the "Apply" button to be visible. This is often a reliable
                # indicator that the dynamic content of the job posting has fully loaded.
                apply_button_selector = 'button.jobs-apply-button'
                print(f"Waiting for page to fully load by finding the Apply button ('{apply_button_selector}')...")
                page.wait_for_selector(apply_button_selector, timeout=60000)
                print("Apply button found. Page is ready for scraping.")
                # --- END OF FIX ---
                
                # Now that we've confirmed the page is loaded, get its full HTML content.
                html_content = page.content()
                
                print("Scraping complete. Closing browser.")
                browser.close()

            soup = BeautifulSoup(html_content, 'html.parser')
            
            company_name_selector = (
                'div.job-details-jobs-unified-top-card__company-name a, '
                'a.topcard__org-name-link, '
                'a.app-aware-link[data-test-app-aware-link]'
            )
        
            company_element = soup.select_one(company_name_selector)
            if company_element:
                company_name = company_element.get_text(strip=True)
                print(f"Successfully scraped Company Name: {company_name}")
            else:
                company_name = "Unknown Company"
                print("Warning: Could not scrape company name. Defaulting to 'Unknown Company'.")

            job_desc_container = (
                soup.find('div', id='job-details') or 
                soup.find('div', class_='description__text')
            )
            if job_desc_container:
                jd_text = ' '.join(job_desc_container.get_text(separator=' ').split())
            else:
                raise Exception("Could not find the job description container on the page.")

            return ScrapedJobData(company_name=company_name, job_description_text=jd_text)
        
        except Exception as e:
            print(f"An error occurred during Playwright operation: {e}")
            raise

    elif source_type == 'text':
        return ScrapedJobData(company_name="Unknown Company", job_description_text=source_value)
    
    elif source_type == 'pdf':
        try:
            text = ""
            with open(source_value, 'rb') as file:
                reader = PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() or ""
            return ScrapedJobData(company_name="Unknown Company", job_description_text=' '.join(text.split()))
        except Exception as e:
            raise Exception(f"Error reading PDF file: {e}")

    else:
        raise ValueError("Invalid source_type. Choose from 'url', 'text', or 'pdf'.")