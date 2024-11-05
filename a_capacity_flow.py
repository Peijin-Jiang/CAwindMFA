import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy.stats import weibull_min
from _params import get_parser

"""
=============
prepare files
=============
"""
def get_capacity_data_from_excel(excel_path):
    df_onshore = pd.read_excel(excel_path, sheet_name='on_capacity')
    df_offshore = pd.read_excel(excel_path, sheet_name='off_capacity')
    # extract the historical onshore inflow data
    inflow_history_onshore = df_onshore['on_historical_capacity_inflow'].dropna().values
    # extract the future onshore/offshore stock capacity data
    stock_future_onshore = {
        'Gcam': df_onshore['on_future_capacity_stock'].dropna().to_list(),
        'GNZ': df_onshore['on_future_capacity_stock_1'].dropna().to_list(),
    }
    stock_future_offshore = {
        'Gcam': df_offshore['off_future_capacity'].dropna().to_list(),
        'GNZ': df_offshore['off_future_capacity_1'].dropna().to_list(),
    }
    # extract the historical/future year data
    def process_years(df_col):
        years = df_col.dropna().to_list()
        years = [int(year) for year in years]
        return years
    years_future_onshore, years_future_offshore, years_history_onshore = [
        process_years(df_col) for df_col in [
            df_onshore['on_future_year'], df_offshore['off_future_year'], df_onshore['on_historical_year']]
    ]
    # extract lifetimes
    lifetimes = pd.read_excel(excel_path, sheet_name='tech_dev', header=0)
    historical_lifetime = list(lifetimes['his_lifetime'].dropna().values)[0]
    future_lifetime = list(lifetimes['future_lifetime'].dropna().values)[0]

    return stock_future_onshore, years_future_onshore, years_history_onshore, inflow_history_onshore, \
        stock_future_offshore, years_future_offshore, historical_lifetime, future_lifetime

"""
================
Define functions
================
"""
class CapacityFlow:
    """
    This class is used to calculate the capacity flow given a dataset

    Arguments:
    ----------
    excel_path: str
        Path to the excel file containing the dataset.
        This excel should include the following information:
        - 1993-2019 inflow
        - 2020-2050 stock (GCam and GNZ)
    """
    def __init__(self, excel_path: str = "input_data/Wind_data.xls"):
        self.excel_path = excel_path
        # read the data from the excel file
        (self.stock_future_onshore, self.years_future_onshore, self.years_history_onshore,
         self.inflow_history_onshore, self.stock_future_offshore, self.years_future_offshore,
         self.historical_lifetime, self.future_lifetime) = get_capacity_data_from_excel(excel_path)

    def interp_annual_for_future(self, 
                                 stock_future_onshore, years_future_onshore_annual, years_future_onshore,
                                 stock_future_offshore, years_future_offshore_annual, years_future_offshore,
                                 capacity_scenario: str = 'Gcam'):
        """Interpolate the stock data for the future years"""
        if capacity_scenario == 'GNZ':
            stock_future_onshore = stock_future_onshore
            stock_future_offshore = stock_future_offshore
        elif capacity_scenario == 'Gcam':
            stock_future_onshore = np.interp(years_future_onshore_annual, years_future_onshore, stock_future_onshore)
            stock_future_offshore = np.interp(years_future_offshore_annual, years_future_offshore, stock_future_offshore)
        else:
            raise ValueError(f"Invalid capacity scenario: {capacity_scenario}")
        return stock_future_onshore, stock_future_offshore

    def update_capacity(self, capacity_scenario: str = 'Gcam'):
        """Update the capacity data"""

        years_future_onshore_annual = np.arange(2020, self.years_future_onshore[-1] + 1)
        years_future_offshore_annual = np.arange(self.years_future_offshore[0], self.years_future_offshore[-1] + 1)

        return self.stock_future_onshore[capacity_scenario], self.years_future_onshore, self.years_history_onshore, \
            self.inflow_history_onshore, self.stock_future_offshore[capacity_scenario], self.years_future_offshore, \
            years_future_onshore_annual, years_future_offshore_annual

    def get_weibull_scale_from_mean(self, mean, shape):
        from scipy.special import gamma
        scale = mean / gamma(1 + 1 / shape)
        return scale

    def get_one_weibull_pdf(self, shape, scale, years):
        '''Generate the Weibull PDF for the given shape and scale'''
        weibull_pdf = weibull_min.pdf(np.arange(len(years)), shape, scale=scale)
        return weibull_pdf

    def get_weibull_pdf(self, years_future_onshore_annual, years_future_offshore_annual):
        shape_history_onshore, mean_history_onshore = 4.07, self.historical_lifetime
        scale_history_onshore = self.get_weibull_scale_from_mean(mean_history_onshore, shape_history_onshore)
        shape_future_onshore, mean_future_onshore = 4.07, self.future_lifetime
        scale_future_onshore = self.get_weibull_scale_from_mean(mean_future_onshore, shape_future_onshore)
        shape_future_offshore, mean_future_offshore = 4.07, self.future_lifetime
        scale_future_offshore = self.get_weibull_scale_from_mean(mean_future_offshore, shape_future_offshore)

        weibull_pdf_history_onshore, weibull_pdf_future_onshore, weibull_pdf_future_offshore = [
            self.get_one_weibull_pdf(shape, scale, years) for shape, scale, years in zip(
                [shape_history_onshore, shape_future_onshore, shape_future_offshore],
                [scale_history_onshore, scale_future_onshore, scale_future_offshore],
                [self.years_history_onshore, years_future_onshore_annual, years_future_offshore_annual])
        ]
        return weibull_pdf_history_onshore, weibull_pdf_future_onshore, weibull_pdf_future_offshore

    def update_outflow_stock_from_inflow(self, inflow, weibull_pdf):
        outflow, outflow_contrib = np.zeros(len(inflow)), np.zeros([len(inflow), len(inflow)])
        stock = np.zeros(len(inflow))
        for i in range(len(inflow)):
            for j in range(i):
                years_diff = i - j
                if years_diff >= len(weibull_pdf): continue
                # calculate the outflow from j to i
                outflow_j_in_i = inflow[j] * weibull_pdf[years_diff]
                outflow[i] += outflow_j_in_i
                # calculate the contribution of j to i
                outflow_contrib[j, i] = outflow_j_in_i
            # add the previous stock to the current stock
            stock[i] = inflow[i] - outflow[i]
            stock[i] += stock[i - 1] if i > 0 else 0
        return outflow, stock, outflow_contrib

    def solver_for_inflow(self, stock_pre, stock_curr, outflow_pre):
        inflow_curr = stock_curr - stock_pre + outflow_pre
        return inflow_curr

    def update_inflow_outflow_from_stock(self, stock, inflow_history=None, stock_history=None, weibull_pdf_history=None, weibull_pdf_future=None):
        inflow_future, outflow_future, outflow_contrib = np.zeros(len(stock)), np.zeros(len(stock)), \
            np.zeros([len(stock) + len(inflow_history), len(stock)]) if inflow_history is not None else np.zeros([len(stock), len(stock)])
        history_length = len(inflow_history) if inflow_history is not None else 0
        for i in range(len(stock)):
            outflow_pre = 0
            # incorporating the historical inflow data
            for j in range(history_length):
                years_diff = i - j + history_length
                if years_diff >= len(weibull_pdf_history): continue
                failure_rate = weibull_pdf_history[years_diff]
                outflow_j_in_i = inflow_history[j] * failure_rate
                outflow_pre += outflow_j_in_i
                outflow_contrib[j, i] = outflow_j_in_i
            for j in range(i):
                years_diff = i - j
                if years_diff >= len(weibull_pdf_future): continue
                failure_rate = weibull_pdf_future[years_diff]
                outflow_j_in_i = inflow_future[j] * failure_rate
                outflow_pre += outflow_j_in_i
                outflow_contrib[j + history_length, i] = outflow_j_in_i
            # calculate the inflow for the current year
            inflow_future[i] = self.solver_for_inflow(stock[i - 1], stock[i], outflow_pre) if i > 0 \
                else self.solver_for_inflow(stock_history[-1], stock[i], outflow_pre)
            # update the outflow for the current year
            outflow_future[i] = outflow_pre
        return inflow_future, outflow_future, outflow_contrib

    def get_stock_contrib(self, outflow_contrib, inflow):
        """Get the contribution of stock given the outflow and inflow data"""
        stock_contrib = outflow_contrib.copy()
        stock_contrib = np.cumsum(stock_contrib, axis=1)
        # inflow minus cumsum of outflow
        for i in range(len(inflow)):
            stock_contrib[i, :] = inflow[i] - stock_contrib[i, :]
        return stock_contrib

    def plot(self, tech_scenario: int = 0):
        """Plot the inflow, stock, outflow for onshore and offshore with larger y-axis font size and consistent significant figures"""
        color_dict = {'Gcam': '#ca0020', 'GNZ': '#0571b0', 'Historical': '#f4a582'}
        years_future = np.arange(2020, 2051)
        years_history = np.arange(1993, 2020)

        def format_ax(ax, title):
            ax.set_title(title)
            ax.set_xlabel('Year')
            ax.set_ylabel('Capacity (MW)', fontsize=12)  # Increased font size for y-axis label
            ax.legend(frameon=False, loc='upper left')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

        # plot onshore and offshore data
        _, axs = plt.subplots(2, 3, figsize=(13, 7), constrained_layout=True)
        for line_type, line_width, capacity_scenario in zip(['-', '--'], [2, 1], ['Gcam', 'GNZ']):
            inflow_onshore, inflow_future_onshore, stock_onshore, outflow_onshore, inflow_offshore, outflow_offshore, stock_offshore, \
                outflow_onshore_contrib, outflow_offshore_contrib, stock_onshore_contrib, stock_offshore_contrib, \
                years_onshore, years_offshore = self(tech_scenario=tech_scenario, capacity_scenario=capacity_scenario)
            
            # Convert to GW by dividing by 1000, keeping full precision for calculation
            inflow_onshore = np.array(inflow_onshore) 
            stock_onshore = np.array(stock_onshore) 
            outflow_onshore = np.array(outflow_onshore) 
            inflow_offshore = np.array(inflow_offshore)
            stock_offshore = np.array(stock_offshore) 
            outflow_offshore = np.array(outflow_offshore)


            # Plot onshore data
            axs[0, 0].plot(np.concatenate((years_history, years_future)), inflow_onshore, label=capacity_scenario, color=color_dict[capacity_scenario], linestyle=line_type, linewidth=line_width)
            axs[0, 1].plot(np.concatenate((years_history, years_future)), stock_onshore, label=capacity_scenario, color=color_dict[capacity_scenario], linestyle=line_type, linewidth=line_width)
            axs[0, 2].plot(np.concatenate((years_history, years_future)), outflow_onshore, label=capacity_scenario, color=color_dict[capacity_scenario], linestyle=line_type, linewidth=line_width)
            
            # Plot offshore data
            axs[1, 0].plot(years_offshore, inflow_offshore, label=capacity_scenario, color=color_dict[capacity_scenario], linestyle=line_type, linewidth=line_width)
            format_ax(axs[1, 0], 'Offshore Inflow')
            axs[1, 1].plot(years_offshore, stock_offshore, label=capacity_scenario, color=color_dict[capacity_scenario], linestyle=line_type, linewidth=line_width)
            format_ax(axs[1, 1], 'Offshore Stock')
            axs[1, 2].plot(years_offshore, outflow_offshore, label=capacity_scenario, color=color_dict[capacity_scenario], linestyle=line_type, linewidth=line_width)
            format_ax(axs[1, 2], 'Offshore Outflow')
            
        # Plot shared historical data
        axs[0, 0].plot(years_history, inflow_onshore[: len(years_history)], label='Historical', color=color_dict['Historical'])
        format_ax(axs[0, 0], 'Onshore Inflow')
        axs[0, 1].plot(years_history, stock_onshore[: len(years_history)], label='Historical', color=color_dict['Historical'])
        format_ax(axs[0, 1], 'Onshore Stock')
        axs[0, 2].plot(years_history, outflow_onshore[: len(years_history)], label='Historical', color=color_dict['Historical'])
        format_ax(axs[0, 2], 'Onshore Outflow')

        plt.savefig('save_figs/capacity_flow_{}.png'.format(tech_scenario))
        plt.close()

    def save_data(self, years_onshore, inflow_onshore, stock_onshore, outflow_onshore, 
                  years_offshore, inflow_offshore, stock_off, outflow_offshore,
                  tech_scenario: int = 0, capacity_scenario: str = 'Gcam', save_root='results/capacity'):
        """Save the data to a csv file"""
        save_onshore = pd.DataFrame({
            'Year': years_onshore, 
            'Inflow (MW)': np.array(inflow_onshore), 
            'Stock (MW)': np.array(stock_onshore), 
            'Outflow (MW)': np.array(outflow_onshore)
        })
        save_offshore = pd.DataFrame({
            'Year': years_offshore, 
            'Inflow (MW)': np.array(inflow_offshore), 
            'Stock (MW)': np.array(stock_off), 
            'Outflow (MW)': np.array(outflow_offshore)
    })

        save_dir = os.path.join(save_root)
        os.makedirs(save_dir, exist_ok=True)
        save_onshore.to_csv(os.path.join(save_dir, f'onshore_{capacity_scenario}_{tech_scenario}.csv'), index=False)
        save_offshore.to_csv(os.path.join(save_dir, f'offshore_{capacity_scenario}_{tech_scenario}.csv'), index=False)

    def __call__(self, tech_scenario: int = 0, capacity_scenario: str = 'Gcam'):
        """Calculate the capacity flow given the dataset"""
        # update the capacity data
        (stock_future_onshore, years_future_onshore, years_history_onshore, inflow_history_onshore,
         stock_future_offshore, years_future_offshore, 
         years_future_onshore_annual, years_future_offshore_annual) = self.update_capacity(capacity_scenario)
    
        # do interpolation for the future years
        stock_future_onshore, stock_future_offshore = self.interp_annual_for_future(
            stock_future_onshore, years_future_onshore_annual, years_future_onshore,
            stock_future_offshore, years_future_offshore_annual, years_future_offshore,
            capacity_scenario)
    
        # make the Weibull PDF
        weibull_pdf_history_onshore, weibull_pdf_future_onshore, weibull_pdf_future_offshore = self.get_weibull_pdf(
            years_future_onshore_annual, years_future_offshore_annual)
    
        # calculate the total years
        years_total_onshore = len(years_history_onshore) + len(years_future_onshore_annual)
        years_total_offshore = len(years_future_offshore_annual)
    
        # register each year's contribution on the current outflow
        outflow_onshore_contrib = np.zeros([years_total_onshore, years_total_onshore])
        outflow_offshore_contrib = np.zeros([years_total_offshore, years_total_offshore])
    
        # update the historical outflow and stock for onshore
        outflow_history_onshore, stock_history_onshore, outflow_history_onshore_contrib = self.update_outflow_stock_from_inflow(
            inflow_history_onshore, weibull_pdf_history_onshore)
        outflow_onshore_contrib[0: len(years_history_onshore), 0: len(years_history_onshore)] = outflow_history_onshore_contrib
    
        # update inflow and outflow of onshore given the stock and previous inflow
        inflow_future_onshore, outflow_future_onshore, outflow_future_onshore_contrib = self.update_inflow_outflow_from_stock(
            stock_future_onshore, inflow_history_onshore, stock_history_onshore, weibull_pdf_history_onshore, weibull_pdf_future_onshore)
        outflow_onshore_contrib[:, len(years_history_onshore): ] = outflow_future_onshore_contrib

        # concatenate inflow, stock, outflow for onshore
        inflow_onshore = np.concatenate((inflow_history_onshore, inflow_future_onshore))
        stock_onshore = np.concatenate((stock_history_onshore, stock_future_onshore))
        outflow_onshore = np.concatenate((outflow_history_onshore, outflow_future_onshore))
    
        # update inflow and outflow of offshore given the stock
        inflow_offshore, outflow_offshore, outflow_offshore_contrib = self.update_inflow_outflow_from_stock(
            stock_future_offshore, stock_history=[0], weibull_pdf_future=weibull_pdf_future_offshore)
    
        # stock offshore
        stock_offshore = stock_future_offshore.copy()
    
        # concatenate years for onshore
        years_onshore = np.concatenate((years_history_onshore, years_future_onshore_annual))
        
        # get the contribution of stock
        stock_onshore_contrib = self.get_stock_contrib(outflow_onshore_contrib, inflow_onshore)
        stock_offshore_contrib = self.get_stock_contrib(outflow_offshore_contrib, inflow_offshore)
        
        # save the data
        self.save_data(years_onshore, inflow_onshore, stock_onshore, outflow_onshore, 
                       years_future_offshore_annual, inflow_offshore, stock_offshore, outflow_offshore,
                       tech_scenario, capacity_scenario)
        return inflow_onshore, inflow_future_onshore, stock_onshore, outflow_onshore, inflow_offshore, outflow_offshore, stock_offshore, \
            outflow_onshore_contrib, outflow_offshore_contrib, \
            stock_onshore_contrib, stock_offshore_contrib, \
            years_onshore, years_future_offshore_annual

"""
=================
Scenario analysis
=================
"""
if __name__ == '__main__':
    capacity_flow = CapacityFlow()  
    capacity_flow.plot(tech_scenario=0)
