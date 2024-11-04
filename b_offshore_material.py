"""
This script is used to calculate offshore wind turbine material inflows

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
import collections
from _utils import *
from _params import get_parser
from a_capacity_flow import CapacityFlow
from b_onshore_material import load_avg_data, load_history_market_share, load_future_market_share, load_replacement_data

"""
================
Define functions
================
"""
# relationship between capacity and height for offshore wind turbine
def get_height(x):
    return 5.0679 * x ** 0.3373

# relationship between capacity and diameter for offshore wind turbine
def get_diameter(x):
    return 0.9466 * x ** 0.5872


def capacity_offshore(tp=1, scen='GNZ'):
    excel_path = "input_data/Wind_data.xls"
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
    avg_turb_offs = avg_turb_offs[len(stock_onshore_contrib) - len(stock_offshore_contrib): ]
    avg_nacl_offs = avg_nacl_offs[len(stock_onshore_contrib) - len(stock_offshore_contrib): ]
    avg_rotor_offs = avg_rotor_offs[len(stock_onshore_contrib) - len(stock_offshore_contrib): ]
    
    stock_offshore_contrib = stock_offshore_contrib / (np.repeat(np.expand_dims(avg_turb_offs, axis=1), len(stock_offshore_contrib), axis=1) + 1e-100)
    avg_nacl_mass = stock_offshore_contrib * np.repeat(np.expand_dims(avg_nacl_offs, axis=1), len(stock_offshore_contrib), axis=1)
    avg_rotor_mass = stock_offshore_contrib * np.repeat(np.expand_dims(avg_rotor_offs, axis=1), len(stock_offshore_contrib), axis=1)
    # process nacl
    avg_nacl_mass_ = []
    for k in ["DFIG/SCIG", "EESGDD", "PMSGDD", "PMSGGB", "PDD", "SDD"]:
        temp = avg_nacl_mass * np.repeat(np.expand_dims(nacl_market_share[k][len(stock_onshore_contrib) - len(stock_offshore_contrib): ], axis=1), len(avg_nacl_mass), axis=1)
        avg_nacl_mass_.append(temp)
    avg_nacl_mass_tech = np.stack(avg_nacl_mass_, axis=-1)
    oh_dict = load_offshore_dict(path=excel_path)
    oh_dict_array = np.asarray(pd.DataFrame({k: oh_dict[k] for k in history_nacl_market_share.keys()}))
    avg_nacl_mass_tech = np.dot(avg_nacl_mass_tech, oh_dict_array.T) 
    for i in range(avg_nacl_mass_tech.shape[-1]-2, avg_nacl_mass_tech.shape[-1]):
        avg_nacl_mass_tech[:, :, i] = avg_nacl_mass_tech[:, :, i] * np.repeat(np.expand_dims(avg_turb_offs, axis=1), len(stock_offshore_contrib), axis=1)/np.repeat(np.expand_dims(avg_nacl_offs, axis=1), len(stock_offshore_contrib), axis=1) / 1000
    # load replacement for nacelle
    future_nacl_rep, future_rotor_rep, his_nacl_rep, his_rotor_rep = load_replacement_data(excel_path)
    future_nacl_rep = future_nacl_rep[tp]
    future_rotor_rep = future_rotor_rep[tp]
    avg_nacl_mass = avg_nacl_mass * future_nacl_rep
    
    # process rotor
    oh_dict = load_offshore_dict(path=excel_path)
    material_list = list(oh_dict['/'].keys())
    oh_dict_array = np.expand_dims(np.asarray([oh_dict['/'][k] for k in material_list]), axis=-1)
    avg_rotor_mass_tech = np.dot(np.expand_dims(avg_rotor_mass, -1), oh_dict_array.T) 
    for i in range(avg_rotor_mass_tech.shape[-1]-2, avg_rotor_mass_tech.shape[-1]):
        avg_rotor_mass_tech[:, :, i] = avg_rotor_mass_tech[:, :, i] * np.repeat(np.expand_dims(avg_turb_offs, axis=1), len(stock_offshore_contrib), axis=1)/np.repeat(np.expand_dims(avg_rotor_offs, axis=1), len(stock_offshore_contrib), axis=1) / 1000
    
    avg_rotor_mass = np.sum(avg_rotor_mass_tech, axis=1)
    avg_nacl_mass = np.sum(avg_nacl_mass_tech, axis=1)

    # load replacement for rotor
    avg_rotor_mass = avg_rotor_mass * future_rotor_rep
    avg_nacl_rotor_rep_mass = avg_nacl_mass + avg_rotor_mass
    
    future_inflow_off = inflow_offshore.copy()
    ratio_off = outflow_offshore_contrib.copy()

    excel_path = "input_data/Wind_data.xls"
    df = pd.read_excel(excel_path, sheet_name='off_capacity')
    per_cap_list = df['Off_Future_capacity_per_turbine'].dropna().tolist()

    # perform the installation calculation
    # assumptions for offshore average capacity per wind turbine
    capacity_per_wind_20_29 = per_cap_list[0]
    capacity_per_wind_30_39 = per_cap_list[1]
    capacity_per_wind_40_50 = per_cap_list[2]
    
    oh_dict = load_offshore_dict(path="input_data/Wind_data.xls")
    ##print(oh_dict)
    capacity_per_wind_list = [capacity_per_wind_20_29] * 10 + [capacity_per_wind_30_39] * 10 + [capacity_per_wind_40_50] * 11   
 
    future_c_list = future_inflow_off.copy() * 1000 # convert to kW
    future_n_list = [future_c_list[i] / capacity_per_wind_list[i] for i in range(len(future_c_list))] # number of wind turbines
    future_d_list = get_diameter(np.array(capacity_per_wind_list)) # diameter of wind turbines
    future_h_list = get_height(np.array(capacity_per_wind_list)) # height of wind turbines
    
    time_list = [2020 + i for i in range(len(future_n_list))]
    
    future_mass_by_year = calculate_future_material_mass_offshore_by_year(future_n_list, np.array(capacity_per_wind_list), future_d_list, future_h_list, oh_dict, time_list, tp=tp)
    
    mass_by_year = collections.OrderedDict()
    mass_by_year_rep = collections.OrderedDict()
    for i, year in enumerate(np.sort(list(future_mass_by_year.keys()))):
        mass_by_year[year] = future_mass_by_year[year]
        mass_by_year_rep[year] = future_mass_by_year[year]
        for j, m in enumerate(material_list):
            mass_by_year_rep[year][m] = mass_by_year_rep[year][m] + avg_nacl_rotor_rep_mass[i, j]

    # save to csv
    df = pd.DataFrame(mass_by_year_rep).T
    # sort using the index
    df = df.sort_index()
    df = df / 1e6
    df.to_csv('results/material_offshore_mass_by_year_{}_{}.csv'.format(tp, scen))
    plot_mass_by_year(df, 'save_figs/offshore_material_{}_{}.png'.format(tp, scen), w_scale=6)
    plt.close()

    
    ratio_off = ratio_off / (np.expand_dims(inflow_offshore, axis=1) + 1e-100)
    ratio_off = {"ratio": ratio_off,
            "years": years_offshore}
    return mass_by_year, avg_nacl_rotor_rep_mass, ratio_off

"""
=================
Scenario analysis
=================
"""
if __name__ == '__main__':
    tp = get_parser().tp
    scen = get_parser().scen
    capacity_offshore(tp=tp, scen=scen)