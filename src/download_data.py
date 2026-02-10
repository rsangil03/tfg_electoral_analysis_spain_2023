#!/usr/bin/env python3
"""
Automated data download script for Electoral Analysis Spain 2023 project.

This script downloads the required datasets from official sources:
- MITECO: Geographic shapefiles for Spanish municipalities
- Infoelectoral: Electoral results for 2019 and 2023 general elections
"""

import requests
import zipfile
from pathlib import Path
import sys
from bs4 import BeautifulSoup
import time
import re

# Base directories
BASE_DIR = Path(__file__).parent.parent
RAW_DATA_DIR = BASE_DIR / 'data' / 'raw'
MITECO_DIR = RAW_DATA_DIR / 'miteco'
INFOELECTORAL_DIR = RAW_DATA_DIR / 'infoelectoral'

# Data sources
INFOELECTORAL_BASE_URL = 'https://infoelectoral.interior.gob.es'
INFOELECTORAL_DOWNLOADS = 'https://infoelectoral.interior.gob.es/opencms/es/elecciones-celebradas/area-de-descargas/'
MITECO_BASE_URL = 'https://www.miteco.gob.es'

# User agent to avoid blocking
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}


def create_directories():
    """Create necessary directory structure for raw data."""
    print("Creating directory structure...")
    MITECO_DIR.mkdir(parents=True, exist_ok=True)
    INFOELECTORAL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Created: {MITECO_DIR}")
    print(f"✓ Created: {INFOELECTORAL_DIR}")
    print()


def download_file(url, output_path, description="", session=None):
    """
    Download a file from URL to output_path.
    
    Args:
        url (str): URL to download from
        output_path (Path): Path where to save the file
        description (str): Description of the file being downloaded
        session: requests.Session object for persistent connections
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Downloading {description}...")
        print(f"URL: {url}")
        
        if session:
            response = session.get(url, stream=True, timeout=60, headers=HEADERS)
        else:
            response = requests.get(url, stream=True, timeout=60, headers=HEADERS)
        
        response.raise_for_status()
        
        # Get file size if available
        total_size = int(response.headers.get('content-length', 0))
        
        with open(output_path, 'wb') as f:
            if total_size > 0:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress = (downloaded / total_size) * 100
                        print(f"\rProgress: {progress:.1f}%", end='', flush=True)
                print()  # New line after progress
            else:
                f.write(response.content)
        
        print(f"✓ Downloaded: {output_path}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Error downloading {description}: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def extract_zip(zip_path, extract_to):
    """
    Extract a ZIP file to specified directory.
    
    Args:
        zip_path (Path): Path to ZIP file
        extract_to (Path): Directory to extract to
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Extracting {zip_path.name}...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"✓ Extracted to: {extract_to}")
        return True
    except Exception as e:
        print(f"✗ Error extracting {zip_path}: {e}")
        return False


def scrape_infoelectoral_data(year, month_name):
    """
    Scrape Infoelectoral website to find and download electoral data.
    
    Args:
        year (str): Election year (e.g., '2023', '2019')
        month_name (str): Month name in Spanish (e.g., 'Julio', 'Noviembre')
    
    Returns:
        str or None: Download URL if found, None otherwise
    """
    try:
        print(f"Scraping Infoelectoral for {month_name} {year} data...")
        
        session = requests.Session()
        
        # First, get the main downloads page
        response = session.get(INFOELECTORAL_DOWNLOADS, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for links containing the year
        year_links = soup.find_all('a', href=True, string=re.compile(year))
        
        if not year_links:
            # Try alternative approach: look for links in the page
            year_links = soup.find_all('a', href=True)
            year_links = [link for link in year_links if year in link.get_text()]
        
        print(f"Found {len(year_links)} potential links for year {year}")
        
        # Try to find the specific election data
        # Looking for patterns like "Congreso", "Resultados", "Municipios"
        for link in year_links:
            href = link.get('href')
            if not href.startswith('http'):
                href = INFOELECTORAL_BASE_URL + href if href.startswith('/') else INFOELECTORAL_BASE_URL + '/' + href
            
            # Visit the year page
            print(f"Exploring: {href}")
            page_response = session.get(href, headers=HEADERS, timeout=30)
            page_soup = BeautifulSoup(page_response.content, 'html.parser')
            
            # Look for download links (xlsx, xls, zip)
            download_links = page_soup.find_all('a', href=re.compile(r'\.(xlsx?|zip)$', re.IGNORECASE))
            
            # Filter for municipality-level data (municipios, mesas, etc.)
            for dl_link in download_links:
                dl_href = dl_link.get('href')
                dl_text = dl_link.get_text().lower()
                
                if 'municipi' in dl_text or 'mesa' in dl_text or '02_' in dl_href:
                    if not dl_href.startswith('http'):
                        dl_href = INFOELECTORAL_BASE_URL + dl_href if dl_href.startswith('/') else href.rsplit('/', 1)[0] + '/' + dl_href
                    
                    print(f"✓ Found potential data file: {dl_href}")
                    return dl_href, session
        
        # Alternative: Try direct URL patterns (common structure)
        # Pattern: /files/elecciones/congreso/YYYYMM/02_YYYYMM_1.xlsx
        month_numbers = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        }
        
        month_num = month_numbers.get(month_name.lower())
        if month_num:
            # Try common URL patterns
            patterns = [
                f"{INFOELECTORAL_BASE_URL}/docxl/02_{year}{month_num}_1.xlsx",
                f"{INFOELECTORAL_BASE_URL}/static/elecciones/congreso/{year}{month_num}/02_{year}{month_num}_1.xlsx",
            ]
            
            for pattern_url in patterns:
                print(f"Trying direct URL pattern: {pattern_url}")
                test_response = session.head(pattern_url, headers=HEADERS, timeout=10)
                if test_response.status_code == 200:
                    print(f"✓ Found data file via direct URL")
                    return pattern_url, session
        
        print(f"✗ Could not find download link for {month_name} {year}")
        return None, session
        
    except Exception as e:
        print(f"✗ Error scraping Infoelectoral: {e}")
        return None, None


def download_infoelectoral_data():
    """
    Download electoral data from Infoelectoral website.
    
    Returns:
        bool: True if all downloads successful, False otherwise
    """
    print("="*80)
    print("Downloading Infoelectoral Electoral Data")
    print("="*80)
    print()
    
    elections = [
        {'year': '2023', 'month': 'Julio', 'filename': '02_202307_1.xlsx'},
        {'year': '2019', 'month': 'Noviembre', 'filename': '02_201911_1.xlsx'}
    ]
    
    all_success = True
    
    for election in elections:
        output_file = INFOELECTORAL_DIR / election['filename']
        
        if output_file.exists():
            print(f"✓ {election['filename']} already exists. Skipping.\n")
            continue
        
        print(f"Searching for {election['month']} {election['year']} data...")
        
        # Try scraping
        download_url, session = scrape_infoelectoral_data(election['year'], election['month'])
        
        if download_url:
            success = download_file(
                download_url, 
                output_file, 
                f"Electoral data {election['month']} {election['year']}",
                session
            )
            all_success = all_success and success
        else:
            print(f"⚠ Could not automatically download {election['filename']}")
            print(f"  Please download manually from: {INFOELECTORAL_DOWNLOADS}")
            print(f"  Navigate to: Congreso > {election['year']} > {election['month']}")
            print(f"  Save as: {output_file}\n")
            all_success = False
        
        time.sleep(2)  # Be polite to the server
    
    return all_success


def download_miteco_data():
    """
    Download geographic data from MITECO website.
    
    Returns:
        bool: True if download successful, False otherwise
    """
    print("="*80)
    print("Downloading MITECO Geographic Data")
    print("="*80)
    print()
    
    # Check if shapefiles already exist
    existing_shp = list(MITECO_DIR.rglob('*.shp'))
    if existing_shp:
        print(f"✓ MITECO shapefiles already exist ({len(existing_shp)} files). Skipping.\n")
        return True
    
    try:
        print("Searching for MITECO municipality shapefiles...")
        
        # MITECO data is often available through their FTP or download portals
        # Common URLs for Spanish administrative boundaries
        miteco_urls = [
            'https://www.miteco.gob.es/content/dam/miteco/es/cartografia-y-sig/sig-descargas/09_lineas_limite/municipios_inspire_peninbal_wgs84.zip',
            'https://centrodedescargas.cnig.es/CentroDescargas/descargaDir',
        ]
        
        session = requests.Session()
        
        # Try to find and download shapefile
        # Option 1: Direct MITECO download
        for url in miteco_urls:
            try:
                print(f"Trying: {url}")
                response = session.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
                
                if response.status_code == 200:
                    zip_path = MITECO_DIR / 'municipios.zip'
                    success = download_file(url, zip_path, "MITECO municipalities shapefile", session)
                    
                    if success:
                        extract_zip(zip_path, MITECO_DIR)
                        zip_path.unlink()  # Remove zip after extraction
                        return True
            except:
                continue
        
        # If automatic download fails, provide instructions
        print("⚠ Could not automatically download MITECO data.")
        print("\nManual download required:")
        print("Option 1: MITECO Website")
        print("  URL: https://www.miteco.gob.es/es/cartografia-y-sig/ide/descargas/desarrollo-rural/municipios.aspx")
        print("  Download the municipality shapefile and extract to:", MITECO_DIR)
        print()
        print("Option 2: IGN (Instituto Geográfico Nacional)")
        print("  URL: https://centrodedescargas.cnig.es/CentroDescargas/")
        print("  Search for: 'Líneas límite municipales'")
        print("  Download and extract to:", MITECO_DIR)
        print()
        
        return False
        
    except Exception as e:
        print(f"✗ Error downloading MITECO data: {e}")
        return False


def check_existing_files():
    """
    Check if required data files already exist.
    
    Returns:
        dict: Status of each required file
    """
    print("Checking for existing data files...\n")
    
    status = {
        'miteco_shapefiles': False,
        'infoelectoral_2023': False,
        'infoelectoral_2019': False
    }
    
    # Check MITECO shapefiles
    if MITECO_DIR.exists():
        shp_files = list(MITECO_DIR.rglob('*.shp'))
        if shp_files:
            status['miteco_shapefiles'] = True
            print(f"✓ MITECO shapefiles found: {len(shp_files)} file(s)")
        else:
            print(f"✗ MITECO shapefiles not found in {MITECO_DIR}")
    else:
        print(f"✗ MITECO directory does not exist: {MITECO_DIR}")
    
    # Check Infoelectoral 2023
    file_2023 = INFOELECTORAL_DIR / '02_202307_1.xlsx'
    if file_2023.exists():
        status['infoelectoral_2023'] = True
        print(f"✓ Electoral data 2023 found: {file_2023}")
    else:
        print(f"✗ Electoral data 2023 not found: {file_2023}")
    
    # Check Infoelectoral 2019
    file_2019 = INFOELECTORAL_DIR / '02_201911_1.xlsx'
    if file_2019.exists():
        status['infoelectoral_2019'] = True
        print(f"✓ Electoral data 2019 found: {file_2019}")
    else:
        print(f"✗ Electoral data 2019 not found: {file_2019}")
    
    print()
    
    all_found = all(status.values())
    if all_found:
        print("✓ All required data files are present!")
        print("  You can proceed with data extraction.")
    else:
        print("⚠ Some data files are missing.")
        print("  Attempting automatic download...")
    
    print()
    return status, all_found


def main():
    """
    Main function to download required datasets.
    """
    print("="*80)
    print("Electoral Analysis Spain 2023 - Automated Data Download")
    print("="*80)
    print()
    
    # Create directory structure
    create_directories()
    
    # Check existing files
    status, all_found = check_existing_files()
    
    if all_found:
        print("All data files are ready. No action needed.")
        return 0
    
    # Download missing data
    print("Starting automatic downloads...\n")
    
    # Download Infoelectoral data
    if not status['infoelectoral_2023'] or not status['infoelectoral_2019']:
        infoelectoral_success = download_infoelectoral_data()
    else:
        infoelectoral_success = True
    
    # Download MITECO data
    if not status['miteco_shapefiles']:
        miteco_success = download_miteco_data()
    else:
        miteco_success = True
    
    # Final status
    print("\n" + "="*80)
    print("Download Summary")
    print("="*80)
    
    status_final, all_found_final = check_existing_files()
    
    if all_found_final:
        print("✓ SUCCESS: All data files downloaded successfully!")
        print("\nNext steps:")
        print("  1. Run: python src/data_extraction.py")
        print("  2. Check the processed data in: data/processed/")
        return 0
    else:
        print("⚠ PARTIAL SUCCESS: Some files require manual download.")
        print("  Please follow the instructions above to complete the setup.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
