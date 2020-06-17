# Handling missing values with a random forest automatically
### For supervised learning

Random forest's definition of proximity is a solution that can be used to replace missing values in a dataset.

If you want to know more about how that implementation was done, you can read this article: https://medium.com/analytics-vidhya/replacing-missing-values-in-a-dataset-by-building-a-random-forest-with-python-d82d4ff24223


## Do you want to give it a try?

- You can get the library with ```pip install MissingValuesHandler```

- Import a dataset

- Choose what type of random forest you want to apply(regressor or classifier)

- Set up the parameters of the random forest. The main difference resides in the criterion: it is **gini** or **entropy** for a random forest classifier and **mse** (mean square error) for a regressor.

- Set up essential parameters like the **number of iterations**, **the additional trees**, **the base estimator**…

- The method **train()** possesses three important arguments among others:
     - **forbidden_variables_list:** variables that don't require encoding will be put in that list
     - **ordinal_variables_list:** suited for ordinal categorical variables encoding
     - **n_iterations_for_convergence:** checks after n rounds if the predicted values converged. 4 or 5 rounds are usually enough

## Coding example:
#DecisionTreeClassifier
```python
from MissingValuesHandler.missing_data_handler import MissingDataHandler
from sklearn.ensemble import RandomForestClassifier
from os.path import join
from pandas import read_csv

"""
############################################
############# MAIN OBJECT ##################
############################################
"""
missing_data_handler = MissingDataHandler()


"""
############################################
############### RUN TIME ###################
############################################
"""
data = read_csv(join("data","test_dataset.csv"), sep=",", index_col=False)
#Setting the ensemble model parameters: it could be a random forest regressor or classifier
missing_data_handler.set_ensemble_model_parameters(n_estimators=30, additional_estimators=5)

#Launching training and getting our new dataset
new_data = missing_data_handler.train(data=data, 
                                      base_estimator=RandomForestClassifier,
                                      target_variable_name="Status",  
                                      n_iterations_for_convergence=4,
                                      path_to_save_dataset=join("data", "test_dataset_no_nan.csv"),
                                      forbidden_variables_list=[])


"""
############################################
########## DATA RETRIEVAL ##################
############################################
"""
features_type_prediction            = missing_data_handler.get_features_type_predictions()
target_variable_type_prediction     = missing_data_handler.get_target_variable_type_prediction()
encoded_features                    = missing_data_handler.get_encoded_features()
"""
The target variable won't be encoded if it is numerical or if the user requires it(by putting the variable name in forbidden_variables_list') 
"""
encoded_target_variable             = missing_data_handler.get_target_variable_encoded()
final_proximity_matrix              = missing_data_handler.get_proximity_matrix()
final_distance_matrix               = missing_data_handler.get_distance_matrix()
weighted_averages                   = missing_data_handler.get_all_weighted_averages()
converged_values                    = missing_data_handler.get_converged_values()
diverged_values                     = missing_data_handler.get_diverged_values()
```

#DecisionTreeRegressor
```python
from MissingValuesHandler.missing_data_handler import MissingDataHandler
from sklearn.ensemble import RandomForestRegressor
from os.path import join
from pandas import read_csv



"""
############################################
############# MAIN OBJECT ##################
############################################
"""
missing_data_handler = MissingDataHandler()


"""
############################################
############### RUN TIME ###################
############################################
"""
data = read_csv(join("data","Advertising.csv"), sep=",", index_col=False)
#Setting the ensemble model parameters: it could be a random forest regressor or classifier
missing_data_handler.set_ensemble_model_parameters(n_estimators=100, additional_estimators=5,  criterion='mse')

#Launching training and getting our new dataset
new_data = missing_data_handler.train(data=data, 
                                      base_estimator=RandomForestRegressor,
                                      target_variable_name="sales",  
                                      n_iterations_for_convergence=4,
                                      path_to_save_dataset=join("data", "Advertising_no_nan.csv"),
                                      forbidden_variables_list=[])


"""
############################################
########## DATA RETRIEVAL ##################
############################################
"""
features_type_prediction            = missing_data_handler.get_features_type_predictions()
target_variable_type_prediction     = missing_data_handler.get_target_variable_type_prediction()
encoded_features                    = missing_data_handler.get_encoded_features()
"""
The target variable won't be encoded if it is numerical or if the user requires it(by putting the variable name in forbidden_variables_list') 
"""
encoded_target_variable             = missing_data_handler.get_target_variable_encoded()
final_proximity_matrix              = missing_data_handler.get_proximity_matrix()
final_distance_matrix               = missing_data_handler.get_distance_matrix()
weighted_averages                   = missing_data_handler.get_all_weighted_averages()
converged_values                    = missing_data_handler.get_converged_values()
diverged_values                     = missing_data_handler.get_diverged_values()
```
