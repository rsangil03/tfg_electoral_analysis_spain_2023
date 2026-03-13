from pathlib import Path
import geopandas as gpd
import pandas as pd

JOING_KEY_MITECO = 'codmun_ine'
INFOELECTORAL_SKIPROWS = 5
BASE_DIR = Path(__file__).parent.parent

INFOELECTORAL_CONVOCATIONS = [
        {
                'name': '2023',
                'path': BASE_DIR / 'data' / 'raw' / 'infoelectoral' / '02_202307_1.xlsx',
                'parties': ['PP', 'PSOE', 'VOX', 'SUMAR'],
                'coalitions': None
                },
        {
                'name': '2019',
                'path': BASE_DIR / 'data' / 'raw' / 'infoelectoral' / '02_201911_1.xlsx',
                'parties': ['PP', 'PSOE', 'VOX'],
                'coalitions': [
                        {
                                'name': 'SUMAR',
                                'parties': ['PODEMOS-IU', 'ECP-GUANYEM EL CANVI', 'MÁS PAÍS-EQUO',
                                        'PODEMOS-EU', 'MÉS COMPROMÍS', 'MÁS PAÍS', 'M PAÍS-CHA-EQUO', 'MÉS-ESQUERRA']
                                }
                        ]
                }
]

def load_miteco(root_dir=None):
        """
        Loads MITECO shapefiles from the specified directory
        
        Args:
                root_dir (str): The path to the MITECO data directory.
        
        Returns:
                A GeoDataFrame containing the combined data from all MITECO shapefiles.
        """

        if root_dir is None:
                root_dir = BASE_DIR / 'data' / 'raw' / 'miteco'
        else:
                root_dir = Path(root_dir)

        gdf_miteco = None

        # We explore all the shapefiles (.shp)
        for path in root_dir.rglob('*.shp'):

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

def load_infoelectoral():
        """
        Loads election .xlsx data from the specified directory

        Returns:
                A DataFrame containing the combined data from all Infoelectoral .xlsx files.
        """

        df_infoelectoral = None

        for convocation in INFOELECTORAL_CONVOCATIONS:
                path = convocation['path']
                parties = convocation['parties']
                coalitions = convocation['coalitions']

                # We load the .xlsx
                df = pd.read_excel(path, skiprows=INFOELECTORAL_SKIPROWS)

                # Generate INE municipal code from province and municipality codes
                df[JOING_KEY_MITECO] = (
                        df['Código de Provincia'].astype(str).str.zfill(2) +
                        df['Código de Municipio'].astype(str).str.zfill(3)
                )

                coalition_names = []

                # If there are coalitions, we sum the votes of the parties in the coalition
                if coalitions is not None:
                        for coalition in coalitions:
                                coalition_name = coalition['name']
                                coalition_parties = coalition['parties']

                                # We sum the votes of the parties in the coalition
                                df[coalition_name] = df[coalition_parties].sum(axis=1)

                                # We add the coalition name to the list of parties to keep
                                coalition_names.append(coalition_name)

                # We filter the data to only include the specified parties
                columns = [JOING_KEY_MITECO, 'Total censo electoral'] + parties + coalition_names
                df = df[columns]

                # Compute the percentage of votes for each party
                df[parties + coalition_names] = df[parties + coalition_names].div(df['Total censo electoral'], axis=0) * 100

                # Rename everything except the joining key
                df = df.add_suffix('_' + convocation['name'])
                df = df.rename(columns={f'{JOING_KEY_MITECO}_{convocation["name"]}': JOING_KEY_MITECO})

                if df_infoelectoral is None:
                        df_infoelectoral = df
                else:
                        # We merge the data
                        df_infoelectoral = df_infoelectoral.merge(
                                df,
                                on=JOING_KEY_MITECO,
                                how='outer'
                        )

        return df_infoelectoral

def extract_data():
        """
        Extracts and combines data from MITECO shapefiles and Infoelectoral .xlsx files.

        Returns:
                A GeoDataFrame containing the combined data from both sources.
        """

        # Load MITECO data
        gdf_miteco = load_miteco()

        # Load Infoelectoral data
        df_infoelectoral = load_infoelectoral()

        # Merge the two datasets on the joining key
        gdf_combined = gdf_miteco.merge(
                df_infoelectoral,
                on=JOING_KEY_MITECO,
                how='outer'
        )

        return gdf_combined

if __name__ == "__main__":
        gdf_combined = extract_data()
        output_dir = BASE_DIR / 'data' / 'processed'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / 'combined_data.gpkg'
        gdf_combined.to_file(output_path, driver='GPKG')
        print(f"Data extraction and combination completed. Output saved to '{output_path}'.")