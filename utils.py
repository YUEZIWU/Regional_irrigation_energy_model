import os
import argparse
import yaml
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

def annualization_rate(i, years):
    return (i*(1+i)**years)/((1+i)**years-1)


def get_args():
    # Store all parameters for easy retrieval
    parser = argparse.ArgumentParser(
        description = 'fixed&flexible')
    parser.add_argument('--params_filename',
                        type=str,
                        default='params.yaml',
                        help = 'Loads model parameters')
    args = parser.parse_args()
    config = yaml.load(open(args.params_filename), Loader=yaml.FullLoader)
    for k,v in config.items():
        args.__dict__[k] = v
    return args


def load_timeseries(args):
    T = args.num_hours
    # Load solar & load time series, all region use the same
    solar_pot_hourly   = np.array(pd.read_excel(os.path.join(args.data_dir, 'solar_pot.xlsx'),
                                                index_col=None))[0:T,0]
    fix_load_hourly_kw = np.array(pd.read_excel(os.path.join(args.data_dir, 'fixed_load_kw.xlsx'),
                                                index_col=None))[0:T,0]
    rain_rate_daily_mm_m2 = np.array(pd.read_excel(os.path.join(args.data_dir, 'rain_rate_mm_m2.xlsx'), index_col=None))[0:T,1]
    return fix_load_hourly_kw, solar_pot_hourly, rain_rate_daily_mm_m2


def read_irrigation_area(args):
    irrigation_area_m2 = pd.read_csv(os.path.join(args.data_dir, 'pts_area.csv'))["AreaSqM"][0:args.num_regions]
    return irrigation_area_m2

def find_extreme_solar_period(args):
    # find the least 5 days solar potential during the irrigation seasons
    T = args.num_hours
    solar_pot_hourly   = np.array(pd.read_excel(os.path.join(args.data_dir, 'solar_pot.xlsx'),
                                                index_col=None))[0:T,0]
    extreme_solar_start_day = 0
    for day in list(range(args.first_season_start, args.first_season_end - args.water_account_days + 2)) + \
               list(range(args.second_season_start, args.second_season_end - args.water_account_days + 2)):
        if np.sum(solar_pot_hourly[day*24:(day+5)*24]) < \
                np.sum(solar_pot_hourly[extreme_solar_start_day*24:(extreme_solar_start_day+5)*24]):
            extreme_solar_start_day = day
    return extreme_solar_start_day

def find_avg_solar(args):
    # find the average solar potnetial
    T = args.num_hours
    solar_pot_hourly   = np.array(pd.read_excel(os.path.join(args.data_dir, 'solar_pot.xlsx'),
                                                index_col=None))[0:T,0]
    solar_pot_hourly_daily = solar_pot_hourly.reshape(int(T/24), 24)
    avg_solar_po_day = np.average(solar_pot_hourly_daily, axis=0)
    avg_solar_po = np.tile(avg_solar_po_day, args.water_account_days)
    return avg_solar_po


def read_tx_distance(args):
    tx_matrix_dist_m = pd.read_csv(os.path.join(args.data_dir, 'tx_matrix_dist_m.csv'), header=0, index_col=0)
    return tx_matrix_dist_m


def get_tx_tuples(args):
    cap_ann = annualization_rate(args.i_rate, args.annualize_years_trans)
    tx_matrix_dist_m = pd.read_csv(os.path.join(args.data_dir, 'tx_matrix_dist_m.csv'),header=0, index_col=0)
    tx_tuple_list = []
    # tuple list in the order: (pt1, pt2), distance, cost kw, loss
    for i in range(len(tx_matrix_dist_m)):
        for j in range(len(tx_matrix_dist_m.columns)):
            if tx_matrix_dist_m.iloc[i, j] > 0:
                tx_tuple_list.append(((i + 1, j + 1),
                                      tx_matrix_dist_m.iloc[i, j],
                                      args.num_year * cap_ann * args.trans_cost_kw_m *
                                      tx_matrix_dist_m.iloc[i, j],
                                      tx_matrix_dist_m.iloc[i, j] * float(args.trans_loss)))
    return tx_tuple_list


def get_raw_columns():
    # Define columns for raw results export
    cap_columns = ['solar_regional', 'diesel_regional', 'battery_regional',
                   'solar_util_regional', 'diesel_util_regional', 'battery_discharge_regional', 'diesel_regional_ext']
    system_ts_columns = ['system_solar_util','system_diesel_util',
                         'system_battery_level','system_battery_charge','system_battery_discharge',
                         'flexible_demand']

    return cap_columns, system_ts_columns


def results_retrieval(args, m, m_ext):
    T = args.num_hours
    # Retrieve necessary model parameters
    cap_columns, system_ts_columns = get_raw_columns()
    tx_tuple_list = get_tx_tuples(args)

    # be careful this is single region, the code will has different range with the previous code
    cap_results = np.zeros((args.num_regions, len(cap_columns)))
    for i in range(args.num_regions):
        cap_results[i,0] = m.getVarByName('solar_cap_region_{}'.format(i + 1)).X
        cap_results[i,1] = m.getVarByName('diesel_cap_region_{}'.format(i + 1)).X
        cap_results[i,2] = m.getVarByName('batt_energy_cap_region_{}'.format(i + 1)).X
        cap_results[i,6] = m_ext.getVarByName('diesel_cap_region_{}'.format(i + 1)).X

    timeseries_results = np.zeros((len(system_ts_columns), T, args.num_regions+1))
    for i in range(args.num_regions):
        for j in range(T):
            timeseries_results[0, j, i] = m.getVarByName('solar_util_region_{}[{}]'.format(i + 1, j)).X
            timeseries_results[1, j, i] = m.getVarByName('diesel_gen_region_{}[{}]'.format(i + 1, j)).X
            timeseries_results[2, j, i] = m.getVarByName('batt_level_region_{}[{}]'.format(i + 1, j)).X
            timeseries_results[3, j, i] = m.getVarByName('batt_charge_region_{}[{}]'.format(i + 1, j)).X
            timeseries_results[4, j, i] = m.getVarByName('batt_discharge_region_{}[{}]'.format(i + 1, j)).X
            timeseries_results[5, j, i] = m.getVarByName('irrigation_load_region_{}[{}]'.format(i + 1, j)).X

        cap_results[i, 3] = np.average(timeseries_results[0, :, i])
        cap_results[i, 4] = np.average(timeseries_results[1, :, i])
        cap_results[i, 5] = np.average(timeseries_results[4, :, i])

    results_ts = np.zeros((T, len(system_ts_columns)))

    # Time series results
    results_ts[:, 0] = np.sum(timeseries_results[0, :, 0:args.num_regions], axis = 1)
    results_ts[:, 1] = np.sum(timeseries_results[1, :, 0:args.num_regions], axis = 1)
    results_ts[:, 2] = np.sum(timeseries_results[2, :, 0:args.num_regions], axis = 1)
    results_ts[:, 3] = np.sum(timeseries_results[3, :, 0:args.num_regions], axis = 1)
    results_ts[:, 4] = np.sum(timeseries_results[4, :, 0:args.num_regions], axis = 1)
    results_ts[:, 5] = np.sum(timeseries_results[5, :, 0:args.num_regions], axis = 1)

    # Transmission result matrix - set as zero for this study
    tx_cap_results_list = np.zeros(len(tx_tuple_list))
    tx_cap_results_matrix = np.zeros((len(tx_tuple_list), len(tx_tuple_list)))

    return cap_results, results_ts, tx_cap_results_list, tx_cap_results_matrix



def get_processed_columns():
    # Define columns for processed results export
    columns = ['Solar [kW]', 'Diesel [kW]', 'Battery Energy [kWh]', 'New Trans. [kW]', 'New Trans. [kW-km]',
               'Peak Demand [kW]', 'Avg. total Demand [kW]', 'Avg. total Gen. [kW]',
               'Avg. Solar Gen. Potential [kW]', 'Avg. Solar Gen. [kW]',
               'Solar Cost [%]', 'Diesel Cost [%]', 'Battery Cost [%]', 'Trans. Cost [%]',
               'Total LCOE [$/kWh]', 'Total LCOE - Demand [$/kWh]', 'Ext. Diesel [kW]']
    return columns



def full_results_processing(args, cap_results, results_ts, tx_cap_results_list, tx_cap_results_matrix):

    # Retrieve necessary model parameters
    export_columns = get_processed_columns()
    T = args.num_hours
    tx_tuple_list = get_tx_tuples(args)
    tx_matrix_dist_m = pd.read_csv(os.path.join(args.data_dir, 'tx_matrix_dist_m.csv'), header=0, index_col=0)

    # annualization rates
    cap_solar   = args.num_year * annualization_rate(args.i_rate, args.annualize_years_solar)
    cap_battery = args.num_year * annualization_rate(args.i_rate, args.annualize_years_storage)
    cap_diesel  = args.num_year * annualization_rate(args.i_rate, args.annualize_years_diesel)
    cap_trans   = args.num_year * annualization_rate(args.i_rate, args.annualize_years_trans)

    # transmission cost based on the input transmission lines
    trans_cost = args.trans_line_m * cap_trans * args.trans_cost_kw_m
    # Potential generation time-series for curtailment calcs
    fix_load_hourly_kw, solar_pot_hourly, rain_rate_daily_mm_m2 = load_timeseries(args)
    # read irrigation area
    irrigation_total_area = np.sum(read_irrigation_area(args) * args.irrgation_area_ratio)

    # Calculate demand, generation, solar uncurtailed/actual CF
    avg_fix_load         = np.mean(fix_load_hourly_kw[0:T], axis=0) * args.fixed_load_rate * irrigation_total_area / 10000 / 100
    avg_total_demand     = avg_fix_load + np.sum(results_ts[:,5]) / T
    avg_solar_gen        = np.sum(results_ts[:, 0])/T
    avg_diesel_gen       = np.sum(results_ts[:, 1])/T
    avg_total_gen        = avg_solar_gen + avg_diesel_gen
    solar_uncurtailed_cf = np.mean(solar_pot_hourly[0:T], axis = 0)
    solar_actual_cf      = avg_solar_gen / np.sum(cap_results[:,0])

    # total capital cost and operation cost
    solar_unit_price_interpld = interp1d(args.solar_pw_cap_kw, args.solar_pw_cost_kw)
    solar_cost_node = np.zeros(args.num_regions)
    for i in range(args.num_regions):
        solar_cost_node[i] = solar_unit_price_interpld(cap_results[i, 0]) * cap_solar
    total_solar_cost = np.sum(solar_cost_node)
    total_diesel_cost  = np.sum(cap_results[:,1]) * cap_diesel  * float(args.diesel_cost_kw) * args.reserve_req
    total_battery_cost = np.sum(cap_results[:,2]) * cap_battery * float(args.battery_cost_kwh)
    total_diesel_fuel_cost = avg_diesel_gen * T * args.diesel_cost_liter * args.liter_per_kwh / args.diesel_eff
    total_new_tx_cost  = np.sum(np.sum(trans_cost))

    for i in range(len(tx_tuple_list)):
        total_new_tx_cost = total_new_tx_cost + tx_cap_results_list[i] * tx_tuple_list[i][2]

    total_cost = total_solar_cost + total_battery_cost + total_diesel_cost + total_new_tx_cost + total_diesel_fuel_cost

    # Create arrays to store energy output & costs
    data_for_export = np.zeros((1,len(export_columns)))

    ## Populate data_for_export
    data_for_export[0, 0] = np.sum(cap_results[:,0]) # Solar [kW]
    data_for_export[0, 1] = np.sum(cap_results[:,1]) # Diesel [kW]
    data_for_export[0, 2] = np.sum(cap_results[:,2]) # Battery Energy [kWh]
    data_for_export[0, 3] = np.sum(tx_cap_results_list)   # New Trans. [kW]
    data_for_export[0, 4] = 0 # np.multiply(tx_cap_results_matrix, tx_matrix_dist_m)  # New Trans. [kW-km]

    data_for_export[0, 5] = 0                      # Peak load [kW] (not done yet)
    data_for_export[0, 6] = avg_total_demand       # average load
    data_for_export[0, 7] = avg_total_gen          # Average generation
    data_for_export[0, 8] = solar_uncurtailed_cf   # Average solar potential generation
    data_for_export[0, 9] = solar_actual_cf        # Actual solar CF

    data_for_export[0, 10] = total_solar_cost / total_cost * 100
    data_for_export[0, 11] = (total_diesel_cost + total_diesel_fuel_cost) / total_cost * 100
    data_for_export[0, 12] = total_battery_cost / total_cost * 100
    data_for_export[0, 13] = total_new_tx_cost / total_cost * 100
    data_for_export[0, 14] = total_cost / (avg_total_gen * T)
    data_for_export[0, 15] = total_cost / (avg_total_demand * T)
    data_for_export[0, 16] = np.sum(cap_results[:,6])  # the diesel capacity from extreme model

    results_df = pd.DataFrame(data_for_export, columns=export_columns)

    return results_df