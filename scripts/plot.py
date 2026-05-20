import pandas as pd
import matplotlib.pyplot as plt

# File path
filename = "sum_proximity_0_1.txt"  # Replace with your actual file

# Read the data, skipping commented lines
df = pd.read_csv(filename, comment='#', sep=r'\s+', header=None)

# Assign column names
df.columns = [
    'index',
    'O_solid', 'O_liquid', 'O_interface',
    'Mg_solid', 'Mg_liquid', 'Mg_interface',
    'Si_solid', 'Si_liquid', 'Si_interface',
    'Fe_solid', 'Fe_liquid', 'Fe_interface',
    'lw', 'chi'
]

# Plot setup
fig, axs = plt.subplots(3, 2, figsize=(12, 10))
axs = axs.flatten()

elements = ['O', 'Mg', 'Si', 'Fe']
line_styles = {'solid': '-', 'liquid': '--', 'interface': ':'}

# Plot solid/liquid/interface for each element
for i, el in enumerate(elements):
    axs[i].plot(df['index'], df[f'{el}_solid'], label='Solid', linestyle=line_styles['solid'])
    axs[i].plot(df['index'], df[f'{el}_liquid'], label='Liquid', linestyle=line_styles['liquid'])
    axs[i].plot(df['index'], df[f'{el}_interface'], label='Interface', linestyle=line_styles['interface'])
    axs[i].set_title(f'{el} atoms')
    axs[i].set_xlabel('Index')
    axs[i].set_ylabel('Count')
    axs[i].legend()

# Plot lw and chi
axs[4].plot(df['index'], df['lw'], label='lw', color='tab:blue')
axs[4].set_title('lw')
axs[4].set_xlabel('Index')
axs[4].set_ylabel('lw')

axs[5].plot(df['index'], df['chi'], label='chi', color='tab:orange')
axs[5].set_title('chi')
axs[5].set_xlabel('Index')
axs[5].set_ylabel('chi')

# Layout and save
plt.tight_layout()
plt.savefig('elemental_evolution.pdf', dpi=450)

print("Figure saved as 'elemental_evolution.pdf'")
