from pathlib import Path

JOING_KEY_MITECO = 'codmun_ine'
INFOELECTORAL_SKIPROWS = 5
BASE_DIR = Path(__file__).parent.parent

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


COLOURS_PARTIES = {
        'PP_2019': '#1e4a90',
        'PP_2023': '#1e4a90',
        'PP_diff_2023_2019': '#1e4a90',
        'PSOE_2019': '#ef4135',
        'PSOE_2023': '#ef4135',
        'PSOE_diff_2023_2019': '#ef4135',
        'VOX_2019': '#4cbb17',
        'VOX_2023': '#4cbb17',
        'VOX_diff_2023_2019': '#4cbb17',
        'SUMAR_2019': '#e61b53',
        'SUMAR_2023': '#e61b53',
        'SUMAR_diff_2023_2019': '#e61b53'
}

V_Population_2023 = 'pob_23'
V_Population_2014 = 'pob_14'
V_Population_change = 'pob_14_23'
V_Population_density = 'dens_pob'
V_Mean_age = 'edad_media'
V_Population_over_65 = 'porc_pob65'
V_Foreign_population = 'porc_pob_e'
V_Native_population = 'pob_npum'
V_Masculinity_ratio = 'rat_mascul'

V_Mean_net_income = 'rta_nt_med'
V_Affiliation_per_1000_inhabitants = 'afi_1000'
V_Unemployment_per_1000_inhabitants = 'paro_1000'
V_Population_over_16_with_higher_education = 'pob_esup16'

V_CCAA = 'cod_ccaa'

# Codes of administrative units
C_CCAA_CANARIAS = '05'
C_CCAA_CEUTA = '18'
C_CCAA_MELILLA = '19'