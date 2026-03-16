from pathlib import Path
import geopandas as gpd
import pandas as pd

from config import *

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
                        gdf_to_merge = gdf[columns].copy()

                        # We merge the data
                        gdf_miteco = gdf_miteco.merge(
                                gdf_to_merge,
                                on=JOING_KEY_MITECO,
                                how='outer'
                        )

        # For each row, we compute the centroid of the geometry and store it in a new column 'centroid'
        gdf_miteco['centroid_x'] = gdf_miteco.geometry.centroid.x
        gdf_miteco['centroid_y'] = gdf_miteco.geometry.centroid.y
                        
        return gdf_miteco

def load_infoelectoral():
        """
        Loads election .xlsx data from the specified directory

        Returns:
                A DataFrame containing the combined data from all Infoelectoral .xlsx files.
        """

        df_convocations = []

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
                all_parties = parties + coalition_names
                columns = [JOING_KEY_MITECO, 'Total censo electoral'] + all_parties
                df = df[columns].copy()

                # Compute the percentage of votes for each party
                df[all_parties] = df[all_parties].div(df['Total censo electoral'], axis=0) * 100

                # Rename everything except the joining key
                df = df.add_suffix('_' + convocation['name'])
                df = df.rename(columns={f'{JOING_KEY_MITECO}_{convocation["name"]}': JOING_KEY_MITECO})

                df_convocations.append(df)

        # We merge all the convocations on the joining key
        df_infoelectoral = df_convocations[0]
        for df in df_convocations[1:]:
                df_infoelectoral = df_infoelectoral.merge(
                        df,
                        on=JOING_KEY_MITECO,
                        how='outer'
                )

        return df_infoelectoral

def compute_vote_differences(df, parties, convocation1, convocation2):
        """
        Computes the difference in vote percentages between two convocations for the specified parties.

        Args:
                df (DataFrame): The DataFrame containing the election data.
                parties (list): A list of party names to compute differences for.
                convocation1 (str): The name of the first convocation (e.g., '2019').
                convocation2 (str): The name of the second convocation (e.g., '2023').

        Returns:
                A DataFrame with the computed vote differences for each party.
        """

        for party in parties:
                col1 = f'{party}_{convocation1}'
                col2 = f'{party}_{convocation2}'
                diff_col = f'{party}_diff_{convocation2}_{convocation1}'

                if col1 in df.columns and col2 in df.columns:
                        df[diff_col] = df[col2] - df[col1]
                else:
                        print(f"Warning: Columns '{col1}' or '{col2}' not found in DataFrame. Skipping difference computation for party '{party}'.")

        return df

def extract_data():
        """
        Extracts and combines data from MITECO shapefiles and Infoelectoral .xlsx files.

        Returns:
                A GeoDataFrame containing the combined data from both sources.
        """

        # Load MITECO data
        gdf_miteco = load_miteco()
        print(f"MITECO data loaded with {len(gdf_miteco)} records.")

        # Load Infoelectoral data
        df_infoelectoral = load_infoelectoral()
        print(f"Infoelectoral data loaded with {len(df_infoelectoral)} records.")

        # Merge the two datasets on the joining key
        gdf_combined = gdf_miteco.merge(
                df_infoelectoral,
                on=JOING_KEY_MITECO,
                how='outer'
        )
        print(f"Data combined with {len(gdf_combined)} records after merging.")

        # Compute vote differences between 2023 and 2019 for the specified parties
        parties = ['PP', 'PSOE', 'VOX', 'SUMAR']
        gdf_combined = compute_vote_differences(gdf_combined, parties, '2019', '2023')
        print("Vote differences computed for parties: " + ", ".join(parties))

        return gdf_combined

if __name__ == "__main__":
        gdf_combined = extract_data()
        output_dir = BASE_DIR / 'data' / 'processed'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / 'combined_data.gpkg'
        gdf_combined.to_file(output_path, driver='GPKG')
        print(f"Data extraction and combination completed. Output saved to '{output_path}'.")