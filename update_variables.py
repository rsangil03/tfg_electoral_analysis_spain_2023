import json
from pathlib import Path

# Read the notebook
notebook_path = Path('notebooks/02_data_analysis.ipynb')
with open(notebook_path, 'r', encoding='utf-8') as f:
    notebook = json.load(f)

# Define all replacements
replacements = {
    'V_Population_2023': 'V_POPULATION_2023',
    'V_Population_density': 'V_DENSITY',
    'V_Population_change': 'V_POPULATION_CHANGE',
    'V_Mean_age': 'V_MEAN_AGE',
    'V_Population_over_65': 'V_POPULATION_OVER_65_REMOVED',  # Mark for removal consideration
    'V_Foreign_population': 'V_FOREIGN_POPULATION',
    'V_Mean_net_income': 'V_MEAN_NET_INCOME',
    'V_Population_over_16_with_higher_education': 'V_HIGHER_EDUCATION',
    'V_Affiliation_per_1000_inhabitants': 'V_AFFILIATION',
    'V_Unemployment_per_1000_inhabitants': 'V_UNEMPLOYMENT',
    'V_PP_diff_2023_2019': 'V_PP_DIFF_2023_2019',
    'V_PSOE_diff_2023_2019': 'V_PSOE_DIFF_2023_2019',
    'V_VOX_diff_2023_2019': 'V_VOX_DIFF_2023_2019',
    'V_SUMAR_diff_2023_2019': 'V_SUMAR_DIFF_2023_2019',
}

# Process all cells
for cell in notebook['cells']:
    if cell['cell_type'] == 'code':
        source = cell['source']
        if isinstance(source, list):
            # Join list of strings
            content = ''.join(source)
        else:
            content = source
        
        # Apply replacements
        for old, new in replacements.items():
            content = content.replace(old, new)
        
        # Update the cell
        if isinstance(cell['source'], list):
            cell['source'] = content.split('\n')
            # Add newlines back except for the last item if needed
            if cell['source'] and cell['source'][-1] != '':
                cell['source'] = [line + '\n' for line in cell['source'][:-1]] + [cell['source'][-1]]
            elif cell['source']:
                cell['source'] = [line + '\n' for line in cell['source']]
        else:
            cell['source'] = content

# Write the notebook back
with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(notebook, f, ensure_ascii=False, indent=1)

print('Notebook updated successfully!')
print(f'Replaced variables in {notebook_path}')
