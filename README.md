# Regional_irrigation_energy_model Overview

This is an electricity capacity planning model designed for studying the regional irrigation load. With the solar potential, fixed load (residential demand), rain rate time series, and the grid connection input, the least cost objective model could come out with the combination of solar, diesel, battery generation, and some relative results to show the energy system. The model will be solved by gurobi and coded in python. Expanding the model with more flexibility will be done in the near future!

Currently, the default setting for 5-day, exclude grid optimization, no rain rate scenario, specific for the irrigation area map in pic 1.

<a href="url"><img src="https://github.com/YUEZIWU/Regional_irrigation_energy_model/blob/master/IMG/irrigation%20area.png" align="center" width="480" ></a>

**Pic 1. The irrigation zones locations and connections**
(From models: [irrigation_detection model](https://github.com/tconlon/irrigation_detection), [dl_irrigation_prediction](https://github.com/tconlon/dl_irrigation_prediction), [two_level_grid_network_planner](https://github.com/nsutezo/two_level_grid_network_planner))

## The model includes:

1. main.py: Used to run the model, with gurobi setting and the results output files. 

2. model.py: The gurobi MILP model building, where all objective functions, constraints are located.

3. utils.py: Functions used in the model, and the model output extraction.

4. params.yaml: The parameters for the model.
