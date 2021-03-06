import numpy as np
from extreme_days_model import create_extreme_day_model
from annual_model import create_annual_model
from utils import *
import datetime

if __name__ == '__main__':
    running_start_time = datetime.datetime.now()

    #########################################################################
    ### --------------------------- Model Run --------------------------- ###
    #########################################################################

    args    = get_args()

    # the extreme weather days model creation and solving
    m_ext = create_extreme_day_model(args)
    # Set model solver parameters
    m_ext.setParam("FeasibilityTol", args.feasibility_tol)
    m_ext.setParam("Method",         args.solver_method)
    # Solve the model
    m_ext.optimize()

    # the annual model creation and solving
    m_an = create_annual_model(args, m_ext)
    m_an.setParam("FeasibilityTol", args.feasibility_tol)
    m_an.setParam("Method",         args.solver_method)
    m_an.optimize()


    ##########################################################################
    ### ------------------------- Results Output ------------------------- ###
    ##########################################################################

    results    = []
    results_ts = []

    test_name = args.case_no + str(args.num_regions) + '_irrigation_zones_' + str(args.fixed_load_rate) + '_i_area_' + \
                str(args.nodes_area) + '_line_' + str(args.trans_line_m)
    cap_columns, system_ts_columns = get_raw_columns()

    # Process the model solution
    tx_tuple_list = get_tx_tuples(args)
    cap_results, results_ts, tx_cap_results_list, tx_cap_results_matrix = results_retrieval(args, m_an, m_ext)

    ## Save results: capacity, time series, transmission matrix
    df_cap_results_raw = pd.DataFrame(np.array(cap_results), columns = cap_columns)
    df_cap_results_raw.to_excel(os.path.join(args.results_dir, 'raw_results_export_' + test_name + '.xlsx'))

    df_results_ts = pd.DataFrame(np.array(results_ts), columns = system_ts_columns)
    df_results_ts.to_csv(os.path.join(args.results_dir, 'ts_results_export_' + test_name + '.csv'))

    tx_cap_results_matrix = pd.DataFrame(np.array(tx_cap_results_matrix))
    tx_cap_results_matrix.to_csv(os.path.join(args.results_dir, 'transmission_capacity_' + test_name + '.csv'))

    df_results_processed = full_results_processing(args, cap_results, results_ts,
                                                   tx_cap_results_list, tx_cap_results_matrix)
    df_results_processed.to_excel(os.path.join(args.results_dir, 'processed_results_export_' + test_name + '.xlsx'))


    running_end_time = datetime.datetime.now()
    print(running_end_time - running_start_time)