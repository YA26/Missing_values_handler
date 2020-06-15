# -*- coding: utf-8 -*-
"""
Created on Mon Nov  4 18:46:50 2019

@author: Yann Avok
"""
from sklearn.ensemble import RandomForestClassifier
from missing_data_handler import MissingDataHandler
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


data = read_csv(join("data","Loan_Approval.csv"), sep=",", index_col=False)
#Setting the ensemble model parameters: it could be a random forest regressor or classifier
missing_data_handler.set_ensemble_model_parameters(n_estimators=40, additional_estimators=20)

#Launching training and getting our new dataset
new_data = missing_data_handler.train(data=data, 
                                      base_estimator=RandomForestClassifier,
                                      target_variable_name="Loan_Status",  
                                      n_iterations_for_convergence=5,
                                      path_to_save_dataset=join("data", "Loan_approval_no_nan.csv"),
                                      forbidden_variables_list=["Credit_History"])


"""
############################################
########## DATA RETRIEVAL ##################
############################################
"""
features_type_prediction            = missing_data_handler.get_features_type_predictions()
target_variable_type_prediction     = missing_data_handler.get_target_variable_type_prediction()
encoded_features                    = missing_data_handler.get_encoded_features()
#The target variable won't be encoded if it is numerical or if the user requires it by putting its name in 'forbidden_variables_list' 
encoded_target_variable             = missing_data_handler.get_target_variable_encoded()
final_proximity_matrix              = missing_data_handler.get_proximity_matrix()
final_distance_matrix               = missing_data_handler.get_distance_matrix()
weighted_averages                   = missing_data_handler.get_all_weighted_averages()
converged_values                    = missing_data_handler.get_converged_values()

