import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any
import requests
import re
from requests import RequestException, Session
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)

GITHUB_TOKEN_REGEX = re.compile(r'^(gh[ps]_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59})$')

def download_repo_zip(user: str, repo_name: str, download_path: Path, session: Session):
    zip_url = f"https://github.com/{user}/{repo_name}/archive/master.zip"
    try:
        response = session.get(zip_url, stream=True)
        response.raise_for_status()
    except RequestException as e:
        logger.error(f"Failed to download {repo_name}. Error: {e}")
        return None
    zip_filename = download_path / f"{repo_name}.zip"
    with open(zip_filename, 'wb') as zip_file:
        shutil.copyfileobj(response.raw, zip_file)
    return zip_filename

def create_session(username: str, github_token: str) -> Session:
    session = requests.Session()
    session.auth = HTTPBasicAuth(username, github_token)
    return session

def current_milli_time() -> int:
    return round(time.time() * 1000)

def download_all_repos(username: str, download_path: Path, github_token: str):
    os.makedirs(download_path, exist_ok=True)
    session = create_session(username, github_token)
    api_url = f"https://api.github.com/search/repositories?q=user:{username}"
    try:
        response = session.get(api_url)
        response.raise_for_status()
    except RequestException as e:
        logger.error(f"Failed to retrieve repositories. Error: {e}")
        return
    repos = response.json()['items']
    min_delay = 500
    current_time = current_milli_time()
    for repo in repos:
        repo_name = repo.get('name')
        if not repo_name:
            logger.warning(f"Invalid name for repo: {repo}")
            continue
        delta_time = current_milli_time() - current_time
        if delta_time < min_delay:
            sleep_time = (min_delay - delta_time) / 1000
            logger.warning(f"Sleeping for: {sleep_time}")
            time.sleep(sleep_time)
        current_time = current_milli_time()
        zip_filename = download_repo_zip(username, repo_name, download_path, session)
        if zip_filename:
            logger.info(f"{repo_name} downloaded to {zip_filename}")

def validate_github_token(github_token: str) -> bool:
    return bool(GITHUB_TOKEN_REGEX.match(github_token))

if __name__ == "__main__":
    username = "metaDAOproject"  # GitHub username
    github_token = "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"  # GitHub token
    download_path = Path.home() / 'GithubRepoDownloader_repos'

    if not username:
        logger.error("GitHub username is empty. Please set GITHUB_USERNAME environment variable.")
        exit(1)

    if not download_path or not download_path.is_absolute():
        logger.error("Download path is invalid. Please set a valid absolute path in DOWNLOAD_PATH environment variable.")
        exit(1)

    if not validate_github_token(github_token):
        logger.error("GitHub token is invalid. Please set a valid GITHUB_TOKEN environment variable.")
        exit(1)

    logger.info("Download Started")
    download_all_repos(username, download_path, github_token)
    logger.info("Download Ended")