import xlrd
import numpy as np
import pandas as pd
import seaborn as sns
from _fig_settings import *

# read the histortcal onshore wind turbine information (1993-2019)
def load_original_data(path="input_data/Wind_data.xls"):
    '''
    :param path: path to the excel file
    :return: list of d, h, nacelle, tower, time
    '''
    wb = xlrd.open_workbook(path)
    # load existing data
    sheet = wb.sheet_by_name('historical_info')
    n_rows = 6698
    c_list = [sheet.cell_value(i, 6) for i in range(1, n_rows)] # c_list is the capacity of wind turbine
    d_list = [sheet.cell_value(i, 7) for i in range(1, n_rows)] # d_list is the diameter of wind turbine
    h_list = [sheet.cell_value(i, 8) for i in range(1, n_rows)] # h_list is the hub height of wind turbine
    nacl_list = [sheet.cell_value(i, 14) for i in range(1, n_rows)] # nacl_list is the nacelle type of wind turbine
    tower_list = [sheet.cell_value(i, 15) for i in range(1, n_rows)] # tower_list is the tower type of wind turbine
    time_list = [sheet.cell_value(i, 5) for i in range(1, n_rows)] # time_list is the installation yearof wind turbine
    
    for i in range(len(nacl_list)):
        if 'DFIG' in nacl_list[i] or 'SCIG' in nacl_list[i]:
            nacl_list[i] = 'DFIG/SCIG'
    # for i in range(len(c_list)):
    #     if '/' in str(c_list[i]):
    #         # get average
    #         c_list[i] = np.mean([float(x) for x in c_list[i].split('/')])
    #     if '-' in str(c_list[i]):
    #         # get average
    #         c_list[i] = np.mean([float(x) for x in c_list[i].split('-')])
    
    return c_list, d_list, h_list, nacl_list, tower_list, time_list

#  read the onshore wind turbine material consumption data
def load_onshore_dict(path="input_data/Wind_data.xls"):
    '''
    return a dictionary of onshore data
    {Nacc: ..., Tower: ..., Blade: ..., Hub: ...}
    '''
    
    wb = xlrd.open_workbook(path)
    sheet = wb.sheet_by_name('on_material')
    import collections
    onshore_dict = collections.OrderedDict()
    for i in range(3, 14):
        m = sheet.cell_value(i, 0)
        if len(m) == 0:
            continue
        for j in range(1, 11):
            t = sheet.cell_value(1, j)
            if t not in onshore_dict:
                onshore_dict[t] = collections.OrderedDict()
            if m not in onshore_dict[t]:
                onshore_dict[t][m] = collections.OrderedDict()
            onshore_dict[t][m] = sheet.cell_value(i, j) if sheet.cell_value(i, j) != '' else 0
            if i >= 12:
                onshore_dict[t][m] = onshore_dict[t][m] / 10**6
    return onshore_dict

# read the offshore wind turbine material consumption data
def load_offshore_dict(path="input_data/Wind_data.xls"):
    '''
    return a dictionary of onshore data
    {Nacc: ..., Tower: ..., Blade: ..., Hub: ...}
    '''
    
    wb = xlrd.open_workbook(path)
    sheet = wb.sheet_by_name('off_material')
    import collections
    onshore_dict = collections.OrderedDict()
    for i in range(3, 14):
        m = sheet.cell_value(i, 0)
        if len(m) == 0:
            continue
        for j in range(1, 11):
            t = sheet.cell_value(1, j)
            if t not in onshore_dict:
                onshore_dict[t] = collections.OrderedDict()
            if m not in onshore_dict[t]:
                onshore_dict[t][m] = collections.OrderedDict()
            onshore_dict[t][m] = sheet.cell_value(i, j) if sheet.cell_value(i, j) != '' else 0
            if i >= 12:
                onshore_dict[t][m] = onshore_dict[t][m] / 10**6
    return onshore_dict
    
# calculate the mass of each component of onshore wind turbine
def calculate_total_mass(d, h, sec):
    if sec == 'Nacelle':
        mass = 0.0091 * d ** (2.0456)
    elif sec == 'Tower':
        mass = 0.0176*(d ** 2 * h) ** 0.6839
    elif sec == 'Rotor':
        mass = 0.0035 * d ** 2.1412
    elif sec == 'Foundation':
        mass = 3.5 * (0.0091 * d ** (2.0456) \
                        + 0.0176*(d ** 2 * h) ** 0.6839 \
                        + 0.0035 * d ** 2.1412) # 3.5 is the ratio of foundation mass to total mass
    else:
        raise ValueError('Unknown section: {}'.format(sec))
    return mass

# calculate the mass of each component of offshore wind turbine
def calculate_offshore_mass(d, h, t, sec):
    if sec == 'Nacelle':
        mass = 0.0091 * d ** (2.0456)
    elif sec == 'Tower':
        mass = 0.0176*(d ** 2 * h) ** 0.6839
    elif sec == 'Rotor':
        mass = 0.0035 * d ** 2.1412
    elif sec == 'Foundation':
        scale = 2.2 if int(t) <= 2035 else 2.8
        mass = scale * (0.0091 * d ** (2.0456) \
                        + 0.0176*(d ** 2 * h) ** 0.6839 \
                        + 0.0035 * d ** 2.1412) # 2.2 or 2.8 is the ratio of foundation mass to total mass
    else:
        raise ValueError('Unknown section: {}'.format(sec))
    return mass

# calculate the historical mass of each material for onshore wind turbine
def calculate_material_mass(c, d, h, nacl, tower, oh_dict):
    f_k = 'flat'
    mass_dict = {m : 0 for m in oh_dict['DFIG/SCIG']}
    for m in mass_dict:
        if m not in ['Nd', 'Dy']:
            nacl_m = calculate_total_mass(d, h, 'Nacelle') * oh_dict[nacl][m] 
            tower_m = calculate_total_mass(d, h, 'Tower') * oh_dict[tower][m]
            rotor_m = calculate_total_mass(d, h, 'Rotor') * oh_dict['/'][m] 
            found_m = calculate_total_mass(d, h, 'Foundation') * oh_dict[f_k][m]
            mass_dict[m] = nacl_m + tower_m + rotor_m + found_m
        else:
            mass_dict[m] = c * oh_dict[nacl][m] \
                           + c * oh_dict[tower][m] \
                           + c * oh_dict['/'][m] \
                           + c * oh_dict[f_k][m]
    return mass_dict

# calculate the future mass of each material under different technology development scenarios for onshore wind turbine
def calculate_future_material_onshore_mass(n, c, d, h, oh_dict, tp=1):
    
    excel_path = "input_data/Wind_data.xls"
    df = pd.read_excel(excel_path, sheet_name='tech_dev', header=1)
    nacl_list = df['nacelle_onshore_summary'].dropna().tolist()
    nacl_vals = df['Unnamed: 3'].dropna().tolist()

    nacl_type = {}
    for i in range(len(nacl_list)):
        if nacl_list[i] not in nacl_type:
            nacl_type[nacl_list[i]] = []
        nacl_type[nacl_list[i]].append(nacl_vals[i])

    nacl_type = {k: v[tp] for k, v in nacl_type.items()}

    tower_type = {
        'Hybrid': df['Hybrid'].dropna().values[0],
        'Steel': df['Steel'].dropna().values[0],
    }
    
    mass_dict = {m : 0 for m in oh_dict['DFIG/SCIG']}
    for m in mass_dict:
        if m not in ['Nd', 'Dy']:
            nacl_m, tower_m = 0, 0
            for t in nacl_type:
                nacl_m += calculate_total_mass(d, h, 'Nacelle') * oh_dict[t][m] * nacl_type[t] 
            for t in tower_type:
                tower_m += calculate_total_mass(d, h, 'Tower') * oh_dict[t][m] * tower_type[t]

            rotor_m = calculate_total_mass(d, h, 'Rotor') * oh_dict['/'][m] 
            found_m = calculate_total_mass(d, h, 'Foundation') * oh_dict['flat'][m]
            mass_dict[m] = nacl_m + tower_m + rotor_m + found_m
        else:
            for t in nacl_type:
                mass_dict[m] += c * oh_dict[t][m] * nacl_type[t] 
            for t in tower_type:
                mass_dict[m] += c * oh_dict[t][m] * tower_type[t]
            mass_dict[m] += c * oh_dict['/'][m] \
                           + c * oh_dict['flat'][m]
            
    return mass_dict

# calculate the future mass of each material under different technology development scenarios for offshore wind turbine
def calculate_future_material_offshore_mass(n, c, d, h, year, oh_dict,tp=1):
    
    excel_path = "input_data/Wind_data.xls"
    df = pd.read_excel(excel_path, sheet_name='tech_dev', header=1)
    nacl_list = df['nacelle_onshore_summary'].dropna().tolist()
    nacl_vals = df['Unnamed: 5'].dropna().tolist()

    nacl_type = {}
    for i in range(len(nacl_list)):
        if nacl_list[i] not in nacl_type:
            nacl_type[nacl_list[i]] = []
        nacl_type[nacl_list[i]].append(nacl_vals[i])

    nacl_type = {k: v[tp] for k, v in nacl_type.items()}

    tower_type = {
        'Hybrid': df['Hybrid'].dropna().values[0],
        'Steel': df['Steel'].dropna().values[0],
    }
    
    f_k = 'flat' if 'flat' in oh_dict else 'Monopile'
    
    mass_dict = {m : 0 for m in oh_dict['DFIG/SCIG']}
    for m in mass_dict:
        if m not in ['Nd', 'Dy']:
            nacl_m, tower_m = 0, 0
            for t in nacl_type:
                nacl_m += calculate_offshore_mass(d, h, year, 'Nacelle') * oh_dict[t][m] * nacl_type[t] 
            for t in tower_type:
                tower_m += calculate_offshore_mass(d, h, year, 'Tower') * oh_dict[t][m] * tower_type[t]

            rotor_m = calculate_offshore_mass(d, h, year, 'Rotor') * oh_dict['/'][m] 
            found_m = calculate_offshore_mass(d, h, year, 'Foundation') * oh_dict[f_k][m]
            mass_dict[m] = nacl_m + tower_m + rotor_m + found_m
        else:
            for t in nacl_type:
                mass_dict[m] += c * oh_dict[t][m] * nacl_type[t]
            for t in tower_type:
                mass_dict[m] += c * oh_dict[t][m] * tower_type[t]
            mass_dict[m] += c * oh_dict['/'][m] \
                           + c * oh_dict[f_k][m]
            
    return mass_dict

# final calculation of historical onshore wind turbine material
def calculate_material_mass_by_year(c_list, d_list, h_list, nacl_list, tower_list, time_list, oh_dict):
    '''
    :param d_list: list of diameters
    :param h_list: list of hub heights
    :param nacl_list: list of nacelle types
    :param tower_list: list of tower types
    :param time_list: list of time
    :param oh_dict: dictionary of onshore data
    :return: list of materials
    '''
    mass_by_year = {}

    excel_path = "input_data/Wind_data.xls"
    df = pd.read_excel(excel_path, sheet_name='tech_dev', header=1)
    
    for i in range(len(time_list)):
        year = int(time_list[i])
        if year not in mass_by_year:
            mass_by_year[year] = {}
            for m in oh_dict['DFIG/SCIG']:
                mass_by_year[year][m] = 0
        c = c_list[i]
        d = d_list[i]
        h = h_list[i]
        mass_dict = calculate_material_mass(c, d, h, nacl_list[i], tower_list[i], oh_dict)
        debug = 0
        for m in mass_dict:
            mass_by_year[year][m] += mass_dict[m]
    # 0 for years without inflow
    for i in [1994, 1996]:
        if i not in mass_by_year:
            mass_by_year[i] = {}
            for m in oh_dict['DFIG/SCIG']:
                mass_by_year[i][m] = 0
    return mass_by_year

# final caculation the mass of future onshore wind turbine material
def calculate_future_material_mass_onshore_by_year(n_list, c_list, d_list, h_list, oh_dict, time_list, tp):
    mass_by_year = {}
    
    for i in range(len(n_list)):
        year = int(time_list[i])
        n = n_list[i]
        c = c_list[i]
        d = d_list[i]
        h = h_list[i]
        mass_dict = calculate_future_material_onshore_mass(n, c, d, h, oh_dict, tp=tp)
        
        for k in mass_dict:
            mass_dict[k] = mass_dict[k] * n

        mass_by_year[year] = mass_dict
    return mass_by_year

# final calculation the mass of future offshore wind turbine material
def calculate_future_material_mass_offshore_by_year(n_list, c_list, d_list, h_list, oh_dict, time_list, tp):
    mass_by_year = {}
    
    for i in range(len(n_list)):
        year = int(time_list[i])
        n = n_list[i]
        c = c_list[i]
        d = d_list[i]
        h = h_list[i]
        mass_dict = calculate_future_material_offshore_mass(n, c, d, h, year, oh_dict, tp=tp)
        
        for k in mass_dict:
            mass_dict[k] = mass_dict[k] * n

        mass_by_year[year] = mass_dict
    return mass_by_year
    
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.ticker as mticker

# plot the mass of each material by year
def plot_mass_by_year(mass_by_year, name, w_scale=1):
    materials = list(mass_by_year.columns)
    mass_by_year['Year'] = mass_by_year.index
    
    fig, ax = plt.subplots(figsize=(1.6 * w_scale, 1.6 * w_scale * 0.75))
    
    bottom = np.zeros(len(mass_by_year))
    
    mean_v = [-np.mean(mass_by_year[m]) for m in materials]
    # sort materials by mean value
    materials = [m for _, m in sorted(zip(mean_v, materials))]
    
    for m in materials:
        ax.plot([], [], label=m, color=COLORS[m])
        
        # fill in color between mass_by_year[m] and bottom
        ax.fill_between(mass_by_year.index, mass_by_year[m] + bottom, bottom, color=COLORS[m], edgecolor='none')
        
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        
        bottom += mass_by_year[m]
    
    ax.set_xlabel('Year', fontsize=18)
    ax.set_ylabel('Mass [Mt]', fontsize=18)  # Increase y-axis label font size
    
    # Format y-axis tick labels to two decimal places
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter('{x:,.2f}'))
    ax.tick_params(axis='y', labelsize=16) 
    ax.tick_params(axis='x', labelsize=18) 
    
    ax.legend(loc='upper left',fontsize=16)
    
    # remove legend frame
    leg = ax.get_legend()
    leg.get_frame().set_linewidth(0.0)
    
    # save to pdf
    fig.tight_layout()
    plt.savefig(name)
    plt.close()


# read different EoL teartment strategies data
def get_data_from_recy_new(path="input_data/Wind_data.xls"):
    wb = xlrd.open_workbook(path)
    # load existing data
    sheet = wb.sheet_by_name('recy_rate_new')
    
    table = {}
    
    for i in range(27):
        
        if 'EoL' in sheet.cell_value(i, 0):
            start_row = i
            t_type = sheet.cell_value(i, 0)
            
            # create t type table
            table[t_type + '_onshore'] = {}
            table[t_type + '_offshore'] = {}
            
            for b_i in range(i + 2, i + 12):
                material = sheet.cell_value(b_i, 1)
                onshore_recy = [sheet.cell_value(b_i, j) for j in range(2, 7)]
                offshore_recy = [sheet.cell_value(b_i, j) for j in range(9, 14)]
                
                # write to table
                table[t_type + '_onshore'][material] = onshore_recy
                table[t_type + '_offshore'][material] = offshore_recy

    proc_methods = [sheet.cell_value(2, j).replace('on_', '') for j in range(2, 7)]
    
    # #print table to verify
    #print(table)
    
    return table, proc_methods