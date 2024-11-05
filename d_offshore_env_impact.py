""" 
This script is used to calculate offshore wind turbine material production environmental impact

It contains:
- climate change impact and energy consumption for material production
- climate change impact reduction and energy consumption reduction through closed-loop recycling
- 2 energy demand scenarios: Gcam and GNZ
- 3 tech development scenarios: CT, AT, NT
- 2 EoL scenarios: EoL_C and EoL_O

"""

"""
================
Import libraries
================
"""
import math
import collections

from _utils import *
from b_offshore_material import capacity_offshore
from _params import get_parser

"""
=============
prepare files
=============
"""
# get environmental impact factor from excel
def get_env_impact(path=''):
    wb = xlrd.open_workbook(path)
    # load existing data
    sheet = wb.sheet_by_name('envir_impact')
    
    env_impact = {}
    
    for i in range(0, 8):
        for j in range(1, 5):
            col_name = sheet.cell_value(0, j)
            if col_name not in env_impact:
                env_impact[col_name] = {}
            row_name = sheet.cell_value(i, 0).strip()
            env_impact[col_name][row_name] = sheet.cell_value(i, j)
            if isinstance(sheet.cell_value(i, j), str) and 'N/A' in sheet.cell_value(i, j):
                env_impact[col_name][row_name] = 0
    return env_impact

"""
================
Define functions
================
"""
# add 10 years impact together
def aggregate_seq(seq, time):
    seq_, time_ = [0, 0, 0], ['2020-2030', '2030-2040', '2040-2050']

    for i in range(len(seq)):
        if time[i] < 2030:
            seq_[0] += seq[i]
        elif time[i] < 2040:
            seq_[1] += seq[i]
        else:
            seq_[2] += seq[i]
    return seq_, time_

colors = {'Steel and iron': '#fbb4ae', 'Cu': '#b3cde3', 'Al': '#ccebc5', 'Concrete': '#decbe4', 'Composites': '#fed9a6', 'REEs': '#ffffcc'}

en_consume_color = ['#deebf7', '#9ecae1', '#3182bd']
en_save_color = ['#e5f5e0', '#a1d99b', '#31a354']

co2_consume_color = ['#fde0dd', '#fa9fb5', '#c51b8a']
co2_save_color = ['#fff7bc', '#fec44f', '#d95f0e']

# calculate the offshore wind turbine material production environmental impact
def get_offshore_env_impact(tp, scen):
    
    export_results = collections.OrderedDict()
    
    excel_path = "input_data/Wind_data.xls"
    env_impact = get_env_impact(path=excel_path)

    mass_by_year, avg_nacl_rotor_rep_mass, ratio_off = capacity_offshore(tp=tp, scen=scen)
    year = [k for k in mass_by_year]
    materials = [m for m in mass_by_year[year[0]]]
    mass_by_year_rep = {}
    #axes[i].bar(year, mass, label=m, color='red')
    for i, yr in enumerate(np.sort(list(mass_by_year.keys()))):
        mass_by_year_rep[yr] = {}
        for j, m in enumerate(materials):
            mass_by_year_rep[yr][m] = mass_by_year[yr][m] + avg_nacl_rotor_rep_mass[i, j]
              
    time_list = [year for year in mass_by_year]

    # save to csv
    df = pd.DataFrame(mass_by_year_rep).T
    # sort using the index
    df = df.sort_index()

    ratio_off_arr = ratio_off['ratio'] # r[i, j] means the ratio from year i to year j
    out_flow_off_material = np.dot(ratio_off_arr.transpose(), df.values) + avg_nacl_rotor_rep_mass
    
    for i in range(len(df.columns)):
        mass = df.columns[i]
        #print('Material for {} is {}'.format(mass, out_flow_off_material[i]))
    
    path = "input_data/Wind_data.xls"
    table, proc_methods = get_data_from_recy_new(path=path)
    
    results = {}
    for k in table.keys():
        if 'on_shore' in k:
            continue
        
        t_type = k.split('_offshore')[0]
        
        results[t_type] = {}
        
        for i, m in enumerate(df.columns):
            recy = np.asarray(table[k][m]) # [m]
            out_flow_m = out_flow_off_material[:, i] # [n]
            
            out_flow_m = np.dot(out_flow_m.reshape(-1, 1), recy.reshape(1, -1)) # [n, m]
            results[t_type][m] = out_flow_m
            # print outflow m
            #print('Outflow for {} is {} on strategy {}'.format(m, out_flow_m, t_type))
    
    # make the figures
    
    en_fig, en_ax = plt.subplots(figsize=(1.8*FIG_WIDTH, 1.8*FIG_HEIGHT))
    co2_fig, co2_ax = plt.subplots(figsize=(1.8*FIG_WIDTH, 1.8*FIG_HEIGHT))

    strategy_list = results.keys()
    strategy_list = [s for s in strategy_list if 'onshore' not in s]
    
    for si, sn in enumerate(strategy_list):

        en_consume, en_save = 0, 0
        co2_consume, co2_save = 0, 0
        
        en_consume_by_mat, en_save_by_mat = {}, {}
        co2_consume_by_mat, co2_save_by_mat = {}, {}

        for i, m in enumerate(mass_by_year_rep[2050]):
            
            mass = np.asarray([mass_by_year_rep[y][m] for y in mass_by_year_rep])
            
            recy_list = results[sn][m][:, 0]

            for k in range(len(recy_list)):
                if recy_list[k] > mass[k]:
                    recy_list[k] = mass[k]
            
            inflow = mass 
            
            if m == 'Cast Iron':
                m_conv = 'Steel and iron'
            elif m == 'Steel':
                m_conv = 'Steel and iron'
            elif m == 'Nd' or m == 'Dy':
                m_conv = 'REEs'
            elif 'Composites' in m:
                m_conv = 'Composites'
            elif m == 'Others' or 'Other' in m:
                continue
            else:
                m_conv = m
                
            coef = env_impact['Energy_consumption(MJ kg-1)'][m_conv]
            en_consume += np.array(inflow) * coef / 1e6  # Convert to PJ
            if m_conv != 'EE':
                en_consume_by_mat[m_conv] = np.array(inflow) * coef / 1e6 if m_conv not in en_consume_by_mat else en_consume_by_mat[m_conv] + np.array(inflow) * coef / 1e6
            
            coef = env_impact['Energy_saved (MJ kg-1)'][m_conv]
            en_save += np.array(recy_list) * coef / 1e6  # Convert to PJ
            if m_conv != 'EE':
                en_save_by_mat[m_conv] = np.array(recy_list) * coef / 1e6 if m_conv not in en_save_by_mat else en_save_by_mat[m_conv] + np.array(recy_list) * coef / 1e6
            
            coef = env_impact['CO2_emission (kg)'][m_conv]
            co2_consume += np.array(inflow) * coef / 1e6  # Convert to Mt
            if m_conv != 'EE':
                co2_consume_by_mat[m_conv] = np.array(inflow) * coef / 1e6 if m_conv not in co2_consume_by_mat else co2_consume_by_mat[m_conv] + np.array(inflow) * coef / 1e6
            
            coef = env_impact['CO2_reduction(kg)'][m_conv]
            co2_save +=  np.array(recy_list) * coef / 1e6  # Convert to Mt
            if m_conv != 'EE':
                co2_save_by_mat[m_conv] = np.array(recy_list) * coef / 1e6 if m_conv not in co2_save_by_mat else co2_save_by_mat[m_conv] + np.array(recy_list) * coef / 1e6
        
        # export env impact to csv
        df = {'Energy consumption': en_consume, 'Energy saved': en_save, 'CO2 emission': co2_consume, 'CO2 saved': co2_save}
        for m in en_consume_by_mat:
            df[m + '_Energy consumption'] = en_consume_by_mat[m]
            df[m + '_Energy saved'] = en_save_by_mat[m]
            df[m + '_CO2 emission'] = co2_consume_by_mat[m]
            df[m + '_CO2 saved'] = co2_save_by_mat[m]
        df = pd.DataFrame(df, index=time_list)
        df.to_csv('results/offshore_env_impact_{}_{}_{}.csv'.format(sn, tp, scen))

        # energy consumption and saving/reduction
        en_consume = aggregate_seq(en_consume, time_list)[0]
        en_save = aggregate_seq(en_save, time_list)[0]
        en_consume_by_mat = {k: aggregate_seq(v, time_list)[0] for k, v in en_consume_by_mat.items()}
        en_save_by_mat = {k: aggregate_seq(v, time_list)[0] for k, v in en_save_by_mat.items()}
        en_net = np.array(en_consume) - np.array(en_save)
        en_net_by_mat = {k: np.array(en_consume_by_mat[k]) - np.array(en_save_by_mat[k]) for k in en_consume_by_mat.keys()}
        
        en_consume_mean_by_mat = {k: -np.mean(en_consume_by_mat[k]) for k in en_consume_by_mat.keys()}
        # sort key by mean value
        en_consume_by_mat = {k: v for k, v in sorted(en_consume_by_mat.items(), key=lambda item: en_consume_mean_by_mat[item[0]])}
        
        # climate change impact emission and saving/reduction
        co2_consume = aggregate_seq(co2_consume, time_list)[0]
        co2_save, time_agg = aggregate_seq(co2_save, time_list)
        co2_save_by_mat = {k: aggregate_seq(v, time_list)[0] for k, v in co2_save_by_mat.items()}
        co2_consume_by_mat = {k: aggregate_seq(v, time_list)[0] for k, v in co2_consume_by_mat.items()}
        co2_net = np.array(co2_consume) - np.array(co2_save)
        co2_net_by_mat = {k: np.array(co2_consume_by_mat[k]) - np.array(co2_save_by_mat[k]) for k in co2_consume_by_mat.keys()}
        
        co2_consume_mean_by_mat = {k: -np.mean(co2_consume_by_mat[k]) for k in co2_consume_by_mat.keys()}
        # sort key by mean value
        co2_consume_by_mat = {k: v for k, v in sorted(co2_consume_by_mat.items(), key=lambda item: co2_consume_mean_by_mat[item[0]])}
        
        res_i = {'en_consume': en_consume, 'en_save': en_save, 'en_net': en_net, 'co2_consume': co2_consume, 'co2_save': co2_save, 'co2_net': co2_net}
        res_i.update({'en_consume_by_mat': en_consume_by_mat, 'en_save_by_mat': en_save_by_mat, 'en_net_by_mat': en_net_by_mat})
        res_i.update({'co2_consume_by_mat': co2_consume_by_mat, 'co2_save_by_mat': co2_save_by_mat, 'co2_net_by_mat': co2_net_by_mat})
        export_results[sn] = res_i
        # plot energy
        
        bar_width = 1 / (len(strategy_list)) * 0.8
        ax = en_ax
        bottom = [0 for _ in range(len(time_agg))]
        for m in en_consume_by_mat:
            ax.bar(np.arange(len(time_agg)) - si * bar_width, bottom=bottom, height=en_net_by_mat[m], color=colors[m], label='{} ({})'.format(m, sn), width=bar_width, alpha=0.5 + 0.5 * si)
            bottom = [bottom[j] + en_net_by_mat[m][j] for j in range(len(time_agg))]
        
        ax.set_xticks(np.arange(len(time_agg)) - bar_width/2)
        ax.set_xticklabels(time_agg)
        ax.set_ylabel('Energy (PJ)',fontsize=18)
        ax.set_xlabel('Year', fontsize=18)
        ax.legend(loc='upper left',fontsize=12)
        ax.tick_params(axis='y', labelsize=16) 
        ax.tick_params(axis='x', labelsize=14)
        leg = ax.get_legend()
        leg.get_frame().set_linewidth(0.0)

        # plot CO2
        ax = co2_ax
        bottom = [0 for _ in range(len(time_agg))]
        for m in co2_consume_by_mat:
            ax.bar(np.arange(len(time_agg)) - si * bar_width, bottom=bottom, height=co2_net_by_mat[m], color=colors[m], label='{} ({})'.format(m, sn), width=bar_width, alpha=0.5 + 0.5 * si)
            bottom = [bottom[j] + co2_net_by_mat[m][j] for j in range(len(time_agg))]
        
        ax.set_xticks(np.arange(len(time_agg)) - bar_width/2)
        ax.set_xticklabels(time_agg)
        ax.set_ylabel('Mt CO₂e',fontsize=18)
        ax.set_xlabel('Year', fontsize=18)
        ax.legend(loc='upper left',fontsize=12)
        ax.tick_params(axis='y', labelsize=16) 
        ax.tick_params(axis='x', labelsize=14) 
        leg = ax.get_legend()
        leg.get_frame().set_linewidth(0.0)
        
    # save en_axes to figure
    en_fig.tight_layout()
    en_fig.savefig('save_figs/offshore_energy_{}_{}.png'.format(tp, scen))
    
    co2_fig.tight_layout()
    co2_fig.savefig('save_figs/offshore_co2_{}_{}.png'.format(tp, scen))
    plt.close()
    
    return export_results

"""
=================
Scenario analysis
=================
"""
if __name__ == '__main__':
    
    args = get_parser()
    tp=args.tp
    scen=args.scen
    
    get_offshore_env_impact(tp, scen)
