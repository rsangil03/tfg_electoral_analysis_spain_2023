from pathlib import Path

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