#!/usr/bin/env python3
"""
Automatic dataset downloader for Electoral Analysis Spain 2023 TFG

This script downloads datasets from official sources:
- MITECO (Ministerio para la Transición Ecológica y el Reto Demográfico)
- Infoelectoral (Ministerio del Interior)

Sources:
    MITECO: https://www.miteco.gob.es/es/cartografia-y-sig/ide/descargas/reto-demografico.html
    Infoelectoral: https://infoelectoral.interior.gob.es/es/elecciones-celebradas/area-de-descargas/

Accessed: 3 February 2026
"""

import requests
import zipfile
from pathlib import Path
import logging
from typing import Optional
import time
import urllib3

# Disable SSL warnings (only for problematic government sites)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Base directories
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data' / 'raw'
MITECO_DIR = DATA_DIR / 'miteco'
INFOELECTORAL_DIR = DATA_DIR / 'infoelectoral'

# Data sources URLs
# Note: MITECO link redirects to HTML page, using alternative approach
DATA_SOURCES = {
    'miteco': {
        'description': 'MITECO - Infraestructura de datos espaciales (Reto Demográfico)',
        'output_dir': MITECO_DIR,
        'is_zip': False,
        'manual': True,  # Requires manual download
        'instructions': (
            "MITECO data requires manual download:\n"
            "1. Visit: https://www.miteco.gob.es/es/cartografia-y-sig/ide/descargas/reto-demografico.html\n"
            "2. Download the shapefile datasets you need\n"
            "3. Extract them to: data/raw/miteco/\n"
            "Common datasets: Población, Envejecimiento, Densidad, etc."
        )
    },
    'infoelectoral_2023': {
        'url': 'https://infoelectoral.interior.gob.es/documentos/elecciones/congreso/202307/02/02_202307_1.xlsx',
        'description': 'Elecciones Generales Julio 2023 - Congreso',
        'output_dir': INFOELECTORAL_DIR,
        'output_filename': '02_202307_1.xlsx',
        'is_zip': False,
        'verify_ssl': False  # Government site has SSL issues
    },
    'infoelectoral_2019': {
        'url': 'https://infoelectoral.interior.gob.es/documentos/elecciones/congreso/201911/02/02_201911_1.xlsx',
        'description': 'Elecciones Generales Noviembre 2019 - Congreso',
        'output_dir': INFOELECTORAL_DIR,
        'output_filename': '02_201911_1.xlsx',
        'is_zip': False,
        'verify_ssl': False  # Government site has SSL issues
    }
}


def download_file(url: str, output_path: Path, description: str, verify_ssl: bool = True) -> bool:
    """
    Download a file from URL to output_path.
    
    Args:
        url: URL to download from
        output_path: Path where to save the file
        description: Description of the file being downloaded
        verify_ssl: Whether to verify SSL certificates
    
    Returns:
        True if download was successful, False otherwise
    """
    try:
        logger.info(f"Downloading {description}...")
        logger.info(f"URL: {url}")
        
        if not verify_ssl:
            logger.warning("SSL verification disabled for this download")
        
        # Make request with headers to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }
        
        response = requests.get(
            url, 
            headers=headers, 
            stream=True, 
            timeout=60,
            verify=verify_ssl,
            allow_redirects=True
        )
        response.raise_for_status()
        
        # Check if we got HTML instead of the expected file
        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' in content_type:
            logger.warning(f"Received HTML instead of file. Content-Type: {content_type}")
            logger.warning("This might be a redirect page or access restriction.")
        
        # Get file size if available
        total_size = int(response.headers.get('content-length', 0))
        
        if total_size > 0:
            logger.info(f"File size: {total_size / (1024*1024):.2f} MB")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Download with progress indication
        downloaded = 0
        chunk_size = 8192
        last_progress = 0
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = int((downloaded / total_size) * 100)
                        # Only log every 10%
                        if progress >= last_progress + 10:
                            logger.info(f"Progress: {progress}%")
                            last_progress = progress
        
        # Verify the download
        if output_path.stat().st_size == 0:
            logger.error("Downloaded file is empty!")
            output_path.unlink()
            return False
        
        logger.info(f"Successfully downloaded to {output_path}")
        logger.info(f"Downloaded size: {output_path.stat().st_size / 1024:.2f} KB")
        return True
        
    except requests.exceptions.SSLError as e:
        logger.error(f"SSL Error downloading {description}: {e}")
        logger.error("Try running with verify_ssl=False or update your certificates")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading {description}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading {description}: {e}")
        return False


def is_valid_zip(file_path: Path) -> bool:
    """
    Check if a file is a valid ZIP file.
    
    Args:
        file_path: Path to the file to check
    
    Returns:
        True if valid ZIP, False otherwise
    """
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # Try to read the file list
            zip_ref.namelist()
        return True
    except zipfile.BadZipFile:
        return False
    except Exception:
        return False


def extract_zip(zip_path: Path, extract_to: Path) -> bool:
    """
    Extract a ZIP file to specified directory.
    
    Args:
        zip_path: Path to the ZIP file
        extract_to: Directory where to extract files
    
    Returns:
        True if extraction was successful, False otherwise
    """
    try:
        logger.info(f"Extracting {zip_path.name}...")
        
        # Verify it's a valid ZIP
        if not is_valid_zip(zip_path):
            logger.error(f"File is not a valid ZIP archive: {zip_path}")
            logger.info("The file might be HTML or corrupted. Check the URL.")
            return False
        
        extract_to.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            members = zip_ref.namelist()
            logger.info(f"Extracting {len(members)} files...")
            zip_ref.extractall(extract_to)
        
        logger.info(f"Successfully extracted to {extract_to}")
        
        # Remove zip file after extraction
        zip_path.unlink()
        logger.info(f"Removed temporary ZIP file")
        
        return True
        
    except zipfile.BadZipFile as e:
        logger.error(f"Invalid ZIP file: {e}")
        return False
    except Exception as e:
        logger.error(f"Error extracting ZIP: {e}")
        return False


def download_dataset(dataset_key: str, force: bool = False) -> bool:
    """
    Download a specific dataset.
    
    Args:
        dataset_key: Key of the dataset in DATA_SOURCES
        force: If True, download even if files already exist
    
    Returns:
        True if download was successful, False otherwise
    """
    if dataset_key not in DATA_SOURCES:
        logger.error(f"Unknown dataset: {dataset_key}")
        return False
    
    source = DATA_SOURCES[dataset_key]
    output_dir = source['output_dir']
    
    # Handle manual download datasets
    if source.get('manual', False):
        logger.warning(f"{dataset_key} requires manual download")
        logger.info(source['instructions'])
        return False
    
    # Check if data already exists
    if not force:
        if source['is_zip']:
            if output_dir.exists() and any(output_dir.iterdir()):
                logger.info(f"Data for {dataset_key} already exists. Use --force to re-download.")
                return True
        else:
            output_filename = source.get('output_filename', Path(source['url']).name)
            output_path = output_dir / output_filename
            if output_path.exists():
                logger.info(f"File {output_filename} already exists. Use --force to re-download.")
                return True
    
    # Determine output path
    if source['is_zip']:
        output_path = output_dir.parent / f"{dataset_key}_temp.zip"
    else:
        output_filename = source.get('output_filename', Path(source['url']).name)
        output_path = output_dir / output_filename
    
    # Download the file
    verify_ssl = source.get('verify_ssl', True)
    success = download_file(source['url'], output_path, source['description'], verify_ssl=verify_ssl)
    
    if not success:
        return False
    
    # Extract if it's a ZIP file
    if source['is_zip']:
        success = extract_zip(output_path, output_dir)
    
    return success


def download_all_datasets(force: bool = False) -> dict:
    """
    Download all datasets.
    
    Args:
        force: If True, download even if files already exist
    
    Returns:
        Dictionary with results for each dataset
    """
    results = {}
    
    logger.info("="*60)
    logger.info("Starting download of all datasets")
    logger.info("="*60)
    
    for dataset_key in DATA_SOURCES.keys():
        logger.info(f"\nProcessing {dataset_key}...")
        results[dataset_key] = download_dataset(dataset_key, force=force)
        
        # Add small delay between downloads to be respectful to servers
        time.sleep(2)
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("Download Summary")
    logger.info("="*60)
    
    for dataset_key, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED/MANUAL"
        logger.info(f"{dataset_key}: {status}")
    
    return results


def main():
    """
    Main function to download all datasets.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Download datasets for Electoral Analysis Spain 2023'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-download even if files exist'
    )
    parser.add_argument(
        '--dataset',
        type=str,
        choices=list(DATA_SOURCES.keys()),
        help='Download only a specific dataset'
    )
    
    args = parser.parse_args()
    
    if args.dataset:
        # Download specific dataset
        success = download_dataset(args.dataset, force=args.force)
        exit(0 if success else 1)
    else:
        # Download all datasets
        results = download_all_datasets(force=args.force)
        # Consider it success if at least automatic downloads worked
        auto_results = {k: v for k, v in results.items() if not DATA_SOURCES[k].get('manual', False)}
        all_success = all(auto_results.values()) if auto_results else False
        exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
