# Regional_irrigation_energy_model Overview

This is an electricity capacity planning model designed for studying the regional irrigation load. With the solar potential, fixed load (eg. residential demand), rain rate time series, and the grid connection input, the least cost objective model could come out with the combination of solar, diesel, battery generation, and some relative results to show the energy system. 

The model solve the problem in two levels. The extreme days model (Mixed integer linear programming model), is solving the solar, battery, diesel during the no rain period (5 days). Because the model is building with interger variables (e.g. pump operating status, solar piecewise cost assumption), the purpose is solving the integer programming with limited computing resources. And then with the output, the model would go to the annual model. The model is defaulted as 5-day, exclude grid optimization, anual average solar potential, specific for the irrigation area map in pic 1. 

2nd, the annual model(linear programming), with the solar and battery capacities from the 1-stage, the model solved the annual energy profile. The model is using the annual variance solar energy, real rain rate data, and assumed two irrigation seasons in a year.

<a href="url"><img src="https://github.com/YUEZIWU/Regional_irrigation_energy_model/blob/master/IMG/irrigation%20area.png" align="center" width="480" ></a>

**Pic 1. The irrigation zones locations and connections**
(From models: [irrigation_detection model](https://github.com/tconlon/irrigation_detection), [dl_irrigation_prediction](https://github.com/tconlon/dl_irrigation_prediction), [two_level_grid_network_planner](https://github.com/nsutezo/two_level_grid_network_planner))

The two-level model should be proved to be robust. 

It's worth to be noted that the grid and transmission lines are not optimized in the model and the assumptions setting is quite specific for the scenario in the model. Should be careful to change the grid and transmission part. So maybe later, more flexible and more clear instructed model would come online.

The model will be solved by gurobi and coded in python. 


## The model includes:

1. main.py: Used to run the model, with gurobi setting and the results output files. 

2. extreme_days_model.py: short-term solar & battery capacities determined in this model

3. annual_mode.py: with the solar and battery capacities output from extreme_days_model, annual model solved energy profile in annual scale 

4. utils.py: functions used in the model, and the model output extraction

5. params.yaml: the parameters for the model

6. Data: solar potential & fixed load data should be in hourly resolution; rain rate time series should be in daily resolution
