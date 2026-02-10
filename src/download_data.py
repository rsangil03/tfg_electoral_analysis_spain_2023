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
DATA_SOURCES = {
    'miteco': {
        'url': 'https://www.miteco.gob.es/es/cartografia-y-sig/ide/descargas/reto-demografico/Reto_demografico.zip',
        'description': 'MITECO - Infraestructura de datos espaciales (Reto Demográfico)',
        'output_dir': MITECO_DIR,
        'is_zip': True
    },
    'infoelectoral_2023': {
        'url': 'https://infoelectoral.interior.gob.es/documentos/elecciones/congreso/202307/02/02_202307_1.xlsx',
        'description': 'Elecciones Generales Julio 2023 - Congreso',
        'output_dir': INFOELECTORAL_DIR,
        'output_filename': '02_202307_1.xlsx',
        'is_zip': False
    },
    'infoelectoral_2019': {
        'url': 'https://infoelectoral.interior.gob.es/documentos/elecciones/congreso/201911/02/02_201911_1.xlsx',
        'description': 'Elecciones Generales Noviembre 2019 - Congreso',
        'output_dir': INFOELECTORAL_DIR,
        'output_filename': '02_201911_1.xlsx',
        'is_zip': False
    }
}


def download_file(url: str, output_path: Path, description: str) -> bool:
    """
    Download a file from URL to output_path.
    
    Args:
        url: URL to download from
        output_path: Path where to save the file
        description: Description of the file being downloaded
    
    Returns:
        True if download was successful, False otherwise
    """
    try:
        logger.info(f"Downloading {description}...")
        logger.info(f"URL: {url}")
        
        # Make request with headers to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        # Get file size if available
        total_size = int(response.headers.get('content-length', 0))
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Download with progress indication
        downloaded = 0
        chunk_size = 8192
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        logger.info(f"Progress: {progress:.1f}%")
        
        logger.info(f"Successfully downloaded to {output_path}")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading {description}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading {description}: {e}")
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
        extract_to.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
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
    
    # Check if data already exists
    if output_dir.exists() and any(output_dir.iterdir()) and not force:
        logger.info(f"Data for {dataset_key} already exists. Use force=True to re-download.")
        return True
    
    # Determine output path
    if source['is_zip']:
        output_path = output_dir.parent / f"{dataset_key}_temp.zip"
    else:
        output_filename = source.get('output_filename', Path(source['url']).name)
        output_path = output_dir / output_filename
    
    # Download the file
    success = download_file(source['url'], output_path, source['description'])
    
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
        status = "✓ SUCCESS" if success else "✗ FAILED"
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
        all_success = all(results.values())
        exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
