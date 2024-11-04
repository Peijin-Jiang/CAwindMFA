"""
This script is used to calculate total (onshore + offshore) wind turbine material production environmental impact

It contains:
- add onshore and offshore environmental impact together
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
from _utils import *
from _params import get_parser
from b_onshore_material import capacity_onshore

from d_onshore_env_impact import get_onshore_env_impact
from d_offshore_env_impact import get_offshore_env_impact

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
            row_name = sheet.cell_value(i, 0)
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
    seq_, time_ = [0, 0, 0, 0, 0, 0], ['1993-2000', '2000-2010', '2010-2020','2020-2030', '2030-2040', '2040-2050']

    for i in range(len(seq)):
        if time[i] < 2000:
            seq_[0] += seq[i]
        elif time[i] < 2010:
            seq_[1] += seq[i]
        elif time[i] < 2020:
            seq_[2] += seq[i]
        elif time[i] < 2030:
            seq_[3] += seq[i]
        elif time[i] < 2040:
            seq_[4] += seq[i]
        else:
            seq_[5] += seq[i]
    return seq_, time_


colors = {'Steel and iron': '#fbb4ae', 'Cu': '#b3cde3', 'Al': '#ccebc5', 'Concrete': '#decbe4', 'Composites': '#fed9a6', 'REEs': '#ffffcc'}

en_consume_color = ['#deebf7', '#9ecae1', '#3182bd']
en_consume_color_by_mat = {'Cast Iron': '#deebf7', 'Steel': '#deebf7', 'Nd': '#deebf7', 'Dy': '#deebf7', 'Composites': '#deebf7'}
en_save_color = ['#e5f5e0', '#a1d99b', '#31a354']
en_save_color_by_mat = {'Cast Iron': '#e5f5e0', 'Steel': '#e5f5e0', 'Nd': '#e5f5e0', 'Dy': '#e5f5e0', 'Composites': '#e5f5e0'}

co2_consume_color = ['#fde0dd', '#fa9fb5', '#c51b8a']
co2_consume_color_by_mat = {'Cast Iron': '#fde0dd', 'Steel': '#fde0dd', 'Nd': '#fde0dd', 'Dy': '#fde0dd', 'Composites': '#fde0dd'}
co2_save_color = ['#fff7bc', '#fec44f', '#d95f0e']
co2_save_color_by_mat = {'Cast Iron': '#fff7bc', 'Steel': '#fff7bc', 'Nd': '#fff7bc', 'Dy': '#fff7bc', 'Composites': '#fff7bc'}

"""
=================
Scenario analysis
=================
"""
if __name__ == '__main__':
    args = get_parser()
    tp = args.tp
    scen = args.scen
    onshore_env = get_onshore_env_impact(tp, scen)
    offshore_env = get_offshore_env_impact(tp, scen)
    
    strategy_list = ['EoL_C', 'EoL_O']
    
    en_fig, en_ax = plt.subplots(figsize=(2.1*FIG_WIDTH, 2.1*FIG_HEIGHT))
    co2_fig, co2_ax = plt.subplots(figsize=(2*FIG_WIDTH, 2*FIG_HEIGHT))

    for si, sn in enumerate(strategy_list):
        onshore_results = onshore_env[sn]
        offshore_results = offshore_env[sn]
        
        total_results = onshore_results.copy()
        for k in onshore_results.keys():
            if isinstance(onshore_results[k], list) or isinstance(onshore_results[k], np.ndarray):
                total_results[k][3: ] = np.asarray(total_results[k][3: ]) + np.asarray(offshore_results[k])
            elif isinstance(onshore_results[k], dict):
                for kk in onshore_results[k].keys():
                    total_results[k][kk][3: ] = np.asarray(total_results[k][kk][3: ]) + np.asarray(offshore_results[k][kk])

        en_net, co2_net = total_results['en_net'], total_results['co2_net']
        en_consume, en_save, co2_consume, co2_save = total_results['en_consume'], total_results['en_save'], total_results['co2_consume'], total_results['co2_save']
        en_consume_by_mat, en_save_by_mat, en_net_by_mat = total_results['en_consume_by_mat'], total_results['en_save_by_mat'], total_results['en_net_by_mat']
        co2_consume_by_mat, co2_save_by_mat, co2_net_by_mat = total_results['co2_consume_by_mat'], total_results['co2_save_by_mat'], total_results['co2_net_by_mat']
        
        time_agg = onshore_env['time_agg']
        
        bar_width = 1 / (len(strategy_list)) * 0.8
        ax = en_ax
        bottom = [0 for _ in range(len(time_agg))]
        for m in en_consume_by_mat:
            ax.bar(np.arange(len(time_agg)) - si * bar_width, bottom=bottom, height=en_net_by_mat[m], color=colors[m], label='{} ({})'.format(m, sn), width=bar_width, alpha=0.5 + 0.5 * si)
            bottom = [bottom[j] + en_net_by_mat[m][j] for j in range(len(time_agg))]
   
        ax.set_xticks(np.arange(len(time_agg)) - bar_width/2)
        ax.set_xticklabels(time_agg)
        ax.set_ylabel('Energy (PJ)')
        ax.legend(loc='upper left')

        # plot CO2
        ax = co2_ax
        bottom = [0 for _ in range(len(time_agg))]
        for m in co2_consume_by_mat:
            ax.bar(np.arange(len(time_agg)) - si * bar_width, bottom=bottom, height=co2_net_by_mat[m], color=colors[m], label='{} ({})'.format(m, sn), width=bar_width, alpha=0.5 + 0.5 * si)
            bottom = [bottom[j] + co2_net_by_mat[m][j] for j in range(len(time_agg))]
        
        ax.set_xticks(np.arange(len(time_agg)) - bar_width/2)
        ax.set_xticklabels(time_agg)
        ax.set_ylabel('Mt CO₂ eq')
        ax.legend()
        
    # save en_axes to figure
    en_fig.tight_layout()
    en_fig.savefig('save_figs/total_energy_{}_{}.png'.format(tp, scen))
    
    co2_fig.tight_layout()
    co2_fig.savefig('save_figs/total_co2_{}_{}.png'.format(tp, scen))
    plt.close()
            