# Automatic RandomForestImputer: Handling missing values with a random forest automatically
## For supervised and semi-supervised learning

This library uses a random forest(regressor or classifier) to replace missing values in a dataset. It tackles:
- Samples having missing values in one or more features
- Samples having a missing target value and missing values in one or more features: both of them will be predicted and replaced.

    
## Dependencies
- Python(version>=3.6)
- Numpy
- Pandas
- Matplolib
- Sklearn
- Tensorflow (version>=2.2.0)
- DataTypeIdentifier

## Instructions

- You can get the library with **```pip install MissingValuesHandler```**

- Import a dataset

- The type of **Random Forest is automatically handled**: if the target variable is numerical, a **RandomForestRegressor** is selected and if it is categorical, the algorithm will choose a **RandomForestClassifier**.

- Class instantiation: **training_resilience** is a parameter that lets the algorithm know how many times it must keep striving for convergence when there are still some values that didn't converge 

- The class possesses three important arguments among others:
     - **forbidden_variables_list:** variables that don't require encoding will be put in that list
     - **ordinal_variables_list:** suited for ordinal categorical variables encoding
     - **n_iterations_for_convergence:** checks after n rounds if the predicted values converged. 4 or 5 rounds are usually enough
     
- Set up the parameters of the random forest except for the **criterion** since it is also taken care of by the software: it is **gini** or **entropy** for a random forest classifier and **mse** (mean squared error) for a regressor. Set up essential parameters like the **number of iterations**, **the additional trees**, **the base estimator**…

- The method **train()** contains two important arguments among others:
    - **sample_size [0;1[**: allows to draw a ***representative sample*** from the data(can be used when the dataset is too big). **0 for no sampling**
    - **n_quantiles**: allows to draw a representative sample from the data when the target variable is numerical(default value at 0 if the variable is categorical)

## Coding example:
```python
from MissingValuesHandler.missing_data_handler import RandomForestImputer
from os.path import join
from pandas import read_csv
"""
############################################
############# IMPORT DATA  #################
############################################
"""
data = read_csv(join("data","Loan_approval.csv"), sep=",", index_col=False)

"""
############################################
############### RUN TIME ###################
############################################
"""
#Main object
random_forest_imputer = RandomForestImputer(data=data,
                                            target_variable_name="Status",
                                            training_resilience=3, 
                                            n_iterations_for_convergence=5,
                                            forbidden_features_list=["Credit_History"],
                                            ordinal_features_list=[])

#Setting the ensemble model parameters: it could be a random forest regressor or classifier
random_forest_imputer.set_ensemble_model_parameters(n_estimators=40, additional_estimators=10)

#Launching training and getting our new dataset
new_data = random_forest_imputer.train(sample_size=0.3, 
                                       path_to_save_dataset=join("data", "Loan_approval_no_nan.csv"))
"""
############################################
########## DATA RETRIEVAL ##################
############################################
"""
sample_used                         = random_forest_imputer.get_sample()
features_type_prediction            = random_forest_imputer.get_features_type_predictions()
target_variable_type_prediction     = random_forest_imputer.get_target_variable_type_prediction()
encoded_features                    = random_forest_imputer.get_encoded_features()
encoded_target_variable             = random_forest_imputer.get_target_variable_encoded()
final_proximity_matrix              = random_forest_imputer.get_proximity_matrix()
final_distance_matrix               = random_forest_imputer.get_distance_matrix()
weighted_averages                   = random_forest_imputer.get_nan_features_predictions(option="all")
convergent_values                   = random_forest_imputer.get_nan_features_predictions(option="conv")
divergent_values                    = random_forest_imputer.get_nan_features_predictions(option="div")
ensemble_model_parameters           = random_forest_imputer.get_ensemble_model_parameters()
all_target_value_predictions        = random_forest_imputer.get_nan_target_values_predictions(option="all")
target_value_predictions            = random_forest_imputer.get_nan_target_values_predictions(option="one")


"""
############################################
######## WEIGHTED AVERAGES PLOT ############
############################################
"""
random_forest_imputer.create_weighted_averages_plots(directory_path="graphs", both_graphs=1)

"""
############################################
######## TARGET VALUE(S) PLOT ##############
############################################
"""
random_forest_imputer.create_target_pred_plot(directory_path="graphs")

"""
############################################
##########      MDS PLOT    ################
############################################
"""
mds_coordinates = random_forest_imputer.get_mds_coordinates(n_dimensions=3, distance_matrix=final_distance_matrix)
random_forest_imputer.show_mds_plot(mds_coordinates, plot_type="3d")

```

## 3d Multidimensional Scaling(MDS):
We can use the **distance matrix** to plot the samples and observe how they are related to one another
![alt_text](img/3d_mds_plot.jpg) 

We can use the **K-means algorithm** to cluster the data and analyze the features of every cluster
![alt_text](img/3d_mds_plot_k_means.jpg)



## References for the supervised algorithm:
- [1]: **Leo Breiman’s website**. Random Forests Leo Breiman and Adele Cutler **stat.berkeley.edu/~breiman/RandomForests/cc_home.htm**
- [2]: **John Starmer’s video** on Youtube Channel StatQuest. **Random Forests Part 2: Missing data and clustering** https://youtu.be/nyxTdL_4Q-Q
