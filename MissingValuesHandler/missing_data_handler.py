# -*- coding: utf-8 -*-
"""
Created on Mon Nov  4 18:46:50 2019

@author: Yann Avok
"""
from MissingValuesHandler.custom_exceptions import VariableNameError, TargetVariableNameError, NoMissingValuesError
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from MissingValuesHandler.data_type_identifier import DataTypeIdentifier
from sklearn.preprocessing import LabelEncoder
from collections import defaultdict, deque, Counter
from colorama import Back, Style
from copy import copy
import matplotlib.pyplot as plt 
import pandas as pd
import numpy as np
import os


class MissingDataHandler(object):
    '''
    This class uses a random forest to replace missing values in a dataset for samples that have a target value. It doesn't tackle missing values in a new sample.
    The main idea is to use the random forest's definition of proximity to find the values that are best fit to replace the missing ones.
    
    We have the following parts: 

    1- We get the dataset, separates the features and the target variable and predict their types:
        - private method: __check_variables_name_validity
        - private method: __separate_features_and_target_variable
        - private method: __predict_feature_type
        - private method: __predict_target_variable_type
        
    2- We retrieve the missing values coordinates(row and column) and fill in the nan cells with initial values:
        - private method: __retrieve_nan_coordinates
        - private method: __make_initial_guesses
        
    3- We encode the features and the target variables if they need to be encoded:
        - private method: __encode_features(As of yet, decision trees in Scikit-Learn don't handle categorical variables. So encoding is necessary)
        - private method: __encode_target_variable
    
    4- We build our model, fit it and evaluate it (we keep the model having the best out of bag score). We then use it to build the proximity matrix:
        - private method: __build_ensemble_model
        - private method: __fit_and_evaluate_ensemble_model
        - public method : build_proximity_matrices
    
    5- We use the proximity matrix to compute weighted averages for all missing values(both in categorical and numerical variables):
        - private method: __compute_weighted_averages
        - private method:__replace_missing_values_in_encoded_dataframe
        
    6- We check if every value that has been replaced has converged after n iterations. If that's not the case, we go back to step 4 and go for another round of n iterations:
        - private method: __compute_standard_deviations
        - private method: __check_for_convergence
        - private method: __replace_missing_values_in_original_dataframe
        
    7- If all values have converged, we stop everything and save the dataset if a path has been given. 'train' is the main function:
         - private method: __save_new_dataset
         - public  method: train
    '''
    
    def __init__(self, training_resilience=2):  

        assert training_resilience>=2, "'training_resilience' has to be greater or equal to 2" 
        #Data type identifier variables
        self.__data_type_identifier_object      = DataTypeIdentifier()
        
        #Main variables
        self.__original_data                    = None 
        self.__features                         = None
        self.__target_variable                  = None
        self.__target_variable_name             = None
        self.__features_type_predictions        = None
        self.__target_variable_type_prediction  = None
        self.__encoded_features                 = None
        self.__target_variable_encoded          = None
        self.__proximity_matrix                 = []
        self.__distance_matrix                  = []
        self.__forbidden_variables_list         = []
        self.__ordinal_variables_list           = []
        self.__missing_values_coordinates       = []
        self.__number_of_nan_values             = 0
        self.__last_n_iterations                = 0
        self.__label_encoder                    = LabelEncoder()
        self.__standard_deviations              = defaultdict()
        self.__converged_values                 = defaultdict()
        self.__all_weighted_averages            = defaultdict(list)
        self.__all_weighted_averages_copy       = defaultdict(list)
        self.__has_converged                    = False
        self.__training_resilience              = training_resilience
        self.__nan_values_remaining_comparator  = deque(maxlen=training_resilience)
        
        #Random forest variables
        self.__estimator                        = None
        self.__n_estimators                     = None
        self.__additional_estimators            = None
        self.__max_depth                        = None
        self.__min_samples_split                = None 
        self.__min_samples_leaf                 = None
        self.__min_weight_fraction_leaf         = None 
        self.__max_features                     = None
        self.__max_leaf_nodes                   = None
        self.__min_impurity_decrease            = None
        self.__min_impurity_split               = None
        self.__n_jobs                           = None 
        self.__random_state                     = None
        self.__verbose                          = None
        self.__bootstrap                        = True
        self.__oob_score                        = True
        self.__warm_start                       = True
        
             
    def set_ensemble_model_parameters(self,
                                      additional_estimators=20,
                                      n_estimators=30,
                                      max_depth=None,
                                      min_samples_split=20, 
                                      min_samples_leaf=20,
                                      min_weight_fraction_leaf=0.0, 
                                      max_features='auto',
                                      max_leaf_nodes=None,
                                      min_impurity_decrease=0.0,
                                      min_impurity_split=None,
                                      n_jobs=-1,
                                      random_state=None,
                                      verbose=0):
        '''
        Sets parameters for a random forest regressor or a random forest classifier
        ''' 
        self.__additional_estimators            = additional_estimators
        self.__n_estimators                     = n_estimators
        self.__max_depth                        = max_depth
        self.__min_samples_split                = min_samples_split 
        self.__min_samples_leaf                 = min_samples_leaf
        self.__min_weight_fraction_leaf         = min_weight_fraction_leaf
        self.__max_features                     = max_features
        self.__max_leaf_nodes                   = max_leaf_nodes
        self.__min_impurity_decrease            = min_impurity_decrease
        self.__min_impurity_split               = min_impurity_split
        self.__n_jobs                           = n_jobs 
        self.__random_state                     = random_state
        self.__verbose                          = verbose
         
        
    def get_features_type_predictions(self):
        '''
        Retrieves all features predictions type whether they are numerical or categorical.
        'data_type_identifer_model' and 'data_type_identifier_object' are used to predict each type.
        '''
        return self.__features_type_predictions
     
        
    def get_target_variable_type_prediction(self):
        '''
        Retrieves prediction about the type of the target variable whether it is numerical or categorical.
        'data_type_identifer_model' and 'data_type_identifier_object' are used to predict each type.
        '''
        return self.__target_variable_type_prediction
     
        
    def get_ensemble_model(self):
        '''
        Used to get the random forest model 
        '''
        return self.__estimator
    
    
    def get_encoded_features(self):
        return self.__encoded_features
    
    
    def get_target_variable_encoded(self):
        return self.__target_variable_encoded
      
        
    def get_proximity_matrix(self):
        '''
        Retrieves the last proximity matrix built with the last random forest(the most optimal one)
        '''
        return self.__proximity_matrix
    
    
    def get_distance_matrix(self):
        '''
        Retrieves distance matrix which is equals to 1 - proximity matrix.
        '''
        if not self.__distance_matrix:
            self.__distance_matrix=1-self.__proximity_matrix
        return self.__distance_matrix
     
        
    def get_all_weighted_averages(self):
        '''
        Retrieves all weighted averages that are used to replace nan values whether those come from categorical or numerical variables.
        '''
        return self.__all_weighted_averages_copy
    
    
    def get_convergent_values(self):
        '''
        Retrieves all nan values and their last calculated values.
        '''
        return self.__converged_values
    
    def get_divergent_values(self):
        '''
        Retrieves values that were not able to converge
        '''
        return self.__all_weighted_averages
    

    def __check_variables_name_validity(self):
        '''
        1- Verifies whether variables in 'forbidden_variables_list' or 'ordinal_variables_list' exist in the dataset. 
        2- Verifies whether one variable is not mentioned twice in both lists.
        '''
        columns_names_set       = set(self.__original_data.columns.tolist())
        forbidden_variables_set = set(self.__forbidden_variables_list)
        ordinal_variables_set   = set(self.__ordinal_variables_list)

        #1 
        unknown_forbidden_set = forbidden_variables_set - forbidden_variables_set.intersection(columns_names_set)
        if unknown_forbidden_set:
            raise VariableNameError(f"Variable(s) {unknown_forbidden_set} in forbidden_variables_list not present in the dataset!")
         
        unknown_ordinal_set = ordinal_variables_set - ordinal_variables_set.intersection(columns_names_set)       
        if unknown_ordinal_set:
            raise VariableNameError(f"Variable(s) {unknown_ordinal_set} in ordinal_variables_list not present in the dataset!")
        #2               
        if True in np.in1d(self.__ordinal_variables_list, self.__forbidden_variables_list):
            duplicated_variables_checklist  = np.in1d(self.__ordinal_variables_list, self.__forbidden_variables_list)
            duplicated_variables_names      = np.where(duplicated_variables_checklist==True)[0]
            ordinal_variables_list          = np.array(self.__ordinal_variables_list)
            raise VariableNameError(f"Variable(s) {ordinal_variables_list[duplicated_variables_names]} in ordinal_variables_list can't be duplicated in forbidden_variables_list")
     
                  
    def __separate_features_and_target_variable(self, target_variable_name):
        try:    
            self.__features             = self.__original_data.drop(target_variable_name, axis=1)
            self.__target_variable      = self.__original_data.loc[:, target_variable_name]
            self.__target_variable_name = target_variable_name
        except KeyError:
            #We raise an exception if the name of the target variable given by the user is not found.
            raise TargetVariableNameError(f"Target variable '{target_variable_name}' does not exist!")
     
        
    def __predict_feature_type(self):
        '''
        Predicts if a feature is either categorical or numerical.
        '''
        self.__features_type_predictions = self.__data_type_identifier_object.predict(self.__features, self.__print_verbose)
     
        
    def __predict_target_variable_type(self):
        '''
        Predicts if the target variable is either categorical or numerical.
        '''
        target_variable                        = self.__target_variable.to_frame()
        self.__target_variable_type_prediction = self.__data_type_identifier_object.predict(target_variable, self.__print_verbose) 


    def __retrieve_nan_coordinates(self):
        '''
        Gets the coordinates(row and column) of every empty cell in the features dataset.
        '''
        #We check if there any missing values in the dataset. If that's not the case, an exception is raised.
        if not self.__features.isnull().values.any():
            raise NoMissingValuesError("No missing values were found in the dataset!")

        features_nan_list   = self.__features.columns[self.__features.isnull().any()]
        features_nan        = self.__features[features_nan_list]
           
        for feature_nan in features_nan:  
            #We use the index to get the row coordinate of every empty cell for a given column(feature)  
            empty_cells_checklist   = self.__features[feature_nan].isnull()
            row_coordinates         = self.__features[feature_nan].index[empty_cells_checklist]
            column_coordinate       = feature_nan  
            nan_coordinates         = list(zip(row_coordinates, [column_coordinate]*len(row_coordinates)))
            self.__missing_values_coordinates.extend(nan_coordinates)
                        
        #We don't forget to get the total number of missing values for future purposes.
        self.__number_of_nan_values = len(self.__missing_values_coordinates)
    
                  
    def __make_initial_guesses(self):
        '''
        Replaces empty cells with initial values in the features dataset:
            - mode for categorical variables 
            - median for numerical variables
        '''
        #Getting features that contains null values only  
        null_columns_checklist  = self.__features.isnull().any() 
        null_columns_names      = self.__features.columns[null_columns_checklist]

        #Getting variable type predictions for features containing null values only
        null_features_type_prediction = self.__features_type_predictions.loc[null_columns_names, "Predictions"]

        #Getting numerical and categorical features' names for features containing null values only
        numerical_variables_names       = null_features_type_prediction[null_features_type_prediction=="numerical"].index
        categorical_variables_names     = null_features_type_prediction[null_features_type_prediction=="categorical"].index

        #Calculating medians and modes
        medians         = self.__features[numerical_variables_names].median()
        modes           = self.__features[categorical_variables_names].mode().iloc[0]
        initial_guesses = pd.concat([medians, modes])

        #Replacing initial_guesses in the dataset
        self.__features.fillna(initial_guesses, inplace=True)
    
           
    def __encode_features(self):
        '''
        Encodes every categorical feature the user wants to encode. Any feature mentioned in 'forbidden_variables_list' will not be considered.
        1- No numerical variable will be encoded
        2- All categorical variables will be encoded as dummies by default. If one wants to encode ordinal categorical variable, he can do so by adding it to the ordinal_variables_list.
        '''
        
        #Creating checklists to highlight categorical and numerical variables only.
        #Example: in 'categorical_variables_checklist', we will get 'True' if a given variable happens to be categorical.
        categorical_variables_checklist = list(self.__features_type_predictions["Predictions"]=="categorical")
        numerical_variables_checklist   = list(self.__features_type_predictions["Predictions"]=="numerical")
        
        #With the right checklist we get the name of the variables that are either categorical or numerical. 
        #The idea here is to separate the two different type of variables and to focus on categorical ones only.
        categorical_variables_names     = self.__features_type_predictions["Predictions"].index[categorical_variables_checklist].to_list()
        numerical_variables_names       = self.__features_type_predictions["Predictions"].index[numerical_variables_checklist].to_list()
            
        #Retrieving all numerical and categorical variables
        numerical_variables             = self.__features[numerical_variables_names]   
        categorical_variables           = self.__features[categorical_variables_names]
        
        #Separating nominal and ordinal categorical variables if ordinal_variables_list is not empty
        if self.__ordinal_variables_list:
            nominal_categorical_variables = categorical_variables.drop(self.__ordinal_variables_list, axis=1)
            ordinal_categorical_variables = categorical_variables.loc[:, self.__ordinal_variables_list] 
            
            #Label encoding ordinal categorical variables   
            encoded_ordinal_categorical_variables = ordinal_categorical_variables.apply(self.__label_encoder.fit_transform)
            
            #One-Hot encoding nominal categorical variables if they're not in forbidden_variables_list: We only keep columns that the user want to encode
            # 'a_c' stands for authorized columns
            a_c = [column_name for column_name in nominal_categorical_variables.columns if column_name not in self.__forbidden_variables_list] 
            encoded_nominal_categorical_variables = pd.get_dummies(nominal_categorical_variables, columns=a_c)
            
            #We gather everything: numericals variables and encoded categorical ones(both ordinal and nominal)
            self.__encoded_features = pd.concat((numerical_variables, encoded_ordinal_categorical_variables, encoded_nominal_categorical_variables), axis=1)      
        elif categorical_variables_names:
            a_c = [column_name for column_name in categorical_variables.columns if column_name not in self.__forbidden_variables_list] 
            encoded_categorical_variables = pd.get_dummies(categorical_variables, columns=a_c)
            #We gather everything: this time only the numerical variables and all nominal categorical variables
            self.__encoded_features = pd.concat((numerical_variables, encoded_categorical_variables), axis=1)
        else:
            self.__encoded_features = self.__features
     
        
    def __encode_target_variable(self):
        '''
        Encodes the target variable if it is permitted by the user(i.e if the name of the variable is not in 'forbidden_variables_list').  
        If the target variable is numerical it will not be encoded so there's no need to put it in 'forbidden_variables_list'.
        The target variable will always be label encoded because the trees in the random forest aren't using it for splitting purposes.
        '''
        #We keep the target variable unchanged if the user requires it or if it is numerical
        self.__target_variable_encoded  = self.__target_variable
        #We encode it if the variable is categorical
        if self.__target_variable_name not in self.__forbidden_variables_list and self.__target_variable_type_prediction["Predictions"].any()=="categorical":
            self.__target_variable_encoded  = self.__label_encoder.fit_transform(self.__target_variable)
     
            
    def __build_ensemble_model(self):
            '''Builds an ensemble model: random forest classifier or regressor'''

            EnsembleModel           = {"categorical":RandomForestClassifier, "numerical":RandomForestRegressor}
            target_variable_type    = self.__target_variable_type_prediction["Predictions"].any()
            self.__estimator        = EnsembleModel[target_variable_type](n_estimators=self.__n_estimators,
                                                                            max_depth=self.__max_depth, 
                                                                            min_samples_split=self.__min_samples_split, 
                                                                            min_samples_leaf=self.__min_samples_leaf, 
                                                                            min_weight_fraction_leaf=self.__min_weight_fraction_leaf, 
                                                                            max_features=self.__max_features, 
                                                                            max_leaf_nodes=self.__max_leaf_nodes, 
                                                                            min_impurity_decrease=self.__min_impurity_decrease, 
                                                                            min_impurity_split=self.__min_impurity_split, 
                                                                            bootstrap=self.__bootstrap, 
                                                                            oob_score=self.__oob_score, 
                                                                            n_jobs=self.__n_jobs, 
                                                                            random_state=self.__random_state, 
                                                                            verbose=self.__verbose,
                                                                            warm_start=self.__warm_start)
           


    def __fit_and_evaluate_ensemble_model(self):
            '''
            Fits and evaluates the model. 
            1- We compare the out of bag score at time t-1 with the one at time t.
            2- If the latter is lower than the former or equals to it, we stop fitting the model and we keep the one at t-1.
            3- If it's the other way around, we add more estimators to the total number of estimators we currently have.
            '''  
            precedent_out_of_bag_score  = 0
            current_out_of_bag_score    = 0
            precedent_estimator         = None
            while current_out_of_bag_score > precedent_out_of_bag_score or not current_out_of_bag_score:
                precedent_estimator = copy(self.__estimator)
                self.__estimator.fit(self.__encoded_features, self.__target_variable_encoded) 
                precedent_out_of_bag_score = current_out_of_bag_score
                current_out_of_bag_score = self.__estimator.oob_score_
                self.__estimator.n_estimators += self.__additional_estimators
                self.__print("- Former out of bag score: {0:f}".format(precedent_out_of_bag_score))
                self.__print("- Current out of bag score: {0:f} ".format(current_out_of_bag_score)+" /{0:+f}".format(current_out_of_bag_score-precedent_out_of_bag_score))
            #We subtract the additional_estimators because we want to keep the configuration of the previous model(i.e the optimal one)
            self.__estimator.n_estimators -= self.__additional_estimators
            self.__estimator = precedent_estimator
            self.__print("\nModel with score {0:f} has been kept\n".format(precedent_out_of_bag_score))
   
    
    def __fill_one_modality(self, predicted_modality, prediction_dataframe):
        one_modality_proximity_matrix   = np.zeros((len(self.__encoded_features), len(self.__encoded_features)))
        prediction_checklist            = prediction_dataframe[0]==predicted_modality
        indices_checklist               = prediction_dataframe.index[prediction_checklist].tolist() 
        indices_checklist               = np.array(indices_checklist)
        #Using broadcasting to replace null values by 1
        one_modality_proximity_matrix[indices_checklist[:, None], indices_checklist]=1
        return one_modality_proximity_matrix
        

    def __build_proximity_matrices(self, predictions):
        '''
            Builds proximity matrices.
            1- We run all the data down the first tree and output predictions.
            2- If two samples fall in the same node (same predictions) we count it as 1.
            3- We do the same for every single tree, sum up the proximity matrices and divide the total by the number of estimators.
        ''' 
        possible_predictions = predictions[0].unique()
        if self.__target_variable_type_prediction.values[0,0] == "categorical":
            array_to_int            = np.vectorize(lambda x: np.int(x))
            possible_predictions    = array_to_int(possible_predictions)       
        one_modality_matrix = [self.__fill_one_modality(predicted_modality, predictions) for predicted_modality in possible_predictions]
        proximity_matrix    = sum(one_modality_matrix)
        return proximity_matrix


    def build_proximity_matrix(self, ensemble_estimator, encoded_features):
            '''
            Builds final proximity matrix: sum of all proximity matrices
            '''
            all_estimators_list     = ensemble_estimator.estimators_
            number_of_estimators    = ensemble_estimator.n_estimators  
            predictions             = [pd.DataFrame(estimator.predict(self.__encoded_features)) for estimator in all_estimators_list] 
            proximity_matrices      = list(map(self.__build_proximity_matrices, predictions))
            final_proximity_matrix  = sum(proximity_matrices)/number_of_estimators
            return final_proximity_matrix
     
    
    def __compute_weighted_averages(self, numerical_features_decimals):
        '''
        Computes weights for every single missing value.
        For categorical variables: Weighted average for the sample that has a missing value = (feature's value of every other sample * its proximity value) / all proximities values in the proximity_vector.
        For numerical variables: Weighted average for the sample that has a missing value = (modality proportion * its proximity value) / all proximities values in the proximity_vector.
        '''     
        for missing_sample in self.__missing_values_coordinates:
            #We handle samples that contain missing values one after another. We get the coordinates of the missing sample from the encoded features.
            #'nan sample number' is the row of the sample that has a missing value.
            #'nan feature name' is the name of the feature we are currently working on.
            nan_sample_number   = missing_sample[0]
            nan_feature_name    = missing_sample[1]
            
            if  self.__features_type_predictions.loc[nan_feature_name].any()=="numerical":
                '''
                For every single numerical feature:
                '''
                #For every sample having a missing value, we get all proximities values(with other samples) and put them in the 'proximity_vector'. 
                #We do not forget to strip the proximity value of the sample with itself(because it is always 1). This is the 'prox_values_of_other_samples'
                proximity_vector                = self.__proximity_matrix[nan_sample_number]
                row_to_be_stripped              = nan_sample_number
                prox_values_of_other_samples    = np.delete(proximity_vector, row_to_be_stripped)
                
                #We compute the weight.
                weight_vector = prox_values_of_other_samples / np.sum(prox_values_of_other_samples)
                
                #We get all feature's values for every other sample
                all_other_samples_checklist = self.__features.index != nan_sample_number
                all_other_feature_values    = self.__features.loc[all_other_samples_checklist, nan_feature_name].values
                
                #We compute the dot product between each feature's value and its weight
                weighted_average = np.dot(all_other_feature_values, weight_vector)
                
                #If the values were originally integers, we could keep them that way. Otherwise, we can still choose the number of decimals.
                weighted_average = int(weighted_average) if not numerical_features_decimals else np.around(weighted_average, decimals=numerical_features_decimals)
                
                #We save each weighted average for each missing value
                self.__all_weighted_averages[(nan_sample_number, nan_feature_name)].append(weighted_average)
            else:
                '''
                For every single categorical feature:
                '''
                #For categorical variables, we're going to take into account the frequency of every modality(per feature)
                frequencies_per_modality    = self.__features[nan_feature_name].value_counts()
                proportion_per_modality     = frequencies_per_modality/np.sum(frequencies_per_modality)
                
                #We iterate over the values Ex: 0 and 1 if the categorical variable is binary
                for modality in proportion_per_modality.index.values:
                    #We get all the samples containing the modality.
                    checklist   = self.__features[nan_feature_name]==modality
                    samples     = self.__features[nan_feature_name].index[checklist].values
                    
                    #We don't want to include the sample we want to predict the value for(i.e sample with missing value)
                    if nan_sample_number in samples:
                        samples = np.delete(samples, np.where(samples == nan_sample_number))
                    
                    #For each modality, we compute the weight
                    prox_values_for_a_modality  = self.__proximity_matrix[samples, nan_sample_number]
                    all_prox_values             = self.__proximity_matrix[:, nan_sample_number]
                    weight                      = np.sum(prox_values_for_a_modality)/np.sum(all_prox_values)
                    
                    #Weighted frequency
                    proportion_per_modality[modality] = proportion_per_modality[modality] * weight
                    
                #We get the modality that has the biggest weighted frequency.
                modality_with_max_weight = proportion_per_modality.idxmax()
                                                
                #We put every weighted frequency in the group.
                self.__all_weighted_averages[(nan_sample_number, nan_feature_name)].append(modality_with_max_weight) 

                                
    def __replace_missing_values_in_dataframe(self):
        '''
        Replaces nan with new values in 'self.__encoded_features'
        '''
        for missing_value_coordinates, substitute in self.__all_weighted_averages.items():
            #Getting the coordinates.
            last_substitute = substitute[-1]
            #Replacing values in the features dataframe.
            self.__features.loc[missing_value_coordinates] = last_substitute
 
            
    def __compute_standard_deviations(self, n_iterations_for_convergence):
        '''
        Computes the standard deviation of the last n substitutes
        '''
        for missing_value_coordinates, substitute in self.__all_weighted_averages.items():
            last_n_substitutes = substitute[-n_iterations_for_convergence:]
            try:
                #Standard deviation for last n numerical values for every nan
                self.__standard_deviations[missing_value_coordinates] = np.std(last_n_substitutes)
            except TypeError:
                #Checking whether our last n substitutes are the same (0) or not (1).
                #We can't compute standard deviation for non numerical variables. So this is a good alternative.
                if len(set(last_n_substitutes))==1:
                     self.__standard_deviations[missing_value_coordinates] = 0 
                else:
                    self.__standard_deviations[missing_value_coordinates] = 1
     

    def __fill_with_nan(self):
        '''
        Replaces every value that didn't converge(after multiple tries) with nan
        '''
        for coordinates in self.__all_weighted_averages.keys():
           self.__features.loc[coordinates] = np.nan
 

    def __remove_convergent_values(self):
        '''
        Checks if a given value has converged. If that's the case, the value is removed from the list 'self.__missing_values_coordinates'
        '''
        missing_value_coordinates = list(self.__standard_deviations.keys())         
        for coordinates in missing_value_coordinates:
            nan_feature_name    = coordinates[1]
            standard_deviation  = self.__standard_deviations[coordinates]
            if (self.__features_type_predictions.loc[nan_feature_name].any()=="numerical" and 0<=standard_deviation<1)\
            or (self.__features_type_predictions.loc[nan_feature_name].any()=="categorical" and not standard_deviation):
                #If a numerical or a categorical missing value converges, we keep the last value.
                converged_value                                 = self.__all_weighted_averages[coordinates][-1] 
                self.__converged_values[coordinates]            = converged_value
                #We do not forget to make a copy of the nan coordinates (row, column) and their values over time(for the user).
                self.__all_weighted_averages_copy[coordinates]  = self.__all_weighted_averages[coordinates]
                #Removing nan values that convergedd               
                self.__missing_values_coordinates.remove(coordinates)
                self.__all_weighted_averages.pop(coordinates)
                self.__standard_deviations.pop(coordinates)

               
    def __check_for_convergence(self):
        '''
        - Checks if all values have converged 
        - If it is the case, training stops
        - Otherwise it will continue as long as there are improvements
        - If there are no improvements, the resiliency factor will kick in and try  for n=training_resilience more set  of iterations.
        - If it happens that some values converged, training will continue. Otherwise, it will stop.

        '''
        #Checking the remaing values and those that converged
        total_nan_values        = self.__number_of_nan_values
        nan_values_remaining    = len(self.__missing_values_coordinates)
        nan_values_converged    = total_nan_values - nan_values_remaining
        self.__print(f"{Back.GREEN}- {nan_values_converged} VALUE(S) CONVERGED!\n- {nan_values_remaining} VALUE(S) REMAINING!{Style.RESET_ALL}")
        
        #Checking if there are still values that didn't converge: If that's the case we stop training and replaces them with the median/mode of the distribution they belong to
        self.__nan_values_remaining_comparator.append(nan_values_remaining)
        if len(set(self.__nan_values_remaining_comparator))==1 and len(self.__nan_values_remaining_comparator)==self.__training_resilience:   
            self.__has_converged = True   
            self.__fill_with_nan()
            self.__make_initial_guesses()
            self.__print(f"\n-{nan_values_remaining}/{total_nan_values} VALUES UNABLE TO CONVERGE. THE MEDIAN AND/OR THE MODE HAVE BEEN USED AS A REPLACEMENT.\n")              
        elif not self.__missing_values_coordinates:
            self.__has_converged = True
            self.__print("\nALL VALUES CONVERGED!\n") 
        else:       
            self.__print("\n-NOT EVERY VALUE CONVERGED. ONTO THE NEXT ROUND OF ITERATIONS...\n")

                                                  
    def __save_new_dataset(self, final_dataset, path_to_save_dataset):
        if path_to_save_dataset:
            final_dataset.to_csv(path_or_buf=path_to_save_dataset, index=False)
            self.__print(f"\n- NEW DATASET SAVED in: {path_to_save_dataset}")


    def __print(self, string):
        if self.__print_verbose:
            print(string)
   
    def train(self, 
            data, 
            target_variable_name,
            n_iterations_for_convergence=4,
            numerical_features_decimals=0, 
            path_to_save_dataset=None,
            verbose=1,
            forbidden_variables_list=[],
            ordinal_variables_list=[]):
        '''
        This is the main function. At run time, every other private functions will be executed one after another.
        '''
        #Updating some of the main variables
        self.__ordinal_variables_list   = ordinal_variables_list
        self.__forbidden_variables_list = forbidden_variables_list
        self.__last_n_iterations        = n_iterations_for_convergence
        self.__has_converged            = False
        self.__print_verbose            = verbose
        total_iterations                = 0
        
        #Initializing training
        self.__print("Getting ready...\nMaking initial guesses...\n")
        self.__original_data = data.copy(deep=True)
        self.__check_variables_name_validity()
        self.__separate_features_and_target_variable(target_variable_name)  
        self.__predict_feature_type()
        self.__predict_target_variable_type()
        self.__retrieve_nan_coordinates()
        self.__make_initial_guesses()
        self.__encode_target_variable()
        
        #Every value has to converge. Otherwise we will be here for another round of n iterations.
        while self.__has_converged==False:
            for iteration in range(1, n_iterations_for_convergence + 1):
                total_iterations += 1 
                self.__encode_features()
                self.__print(f"\n##################### ROUND :{iteration} / TOTAL ROUNDS: {total_iterations} #####################\n")
                
                self.__print("\n1- MODEL BULDING...\n")
                self.__build_ensemble_model()
                self.__print("\nMODEL BUILT!\n")
                
                self.__print("\n2- FITTING AND EVALUATING THE MODEL...\n")
                self.__fit_and_evaluate_ensemble_model()
                self.__print("MODEL FITTED AND EVALUATED!")
                
                self.__print("\n3- BUILDING PROXIMITY MATRIX...")  
                self.__print(f"\n{Back.GREEN} {self.__estimator.n_estimators} estimators have been counted {Style.RESET_ALL}\nEach estimator is being used for predictions...")
                self.__proximity_matrix = self.build_proximity_matrix(self.__estimator, self.__encoded_features)
                self.__print("\nPROXIMITY MATRIX BUILT!\n")
                      
                self.__print("\n4- COMPUTING WEIGHTED AVERAGES...")
                self.__compute_weighted_averages(numerical_features_decimals)
                self.__print("\nWEIGHTED AVERAGES COMPUTED!\n")
                        
                self.__print("\n5- REPLACING NAN VALUES IN ENCODED DATA...")           
                self.__replace_missing_values_in_dataframe()
                self.__print("\nNAN VALUES REPLACED!\n")
                
            self.__print("\n\n##################### CHECKING FOR CONVERGENCE...#####################\n\n")
            self.__compute_standard_deviations(n_iterations_for_convergence)
            self.__remove_convergent_values()
            self.__check_for_convergence()
                
        self.__print(f"\n- TOTAL ITERATIONS: {total_iterations}")
        #We save the final dataset if a path is given
        final_dataset = pd.concat((self.__features, self.__target_variable), axis=1)
        self.__save_new_dataset(final_dataset, path_to_save_dataset)  
        return  final_dataset 
    

    def create_weighted_averages_plots(self, directory_path, both_graphs=0, verbose=1):
        '''
        Creates plots of nan predicted values evolution over n iterations.
        Two type of plots can be generated: for values that diverged and those that converged.
        These are the parameters:
            - If 'both_graphs' is set to 1, those two type of graph will be generated
            - 'directory_path' is set to specify the path for the graphs to be stored into
            - If 'verbose' is set to 1, messages will be displayed
        '''
        self.__print_verbose        = verbose
        convergent_and_divergent    = [(self.__all_weighted_averages, "divergent_graphs")]
        if both_graphs:
            convergent_and_divergent.append((self.__all_weighted_averages_copy, "convergent_graphs"))
        for value in convergent_and_divergent:
            weighted_average_dict   = value[0]
            graph_type              = value[1]
            std                     = 0
            for coordinates, values in weighted_average_dict.items():
                self.__print(f"-{coordinates} graph created")                       
                try:
                    std = np.round(np.std(values[-self.__last_n_iterations:]),2)
                except TypeError:
                    pass
                row_number      = coordinates[0] 
                variable_name   = coordinates[1]
                std_str         = f"std_{std}"
                filename        = f"row_{row_number}_column_{variable_name}" 
                iterations      = len(values)
                path            = os.path.join(directory_path, graph_type, variable_name)
                if not os.path.exists(path):
                    os.makedirs(path)                     
                if self.__features_type_predictions.loc[variable_name].any()=="numerical":
                    plt.ioff()
                    plt.figure()
                    plt.title(f"Evolution of value {coordinates} over {iterations} iterations\nstd on the last {self.__last_n_iterations} iterations:{std}")
                    plt.plot(np.arange(1,iterations+1), values)
                    plt.xlabel('Iterations')
                    plt.ylabel('Values')
                    plt.savefig(os.path.join(path, filename+"_"+std_str+".jpg"))
                else:
                    plt.ioff()
                    plt.figure()
                    data        = Counter(values)
                    names       = list(data.keys())
                    values      = list(data.values())
                    percentages = list(map(int, (values/np.sum(values))*100))
                    for i in range(len(percentages)):
                        plt.annotate(s=percentages[i], xy=(names[i], percentages[i]+1), fontsize=10)
                        plt.hlines(percentages[i], xmin=0, xmax=0)
                    plt.bar(names, percentages, align="center")
                    plt.ylabel('Proportion')
                    plt.title(f"Proportions of value {coordinates} modalities after {iterations} iterations")
                    plt.savefig(os.path.join(path, filename+".jpg"))
