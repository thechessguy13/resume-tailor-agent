from datetime import datetime
from pathlib import Path
import shutil
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pypdf import PdfReader
from playwright.sync_api import sync_playwright
import os
import time

env_path = Path(__file__).parent.parent / '.env' 
load_dotenv(dotenv_path=env_path)



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

def get_job_description_text(source_type: str, source_value: str) -> str:
    """
    Retrieves the raw text of a job description from a given source.

    Args:
        source_type (str): The type of source. One of ['text', 'url', 'pdf'].
        source_value (str): The actual text, URL, or file path.

    Returns:
        str: The extracted text content of the job description.
        
    Raises:
        ValueError: If the source_type is invalid.
        Exception: For issues with URL fetching or file reading.
    """
    print(f"Processing job description from source: {source_type}")

    if source_type == 'text':
        return source_value

    elif source_type == 'url':
        if 'linkedin.com' not in source_value:
            # For non-LinkedIn URLs, we can try the simple method first
            print("Non-LinkedIn URL detected, using simple fetch.")
            try:
                response = requests.get(source_value, headers={'User-Agent': 'Mozilla/5.0'})
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                return ' '.join(soup.body.get_text(separator=' ').split())
            except Exception as e:
                print(f"Simple fetch failed: {e}. Falling back to Playwright.")
        
        # For LinkedIn or failed simple fetches, use the full login method
        print("Using Playwright to fetch dynamic content with login...")
        
        email = os.getenv("LINKEDIN_EMAIL")
        password = os.getenv("LINKEDIN_PASSWORD")

        # --- START OF NEW DEBUGGING CODE ---
        print("--- DEBUGGING CREDENTIALS ---")
        print(f"Loaded Email: {email}")
        print(f"Loaded Password: {'*' * len(password) if password else None}") # Don't print the actual password
        
        if not email or not password:
            print("ERROR: Credentials not found in environment variables. Stopping.")
            raise ValueError("LINKEDIN_EMAIL and LINKEDIN_PASSWORD must be set in the .env file")
        
        print("--- CREDENTIALS LOADED SUCCESSFULLY ---")
        
        # In utils/input_handler.py -> get_job_description_text -> elif source_type == 'url'

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
                    # --- APPLYING THE FIX ---
                    print("Waiting for login form to be ready...")
                    
                    # Use the new ID for the email/username field
                    email_field_selector = 'input#username' # <-- CHANGED
                    page.wait_for_selector(email_field_selector, timeout=30000)

                    print("Filling email...")
                    page.fill(email_field_selector, email)

                    # Use the new ID for the password field
                    password_field_selector = 'input#password' # <-- CHANGED
                    page.wait_for_selector(password_field_selector, timeout=30000)

                    print("Filling password...")
                    page.fill(password_field_selector, password)
                    # --- END OF FIX ---

                    print("Signing in...")
                    # The submit button selector is usually stable, so we leave it.
                    page.click('button[data-litms-control-urn="login-submit"]') # Using a more specific button selector
                    
                    print("Waiting for login confirmation (main search bar)...")
                    # We are replacing the old selector with a more reliable one.
                    login_confirmation_selector = 'input.search-global-typeahead__input' # <-- CHANGED
                    page.wait_for_selector(login_confirmation_selector, timeout=60000)
                    print("Login successful!")

                print(f"Navigating to job URL: {source_value}")
                page.goto(source_value, timeout=60000)

                # This is the selector for the job description text on LinkedIn's job pages
                job_description_selector = '#job-details, div.description__text'
                print(f"Waiting for job description to appear using robust selector: {job_description_selector}")
                page.wait_for_selector(job_description_selector, timeout=60000)
                html_content = page.content()
                
                print("Scraping complete. Closing browser.")
                browser.close()

            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Now we need to find the content using either class
            job_desc_container = (
                soup.find('div', id='job-details') or 
                soup.find('div', class_='description__text')
            )
            
            if job_desc_container:
                text = ' '.join(job_desc_container.get_text(separator=' ').split())
            else:
                raise Exception("Could not find the job description container on the page.")
            return text
        except Exception as e:
            # Add a print statement to the exception to see more detail if it fails
            print(f"An error occurred during Playwright operation: {e}")
            raise

    elif source_type == 'pdf':
        try:
            text = ""
            with open(source_value, 'rb') as file:
                reader = PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() or ""
            return ' '.join(text.split())
        except FileNotFoundError:
            raise Exception(f"Error: PDF file not found at '{source_value}'")
        except Exception as e:
            raise Exception(f"Error reading PDF file: {e}")

    else:
        raise ValueError("Invalid source_type. Choose from 'text', 'url', or 'pdf'.")