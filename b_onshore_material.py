"""
This script is used to calculate onshore wind turbine material inflows

It contains:
- material inflows for constructing new wind turbines
- material inflows for replacing damaged components
- 2 energy demand scenarios: Gcam and GNZ
- 3 tech development scenarios: CT, AT, NT

"""

"""
================
Import libraries
================
"""
import math
from _utils import *
from _params import get_parser
from a_capacity_flow import CapacityFlow

"""
=============
prepare files
=============
"""
# read the avg_turb, avg_nacl and avg_rotor from the excel file
def load_avg_data(path):
    df = pd.read_excel(path, sheet_name='his_analysis', header=1)
    avg_turb = df["Average of Turbine rated capacity (kW)"].dropna().tolist()
    avg_nacl = df["Average of Nacelle mass (t)"].dropna().tolist()
    avg_rotor = df["Average of Rotor mass (t)"].dropna().tolist()
    # post processing
    avg_turb_onshore = avg_turb[:27] + [avg_turb[27]] * 10 + [avg_turb[28]] * 10 + [avg_turb[29]] * 11
    avg_turb_offshore = avg_turb[:27] + [avg_turb[30]] * 10 + [avg_turb[31]] * 10 + [avg_turb[32]] * 11
    avg_nacl_onshore = avg_nacl[:27] + [avg_nacl[27]] * 10 + [avg_nacl[28]] * 10 + [avg_nacl[29]] * 11
    avg_nacl_offshore = avg_nacl[:27] + [avg_nacl[30]] * 10 + [avg_nacl[31]] * 10 + [avg_nacl[32]] * 11
    avg_rotor_onshore = avg_rotor[:27] + [avg_rotor[27]] * 10 + [avg_rotor[28]] * 10 + [avg_rotor[29]] * 11
    avg_rotor_offshore = avg_rotor[:27] + [avg_rotor[30]] * 10 + [avg_rotor[31]] * 10 + [avg_rotor[32]] * 11
    return np.asarray(avg_turb_onshore), np.asarray(avg_nacl_onshore), np.asarray(avg_rotor_onshore), \
        np.asarray(avg_turb_offshore), np.asarray(avg_nacl_offshore), np.asarray(avg_rotor_offshore)

# load the historical tech data from the excel file
def load_history_market_share(excel_path = "input_data/Wind_data.xls", tp=1):
    df = pd.read_excel(excel_path, sheet_name='his_analysis', header=1)
    nacl_type = {}
    for k in ["DFIG/SCIG", "EESGDD", "PMSGDD", "PMSGGB", "PDD", "SDD"]:
        nacl_type[k] = df[k].dropna().tolist()
    return nacl_type

# load the future tech data from the excel file
def load_future_market_share(excel_path = "input_data/Wind_data.xls", tp=1):
    df = pd.read_excel(excel_path, sheet_name='tech_dev', header=1)
    nacl_list = df['nacelle_onshore_summary'].dropna().tolist()
    nacl_vals = df['Unnamed: 3'].dropna().tolist()
    nacl_type = {}
    for i in range(len(nacl_list)):
        if nacl_list[i] not in nacl_type:
            nacl_type[nacl_list[i]] = []
        nacl_type[nacl_list[i]].append(nacl_vals[i])
    nacl_type = {k: v[tp] for k, v in nacl_type.items()}
    return nacl_type

def load_replacement_data(excel_path = "input_data/Wind_data.xls"):
    df = pd.read_excel(excel_path, sheet_name='tech_dev', header=1)
    future_nacl_rep = df['future_nacelle_replacement'].dropna().tolist()
    future_rotor_rep = df['future_rotor_replacement'].dropna().tolist()
    his_nacl_rep = df['his_nacelle_replacement'].dropna().tolist()
    his_rotor_rep = df['his_rotor_replacement'].dropna().tolist()
    return future_nacl_rep, future_rotor_rep, his_nacl_rep, his_rotor_rep

"""
================
Define functions
================
"""
# relationship between capacity and height for Canadian onshore wind turbine from regression
def get_height(x):
    return 4.1099 * x ** 0.3974

# relationship between capacity and diameter for Canadian onshore wind turbine from regression
def get_diameter(x):
    return 2.1464 * x ** 0.4913

def capacity_onshore(tp=1, scen='Gcam'):
    
    excel_path = "input_data/Wind_data.xls"
    df = pd.read_excel(excel_path, sheet_name='on_capacity')
    per_cap_list = df['on_future_capacity_per_turbine '].dropna().tolist()
    
    # load nacl market share
    history_nacl_market_share = load_history_market_share(excel_path, tp)
    future_nacl_market_share = load_future_market_share(excel_path, tp)
    nacl_market_share = {k: history_nacl_market_share[k] + [future_nacl_market_share[k]] * 31 \
        for k in history_nacl_market_share.keys()}
    
    # read avg_turb, avg_nacl and avg_rotor
    avg_turb_ons, avg_nacl_ons, avg_rotor_ons, \
        avg_turb_offs, avg_nacl_offs, avg_rotor_offs = load_avg_data(excel_path)

    inflow_onshore, inflow_future_onshore, stock_onshore, outflow_onshore, inflow_offshore, outflow_offshore, stock_offshore, \
                outflow_onshore_contrib, outflow_offshore_contrib, stock_onshore_contrib, stock_offshore_contrib, years_onshore, years_offshore = CapacityFlow()(tp, scen)

    # perform replacement calculation
    stock_onshore_contrib = stock_onshore_contrib / (np.repeat(np.expand_dims(avg_turb_ons, axis=1), len(stock_onshore_contrib), axis=1) + 1e-100)
    avg_nacl_mass = stock_onshore_contrib * np.repeat(np.expand_dims(avg_nacl_ons, axis=1), len(stock_onshore_contrib), axis=1)
    avg_rotor_mass = stock_onshore_contrib * np.repeat(np.expand_dims(avg_rotor_ons, axis=1), len(stock_onshore_contrib), axis=1)
    # process nacl
    avg_nacl_mass_ = []
    for k in ["DFIG/SCIG", "EESGDD", "PMSGDD", "PMSGGB", "PDD", "SDD"]:
        temp = avg_nacl_mass * np.repeat(np.expand_dims(nacl_market_share[k], axis=1), len(avg_nacl_mass), axis=1)
        avg_nacl_mass_.append(temp)
    avg_nacl_mass_tech = np.stack(avg_nacl_mass_, axis=-1)
    oh_dict = load_onshore_dict(path=excel_path)
    oh_dict_array = np.asarray(pd.DataFrame({k: oh_dict[k] for k in history_nacl_market_share.keys()}))
    avg_nacl_mass_tech = np.dot(avg_nacl_mass_tech, oh_dict_array.T) # [58, 58, 10]
    for i in range(avg_nacl_mass_tech.shape[-1]-2, avg_nacl_mass_tech.shape[-1]):
        avg_nacl_mass_tech[:, :, i] = avg_nacl_mass_tech[:, :, i] * np.repeat(np.expand_dims(avg_turb_ons, axis=1), len(stock_onshore_contrib), axis=1)/(np.repeat(np.expand_dims(avg_nacl_ons, axis=1), len(stock_onshore_contrib), axis=1) + 1e-100) / 1000
    # seperate historical installed wind turbines and future installed wind turbines
    avg_nacl_mass_hist = np.sum(avg_nacl_mass_tech[:, :27, :], axis=1)
    avg_nacl_mass_future = np.sum(avg_nacl_mass_tech[:, 27:, :], axis=1)
    avg_nacl_mass = np.stack([avg_nacl_mass_hist, avg_nacl_mass_future], axis=1)
    # load different replacement rates for nacelle
    future_nacl_rep, future_rotor_rep, his_nacl_rep, his_rotor_rep = load_replacement_data(excel_path)
    future_nacl_rep = future_nacl_rep[tp]
    future_rotor_rep = future_rotor_rep[tp]
    his_nacl_rep = his_nacl_rep[tp]
    his_rotor_rep = his_rotor_rep[tp]
    avg_nacl_mass[:, 1] = avg_nacl_mass[:, 1] * future_nacl_rep
    avg_nacl_mass[:, 0] = avg_nacl_mass[:, 0] * his_nacl_rep
    
    # process rotor
    avg_rotor_mass_ = []
    oh_dict = load_onshore_dict(path=excel_path)
    material_list = list(oh_dict['/'].keys())
    oh_dict_array = np.expand_dims(np.asarray([oh_dict['/'][k] for k in material_list]), axis=-1)
    avg_rotor_mass_tech = np.dot(np.expand_dims(avg_rotor_mass, -1), oh_dict_array.T) # [58, 58, 10]

    for i in range(avg_rotor_mass_tech.shape[-1]-2, avg_rotor_mass_tech.shape[-1]):
        avg_rotor_mass_tech[:, :, i] = avg_rotor_mass_tech[:, :, i] * np.repeat(np.expand_dims(avg_turb_ons, axis=1), len(stock_onshore_contrib), axis=1)/(np.repeat(np.expand_dims(avg_rotor_ons, axis=1), len(stock_onshore_contrib), axis=1) + 1e-100) / 1000
    
    # seperate historical installed wind turbines and future installed wind turbines
    avg_rotor_mass_hist = np.sum(avg_rotor_mass_tech[:, :27, :], axis=1)
    avg_rotor_mass_future = np.sum(avg_rotor_mass_tech[:, 27:, :], axis=1)
    avg_rotor_mass = np.stack([avg_rotor_mass_hist, avg_rotor_mass_future], axis=1)
    # load different replacement rates for rotor
    avg_rotor_mass[:, 1] = avg_rotor_mass[:, 1] * future_rotor_rep
    avg_rotor_mass[:, 0] = avg_rotor_mass[:, 0] * his_rotor_rep
    # [58, 2, 10] -> [58, 10]
    avg_rotor_mass = np.sum(avg_rotor_mass, axis=1)
    avg_nacl_mass = np.sum(avg_nacl_mass, axis=1)
    avg_nacl_rotor_rep_mass = avg_nacl_mass + avg_rotor_mass
    
    future_inflow_on = inflow_onshore[27: ]
    ratio_on = outflow_onshore_contrib.copy()

    # perform the installation calculation
    # assumptions for future onshore average capacity per wind turbine
    capacity_per_wind_20_29 = per_cap_list[0]
    capacity_per_wind_30_39 = per_cap_list[1]
    capacity_per_wind_40_50 = per_cap_list[2]
    
    capacity_per_wind_list = [capacity_per_wind_20_29] * 10 + [capacity_per_wind_30_39] * 10 + [capacity_per_wind_40_50] * 11   
 
    future_c_list = future_inflow_on.copy() * 1000 # convert to kW 
    future_n_list = [future_c_list[i] / capacity_per_wind_list[i] for i in range(len(future_c_list))] # number of wind turbines
    future_d_list = get_diameter(np.array(capacity_per_wind_list))  # diameter of wind turbines
    future_h_list = get_height(np.array(capacity_per_wind_list))  # height of wind turbines

    c_list, d_list, h_list, nacl_list, tower_list, time_list = load_original_data(path=excel_path)
    hist_mass_by_year = calculate_material_mass_by_year(c_list, d_list, h_list, nacl_list, tower_list, time_list, oh_dict)
    
    time_list = [2020 + i for i in range(len(future_n_list))]
    
    future_mass_by_year = calculate_future_material_mass_onshore_by_year(future_n_list, np.array(capacity_per_wind_list), future_d_list, future_h_list, oh_dict, time_list, tp=tp)
    
    mass_by_year = {}
    mass_by_year_rep = {}
    
    for i, year in enumerate(np.sort(list(hist_mass_by_year.keys()))):
        mass_by_year[year] = hist_mass_by_year[year]
        mass_by_year_rep[year] = hist_mass_by_year[year]
        for j, m in enumerate(material_list):
            mass_by_year_rep[year][m] = mass_by_year_rep[year][m] + avg_nacl_rotor_rep_mass[i, j]
    for i, year in enumerate(np.sort(list(future_mass_by_year.keys()))):
        mass_by_year[year] = future_mass_by_year[year]
        mass_by_year_rep[year] = future_mass_by_year[year]
        for j, m in enumerate(material_list):
            mass_by_year_rep[year][m] = mass_by_year_rep[year][m] + avg_nacl_rotor_rep_mass[i + len(hist_mass_by_year), j]
    
    # save to csv
    df = pd.DataFrame(mass_by_year_rep).T
    # sort using the index
    df = df.sort_index()
    df.to_csv('results/material_onshore_mass_by_year_{}_{}.csv'.format(tp, scen))
    plot_mass_by_year(df, 'save_figs/onshore_material_{}_{}.png'.format(tp, scen), w_scale=6)
    # only plot the Dy and Nd columns
    plot_mass_by_year(df[['Dy', 'Nd']], 'save_figs/material_onshore_Dy_Nd_{}_{}.png'.format(tp, scen), w_scale=6)

    ratio_on = ratio_on / (np.expand_dims(inflow_onshore, axis=1) + 1e-100)
    ratio_on = {"ratio": ratio_on,
                "years": years_onshore}
    return mass_by_year, avg_nacl_rotor_rep_mass, ratio_on

"""
=================
Scenario analysis
=================
"""
if __name__ == '__main__':
    
    args = get_parser()
    tp=args.tp
    scen=args.scen
    capacity_onshore(tp=tp, scen=scen)