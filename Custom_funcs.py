# -*- coding: utf-8 -*-
"""
Created on Thu Jun 23 15:01:28 2022

@author: Florian Cataldi
"""

"""
Fonctions wich need to be adapted to your dataset
"""
#%% DO NOT MODIFY THESE FUNCTIONS !!

def load_data(filename, progress_bar=None):
    file = open(filename, encoding="utf8")
    temp = file.readlines()
    file.close()
    
    data = []
    for line in temp :
        new_line = ""
        for carac in line :
            if carac not in ["\ufeff"] :
                new_line += carac
        data.append(new_line)
        if progress_bar != None :
            progress_bar.update()
    
    return (data)

def get_metadata():
    type_map = {
        "InputFilename" : "str",
        "AvailableLanguage" : "strlist",
        "InputDataDir" : "str",
        "OutputDataDir" : "str",
        "CuratedDataDir" : "str"
    }
    
    temp = load_data("metadata.CONFIG_")
    metadata = {}
    for line in temp :
        info = line.split("=")[0]
        value = line.split("=")[1][:-1]
        if type_map[info] == "strlist" :
            value = value.split(";")
        metadata[info] = value
    
    return (metadata)

#%% Functions to get all reviews from your dataset (GET_COMMS)
#   and the lenght of a review (GET_COMM_LEN)

def trouve_id_comm(texte):
    id_comm = None
    
    temp = texte.split(",")
    try :
        int(temp[0].split(".")[0])
        id_comm = temp[0].split(".")[0]
    except :
        None
    
    return (id_comm)

def trouve_debut_comm(texte, lang="en"):
    i_debut = None
    
    temp = texte.split(",")
    ok_ = True
    try :
        if lang == "en" :
            int(temp[0].split(".")[0])
            int(temp[0].split(".")[1])
        elif lang == "fr" :
            int(temp[0])
    except :
        ok_ = False
    if len(temp) != 1 and len(temp) >= 3 and ok_ == True :
        i_debut = 0
        target = 3
        
        if temp[2][0] == '"' :
            while '"' not in temp[target] :
                target += 1
            target += 1
        
        for i in range(target) :
            i_debut += len(temp[i])+1
        
        if temp[target][0] == '"' :
            i_debut += 1
    
    return (i_debut)

def trouve_fin_comm(texte, lang="en"):
    i_fin = None
    
    temp = texte.split(",")
    temp.reverse()
    ok_ = True
    if lang == "en" :
        try :
            float(temp[0])
        except :
            ok_ = False
    elif lang == "fr" :
        try :
            int(temp[1])
        except :
            ok_ = False
    if len(temp) != 1 and len(temp) >= 5 and ok_ == True:
        i_fin = 0
        temp.reverse()
        ajust = 5
        if lang == "fr" :
            ajust += 1
        for i in range(len(temp)-ajust) :
            i_fin += len(temp[i])+1
        i_fin -= 2
        if lang == "fr" :
            i_fin += 1
    
    return (i_fin)

def get_real_comm_from_line(line, langue, num_comm, func_for_invalid_carac):
    output = None
    
    id_comm = trouve_id_comm(line)
    if id_comm != None :
        i_deb = trouve_debut_comm(line, lang=langue)
        i_fin = trouve_fin_comm(line, lang=langue)
        if func_for_invalid_carac(line[i_deb:i_fin]) == False :
            output = line[i_deb:i_fin]
    
    return (id_comm, output)

def GET_COMM_LEN(comm, lang):
    """
    Parameters
    ----------
    comm : str
        The review to extract the lenght from.
        It comes from the file 'InputDataDir' specified in metadata.CONFIG_,
        i.e. the line with extra informations about the review if there are
    lang : str
        Language of the reviews.
        This parameter can be passed to helper functions if your data structures
        depend of the reviews language.
    
    Returns
    -------
    int
        Lenght in character of the review.
        Think of it as the lenght of the string varaiable that contains the
        whole line of the review data striped of surplus info to only keep the
        review.
    """
    i_deb = trouve_debut_comm(comm, lang=lang)
    i_fin = trouve_fin_comm(comm, lang=lang)
    return (i_fin-i_deb)

def GET_COMMS(mode, lang, params, func_for_invalid_carac):
    """
    Parameters
    ----------
    mode : str
        One of ['labelisation', 'validation', 'partition']
        Specifies how this function works
    lang : str
        Language of the reviews.
        This parameter can be passed to helper functions if your data structures
        depend of the reviews language.
    func_for_invalid_carac : function
        Function used to check incompatible characters with Tkinter
    params : tuple
        Contains the different parameters that are passed to this functions.
        Depending on what mode is, this parameters defer like this :
            
            - mode == 'labelisation'
                -> params = (Filenames, comms, progress_bar)
                Filenames : dict
                    Dictionnary containing the filenames of the partitions to be loaded.
                    Basic structure of the dictionnary :
                        Filenames[(language)] = (filename)
                        language is one of AvailableLanguage of the metadata.CONFIG_ file
                comms : dict
                    Dictionnary that will contain for each language the reviews.
                    Basic structure of the dictionnary :
                        comms[(language)][(review ID)] = (review)
                        language is one of AvailableLanguage of the metadata.CONFIG_ file
                progress_bar : Tkinter ttk.progressbar object
                    This is the progress bar that will be updated everytime a
                    review has been acquired and writen in comms
            
            - mode == 'validation'
                -> params = (part, comms, progress_bar)
                part : str
                    Partition to be validated.
                comms : 
                    Dictionnary that will contain for each language the reviews.
                    Basic structure of the dictionnary :
                        comms[(language)][(review ID)] = (review)
                        language is one of AvailableLanguage of the metadata.CONFIG_ file
                progress_bar : Tkinter ttk.progressbar object
                    This is the progress bar that will be updated everytime a
                    review has been acquired and writen in comms
            
            - mode == 'partition'
                -> params = (Filenames, comms_var, progress_bar)
                Filenames : dict
                    Dictionnary containing the filenames of the unpartitioned files.
                    Basic structure of the dictionnary :
                        Filenames[(language)] = (filename)
                        language is one of AvailableLanguage of the metadata.CONFIG_ file
                comms_var : dict
                    Dictionnary that will contain for each language the
                    informations of reviews.
                    Those informations are the text and the length of the review
                    and are stored in to lists.
                    Basic structure of the dictionnary :
                        comms_var[(language)] = {'text' : [(list of the reviews text)]
                                                 'len'  : [(list of the reviews lenghts)]}
                        language is one of AvailableLanguage of the metadata.CONFIG_ file
                progress_bar : Tkinter ttk.progressbar object
                    This is the progress bar that will be updated over time
    

    Returns
    -------
    None.
    
    Useful Notes :
        - You must use func_for_invalid_carac(extracted_review) to check the
          presence of an incompatible character before writing it params[1] in
          'labelisation' and 'validation' mode.
          func_for_invalid_carac(extracted_review) takes as input the text of
          the extracted review and returns a boolean. If it returns True, it
          means that such a character has been found in the text. Else, it
          returns False.
        - 
    """
    
    metadata = get_metadata()
    LABEL = "labelisation"
    VALID = "validation"
    PART = "partition"
    if mode in (LABEL, VALID, PART) :
        if mode == LABEL :
            Filenames = params[0]
            comms = params[1]
            progress_bar = params[2]
            
            data = load_data(metadata["InputDataDir"]+Filenames[lang])
            if "_part" not in Filenames[lang] :
                data = data[1:]
            
            line = ""
            k = 0
            for element in data :
                line += element
                
                temp = line.split(",")
                elem_0_ok = True
                elem_last_ok = True
                try :
                    float(temp[0])
                except :
                    elem_0_ok = False
                if lang == "en" :
                    try :
                        float(temp[len(temp)-1])
                        float(temp[len(temp)-3])
                    except :
                        elem_last_ok = False
                elif lang == "fr" :
                    if temp[len(temp)-1][:-1] not in ["train", "test", "valid"] :
                        elem_last_ok = False
                
                if elem_0_ok == True and elem_last_ok == True :
                    id_comm, comm = get_real_comm_from_line(line, lang, k, func_for_invalid_carac)
                    if comm != None :
                        comms[lang][id_comm] = comm
                    progress_bar.step()
                    progress_bar.update()
                    line = ""
                    k += 1
        
        elif mode == VALID :
            part = params[0]
            comms = params[1]
            progress_bar = params[2]
            
            path = metadata["InputFilename"]+"_"+part+".txt"
            data = load_data(metadata["InputDataDir"]+path)
            if "_part" not in path :
                data = data[1:]
            
            line = ""
            k = 0
            for element in data :
                line += element
                
                temp = line.split(",")
                elem_0_ok = True
                elem_last_ok = True
                try :
                    float(temp[0])
                except :
                    elem_0_ok = False
                if lang == "en" :
                    try :
                        float(temp[len(temp)-1])
                        float(temp[len(temp)-3])
                    except :
                        elem_last_ok = False
                elif lang == "fr" :
                    if temp[len(temp)-1][:-1] not in ["train", "test", "valid"] :
                        elem_last_ok = False
                
                if elem_0_ok == True and elem_last_ok == True :
                    id_comm, comm = get_real_comm_from_line(line, lang, k, func_for_invalid_carac)
                    if comm != None :
                        comms[id_comm] = comm
                    progress_bar.step()
                    progress_bar.update()
                    line = ""
                    k += 1
        
        elif mode == PART :
            Filenames = params[0]
            comms_var = params[1]
            progress_bar = params[2]
            
            data = load_data(metadata["InputDataDir"]+Filenames[lang],
                             progress_bar=progress_bar)
            if "_part" not in Filenames[lang] :
                data = data[1:]
            
            line = ""
            k = 0
            for element in data :
                line += element
                
                temp = line.split(",")
                elem_0_ok = True
                elem_last_ok = True
                try :
                    float(temp[0])
                except :
                    elem_0_ok = False
                if lang == "en" :
                    try :
                        float(temp[len(temp)-1])
                        float(temp[len(temp)-3])
                    except :
                        elem_last_ok = False
                elif lang == "fr" :
                    if temp[len(temp)-1][:-1] not in ["train", "test", "valid"] :
                        elem_last_ok = False
                
                if elem_0_ok == True and elem_last_ok == True :
                    comms_var[lang]["text"].append(line)
                    comms_var[lang]["len"].append(GET_COMM_LEN(line, lang))
                    progress_bar.update()
                    line = ""
                    k += 1


#%% Function to extract words from a review

def Word_Sep(text):
    """
    If the default function is enough or you don't want to use your own function,
    this function must return nothing or a None.
    
    Parameters
    ----------
    text : str
        The text of a review.

    Returns
    -------
    words : list
        List containing each words in the text.
    shifts : list
        List containing integers representing the number of characters between
        the n-th word and the (n-1)-th word. This list begins with a 0.
    """
    
    None
