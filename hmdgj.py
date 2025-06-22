#!/opt/homebrew/bin/python3.11
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as colors
import sqlite3
from datetime import datetime, timedelta
import calendar

# Connect to the database
conn = sqlite3.connect('/Users/blaine/6003TimeTracking/cb/mytime.db')

# Query for manuscript data (ProjectIDs 0001-0999)
manuscript_data = pd.read_sql('''
    SELECT DateDashed, SUM(TimeHr) as TimeHr
    FROM zTimeSpent 
    WHERE ProjectID BETWEEN 001 AND 999
    GROUP BY DateDashed
''', conn)
manuscript_data['Date'] = pd.to_datetime(manuscript_data['DateDashed'])
manuscript_data = manuscript_data.set_index('Date')
manuscript_data = manuscript_data.rename(columns={'TimeHr': 'ManuscriptHours'})

# Query for grant application data (ProjectIDs 1001-1999)
grant_data = pd.read_sql('''
    SELECT DateDashed, SUM(TimeHr) as TimeHr
    FROM zTimeSpent 
    WHERE ProjectID BETWEEN 1001 AND 1999
    GROUP BY DateDashed
''', conn)
grant_data['Date'] = pd.to_datetime(grant_data['DateDashed'])
grant_data = grant_data.set_index('Date')
grant_data = grant_data.rename(columns={'TimeHr': 'GrantHours'})

# Merge the two datasets
all_data = pd.merge(manuscript_data, grant_data, left_index=True, right_index=True, how='outer').fillna(0)

# Function to create a custom calendar heatmap with diagonal split cells
def split_cell_calendar(data, year=None, figsize=(16, 10), cmap_manuscript='Blues', cmap_grant='Greens'):
    # If year is not specified, use the year of the most recent data
    if year is None:
        year = data.index.max().year
    
    # Filter data for the specified year
    year_data = data[data.index.year == year].copy()
    
    # Create a figure
    fig, axes = plt.subplots(3, 4, figsize=figsize)
    axes = axes.flatten()
    
    # Define color maps
    manuscript_cmap = plt.cm.get_cmap(cmap_manuscript)
    grant_cmap = plt.cm.get_cmap(cmap_grant)
    
    # Get the maximum values for color scaling
    max_manuscript = data['ManuscriptHours'].max()
    max_grant = data['GrantHours'].max()
    
    # Create normalization objects for the colormaps
    manuscript_norm = colors.Normalize(vmin=0, vmax=max(max_manuscript, 1))
    grant_norm = colors.Normalize(vmin=0, vmax=max(max_grant, 1))
    
    for month in range(12):
        ax = axes[month]
        
        # Set the title to the month name
        ax.set_title(calendar.month_name[month + 1])
        
        # Calculate the number of days in the month
        _, num_days = calendar.monthrange(year, month + 1)
        
        # Get the day of the week for the first day of the month (0 = Monday, 6 = Sunday)
        first_day_weekday = datetime(year, month + 1, 1).weekday()
        
        # Create a 7x6 grid of days (max 6 weeks per month)
        week_rows = 6
        day_cols = 7
        
        # Remove all axis elements
        ax.set_xlim(0, day_cols)
        ax.set_ylim(0, week_rows)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        
        # Add day labels (Monday to Sunday)
        for i, day in enumerate(['M', 'T', 'W', 'T', 'F', 'S', 'S']):
            ax.text(i + 0.5, week_rows + 0.1, day, ha='center', va='center', fontsize=9)
        
        # Plot each day of the month
        for day in range(1, num_days + 1):
            # Calculate row (week) and column (day of week)
            week_row = (first_day_weekday + day - 1) // 7
            day_col = (first_day_weekday + day - 1) % 7
            
            # Create the date and check if we have data for it
            current_date = datetime(year, month + 1, day)
            
            manuscript_hours = 0
            grant_hours = 0
            
            if current_date in year_data.index:
                manuscript_hours = year_data.loc[current_date, 'ManuscriptHours']
                grant_hours = year_data.loc[current_date, 'GrantHours']
            
            # Calculate cell coordinates
            x = day_col
            y = week_rows - 1 - week_row  # Invert y-axis to have weeks go from top to bottom
            
            # Draw cell background (light gray)
            rect = patches.Rectangle((x, y), 1, 1, linewidth=0.5, edgecolor='gray', facecolor='#f8f8f8')
            ax.add_patch(rect)
            
            # Add day number
            ax.text(x + 0.05, y + 0.85, str(day), ha='left', va='top', fontsize=8, color='#555555')
            
            # Draw diagonal split cells if there is data
            if manuscript_hours > 0:
                # Bottom-left triangle for manuscripts (blue)
                triangle1 = patches.Polygon([(x, y), (x+1, y), (x, y+1)], 
                                           facecolor=manuscript_cmap(manuscript_norm(manuscript_hours)),
                                           edgecolor='none')
                ax.add_patch(triangle1)
            
            if grant_hours > 0:
                # Top-right triangle for grants (green)
                triangle2 = patches.Polygon([(x+1, y), (x+1, y+1), (x, y+1)], 
                                           facecolor=grant_cmap(grant_norm(grant_hours)),
                                           edgecolor='none')
                ax.add_patch(triangle2)
            
            # Add a thin black diagonal line to separate the triangles
            ax.plot([x, x+1], [y+1, y], 'k-', linewidth=0.5, alpha=0.6)
    
    # Add color bars
    manuscript_cax = fig.add_axes([0.15, 0.05, 0.3, 0.02])
    manuscript_cb = plt.colorbar(plt.cm.ScalarMappable(norm=manuscript_norm, cmap=manuscript_cmap), 
                               cax=manuscript_cax, orientation='horizontal')
    manuscript_cb.set_label('Manuscript Hours (Blue, lower left)')
    
    grant_cax = fig.add_axes([0.55, 0.05, 0.3, 0.02])
    grant_cb = plt.colorbar(plt.cm.ScalarMappable(norm=grant_norm, cmap=grant_cmap), 
                          cax=grant_cax, orientation='horizontal')
    grant_cb.set_label('Grant Hours (Green, upper right)')
    
    plt.suptitle(f'Daily Writing Effort for {year}', y=0.98, fontsize=16)
    plt.tight_layout(rect=[0, 0.08, 1, 0.95])
    
    return fig, axes

# Create the split cell calendar visualization
# Use the current year from the data
year_to_use = datetime.now().year
if all_data.index.max().year < year_to_use:
    year_to_use = all_data.index.max().year
    
fig, axes = split_cell_calendar(all_data, year=year_to_use)

# Save the figure
output_file = "/Users/blaine/6003TimeTracking/cb/hmdgj.png"
if os.path.isfile(output_file):
    os.remove(output_file)
plt.savefig(output_file, dpi=300, bbox_inches='tight')
plt.show()

conn.close()