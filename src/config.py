from pathlib import Path

# Variables from MITECO geographical data
V_MUNICIPALITY = 'Code of municipality'
V_MUNICIPALITY_NAME = 'Name of municipality'
V_CCAA = 'Code of autonomous community'
V_CCAA_NAME = 'Name of autonomous community'
V_PROVINCE = 'Code of province'
V_PROVINCE_NAME = 'Name of province'
V_LATITUDE = 'Latitude'
V_LONGITUDE = 'Longitude'
V_AREA = 'Area in km2'

# Variables from INE demographics data
V_POPULATION_2023 = 'Population in 2023'
V_MEAN_AGE = 'Mean age'
V_FOREIGN_POPULATION = 'Foreign-born population (%)'
V_DENSITY = 'Population density (inhabitants/km2)'
V_HIGHER_EDUCATION = 'Population with higher education (%)'
V_POPULATION_CHANGE = 'Population change from 2019 to 2023 (%)'

# Variables from economic and unemployment data
V_MEAN_NET_INCOME = 'Mean net income per person'
V_AFFILIATION = 'Affiliation to Social Security per 1000 inhabitants'
V_UNEMPLOYMENT = 'Unemployment per 1000 inhabitants'

# Variables from electoral data
V_VOTES_2023 = 'Number of votes in 2023'
V_VOTES_2019 = 'Number of votes in 2019'

V_PP_2023 = 'Votes for PP in 2023 (%)'
V_PSOE_2023 = 'Votes for PSOE in 2023 (%)'
V_VOX_2023 = 'Votes for VOX in 2023 (%)'
V_SUMAR_2023 = 'Votes for SUMAR in 2023 (%)'

V_PP_2019 = 'Votes for PP in 2019 (%)'
V_PSOE_2019 = 'Votes for PSOE in 2019 (%)'
V_VOX_2019 = 'Votes for VOX in 2019 (%)'
V_SUMAR_2019 = 'Votes for SUMAR in 2019 (%)'

V_PP_DIFF_2023_2019 = 'Vote difference for PP from 2019 to 2023'
V_PSOE_DIFF_2023_2019 = 'Vote difference for PSOE from 2019 to 2023'
V_VOX_DIFF_2023_2019 = 'Vote difference for VOX from 2019 to 2023'
V_SUMAR_DIFF_2023_2019 = 'Vote difference for SUMAR from 2019 to 2023'

V_LIST = [
    V_POPULATION_2023,
    V_DENSITY,
    V_MEAN_AGE,
    V_FOREIGN_POPULATION,
    V_HIGHER_EDUCATION,
    V_POPULATION_CHANGE,
    V_MEAN_NET_INCOME,
    V_UNEMPLOYMENT,
    V_AFFILIATION,
    V_PP_2023,
    V_PSOE_2023,
    V_VOX_2023,
    V_SUMAR_2023,
    V_PP_2019,
    V_PSOE_2019,
    V_VOX_2019,
    V_SUMAR_2019,
    V_PP_DIFF_2023_2019,
    V_PSOE_DIFF_2023_2019,
    V_VOX_DIFF_2023_2019,
    V_SUMAR_DIFF_2023_2019
]

BASE_DIR = Path(__file__).parent.parent

# This is the filename of the INE demographics CSV in the raw data directory
INE_DEMOGRAPHICS = '68541.csv'
INE_HIGHER_EDUCATION = '66592.csv'
INE_INCOME = '30824.csv'
INE_REGISTER_2019 = 'pobmun19.xlsx'
INE_REGISTER_2023 = 'pobmun23.xlsx'
SEPE_UNEMPLOYMENT = 'Paro_por_municipios_2023_csv.csv'

INFOELECTORAL_SKIPROWS = 5

INFOELECTORAL_CONVOCATIONS = [
        {
                'name': '2023',
                'path': BASE_DIR / 'data' / 'raw' / 'infoelectoral' / '02_202307_1.xlsx',
                'parties': ['PSOE', 'VOX', 'SUMAR'],
                'coalitions': [
                        {
                                'name': 'PP', # We create a coalition for PP and U.P.N., as in Navarra they 
                                              # run together as NA+ in 2019, but in 2023 they run separately
                                'parties': ['PP', 'U.P.N.']
                                }
                        ]
                },
        {
                'name': '2019',
                'path': BASE_DIR / 'data' / 'raw' / 'infoelectoral' / '02_201911_1.xlsx',
                'parties': ['PSOE', 'VOX'],
                'coalitions': [
                        {
                                'name': 'PP', # We create a coalition for PP and U.P.N., as in Navarra 
                                              # they run together as NA+ in 2019, but in 2023 they run separately
                                'parties': ['PP', 'NA+']
                                },
                        {
                                'name': 'SUMAR', # We create a coalition for the parties that are part of Sumar in 2023, since they were not in 2019
                                'parties': ['PODEMOS-IU', 'ECP-GUANYEM EL CANVI', 'MÁS PAÍS-EQUO',
                                        'PODEMOS-EU', 'MÉS COMPROMÍS', 'MÁS PAÍS', 'M PAÍS-CHA-EQUO', 'MÉS-ESQUERRA']
                                }
                        ]
                }
]

# Codes of administrative units (Autonomous Communities / CCAA)
C_CCAA_ANDALUCIA = '01'
C_CCAA_ARAGON = '02'
C_CCAA_ASTURIAS = '03'
C_CCAA_BALEARES = '04'
C_CCAA_CANARIAS = '05'
C_CCAA_CANTABRIA = '06'
C_CCAA_CASTILLA_Y_LEON = '07'
C_CCAA_CASTILLA_LA_MANCHA = '08'
C_CCAA_CATALUNYA = '09'
C_CCAA_COMUNIDAD_VALENCIANA = '10'
C_CCAA_EXTREMADURA = '11'
C_CCAA_GALICIA = '12'
C_CCAA_MADRID = '13'
C_CCAA_MURCIA = '14'
C_CCAA_NAVARRA = '15'
C_CCAA_PAIS_VASCO = '16'
C_CCAA_LA_RIOJA = '17'
C_CCAA_CEUTA = '18'
C_CCAA_MELILLA = '19'

# Mapping of CCAA codes to their names in English, for easier interpretation of results
C_CODE_TO_NAME = {
        C_CCAA_ANDALUCIA: 'Andalusia',
        C_CCAA_ARAGON: 'Aragon',
        C_CCAA_ASTURIAS: 'Asturias',
        C_CCAA_BALEARES: 'Balearic Islands',
        C_CCAA_CANARIAS: 'Canary Islands',
        C_CCAA_CANTABRIA: 'Cantabria',
        C_CCAA_CASTILLA_Y_LEON: 'Castile and León',
        C_CCAA_CASTILLA_LA_MANCHA: 'Castile-La Mancha',
        C_CCAA_CATALUNYA: 'Catalonia',
        C_CCAA_COMUNIDAD_VALENCIANA: 'Valencian Community',
        C_CCAA_EXTREMADURA: 'Extremadura',
        C_CCAA_GALICIA: 'Galicia',
        C_CCAA_MADRID: 'Madrid',
        C_CCAA_MURCIA: 'Murcia',
        C_CCAA_NAVARRA: 'Navarra',
        C_CCAA_PAIS_VASCO: 'Basque Country',
        C_CCAA_LA_RIOJA: 'La Rioja',
        C_CCAA_CEUTA: 'Ceuta',
        C_CCAA_MELILLA: 'Melilla'
}

ELECTORAL_RESULTS_2023 = {
        V_PP_2023: 33.27,
        V_PSOE_2023: 31.68,
        V_VOX_2023: 12.38,
        V_SUMAR_2023: 12.33
}

ELECTORAL_RESULTS_2019 = {
        V_PP_2019: 21.21,
        V_PSOE_2019: 28.00,
        V_VOX_2019: 15.07,
        V_SUMAR_2019: 15.33
}

ELECTORAL_DIFF_2023_2019 = {
        V_PP_DIFF_2023_2019: ELECTORAL_RESULTS_2023[V_PP_2023] - ELECTORAL_RESULTS_2019[V_PP_2019],
        V_PSOE_DIFF_2023_2019: ELECTORAL_RESULTS_2023[V_PSOE_2023] - ELECTORAL_RESULTS_2019[V_PSOE_2019],
        V_VOX_DIFF_2023_2019: ELECTORAL_RESULTS_2023[V_VOX_2023] - ELECTORAL_RESULTS_2019[V_VOX_2019],
        V_SUMAR_DIFF_2023_2019: ELECTORAL_RESULTS_2023[V_SUMAR_2023] - ELECTORAL_RESULTS_2019[V_SUMAR_2019]
}

COLOURS_PARTIES = {
        V_PP_2019: '#1e4a90',
        V_PP_2023: '#1e4a90',
        V_PP_DIFF_2023_2019: '#1e4a90',
        V_PSOE_2019: '#ef4135',
        V_PSOE_2023: '#ef4135',
        V_PSOE_DIFF_2023_2019: '#ef4135',
        V_VOX_2019: '#4cbb17',
        V_VOX_2023: '#4cbb17',
        V_VOX_DIFF_2023_2019: '#4cbb17',
        V_SUMAR_2019: '#e61b53',
        V_SUMAR_2023: '#e61b53',
        V_SUMAR_DIFF_2023_2019: '#e61b53'
}

