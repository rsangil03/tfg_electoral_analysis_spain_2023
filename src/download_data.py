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
from urllib.parse import urlparse
import time

# Base directories
BASE_DIR = Path(__file__).parent.parent
RAW_DATA_DIR = BASE_DIR / 'data' / 'raw'
MITECO_DIR = RAW_DATA_DIR / 'miteco'
INFOELECTORAL_DIR = RAW_DATA_DIR / 'infoelectoral'

# Data sources
DATA_SOURCES = {
    'miteco': {
        'url': 'https://www.miteco.gob.es/es/cartografia-y-sig/ide/descargas/desarrollo-rural/municipios.aspx',
        'description': 'MITECO - Spanish municipalities shapefile',
        'output_dir': MITECO_DIR,
        'note': 'Manual download required from MITECO website'
    },
    'infoelectoral_2023': {
        'url': 'https://infoelectoral.interior.gob.es/opencms/es/elecciones-celebradas/area-de-descargas/',
        'description': 'Infoelectoral - General Elections July 2023',
        'output_dir': INFOELECTORAL_DIR,
        'filename': '02_202307_1.xlsx',
        'note': 'Manual download required from Interior Ministry website'
    },
    'infoelectoral_2019': {
        'url': 'https://infoelectoral.interior.gob.es/opencms/es/elecciones-celebradas/area-de-descargas/',
        'description': 'Infoelectoral - General Elections November 2019',
        'output_dir': INFOELECTORAL_DIR,
        'filename': '02_201911_1.xlsx',
        'note': 'Manual download required from Interior Ministry website'
    }
}


def create_directories():
    """Create necessary directory structure for raw data."""
    print("Creating directory structure...")
    MITECO_DIR.mkdir(parents=True, exist_ok=True)
    INFOELECTORAL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Created: {MITECO_DIR}")
    print(f"✓ Created: {INFOELECTORAL_DIR}")
    print()


def download_file(url, output_path, description=""):
    """
    Download a file from URL to output_path.
    
    Args:
        url (str): URL to download from
        output_path (Path): Path where to save the file
        description (str): Description of the file being downloaded
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Downloading {description}...")
        print(f"URL: {url}")
        
        response = requests.get(url, stream=True, timeout=30)
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


def print_manual_instructions():
    """
    Print instructions for manual data download.
    
    Spanish electoral and geographic data often requires manual download
    from official government websites.
    """
    print("="*80)
    print("MANUAL DOWNLOAD INSTRUCTIONS")
    print("="*80)
    print()
    print("Unfortunately, the required datasets need to be downloaded manually from")
    print("official government sources. Please follow these instructions:\n")
    
    print("1. MITECO - Geographic Data (Shapefiles)")
    print("   " + "-"*70)
    print(f"   URL: {DATA_SOURCES['miteco']['url']}")
    print(f"   Save to: {MITECO_DIR}")
    print("   Steps:")
    print("   - Visit the MITECO website")
    print("   - Download 'Municipios' shapefile (look for .zip file)")
    print("   - Extract all .shp, .dbf, .shx, .prj files to the miteco folder")
    print()
    
    print("2. Infoelectoral - Electoral Results 2023")
    print("   " + "-"*70)
    print(f"   URL: {DATA_SOURCES['infoelectoral_2023']['url']}")
    print(f"   Save as: {INFOELECTORAL_DIR / DATA_SOURCES['infoelectoral_2023']['filename']}")
    print("   Steps:")
    print("   - Visit Interior Ministry's election data portal")
    print("   - Navigate to: Congreso > 2023 > Julio")
    print("   - Download municipality-level results (XLSX format)")
    print("   - Rename to: 02_202307_1.xlsx")
    print()
    
    print("3. Infoelectoral - Electoral Results 2019")
    print("   " + "-"*70)
    print(f"   URL: {DATA_SOURCES['infoelectoral_2019']['url']}")
    print(f"   Save as: {INFOELECTORAL_DIR / DATA_SOURCES['infoelectoral_2019']['filename']}")
    print("   Steps:")
    print("   - Visit Interior Ministry's election data portal")
    print("   - Navigate to: Congreso > 2019 > Noviembre")
    print("   - Download municipality-level results (XLSX format)")
    print("   - Rename to: 02_201911_1.xlsx")
    print()
    
    print("="*80)
    print("After downloading all files, run the data extraction script:")
    print("  python src/data_extraction.py")
    print("="*80)
    print()


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
    file_2023 = INFOELECTORAL_DIR / DATA_SOURCES['infoelectoral_2023']['filename']
    if file_2023.exists():
        status['infoelectoral_2023'] = True
        print(f"✓ Electoral data 2023 found: {file_2023}")
    else:
        print(f"✗ Electoral data 2023 not found: {file_2023}")
    
    # Check Infoelectoral 2019
    file_2019 = INFOELECTORAL_DIR / DATA_SOURCES['infoelectoral_2019']['filename']
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
        print("  Please follow the manual download instructions below.")
    
    print()
    return status, all_found


def main():
    """
    Main function to download required datasets.
    """
    print("="*80)
    print("Electoral Analysis Spain 2023 - Data Download Script")
    print("="*80)
    print()
    
    # Create directory structure
    create_directories()
    
    # Check existing files
    status, all_found = check_existing_files()
    
    if all_found:
        print("All data files are ready. No action needed.")
        return 0
    
    # Print manual download instructions
    print_manual_instructions()
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
