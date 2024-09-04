"""
This script is used to calculate onshore wind turbine material outnflows

It contains:
- material outflows form wind turbines reaching the end of their service life
- material outflows form damaged components
- 2 energy demand scenarios: Gcam and GNZ
- 3 tech development scenarios: CT, AT, NT
- 2 EoL scenarios: EoL_C and EoL_O

"""

"""
================
Import libraries
================
"""
import os
import math
from tqdm import tqdm
from _utils import *
from _fig_settings import *
from _params import get_parser
from b_onshore_material import capacity_onshore

"""
=================
Scenario analysis
=================
"""
if __name__ == '__main__':
    args = get_parser()
    tp=args.tp
    scen=args.scen
    mass_by_year, avg_nacl_rotor_rep_mass, ratio_on = capacity_onshore(tp=tp, scen=scen)
    

    df = pd.DataFrame(mass_by_year).T
    # sort using the index
    df = df.sort_index()
    
    # material outflows form wind turbines reaching the end of their service life
    ratio_on_arr = ratio_on['ratio'] # r[i, j] means the ratio from year i to year j
    # add material outflows form damaged components
    out_flow_on_material = np.dot(ratio_on_arr.transpose(), df.values) + avg_nacl_rotor_rep_mass
    
    out_flow_df = pd.DataFrame(out_flow_on_material, index=df.index, columns=df.columns)
    
    for i in range(len(df.columns)):
        mass = df.columns[i]
        #print('Material for {} is {}'.format(mass, out_flow_on_material[i]))
    
    path = "input_data/Wind_data.xls"
    table, proc_methods = get_data_from_recy_new(path=path)
    
    # 5 EoL strategies 
    results = {}
    for k in table.keys():
        if 'off_shore' in k:
            continue
        
        t_type = k.split('_onshore')[0]
        
        results[t_type] = {}
        
        for i, m in enumerate(df.columns):
            recy = np.asarray(table[k][m])# [m]
            out_flow_m = out_flow_on_material[:, i] # [n]
            hist_len = 27
            hist_recy = np.asarray(table['EoL_C_onshore'][m])
            # calculate historical outflow
            out_flow_his = np.dot(out_flow_m.reshape(-1, 1)[:hist_len], hist_recy.reshape(1, -1)) # [m]
            out_flow_future = np.dot(out_flow_m.reshape(-1, 1)[hist_len:], recy.reshape(1, -1)) # [m]
            out_flow_m = np.concatenate([out_flow_his, out_flow_future], axis=0)
            results[t_type][m] = out_flow_m
            # #print outflow m
            #print('Outflow for {} is {} on strategy {}'.format(m, out_flow_m, t_type))
    
    df.to_csv('results/material_onshore_mass_by_year_{}_{}.csv'.format(tp, scen))
    
    # 2 scenarios in total（EoL_C_onshore, EoL_O_onshore）
    for strategy in results:
        
        if 'offshore' in strategy:
            continue
        
        result = results[strategy]
        
        fig, ax = plt.subplots(figsize=(6, 6))
        
        # plot mass by year first
        year = [k for k in mass_by_year]
        materials = [m for m in mass_by_year[year[0]]]
            
        result_sum = np.zeros_like(result[materials[0]])
        
        for m in materials:
            out_flow_m = result[m]
            result_sum += out_flow_m
        
        #axes[i].bar(year, mass, label=m, color='red')
        mass_by_year_rep = {}
        #axes[i].bar(year, mass, label=m, color='red')
        for i, yr in enumerate(np.sort(list(mass_by_year.keys()))):
            mass_by_year_rep[yr] = {}
            for j, m in enumerate(materials):
                mass_by_year_rep[yr][m] = mass_by_year[yr][m] + avg_nacl_rotor_rep_mass[i, j]
        virgin_material = {}
        for m in materials:
            diff = np.asarray([mass_by_year_rep[i][m] for i in range(2020, 2051)]) - result[m][-31:, 0]
            virgin_material[m] = diff
            
        virgin_material = pd.DataFrame(virgin_material, index=year[-31:])
        os.makedirs('results/onshore_virgin', exist_ok=True)
        virgin_material.to_csv('results/onshore_virgin/onshore_{}_{}_{}.csv'.format(strategy, tp, scen))
        
        cum_recy = np.zeros(len(year))
        colors = ['#fbb4ae', '#b3cde3', '#ccebc5', '#decbe4', '#fed9a6']
        for j, p in enumerate(tqdm(proc_methods)):

            #ax.bar(year, result_sum[:, j], bottom=cum_recy, label=p, color=colors[j])

            ax.plot([], [], label=p, color=colors[j])

            # fill in color between result_sum[:, j] and cum_recy
            ax.fill_between(year, cum_recy + result_sum[:, j], cum_recy, color=colors[j], edgecolor='none')
            
            cum_recy = result_sum[:, j] + cum_recy
        
        #print(result[m][:, 1])

        ax.legend(loc='upper left')
        
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        
        ax.set_xlabel('Year')
        ax.set_ylabel('Mass [t]')
        
        leg = ax.get_legend()
        leg.get_frame().set_linewidth(0.0)
        
        fig.tight_layout()
            
        plt.savefig('save_figs/onshore_{}_{}_{}.png'.format(strategy, tp, scen))
        plt.close()

        os.makedirs('results/onshore_EoL', exist_ok=True)
        # export plot data as df
        df = pd.DataFrame(result_sum, columns=proc_methods, index=year)
        df.to_csv('results/onshore_EoL/onshore_{}_sum_{}_{}.csv'.format(strategy, tp, scen))

        for m in result.keys():
            result[m][result[m] < 0] = 0
            df = pd.DataFrame(result[m], columns=proc_methods, index=year)
            df.to_csv('results/onshore_EoL/onshore_{}_{}_{}_{}.csv'.format(strategy, m, tp, scen))