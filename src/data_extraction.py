from pathlib import Path
import geopandas as gpd
import pandas as pd

JOING_KEY_MITECO = 'nombre'
INFOELECTORAL_SKIPROWS = 5

def load_miteco(root_dir='../data/raw/miteco/'):
        """
        Loads MITECO shapefiles from the specified directory
        
        Args:
                root_dir (str): The path to the MITECO data directory.
        
        Returns:
                A GeoDataFrame containing the combined data from all MITECO shapefiles.
        """

        gdf_miteco = None

        # We explore all the shapefiles (.shp)
        for path in Path(root_dir).rglob('*.shp'):

                # We load the .shp
                gdf = gpd.read_file(path)

                # First file is the base
                if gdf_miteco is None:
                        gdf_miteco = gdf
                else:
                        # We will only use the columns that
                        # can not be found at gdf_miteco
                        columns = [JOING_KEY_MITECO]

                        for col in gdf.columns:
                                if col not in gdf_miteco.columns and col not in columns:
                                        columns.append(col)

                        # We create the merge data
                        gdf_to_merge = gdf[columns]

                        # We merge the data
                        gdf_miteco = gdf_miteco.merge(
                                gdf_to_merge,
                                on=JOING_KEY_MITECO,
                                how='outer'
                        )
                
        return gdf_miteco

def load_infoelectoral_xlsx(path, convocation_name):
        """
        Loads election .xlsx data from the specified directory

        Args:
                path (str): The path to the .xlsx file.
                convocation_name (str): The election convocation to load.

        Returns:
                A DataFrame containing the data from the specified .xlsx file.
        """
        df = pd.read_excel(path, skiprows=INFOELECTORAL_SKIPROWS)


def load_infoelectoral(root_dir='../data/raw/infoelectoral/'):
        """
        Loads election .xlsx data from the specified directory

        Args:
                root_dir (str): The path to the Infoelectoral data directory.

        Returns:
                A DataFrame containing the combined data from all Infoelectoral .xlsx files.
        """

        # First we 