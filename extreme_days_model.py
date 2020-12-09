import numpy as np
from gurobipy import *
from utils import annualization_rate, load_timeseries, read_irrigation_area, read_tx_distance
import pandas as pd

def create_model(args):
    m = Model("capacity_optimization_model")
    T = args.num_hours
    trange = range(T)

    fix_load_hourly_kw, solar_pot_hourly, rain_rate_daily_mm_m2 = load_timeseries(args)

    # Annualize capacity costs for model
    annualization_solar   = annualization_rate(args.i_rate, args.annualize_years_solar)
    annualization_storage = annualization_rate(args.i_rate, args.annualize_years_storage)
    annualization_diesel  = annualization_rate(args.i_rate, args.annualize_years_diesel)
    # only solar will use piecewise capital cost
    solar_cap_cost = [args.num_year * annualization_solar * float(args.solar_pw_cost_kw[i])
                      for i in range(len(args.solar_pw_cost_kw))]
    battery_cost_kwh  = args.num_year * annualization_storage * float(args.battery_cost_kwh)
    diesel_cost_kw    = args.num_year * annualization_diesel  * float(args.diesel_cost_kw) * args.reserve_req

    # Regional area read m2
    irrigation_area = read_irrigation_area(args) * args.irrgation_area_ratio

    # set up regional model
    for i in range(args.num_regions):

        # read the fix load in each region, scaled by the region area
        fix_demand = fix_load_hourly_kw * args.fixed_load_rate * irrigation_area[i] / 10000 / 100

        # Initialize capacity variables
        solar_cap = m.addVar(name='solar_cap_region_{}'.format(i + 1))
        m.setPWLObj(solar_cap, args.solar_pw_cap_kw, solar_cap_cost)
        diesel_cap      = m.addVar(obj=diesel_cost_kw, name='diesel_cap_region_{}'.format(i + 1))
        battery_cap_kwh = m.addVar(obj=battery_cost_kwh, name = 'batt_energy_cap_region_{}'.format(i + 1))

        # Initialize time-series variables
        irrigation_load              = m.addVars(trange, obj=0.001, name = 'irrigation_load_region_{}'.format(i + 1))
        irrigation_binary            = m.addVars(trange, vtype=GRB.BINARY, name = "irrigation_binary_region_{}".format(i+1))
        irrigation_continuous_binary = m.addVars(trange, vtype=GRB.BINARY, name = "irrigation_continuous_binary_region_{}".format(i+1))
        solar_util      = m.addVars(trange, name = 'solar_util_region_{}'.format(i + 1))
        batt_charge     = m.addVars(trange, obj = args.nominal_charge_discharge_cost_kwh,
                                    name= 'batt_charge_region_{}'.format(i + 1))
        batt_discharge  = m.addVars(trange, obj = args.nominal_charge_discharge_cost_kwh,
                                    name= 'batt_discharge_region_{}'.format(i + 1))
        batt_level      = m.addVars(trange, name='batt_level_region_{}'.format(i + 1))
        diesel_gen      = m.addVars(trange, obj=(args.diesel_cost_liter * args.liter_per_kwh / args.diesel_eff),
                                    name="diesel_gen_region_{}".format(i + 1))
        m.update()


        # Add time-series Constraints
        for j in trange:

            # solar and diesel generation constraint
            m.addConstr(diesel_gen[j] <= diesel_cap)
            m.addConstr(solar_util[j] <= solar_cap * solar_pot_hourly[j])

            # Energy Balance
            m.addConstr(solar_util[j] + diesel_gen[j] - batt_charge[j] + batt_discharge[j] ==
                        fix_demand[j] + irrigation_load[j])

            # Battery operation constraints
            m.addConstr(batt_charge[j] - battery_cap_kwh * args.battery_p2e_ratio_range <= 0)
            m.addConstr(batt_discharge[j] - battery_cap_kwh * args.battery_p2e_ratio_range <= 0)
            m.addConstr(batt_level[j] - battery_cap_kwh <= 0)

            ## Battery control
            # initial and final SoC == 100%
            if j == 0:
                m.addConstr(batt_discharge[j] / args.battery_eff - args.battery_eff * batt_charge[j] ==
                            battery_cap_kwh - batt_level[j])
            else:
                m.addConstr(batt_discharge[j] / args.battery_eff - args.battery_eff * batt_charge[j] ==
                            batt_level[j - 1] - batt_level[j])
            if j == (args.num_hours - 1):
                m.addConstr(batt_level[j] == battery_cap_kwh)

            # Irrigation load control
            # lowest power: 1kW; must >= 2 hours continuous operation pattern
            m.addConstr(irrigation_load[j] >= args.irrigation_minimum_power * irrigation_binary[j])
            m.addConstr(irrigation_load[j] <= args.irrigation_maximum_power * irrigation_binary[j])
            if j > 0:
                m.addConstr(irrigation_continuous_binary[j-1] + irrigation_continuous_binary[j] <= irrigation_binary[j])
                m.addConstr(irrigation_continuous_binary[j] >= irrigation_binary[j] - irrigation_binary[j-1])

        m.update()


        # Irrigation + Rain Rate Constraints
        water_kg_in_period = irrigation_area[i] * args.water_demand_kg_m2_day * args.water_account_days
        for d in list(range(args.first_season_start, args.first_season_end - args.water_account_days + 2)) + \
                 list(range(args.second_season_start, args.second_season_end - args.water_account_days + 2)):
            irrigation_kg_in_period = quicksum(irrigation_load[k]/args.irrigation_kwh_p_kg
                                               for k in range(d * 24, (d + args.water_account_days) * 24))
            rain_kg_in_period = sum(rain_rate_daily_mm_m2[k] * irrigation_area[i]
                                    for k in range(d, d + args.water_account_days))

            m.addConstr(irrigation_kg_in_period + rain_kg_in_period >= water_kg_in_period)

        m.update()

    return m
