from pathlib import Path
import geopandas as gpd
import pandas as pd

from src.config import *

def load_miteco():
    data_dir = BASE_DIR / 'data' / 'raw' / 'miteco'
    
    shp_files = list(data_dir.glob('*.shp'))
    if not shp_files:
        raise FileNotFoundError(f"No .shp file found in {data_dir}")
    
    gdf = gpd.read_file(shp_files[0])

    gdf[V_AREA] = gdf.geometry.to_crs(epsg=25830).area / 1e6

    centroids_wgs84 = gdf.geometry.to_crs(epsg=25830).centroid.to_crs(epsg=4326)
    gdf[V_LATITUDE] = centroids_wgs84.y
    gdf[V_LONGITUDE] = centroids_wgs84.x

    gdf = gdf.to_crs(epsg=4326)

    rename_dict = {
        'codmun_ine': V_MUNICIPALITY,
        'nombre': V_MUNICIPALITY_NAME,
        'cod_ccaa': V_CCAA,
        'ccaa': V_CCAA_NAME,
        'cod_pro': V_PROVINCE,
        'provincia': V_PROVINCE_NAME
    }
    
    gdf.rename(columns=rename_dict, inplace=True)

    final_cols = [
        V_MUNICIPALITY, V_MUNICIPALITY_NAME, V_CCAA, V_CCAA_NAME, 
        V_PROVINCE, V_PROVINCE_NAME, V_AREA, V_LATITUDE, 
        V_LONGITUDE, 'geometry'
    ]

    existing_cols = [col for col in final_cols if col in gdf.columns]
    
    if 'geometry' not in existing_cols:
        existing_cols.append('geometry')

    return gdf[existing_cols].copy()

def load_demographics_ine(year=2023):
    """
    Reads the demographic CSV and extracts population, mean age, 
    % of foreign-born population, and population density per municipality.
    
    Args:
        year (int): The year of the data to extract (default 2023 to match config).
                                             
    Returns:
        DataFrame containing the extracted demographic metrics.
    """
    
    csv_path = BASE_DIR / 'data' / 'raw' / 'ine' / INE_DEMOGRAPHICS
    
    # Read the CSV. The parameters thousands='.' and decimal=',' automatically 
    # parse the Spanish number formats (e.g. 49.128.297 or 44,55) into standard floats.
    df = pd.read_csv(csv_path, sep=';', thousands='.', decimal=',', na_values=['.', '..', '...', '-'])
    
    # Filter out National and Provincial aggregate rows (where the 'Municipios' column is missing)
    df = df.dropna(subset=['Municipios']).copy()
    
    # Filter by the specified year
    df = df[df['Periodo'] == year]
    
    # Extract the 5-digit INE Municipality Code from the beginning of the string
    df[V_MUNICIPALITY] = df['Municipios'].str[:5].astype(str)
    
    # Total Population
    pop_total = df[
        (df['Conceptos Demográficos'] == 'Población') & 
        (df['Sexo'] == 'Total') & 
        (df['Lugar de nacimiento'] == 'Total')
    ][[V_MUNICIPALITY, 'Total']].rename(columns={'Total': V_POPULATION_2023})
    
    # Foreign-born Population (Temporary column)
    pop_foreign = df[
        (df['Conceptos Demográficos'] == 'Población') & 
        (df['Sexo'] == 'Total') & 
        (df['Lugar de nacimiento'] == 'Extranjero')
    ][[V_MUNICIPALITY, 'Total']].rename(columns={'Total': 'foreign_pop'})
    
    # Mean Age
    mean_age = df[
        (df['Conceptos Demográficos'] == 'Edad media de la población') & 
        (df['Sexo'] == 'Total') & 
        (df['Lugar de nacimiento'] == 'Total')
    ][[V_MUNICIPALITY, 'Total']].rename(columns={'Total': V_MEAN_AGE})
    
    # Merge the individual metrics on the municipality code
    metrics_df = pop_total.merge(pop_foreign, on=V_MUNICIPALITY, how='left')
    metrics_df = metrics_df.merge(mean_age, on=V_MUNICIPALITY, how='left')
    
    # Calculate % of the population born out of Spain
    metrics_df[V_FOREIGN_POPULATION] = (metrics_df['foreign_pop'] / metrics_df[V_POPULATION_2023]) * 100
    
    # Keep only the relevant columns 
    metrics_df = metrics_df[[V_MUNICIPALITY, V_POPULATION_2023, V_MEAN_AGE, V_FOREIGN_POPULATION]]

    return metrics_df

def compute_population_density(df):
    """
    Computes population density (inhabitants/km2) for each municipality.

    Args:
        df (DataFrame): The DataFrame containing population and area data.

    Returns:
        DataFrame with an additional column for population density.
    """
    if V_POPULATION_2023 in df.columns and V_AREA in df.columns:
        df[V_DENSITY] = df[V_POPULATION_2023] / df[V_AREA]
    else:
        print(f"Warning: Columns '{V_POPULATION_2023}' or '{V_AREA}' not found in DataFrame. Cannot compute population density.")
    
    return df

def load_higher_education_ine(year=2023):
    """
    Reads the education level CSV and extracts the percentage of the
    population (aged 15 and over) with higher education by municipality.
    
    Args:
        year (int): The year of the data to extract (default 2023).
                                             
    Returns:
        DataFrame with the higher education metric per municipality.
    """
    
    csv_path = BASE_DIR / 'data' / 'raw' / 'ine' / INE_HIGHER_EDUCATION 

    # We read the CSV with the same parameters as in load_demographics_ine
    df = pd.read_csv(csv_path, sep=';', thousands='.', decimal=',', na_values=['.', '..', '...', '-'])

    df = df.dropna(subset=['Municipios']).copy()
    
    # We ignore the rows that contain data for censal sections, which are not relevant for our analysis
    df = df[df['Secciones'].isna()]
    
    df = df[(df['Periodo'] == year) & (df['Sexo'] == 'Total')]
    
    # Extract the 5-digit INE Municipality Code from the beginning of the string
    df[V_MUNICIPALITY] = df['Municipios'].str[:5].astype(str)
    
    # Base population: population over 15 years old
    pop_15_plus = df[
        df['Nivel de formación alcanzado'] == 'Total'
    ][[V_MUNICIPALITY, 'Total']].rename(columns={'Total': 'pop_over_15'})
    
    # Population with higher education: population over 15 years old with higher education
    pop_higher_ed = df[
        df['Nivel de formación alcanzado'] == 'Educación superior'
    ][[V_MUNICIPALITY, 'Total']].rename(columns={'Total': 'pop_higher_ed'})
    
    # Cruzar ambos dataframes
    metrics_df = pop_15_plus.merge(pop_higher_ed, on=V_MUNICIPALITY, how='outer')
    
    # Calcular el porcentaje (asegúrate de renombrar la constante en config.py)
    metrics_df[V_HIGHER_EDUCATION] = (
        metrics_df['pop_higher_ed'] / metrics_df['pop_over_15']
    ) * 100
    
    # Quedarnos solo con la clave de cruce y la métrica final
    metrics_df = metrics_df[[V_MUNICIPALITY, V_HIGHER_EDUCATION]]

    return metrics_df

def load_economic_ine(year=2023):
    """
    Reads INE economic data and extracts the
    Net Average Income per Person for each municipality.

    Args:
        year (int): The year of the data to extract (default 2023).

    Returns:
        DataFrame with the net average income by municipality.
    """
    
    # Asegúrate de usar el nombre correcto del CSV en tu carpeta raw
    csv_path = BASE_DIR / 'data' / 'raw' / 'ine' / INE_INCOME
    
    df = pd.read_csv(
        csv_path, 
        sep=';', 
        thousands='.', 
        decimal=',', 
        na_values=['.', '..', '...', '-', '""', '"" '],
        skipinitialspace=True
    )
    
    df = df.dropna(subset=['Municipios']).copy()
    
    if 'Distritos' in df.columns:
        df = df[df['Distritos'].isna()]
    if 'Secciones' in df.columns:
        df = df[df['Secciones'].isna()]
        
    df = df[
        (df['Periodo'] == year) & 
        (df['Indicadores de renta media'] == 'Renta neta media por persona')
    ].copy()
        
    df[V_MUNICIPALITY] = df['Municipios'].str[:5].astype(str)
    
    df_economic = df[[V_MUNICIPALITY, 'Total']].rename(columns={'Total': V_MEAN_NET_INCOME})
            
    return df_economic

def load_population_change_ine():
    """
    Loads 2019 and 2023 municipal register population data, 
    calculates the % change, and returns a DataFrame ready to be merged.

    Returns:
        DataFrame with the net average income by municipality.
    """
    # Assuming the files are stored in data/raw/ine/ (adjust path as needed in your project)
    # If they are in the root directory for now, you can change the path to BASE_DIR / 'pobmun19.xlsx - dic18.csv'
    data_dir = BASE_DIR / 'data' / 'raw' / 'ine' 
    
    # Read the files, skipping the first row because of the title
    # Force CPRO and CMUN to be strings to preserve leading zeros
    df_19 = pd.read_excel(data_dir /INE_REGISTER_2019, header=1, dtype={'CPRO': str, 'CMUN': str})
    df_23 = pd.read_excel(data_dir / INE_REGISTER_2023, header=1, dtype={'CPRO': str, 'CMUN': str})
    
    # Create the 5-digit INE municipality code
    df_19[V_MUNICIPALITY] = df_19['CPRO'].str.zfill(2) + df_19['CMUN'].str.zfill(3)
    df_23[V_MUNICIPALITY] = df_23['CPRO'].str.zfill(2) + df_23['CMUN'].str.zfill(3)
    
    # Keep only the relevant columns to make the merge cleaner
    df_19 = df_19[[V_MUNICIPALITY, 'POB19']]
    df_23 = df_23[[V_MUNICIPALITY, 'POB23']]
    
    # Merge both years on the municipality code
    df_pop = pd.merge(df_19, df_23, on=V_MUNICIPALITY, how='inner')
    
    # Ensure population columns are numeric
    df_pop['POB19'] = pd.to_numeric(df_pop['POB19'], errors='coerce')
    df_pop['POB23'] = pd.to_numeric(df_pop['POB23'], errors='coerce')
    
    # Calculate population change in percentage
    df_pop[V_POPULATION_CHANGE] = ((df_pop['POB23'] - df_pop['POB19']) / df_pop['POB19']) * 100
    
    # Return the clean dataframe ready for the master merge
    return df_pop[[V_MUNICIPALITY, V_POPULATION_CHANGE]]

def load_unemployment():
    """
    Loads and cleans the 2023 municipal unemployment data from SEPE.

    This function reads the raw monthly unemployment CSV file, processes 
    statistical secrecy symbols (converting '<5' to a midpoint of '2.5', 
    and stripping '>=' or '>'), and calculates the annual mean of absolute 
    registered unemployment for each municipality.

    Returns:
        pandas.DataFrame: A dataframe containing the municipality code 
                          and its annual mean of registered unemployment.
    """
    data_path = BASE_DIR / 'data' / 'raw' / 'sepe' / SEPE_UNEMPLOYMENT
    df = pd.read_csv(data_path, sep=';', header=1, dtype={'Codigo Municipio': str}, encoding='latin-1')
    
    df.rename(columns={'Codigo Municipio': V_MUNICIPALITY}, inplace=True)
    df = df[[V_MUNICIPALITY, 'total Paro Registrado']]
    
    df['total Paro Registrado'] = df['total Paro Registrado'].astype(str)
    
    df['total Paro Registrado'] = df['total Paro Registrado'].replace('<5', '2.5')
    df['total Paro Registrado'] = df['total Paro Registrado'].str.replace('>=', '', regex=False)
    df['total Paro Registrado'] = df['total Paro Registrado'].str.replace('>', '', regex=False)
    
    df['total Paro Registrado'] = pd.to_numeric(df['total Paro Registrado'], errors='coerce')
    
    df_annual_mean = df.groupby(V_MUNICIPALITY, as_index=False)['total Paro Registrado'].mean()
    
    return df_annual_mean

def compute_unemployment_per_1000(gdf_combined, df_unemployment):
    """
    Merges absolute unemployment data with the main spatial dataset and 
    calculates the unemployment rate per 1,000 inhabitants.

    This function joins the cleaned unemployment dataframe to the main 
    GeoDataFrame using the municipality code, calculates the rate based 
    on the 2023 population, handles missing values, and drops temporary columns.

    Args:
        gdf_combined (geopandas.GeoDataFrame): The main dataset containing 
                                               2023 population figures.
        df_unemployment (pandas.DataFrame): The cleaned dataframe containing 
                                            absolute annual unemployment means.

    Returns:
        geopandas.GeoDataFrame: The main dataset updated with the standardized 
                                unemployment rate metric.
    """
    gdf_combined = gdf_combined.merge(df_unemployment, on=V_MUNICIPALITY, how='left')
    
    gdf_combined[V_UNEMPLOYMENT] = (gdf_combined['total Paro Registrado'] / gdf_combined[V_POPULATION_2023]) * 1000
    
    gdf_combined.drop(columns=['total Paro Registrado'], inplace=True)
    
    return gdf_combined

def load_affiliation(year = 2023):
    """
    Loads and cleans municipal affiliation data from the Social Security.

    This function reads all monthly affiliation Excel files, extracts the 
    municipality code, processes statistical secrecy symbols (converting '<5' 
    to a midpoint of '2.5', stripping '>=', and removing thousand separators), 
    and calculates the annual mean of affiliated workers for each municipality.

    Args:
        year (int): The year of the data to extract (default 2023).

    Returns:
        pandas.DataFrame: A dataframe containing the municipality code 
                          and its annual mean of affiliated workers.
    """
    # Define the directory where your affiliation files are stored. 
    # Adjust the path if they are inside a specific subfolder like 'seguridad_social'
    data_dir = BASE_DIR / 'data' / 'raw' / 'seguridad social'
    
    # Find all Excel files matching the affiliation naming pattern
    file_paths = list(data_dir.glob(f'AfiliadosMuni-*-{year}.xlsx'))
    
    df_list = []
    for file_path in file_paths:
        # Read each excel file, skipping the title row (header=1)
        df_month = pd.read_excel(file_path, header=1, dtype=str)
        df_list.append(df_month)
        
    df = pd.concat(df_list, ignore_index=True)
    
    # Extract the 5-digit municipality code from the 'MUNICIPIO' column
    df[V_MUNICIPALITY] = df['MUNICIPIO'].str[:5]
    
    df = df[[V_MUNICIPALITY, 'TOTAL']]
    
    df['TOTAL'] = df['TOTAL'].astype(str)
    
    # Remove thousand separators (periods) before converting to numeric
    df['TOTAL'] = df['TOTAL'].str.replace('.', '', regex=False)
    
    # Process statistical secrecy symbols
    df['TOTAL'] = df['TOTAL'].replace('<5', '2.5')
    df['TOTAL'] = df['TOTAL'].str.replace('>=', '', regex=False)
    df['TOTAL'] = df['TOTAL'].str.replace('>', '', regex=False)
    
    df['TOTAL'] = pd.to_numeric(df['TOTAL'], errors='coerce')
    
    df_annual_mean = df.groupby(V_MUNICIPALITY, as_index=False)['TOTAL'].mean()
    
    return df_annual_mean


def compute_affiliation_per_1000(gdf_combined, df_affiliation):
    """
    Merges absolute Social Security affiliation data with the main spatial dataset 
    and calculates the affiliation rate per 1,000 inhabitants.

    This function joins the cleaned affiliation dataframe to the main GeoDataFrame 
    using the municipality code, calculates the rate based on the 2023 population, 
    handles missing values, and drops temporary columns.

    Args:
        gdf_combined (geopandas.GeoDataFrame): The main dataset containing 
                                               2023 population figures.
        df_affiliation (pandas.DataFrame): The cleaned dataframe containing 
                                           absolute annual affiliation means.

    Returns:
        geopandas.GeoDataFrame: The main dataset updated with the standardized 
                                affiliation rate metric.
    """
    gdf_combined = gdf_combined.merge(df_affiliation, on=V_MUNICIPALITY, how='left')
    
    gdf_combined[V_AFFILIATION] = (gdf_combined['TOTAL'] / gdf_combined[V_POPULATION_2023]) * 1000
    
    gdf_combined.drop(columns=['TOTAL'], inplace=True)
    
    return gdf_combined

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
                df[V_MUNICIPALITY] = (
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
                columns = [V_MUNICIPALITY, 'Votos válidos'] + all_parties
                df = df[columns].copy()

                # Compute the percentage of votes for each party
                df[all_parties] = df[all_parties].div(df['Votos válidos'], axis=0) * 100

                # Rename everything except the joining key
                df = df.rename(columns={party: f'Votes for {party} in {
                       convocation["name"]} (%)' for party in all_parties
                       })
                df = df.rename(columns={'Votos válidos': f'Number of votes in {convocation["name"]}'})

                df_convocations.append(df)

        # We merge all the convocations on the joining key
        df_infoelectoral = df_convocations[0]
        for df in df_convocations[1:]:
                df_infoelectoral = df_infoelectoral.merge(
                        df,
                        on=V_MUNICIPALITY,
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
                col1 = f'Votes for {party} in {convocation1} (%)'
                col2 = f'Votes for {party} in {convocation2} (%)'
                diff_col = f'Vote difference for {party} from {convocation1} to {convocation2}'

                if col1 in df.columns and col2 in df.columns:
                        df[diff_col] = df[col2] - df[col1]
                else:
                        print(f"Warning: Columns '{col1}' or '{col2}' not found in DataFrame. Skipping difference computation for party '{party}'.")

        return df

def extract_data():
        """
        Extracts and combines data from MITECO shapefiles, INE (Spanish National Institute of Statistics)
        and Infoelectoral .xlsx files.

        Returns:
                A GeoDataFrame containing the combined data from both sources.
        """

        # Load MITECO data geographical data
        gdf_miteco = load_miteco()
        print(f"MITECO data loaded with {len(gdf_miteco)} records.")

        # Load demographic data from INE
        df_demographics = load_demographics_ine()
        print(f"Demographic data loaded with {len(df_demographics)} records.")

        # Merge demographic data with MITECO data to compute population density
        gdf_combined = gdf_miteco.merge(
                df_demographics,
                on=V_MUNICIPALITY,
                how='left'
        )
        gdf_combined = compute_population_density(gdf_combined)
        print("Population density computed and merged with MITECO data.")

        # Load higher education data from INE and merge it with the existing data
        df_higher_education = load_higher_education_ine()
        gdf_combined = gdf_combined.merge(
                df_higher_education,
                on=V_MUNICIPALITY,
                how='left'
        )
        print(f"Higher education data merged with {len(gdf_combined)} records.")

        # Load income data from INE and merge it with the existing data
        df_income = load_economic_ine()
        gdf_combined = gdf_combined.merge(
                df_income,
                on=V_MUNICIPALITY,
                how='left'
        )
        print(f"Income data merged with {len(gdf_combined)} records.")

        # Load population change data from INE and merge it with the existing data
        df_population_change = load_population_change_ine()
        gdf_combined = gdf_combined.merge(
                df_population_change,
                on=V_MUNICIPALITY,
                how='left'
        )
        print(f"Population change data merged with {len(gdf_combined)} records.")

        # Load unemployment data from SEPE and compute unemployment per 1000 inhabitants
        df_unemployment = load_unemployment()
        gdf_combined = compute_unemployment_per_1000(gdf_combined, df_unemployment)
        print(f"Unemployment data merged and standardized with {len(gdf_combined)} records.")

        # Load affiliation data from Social Security and compute affiliation per 1000 inhabitants
        df_affiliation = load_affiliation()
        gdf_combined = compute_affiliation_per_1000(gdf_combined, df_affiliation)
        print(f"Affiliation data merged and standardized with {len(gdf_combined)} records.")

        # Load Infoelectoral data
        df_infoelectoral = load_infoelectoral()
        print(f"Infoelectoral data loaded with {len(df_infoelectoral)} records.")

        # Merge the two datasets on the joining key
        gdf_combined = gdf_combined.merge(
                df_infoelectoral,
                on=V_MUNICIPALITY,
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
        gdf_combined.drop(columns='geometry').to_excel(output_dir / 'combined_data.xlsx', index=False)
        print(f"Data extraction and combination completed. Output saved to '{output_dir}'.")