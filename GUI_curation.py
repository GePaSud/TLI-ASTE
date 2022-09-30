# -*- coding: utf-8 -*-
"""
Created on Mon Jun 27 14:41:53 2022

@author: Florian Cataldi
"""

"""
GUI pour labelisation des triplets dans les commentaires

Curation Window
"""

# TODO : mettre en place une métrique en post-GUI sur la fiabilité des users
# TODO : ajouter la possibilité au curateur de déclarer le commentaire incohérent
#        et de sauvegarder ça comme un commentaire sans triplet (ça ou d'une autre manière)

import tkinter as tk
from tkinter import colorchooser
from tkinter import messagebox
from os import walk, mkdir
from time import sleep, time
import numpy as np
import Utils
import Other_windows as wnds
import Custom_funcs as ctmf

def check_carac_non_supporte(comm):
    sortie = False
    for carac in comm :
        unicode = int(hex(ord(carac)),0)
        if unicode > 0xffff :
            sortie = True
            break
    return (sortie)

use_default_word_sep = False
try :
    if ctmf.Word_Sep("test") == None :
        print ("Custom function for word separation found but not defined by user. Proceeding with the default one.")
        use_default_word_sep = True
except :
    print ("Custom function for word separation not found. Proceeding with the default one.")
    use_default_word_sep = True

#%% Séléction de la localisation

Loc_Data, Loc_lang = Utils.select_loc()

#%% Chargement des metadonnées nécessaires au bon fonctionnement du GUI

Metadata = Utils.get_metadata()
WrkDir = {
    "out" : Metadata["OutputDataDir"],
    "in"  : Metadata["InputDataDir"],
    "val"  : Metadata["CuratedDataDir"]
}
if WrkDir["val"].split("/")[1] not in next(walk("Data"))[1] :
    mkdir(WrkDir["val"])

#%% Récupération de la partition à valider

Info_for_validation = Utils.get_part_for_val(Loc_Data)
Langue_Part = Info_for_validation["part"].split("_")[0].capitalize()

save_file = WrkDir["val"]+"Comms_curated_{}".format(Info_for_validation["part"].split("_")[0])
for extension in [".txt", ".HELPER_"] :
    try :
        file = open(save_file + extension, "r", encoding="utf8")
        file.close()
    except :
        file = open(save_file + extension, "x", encoding="utf8")
        file.close()

#%% On n'exécute pas plus s'il n'y a rien à valider

ok_to_run = True
if Info_for_validation["part"] == "" :
    ok_to_run = False

if ok_to_run == True :

    #%% Chargement des commentaires à valider
    
    comms = {}
    chargement_comms = wnds.load_comms_window(Info_for_validation["part"].split("_")[0], Info_for_validation["nb_comms"],
                                              Loc_Data, "validation", (Info_for_validation["part"], comms),
                                              check_carac_non_supporte)
    chargement_comms.run_window()
    
    #%% Chargement des triplets de chaque utilisateur
    
    def str2trip(string):
        out = []
        temp = string.split("<|>")
        for i in range(len(temp)) :
            if i in [0,1] :
                to_add = []
                for elem in temp[i][1:-1].split(", ") :
                    if elem[0] in ["'", '"'] :
                        to_add.append(elem[1:-1])
                    else :
                        to_add.append(elem)
                out.append(to_add)
            elif i == 2 :
                out.append(temp[i])
            elif i in [3,4] :
                to_add = []
                for elem in temp[i][1:-1].split(", ") :
                    to_add.append(int(elem))
                out.append(to_add)
        return (out)
    
    def rearrange_triplets(triplets):
        def extract_first_index_of_aspect(item):
            return (item[3][0])
        def extract_first_index_of_opinion(item):
            return (item[4][0])
        
        out = sorted(sorted(triplets, key=extract_first_index_of_aspect), key=extract_first_index_of_opinion)
        return (out)
    
    Users_Triplets = {}
    # Users = next(walk(WrkDir["out"]))[1]
    Users = Info_for_validation["users"]
    for user in Users :
        Users_Triplets[user] = {}
        data = Utils.load_data(WrkDir["out"]+user+"/Comms_labeled_"+Info_for_validation["part"]+".txt")
        for comm in data :
            temp = comm.split("\|/")
            id_ = temp[0]
            trips = []
            for trip in temp[2:-1] :
                trips.append(str2trip(trip))
            Users_Triplets[user][id_] = rearrange_triplets(trips)
    
    #%% Création de la matrice de regroupement des triplets
    # d'après la def générale de wikipédia (https://en.wikipedia.org/wiki/Similarity_measure) c'est une matrice de similarité
    # qui utilise une métrique de similarité (http://www.scholarpedia.org/article/Similarity_measures pour plus d'info)
    # et qui est symétrique avec le nombre d'éléments communs comme métrique
    
    # TODO : trouver un moyen de pénaliser les triplets fourre-tout sans pour autant mettre en l'air la suite de l'algo
    
    def get_users_for_match(I,K,repartition):
        out = {"ref" : "", "comp" : ""}
        i_ = 0
        k_ = 0
        
        for l in range(2) :
            if l == 0 :
                target = "ref"
                index = I
            elif l == 1 :
                target = "comp"
                index = K
            prev = 0
            cumul = repartition[0]
            for i in range(len(repartition)) :
                if index >= prev and index < cumul :
                    out[target] = Users[i]
                    break
                else :
                    prev += repartition[i]
                    cumul += repartition[i+1]
        
        i_ = I - sum(repartition[:Users.index(out["ref"])])
        k_ = K - sum(repartition[:Users.index(out["comp"])])
        
        return (out["ref"], out["comp"], i_, k_)
    
    def crea_mat_similarity(id_comm):
        users_repartition = []
        for user in Users :
            try :
                users_repartition.append(len(Users_Triplets[user][id_comm]))
            except :
                users_repartition.append(None)
        dim = 0
        for size in users_repartition :
            if size == None :
                dim += 1
            else :
                dim += size
        
        def ignore_value(N, is_mat=False):
            if is_mat == False :
                return (N)
            else :
                bloc = np.nan*np.eye(N)
                for i in range(N) :
                    bloc[i,i] = i
                return (bloc)
        
        mat = np.zeros((dim,dim))
        ranges = []
        CSG = 0
        for i in range(len(users_repartition)) :
            if i != 0 :
                if users_repartition[i-1] != None :
                    CSG += users_repartition[i-1]
                else :
                    CSG += 1
            range_index = [j for j in range(dim)]
             
            if users_repartition[i] != None :
                mat[CSG:CSG+users_repartition[i], CSG:CSG+users_repartition[i]] = ignore_value(users_repartition[i], is_mat=True)
                for j in range(CSG, CSG+users_repartition[i]) :
                    range_index.remove(j)
                S = 0
                for k in range(len(users_repartition)) :
                    if users_repartition[k] == None :
                        range_index.remove(S)
                        S += 1
                    else :
                        S += users_repartition[k]
                for j in range(users_repartition[i]) :
                    ranges.append(range_index)
            else :
                mat[CSG, :] = ignore_value(users_repartition[i])
                mat[:, CSG] = ignore_value(users_repartition[i])
                ranges.append([])
        
        for i in range(len(users_repartition)) :
            if users_repartition[i] == None :
                users_repartition[i] = 1
        
        for i in range(dim) :
            range_index = ranges[i]
            for k in range_index :
                nb_match = 0
                user_ref, user_comp, i_, k_ = get_users_for_match(i,k,users_repartition)
                
                # calcul du match pour le sentiment
                if Users_Triplets[user_ref][id_comm][i_][2] == Users_Triplets[user_comp][id_comm][k_][2] :
                    nb_match += 1
                
                # calcul du match pour les termes (version stricte : aspect/aspect et opinion/opinion)
                for term in [3,4] :
                    # calcul du match pour l'aspect inexistant puis l'opinion inexistante
                    if Users_Triplets[user_ref][id_comm][i_][term] == -1 and Users_Triplets[user_comp][id_comm][k_][term] == -1 :
                        nb_match += 1
                    # calcul du match pour les aspects strictement puis pour les opinions strictement
                    termes_ref = [_ for _ in Users_Triplets[user_ref][id_comm][i_][term] if _ != -1]
                    termes_comp = [_ for _ in Users_Triplets[user_comp][id_comm][k_][term] if _ != -1]
                    if len(termes_ref) < len(termes_comp) :
                        source = termes_ref
                        other = termes_comp
                    else :
                        source = termes_comp
                        other = termes_ref
                    for word in source :
                        if word in other :
                            nb_match += 1
                # calcul du match pour les termes (version non stricte malussée : aspect et opinion ne correspondant pas à sa contrepartie)
                termes_ref = [_ for _ in Users_Triplets[user_ref][id_comm][i_][3] if _ != -1 and _ not in Users_Triplets[user_comp][id_comm][k_][3]]
                termes_ref += [_ for _ in Users_Triplets[user_ref][id_comm][i_][4] if _ != -1 and _ not in Users_Triplets[user_comp][id_comm][k_][4]]
                termes_comp = [_ for _ in Users_Triplets[user_comp][id_comm][k_][3] if _ != -1 and _ not in Users_Triplets[user_ref][id_comm][i_][3]]
                termes_comp += [_ for _ in Users_Triplets[user_comp][id_comm][k_][4] if _ != -1 and _ not in Users_Triplets[user_ref][id_comm][i_][4]]
                if len(termes_ref) < len(termes_comp) :
                    source = termes_ref
                    other = termes_comp
                else :
                    source = termes_comp
                    other = termes_ref
                for word in source :
                    if word in other :
                        nb_match += 0.5
                    
                mat[i,k] = nb_match
        
        return (mat, users_repartition, ranges)
    
    def get_ori_max_in_mat_sim(mat, ranges):
        mask = np.zeros(mat.shape)
        for i in range(len(ranges)) :
            for j in ranges[i] :
                if i > j :
                    mask[i,j] = 1
        explo_mat = np.where(np.isnan(mat), 0, mat)*mask
        
        out = None
        max_val = explo_mat.max()
        max_pos = np.unravel_index(explo_mat.argmax(), mat.shape)
        if max_val > 1 :
            out = max_pos
        return (out, max_val)
    
    def get_other_max_in_mat_sim(mat, repartition, ori_pos):
        maxes = [ori_pos]
        ligne, colonne = [None for _ in Users], [None for _ in Users]
        prev = 0
        for i in range(len(repartition)) :
            if ori_pos[0] < prev or ori_pos[0] >= prev+repartition[i] : # on évite les blocs de nan
                if ori_pos[1] < prev or ori_pos[1] >= prev+repartition[i] : # on évite le bloc du max d'origine
                    # on ajoute l'array à ligne où trouver les max par bloc d'user que
                    # si c'est pas un bloc de nan et si c'est pas le bloc du max d'origine
                    ligne[i] = mat[ori_pos[0],prev:prev+repartition[i]]
                    ligne[i] = np.where(np.isnan(ligne[i]), -1, ligne[i])
                    ligne[i] = (ligne[i].max(), (ori_pos[0], prev+ligne[i].argmax()))
            if ori_pos[1] < prev or ori_pos[1] >= prev+repartition[i] : # on évite les blocs de nan
                if ori_pos[0] < prev or ori_pos[0] >= prev+repartition[i] : # on évite le bloc du max d'origine
                    # on ajoute l'array à colonne où trouver les max par bloc d'user que
                    # si c'est pas un bloc de nan et si c'est pas le bloc du max d'origine
                    colonne[i] = mat[prev:prev+repartition[i], ori_pos[1]]
                    colonne[i] = np.where(np.isnan(colonne[i]), -1, colonne[i])
                    colonne[i] = (colonne[i].max(), (prev+colonne[i].argmax(), ori_pos[1]))
            prev += repartition[i]
        for item in [ligne, colonne] :
            for vec in item :
                if type(vec) != type(None) :
                    if vec[0] > 1 :
                        maxes.append(vec[1])
        return (maxes)
    
    def secu_to_much_trips(similarity, users_repartition, mat):
        # TODO : faire en sorte que cette sécurité fonctionne lorsque plusieurs utilisateurs
        #        ont plus d'un triplet dans similarity
        nb_per_user = [0 for _ in Users]
        user_to_much = None
        for i in range(len(Users)) :
            for element in similarity :
                if element[0] == Users[i] :
                    nb_per_user[i] += 1
                if nb_per_user[i] > 1 and user_to_much == None :
                    user_to_much = Users[i]
        
        if user_to_much != None :
            trips_to_compare = []
            to_remove = []
            trips_ref = []
            for trip in similarity :
                mat_index = 0
                for i in range(Users.index(trip[0])) :
                    mat_index += users_repartition[i]
                mat_index += trip[1]
                
                if trip[0] == user_to_much :
                    trips_to_compare.append(mat_index)
                    to_remove.append(trip)
                else :
                    trips_ref.append(mat_index)
            
            mean_sim = []
            for i in range(len(trips_to_compare)) :
                value = 0
                for element in trips_ref :
                    value += mat[trips_to_compare[i],element]
                value /= len(trips_ref)
                mean_sim.append(value)
            to_remove.remove(to_remove[np.argmax(mean_sim)])
            
            for trip in to_remove :
                similarity.remove(trip)
        
    def get_similarity_in_comm(id_comm):
        similarities = []
        mat, users_repartition, ranges = crea_mat_similarity(id_comm)
        
        ori_max, value_max = get_ori_max_in_mat_sim(mat, ranges)
        while value_max > 1 :
            maxes = get_other_max_in_mat_sim(mat, users_repartition, ori_max)
            temp = []
            for pos in maxes :
                user_ref, user_comp, trip_ref, trip_comp = get_users_for_match(pos[0], pos[1], users_repartition)
                if (user_ref, trip_ref) not in temp :
                    temp.append((user_ref, trip_ref))
                if (user_comp, trip_comp) not in temp :
                    temp.append((user_comp, trip_comp))
            secu_to_much_trips(temp, users_repartition, mat)
            similarities.append(temp)
            
            indexes_to_nan = []
            for item in temp :
                mat_index = 0
                for i in range(Users.index(item[0])) :
                    mat_index += users_repartition[i]
                mat_index += item[1]
                indexes_to_nan.append(mat_index)
            for item in indexes_to_nan :
                mat[item, :] *= np.nan
                mat[:, item] *= np.nan
            ori_max, value_max = get_ori_max_in_mat_sim(mat, ranges)
        
        def extract_min_ind(item):
            temp = []
            for info in item :
                for term in [3,4] :
                    for ind in Users_Triplets[info[0]][id_comm][info[1]][term] :
                        if ind not in temp and ind != -1 :
                            temp.append(ind)
            return (min(temp))
        similarities = sorted(similarities, key=extract_min_ind)
        
        alones = []
        for i in range(mat.shape[0]) :
            if np.isnan(mat[i,i]) == False :
                prev = 0
                for k in range(len(users_repartition)) :
                    if i >= prev and i < prev+users_repartition[k] :
                        if np.isnan(mat[i,i]) == False :
                            alones.append([(Users[k], i-prev)])
                    prev += users_repartition[k]
        similarities += sorted(alones, key=extract_min_ind)
        return (similarities)
    
    #%% Création des similarités entre chaque utilisateur
    comm_ids_list = [str(id_) for id_ in sorted([int(_) for _ in list(comms.keys())])]
    Triplets_Similarities = {}
    deb_time = time()
    for id_ in comm_ids_list :
        Triplets_Similarities[id_] = get_similarity_in_comm(id_)
    print ("Durée de chargement : {} s".format(round(time()-deb_time,3)))
    
    #%% Chargement des oddities de chaque utilisateur
    
    Users_Oddities = {}
    for user in Users :
        Users_Oddities[user] = []
        data = Utils.load_data(WrkDir["out"]+user+"/oddities.txt")
        for oddity in data :
            id_ = oddity.split("-")[1][:-1]
            if id_ in list(comms.keys()) :
                Users_Oddities[user].append(oddity[:-1])
    
    #%% Définition du commentairede départ
    
    curated_comms = [0 for i in range(len(comm_ids_list))]
    data = Utils.load_data(save_file+".HELPER_")
    for line in data :
        try :
            curated_comms[comm_ids_list.index(line.split("\|/")[0])] = 1
        except :
            None
    
    id_curation = comm_ids_list[curated_comms.index(0)]
    comm = comms[id_curation]
    
    if curated_comms[comm_ids_list.index(id_curation)] == 1 :
        data = Utils.load_data(save_file+".HELPER_")
        curated_trips = []
        for line in data :
            if line.split("\|/")[0] == id_curation :
                for element in line.split("\|/")[1:-1] :
                    if element == "None" :
                        curated_trips.append(None)
                    elif element[0] == "(" :
                        temp = element[1:-1].split(", ")
                        curated_trips.append((temp[0][1:-1], int(temp[1])))
                    elif element[0] == "[" :
                        curated_trips.append(str2trip(element))
                break
    else :
        curated_trips = [0 for i in range(len(Triplets_Similarities[id_curation]))]
    
    #%% Définition du triplet de départ
    
    triplet_similarity = 0
    Triplet_actuel = {}
    def update_Trip_actuel(id_comm, num_sim):
        global Triplet_actuel
        Triplet_actuel = {}
        if Triplets_Similarities[id_comm] != [] :
            if num_sim < len(Triplets_Similarities[id_comm]) :
                for user, id_trip in Triplets_Similarities[id_comm][num_sim] :
                    Triplet_actuel[user] = Users_Triplets[user][id_comm][id_trip]
        for user in Users :
            if user not in list(Triplet_actuel.keys()) :
                Triplet_actuel[user] = None
    update_Trip_actuel(id_curation, triplet_similarity)
    
    #%% Récupération des informations sur le commentaire
    
    def get_comm_plus(texte):
        if use_default_word_sep == True :
            # récupération de tous les caractères non voulus pour séparation
            carac_split = []
            for carac in texte :
                if carac.isalnum() == False and carac not in carac_split and carac not in ["'","/","’","%"]:
                    carac_split.append(carac)
            
            # séparation du texte par tous les caractères non voulus
            temp_mots = texte.split(carac_split[0])
            for carac in carac_split[1:] :
                temp = []
                for element in temp_mots :
                    for item in element.split(carac) :
                        temp.append(item)
                temp_mots = temp
            
            # on supprime de la variable temporaire tous les '' qui servent à rien
            mots_ = []
            for element in temp_mots :
                if element != "" :
                    mots_.append(element)
            
            # indique pour chaque mots combien de caractères non voulus sont entre lui et le mot précédent
            decalage_ = []
            temp = ""
            c = 0
            i = 0
            for char in texte :
                if char not in carac_split or char in ["'","/","’"]:
                    temp += char
                else :
                    c += 1
                if temp == mots_[i] :
                    decalage_.append(c)
                    c = 0
                    temp = ""
                    if i+1 < len(mots_) :
                        i += 1
        else :
            mots_, decalage_ = ctmf.Word_Sep(texte)
        
        review_lenght_ = {"mots" : len(mots_),
                         "caracteres" : len(texte)}
        
        carac_per_line_ = []
        c = 0
        for carac in texte :
            if carac != "\n" :
                c += 1
            else :
                carac_per_line_.append(c)
                c = 0
        
        return (mots_, decalage_, review_lenght_, carac_per_line_)
    
    mots, decalage, review_lenght, carac_per_line = get_comm_plus(comm)
    
    #%% Création de la fenêtre principale
    
    root = tk.Tk()
    root.option_add('*tearOff', False)
    root.title(Loc_Data["17.1"])
    
    #%% Récupération des paramètres du GUI ou création par défaut
    
    taille_police = 14
    taille_police_review = 18
    interaction_spin = tk.IntVar(value=0)
    mode_vertical = tk.BooleanVar(value=True)
    raccourcis = {"spin_u" : "z",
                  "spin_d" : "s",
                  "spin_v_u" : "d",
                  "spin_v_d" : "q",
                  "spin_reset_col" : "x",
                  "vit_plus" : "e",
                  "vit_moins" : "a",
                  "reset_trip_selec" : "n"}
    Comm_State_Colors = {
        "not_labeled" : "grey",
        "labeled" : "green",
        "odd" : "red"
    }
    Triplets_State_Colors = {
        "not_curated" : "grey",
        "curated" : "green",
        "ignored" : "red"
    }
    Heatmap_Colors = ["#ff0000", "purple", "pink", "saddlebrown", "gold2", "#00c000"]
    
    try :
        file = open("Settings/curation.CONFIG_", "r")
        for line in file.readlines() :
            line.strip("\n")
            temp = line.split("=")
            value = temp[1].strip("\n")
            if temp[0] == "taille_police" :
                taille_police = int(value)
            elif temp[0] == "taille_police_review" :
                taille_police_review = int(value)
            elif temp[0] == "interaction_spin" :
                interaction_spin.set(int(value))
            elif temp[0] == "mode_vertical" :
                mode_vertical.set(value=="True")
            elif temp[0] == "heat_colors" :
                Heatmap_Colors = value.split(";")
            elif temp[0][:14] == "state_colors_c" :
                temp_ = temp[0].split(".")
                Comm_State_Colors[temp_[1]] = value
            elif temp[0][:14] == "state_colors_t" :
                temp_ = temp[0].split(".")
                Triplets_State_Colors[temp_[1]] = value
            elif temp[0][:10] == "raccourcis" :
                temp_ = temp[0].split(".")
                raccourcis[temp_[1]] = value
        file.close()
    except :
        file = open("Settings/curation.CONFIG_", "x")
        default_settings = "taille_police=14\n"
        default_settings += "taille_police_review=18\n"
        default_settings += "interaction_spin=0\n"
        default_settings += "mode_vertical=True\n"
        default_settings += "heat_colors=#ff0000;purple;pink;saddlebrown;gold2;#00c000\n"
        default_settings += "state_colors_c.not_labeled=grey\n"
        default_settings += "state_colors_c.labeled=green\n"
        default_settings += "state_colors_c.odd=red\n"
        default_settings += "state_colors_t.not_curated=grey\n"
        default_settings += "state_colors_t.curated=green\n"
        default_settings += "state_colors_t.ignored=red\n"
        default_settings += "raccourcis.spin_u=z\n"
        default_settings += "raccourcis.spin_d=s\n"
        default_settings += "raccourcis.spin_v_u=d\n"
        default_settings += "raccourcis.spin_v_d=q\n"
        default_settings += "raccourcis.spin_reset_col=x\n"
        default_settings += "raccourcis.vit_plus=e\n"
        default_settings += "raccourcis.vit_moins=a\n"
        default_settings += "raccourcis.reset_trip_selec=n\n"
        file.write(default_settings)
        file.close()
    
    def save_config():
        settings = "taille_police={}\n".format(taille_police)
        settings += "taille_police_review={}\n".format(taille_police_review)
        settings += "interaction_spin={}\n".format(interaction_spin.get())
        settings += "mode_vertical={}\n".format(mode_vertical.get())
        settings += "heat_colors="
        for color in Heatmap_Colors :
            settings += color + ";"
        settings = settings[:-1]+"\n"
        for color_state in list(Comm_State_Colors.keys()) :
            settings += "state_colors_c.{}={}\n".format(color_state, Comm_State_Colors[color_state])
        for color_state in list(Triplets_State_Colors.keys()) :
            settings += "state_colors_t.{}={}\n".format(color_state, Triplets_State_Colors[color_state])
        for bind in list(raccourcis.keys()) :
            settings += "raccourcis.{}={}\n".format(bind,raccourcis[bind])
        
        file = open("Settings/curation.CONFIG_", "w")
        file.write(settings)
        file.close()
    
    #%% Création des menus
    
    menubar = tk.Menu(root)
    root["menu"] = menubar
    
    def changer_taille_police():
        def change_taille(what):
            global taille_police, taille_police_review
            if what == "T_U" and taille_police < 50 :
                taille_police += 1
            elif what == "T_D" and taille_police > 2 :
                taille_police -= 1
            elif what == "R_U" and taille_police_review < 50 :
                taille_police_review += 1
            elif what == "R_D" and taille_police_review > 2 :
                taille_police_review -= 1
            
            texte_ex.configure(font="Helvetica {}".format(taille_police))
            size_texte.configure(text=str(taille_police))
            review_ex.configure(font="Helvetica {}".format(taille_police_review))
            size_review.configure(text=str(taille_police_review))
            
            save_config()
        
        def up_texte():
            change_taille("T_U")
        def down_texte():
            change_taille("T_D")
        def up_review():
            change_taille("R_U")
        def down_review():
            change_taille("R_D")
        
        fen_taille = tk.Toplevel(root)
        fen_taille.title(Loc_Data["9.1"])
        #fen_taille.resizable(False, False)
        fen_taille.geometry("1200x400")
        
        texte_frame = tk.LabelFrame(fen_taille, text=Loc_Data["9.2"],
                                    font="Helvetica 14 bold")
        texte_ex = tk.Label(texte_frame, text=Loc_Data["9.3"],
                         font="Helvetica {}".format(taille_police))
        but_texte_down = tk.Button(texte_frame, text="-", font="Helvetica 14", command=down_texte)
        size_texte = tk.Label(texte_frame, text=str(taille_police))
        but_texte_up = tk.Button(texte_frame, text="+", font="Helvetica 14", command=up_texte)
        texte_frame.grid(column=0, row=0)
        texte_ex.grid(column=0, row=0, columnspan=3)
        but_texte_down.grid(column=0, row=1)
        size_texte.grid(column=1, row=1)
        but_texte_up.grid(column=2, row=1)
        
        separation = tk.Label(fen_taille, text="\n"*1)
        separation.grid(column=0, row=1)
        
        review_frame = tk.LabelFrame(fen_taille, text=Loc_Data["9.4"],
                                    font="Helvetica 14 bold")
        review_ex = tk.Label(review_frame, text=Loc_Data["9.5"],
                         font="Helvetica {}".format(taille_police_review))
        but_review_down = tk.Button(review_frame, text="-", font="Helvetica 14", command=down_review)
        size_review = tk.Label(review_frame, text=str(taille_police_review))
        but_review_up = tk.Button(review_frame, text="+", font="Helvetica 14", command=up_review)
        review_frame.grid(column=0, row=2)
        review_ex.grid(column=0, row=0, columnspan=3)
        but_review_down.grid(column=0, row=1)
        size_review.grid(column=1, row=1)
        but_review_up.grid(column=2, row=1)
        
        Utils.center_(fen_taille)
        
        def escape_apply(*args):
            taille_texte = {"normal" : [aspect["long"],aspect["debut"],
                                        aspect_visual,opinion["long"],opinion["debut"],
                                        opinion_visual,sentiment["negatif"],
                                        sentiment["neutre"],sentiment["positif"],
                                        prog_lab,curator_frame,radio_create_curator_trip,
                                        aspect_selection, opinion_selection,
                                        reset_aspect_but, reset_opinion_but,
                                        emergency_aspect["term_label"],emergency_aspect["term_entry"],
                                        emergency_aspect["id_label"],emergency_aspect["id_entry"],
                                        emergency_opinion["term_label"],emergency_opinion["term_entry"],
                                        emergency_opinion["id_label"],emergency_opinion["id_entry"],
                                        bouton_moins,bouton_plus,label_vitesse,valid_trip_but,
                                        next_trip_but,prev_trip_but],
                            "bold" : [users_frame,comm_frame,aspect_frame,opinion_frame,
                                      parcours_frame,curator_frame,sentiment_frame,
                                      plus_vite,heatmap_frame]}
            for user in Users :
                taille_texte["bold"].append(users_visual.users_info[user]["frame"])
            for widget in taille_texte["normal"] :
                widget.configure(font="Helvetica {}".format(taille_police))
            for widget in taille_texte["bold"] :
                widget.configure(font="Helvetica {} bold".format(taille_police))
            
            comm_visuel.tag_configure("aspect", font="Helvetica {}".format(taille_police_review))
            comm_visuel.tag_configure("opinion", font="Helvetica {}".format(taille_police_review))
            comm_visuel.tag_configure("normal", font="Helvetica {}".format(taille_police_review))
            for user in Users :
                users_visual.users_info[user]["widget"].tag_configure("normal", font="Helvetica {}".format(taille_police_review))
                users_visual.users_info[user]["widget"].tag_configure("aspect", foreground="orange",
                                                                      font="Helvetica {}".format(taille_police_review))
                users_visual.users_info[user]["widget"].tag_configure("opinion", foreground="blue",
                                                                      font="Helvetica {}".format(taille_police_review))
            
            fen_taille.destroy()
        
        fen_taille.protocol("WM_DELETE_WINDOW", escape_apply)
        fen_taille.bind("<Key-Escape>", escape_apply)
        
        fen_taille.transient(root)
        fen_taille.wait_visibility()
        fen_taille.grab_set()
        fen_taille.wait_window()
    
    def remap_binds(mode="remap"):
        fen_binds = tk.Toplevel(root)
        fen_binds.title(Loc_Data["10.1"])
        #fen_binds.resizable(False, False)
        
        possible_keys = ['Escape','F1','F2','F3','F4','F5','F6','F7','F8','F9',
                         'F10','ampersand','eacute','quotedbl','quoteright',
                         'parenleft','minus','egrave','underscore','ccedilla',
                         'agrave','parenright','equal','BackSpace','Num_Lock',
                         'slash','asterisk','a','z','e','r','t','y','u',
                         'i','o','p','Multi_key','dollar','7','8','9','plus',
                         'Caps_Lock','q','s','d','f','g','h','j','k','l','m',
                         'ugrave','Return','4','5','6','3','2','1','Shift_R',
                         'exclam','colon','semicolon','comma','n','b','v','c',
                         'x','w','less','Shift_L','Control_L','Alt_L','space',
                         'Alt_R','App','Control_R','Up','0','period','Left','Down','Right']
        nicknames = {"ampersand":"&","eacute":"é","quotedbl":'"',"quoteright":"'",
                     "parenleft":"(","minus":"-","egrave":"è","underscore":"_",
                     "ccedilla":"ç","agrave":"à","parenright":")","equal":"=",
                     "slash":"/","asterisk":"*","Multi_key":"^","dollar":"$",
                     "plus":"+","ugrave":"ù","exclam":"!","colon":":",
                     "semicolon":";","coma":",","less":"<"}
        
        def check_nick(keysym):
            if keysym in list(nicknames.keys()) :
                return (nicknames[keysym])
            else :
                return (keysym)
        
        def get_widget_but(action):
            out = None
            if action == "spin_u" :
                out = spin_u_but
            elif action == "spin_d" :
                out = spin_d_but
            elif action == "spin_v_u" :
                out = spin_v_u_but
            elif action == "spin_v_d" :
                out = spin_v_d_but
            elif action == "spin_reset_col" :
                out = spin_reset_col_but
            elif action == "vit_plus" :
                out = vitesse_plus_but
            elif action == "vit_moins" :
                out = vitesse_moins_but
            elif action == "reset_trip_selec" :
                out = reset_trip_selec_but
            return (out)
        
        def get_bind_callback(action):
            out = None
            if action == "spin_u" :
                out = go_up
            elif action == "spin_d" :
                out = go_down
            elif action == "spin_v_u" :
                out = value_up
            elif action == "spin_v_d" :
                out = value_down
            elif action == "spin_reset_col" :
                out = reset_spin_selec
            elif action == "vit_plus" :
                out = vitesse_plus
            elif action == "vit_moins" :
                out = vitesse_moins
            elif action == "reset_trip_selec" :
                out = reset_trip_selec
            return (out)
        
        def update_aff():
            for bind in list(raccourcis.keys()) :
                get_widget_but(bind).configure(text=check_nick(raccourcis[bind]))
        
        def blink(widget_list, nb_repet, delay, color="light pink"):
            for i in range(nb_repet) :
                for widget in widget_list :
                    widget.configure(bg=color)
                    widget.update()
                sleep(delay/1000)
                for widget in widget_list :
                    widget.configure(bg="SystemButtonFace")
                    widget.update()
                sleep(delay/1000)
        
        def change_bind(action):
            def in_raccourcis(key, fen):
                out = False
                info = None
                
                for bind in list(raccourcis.keys()) :
                    if key == raccourcis[bind] :
                        out = True
                        info = "{}".format(bind)
                        break
                
                return (out, info)
            
            def fonc_get_key(event):
                touche = event.keysym
                
                if touche in possible_keys :
                    cond, info = in_raccourcis(touche, action)
                    if cond == False :
                        root.unbind("<Key-{}>".format(raccourcis[action]))
                        raccourcis[action] = touche
                        root.bind("<Key-{}>".format(raccourcis[action]),
                                      get_bind_callback(action))
                        update_aff()
                        blink([get_widget_but(action)],1,500,"light green")
                        save_config()
                    else :
                        blink([get_widget_but(action), get_widget_but(info)],10,50)
                
                fen_binds.unbind("<Key>")
            fen_binds.bind("<Key>", fonc_get_key)
        
        def bind_vit_plus():
            change_bind("vit_plus")
        def bind_vit_moins():
            change_bind("vit_moins")
        def bind_spin_u():
            change_bind("spin_u")
        def bind_spin_d():
            change_bind("spin_d")
        def bind_spin_v_u():
            change_bind("spin_v_u")
        def bind_spin_v_d():
            change_bind("spin_v_d")
        def bind_spin_reset_col():
            change_bind("spin_reset_col")
        def bind_reset_trip_selec():
            change_bind("reset_trip_selec")
        
        vit_plus_lab = tk.Label(fen_binds,text=Loc_Data["10.10"],font="Helvetica {}".format(taille_police))
        vit_moins_lab = tk.Label(fen_binds,text=Loc_Data["10.11"],font="Helvetica {}".format(taille_police))
        spin_u_lab = tk.Label(fen_binds,text=Loc_Data["10.12"],font="Helvetica {}".format(taille_police))
        spin_d_lab = tk.Label(fen_binds,text=Loc_Data["10.14"],font="Helvetica {}".format(taille_police))
        spin_v_u_lab = tk.Label(fen_binds,text=Loc_Data["10.16"],
                                font="Helvetica {}".format(taille_police))
        spin_v_d_lab = tk.Label(fen_binds,text=Loc_Data["10.17"],
                                font="Helvetica {}".format(taille_police))
        spin_reset_col_lab = tk.Label(fen_binds,text=Loc_Data["10.18"],
                                      font="Helvetica {}".format(taille_police))
        reset_trip_selec_lab = tk.Label(fen_binds,text=Loc_Data["10.22"],
                                        font="Helvetica {}".format(taille_police))
        vit_plus_lab.grid(column=0, row=0)
        vit_moins_lab.grid(column=0, row=1)
        spin_u_lab.grid(column=0, row=2)
        spin_d_lab.grid(column=0, row=3)
        spin_v_u_lab.grid(column=0, row=4)
        spin_v_d_lab.grid(column=0, row=5)
        spin_reset_col_lab.grid(column=0, row=6)
        reset_trip_selec_lab.grid(column=0, row=7)
        
        if mode == "remap" :
            vitesse_plus_but = tk.Button(fen_binds,font="Helvetica {}".format(taille_police),
                                   command=bind_vit_plus)
            vitesse_moins_but = tk.Button(fen_binds,font="Helvetica {}".format(taille_police),
                                   command=bind_vit_moins)
            
            spin_u_but = tk.Button(fen_binds,font="Helvetica {}".format(taille_police),
                                   command=bind_spin_u)
            spin_d_but = tk.Button(fen_binds,font="Helvetica {}".format(taille_police),
                                   command=bind_spin_d)
            spin_v_u_but = tk.Button(fen_binds,font="Helvetica {}".format(taille_police),
                                   command=bind_spin_v_u)
            spin_v_d_but = tk.Button(fen_binds,font="Helvetica {}".format(taille_police),
                                   command=bind_spin_v_d)
            spin_reset_col_but = tk.Button(fen_binds,font="Helvetica {}".format(taille_police),
                                   command=bind_spin_reset_col)
            reset_trip_selec_but = tk.Button(fen_binds,font="Helvetica {}".format(taille_police),
                                             command=bind_reset_trip_selec)
        elif mode == "map" :
            vitesse_plus_but = tk.Label(fen_binds,font="Helvetica {}".format(taille_police))
            vitesse_moins_but = tk.Label(fen_binds,font="Helvetica {}".format(taille_police))
            spin_u_but = tk.Label(fen_binds,font="Helvetica {}".format(taille_police))
            spin_d_but = tk.Label(fen_binds,font="Helvetica {}".format(taille_police))
            spin_v_u_but = tk.Label(fen_binds,font="Helvetica {}".format(taille_police))
            spin_v_d_but = tk.Label(fen_binds,font="Helvetica {}".format(taille_police))
            spin_reset_col_but = tk.Label(fen_binds,font="Helvetica {}".format(taille_police))
            reset_trip_selec_but = tk.Label(fen_binds,font="Helvetica {}".format(taille_police))
        
        vitesse_plus_but.grid(column=1, row=0)
        vitesse_moins_but.grid(column=1, row=1)
        spin_u_but.grid(column=1, row=2)
        spin_d_but.grid(column=1, row=3)
        spin_v_u_but.grid(column=1, row=4)
        spin_v_d_but.grid(column=1, row=5)
        spin_reset_col_but.grid(column=1, row=6)
        reset_trip_selec_but.grid(column=1, row=7)
        
        update_aff()
        
        Utils.center_(fen_binds)
        
        fen_binds.transient(root)
        fen_binds.wait_visibility()
        fen_binds.grab_set()
        fen_binds.wait_window()
    
    def modif_colors():
        fen_colors = tk.Toplevel(root)
        fen_colors.title(Loc_Data["18.1"])
        
        class select_color_canvas():
            def update_color(self):
                if self.palette == "trip" :
                    self.canvas.configure(bg=Triplets_State_Colors[self.state])
                elif self.palette == "comm" :
                    self.canvas.configure(bg=Comm_State_Colors[self.state])
            
            def select_color(self, *args):
                global Comm_State_Colors, Triplets_State_Colors
                if self.palette == "trip" :
                    dico = {
                        "not_curated" : Loc_Data["18.3"],
                        "curated" : Loc_Data["18.4"],
                        "ignored" : Loc_Data["18.5"]
                    }
                    titre = "{} {}".format(Loc_Data["18.2"], dico[self.state])
                    new_color = colorchooser.askcolor(parent=fen_colors,
                                                      initialcolor=Triplets_State_Colors[self.state],
                                                      title=titre)
                    if new_color[1] != None :
                        Triplets_State_Colors[self.state] = new_color[1]
                        self.canvas.configure(bg=Triplets_State_Colors[self.state])
                elif self.palette == "comm" :
                    dico = {
                        "not_labeled" : Loc_Data["18.7"],
                        "labeled" : Loc_Data["18.8"],
                        "odd" : Loc_Data["18.9"]
                    }
                    titre = "{} {}".format(Loc_Data["18.6"], dico[self.state])
                    new_color = colorchooser.askcolor(parent=fen_colors,
                                                      initialcolor=Comm_State_Colors[self.state],
                                                      title=titre)
                    if new_color[1] != None :
                        Comm_State_Colors[self.state] = new_color[1]
                        self.canvas.configure(bg=Comm_State_Colors[self.state])
            
            def __init__(self, parent, width, height, state, grid_infos):
                self.state = state
                
                if state in ["not_labeled", "labeled", "odd"] :
                    self.palette = "comm"
                elif state in ["not_curated", "curated", "ignored"] :
                    self.palette = "trip"
                
                self.canvas = tk.Canvas(parent, width=width, height=height)
                if self.palette == "trip" :
                    self.canvas.configure(bg=Triplets_State_Colors[state])
                elif self.palette == "comm" :
                    self.canvas.configure(bg=Comm_State_Colors[state])
                
                self.canvas.grid(column=grid_infos[0], row=grid_infos[1])
                self.canvas.bind("<ButtonPress>", self.select_color)
        
        def escape_apply(*args):
            save_config()
            users_visual.update_comm()
            heatmap_wrapper()
            similarity_prog.update_aff()
            root.update()
            fen_colors.destroy()
        
        comm_state_frame = tk.LabelFrame(fen_colors, text=Loc_Data["18.10"],
                                         font="Helvetica {} bold".format(taille_police))
        not_labeled_label = tk.Label(comm_state_frame, text=Loc_Data["18.11"],
                                     font="Helvetica {}".format(taille_police))
        labeled_label = tk.Label(comm_state_frame, text=Loc_Data["18.12"],
                                     font="Helvetica {}".format(taille_police))
        odd_label = tk.Label(comm_state_frame, text=Loc_Data["18.13"],
                                     font="Helvetica {}".format(taille_police))
        comm_state_frame.grid(column=0, row=0, sticky="ns")
        not_labeled_label.grid(column=0, row=0)
        labeled_label.grid(column=0, row=1)
        odd_label.grid(column=0, row=2)
        not_labeled_col = select_color_canvas(comm_state_frame, 90, 25, "not_labeled", (1,0))
        labeled_col = select_color_canvas(comm_state_frame, 90, 25, "labeled", (1,1))
        odd_col = select_color_canvas(comm_state_frame, 90, 25, "odd", (1,2))
        
        trip_state_frame = tk.LabelFrame(fen_colors, text=Loc_Data["18.14"],
                                         font="Helvetica {} bold".format(taille_police))
        trip_state_frame.grid(column=0, row=1, sticky="ns")
        not_curated_label = tk.Label(trip_state_frame, text=Loc_Data["18.15"],
                                     font="Helvetica {}".format(taille_police))
        curated_label = tk.Label(trip_state_frame, text=Loc_Data["18.16"],
                                     font="Helvetica {}".format(taille_police))
        ignored_label = tk.Label(trip_state_frame, text=Loc_Data["18.17"],
                                     font="Helvetica {}".format(taille_police))
        not_curated_label.grid(column=0, row=0)
        curated_label.grid(column=0, row=1)
        ignored_label.grid(column=0, row=2)
        not_curated_col = select_color_canvas(trip_state_frame, 90, 25, "not_curated", (1,0))
        curated_col = select_color_canvas(trip_state_frame, 90, 25, "curated", (1,1))
        ignored_col = select_color_canvas(trip_state_frame, 90, 25, "ignored", (1,2))
        
        def selec_color(*args):
            global Heatmap_Colors
            color_id = int(color_selec_scale.get())-1
            if color_id <= len(Heatmap_Colors)-1 :
                color_init = Heatmap_Colors[color_id]
                titre = "{} {}".format(Loc_Data["18.18"], color_init)
            elif color_id == len(Heatmap_Colors) :
                color_init = None
                titre = Loc_Data["18.19"]
            new_color = colorchooser.askcolor(parent=fen_colors,
                                              initialcolor=color_init,
                                              title=titre)
            if new_color[1] != None :
                if color_init != None :
                    Heatmap_Colors[color_id] = new_color[1]
                else :
                    Heatmap_Colors.append(new_color[1])
                    color_selec_canvas.delete("texte")
                    info_label.configure(text="{} {}".format(Loc_Data["18.20"], len(Heatmap_Colors)))
                color_selec_canvas.configure(bg=Heatmap_Colors[color_id])
                if len(Heatmap_Colors) > 2 :
                    color_suppr_but.configure(state="active")
            
            save_config()
        
        def selec_scale_wrapper(value):
            value = int(value)
            if value <= len(Heatmap_Colors) :
                color_selec_canvas.configure(bg=Heatmap_Colors[int(value)-1])
                color_selec_canvas.delete("texte")
            else :
                color_selec_canvas.configure(bg="SystemButtonFace")
                color_selec_canvas.create_text((200,30), text="("+Loc_Data["18.21"]+")",
                                               font="Helvetica {}".format(taille_police), tags=("texte"))
        def arrow_selec_wrapper(side):
            value = color_selec_scale.get()
            if side == "L" and value > 1 :
                value -= 1
            elif side == "R" and value <= len(Heatmap_Colors)+1 :
                value += 1
            if value == len(Heatmap_Colors)+1 :
                color_selec_scale.configure(to=len(Heatmap_Colors)+1)
                color_selec_scale.set(value)
            elif value == len(Heatmap_Colors) and color_selec_scale["to"] == len(Heatmap_Colors)+1 :
                color_selec_scale.configure(to=len(Heatmap_Colors))
                color_selec_scale.set(value)
            else :
                color_selec_scale.set(value)
        def arrow_left_wrapper(*args):
            arrow_selec_wrapper("L")
        def arrow_right_wrapper(*args):
            arrow_selec_wrapper("R")
        
        def suppr_color():
            global Heatmap_Colors
            color_id = color_selec_scale.get()-1
            Heatmap_Colors.remove(Heatmap_Colors[color_id])
            color_selec_scale.configure(to=len(Heatmap_Colors))
            info_label.configure(text="{} : {}".format(Loc_Data["18.20"], len(Heatmap_Colors)))
            if color_id == len(Heatmap_Colors) :
                color_id -= 1
            color_selec_canvas.configure(bg=Heatmap_Colors[color_id])
            if len(Heatmap_Colors) == 2 :
                color_suppr_but.configure(state="disabled")
        
        heat_frame = tk.LabelFrame(fen_colors, text=Loc_Data["18.22"],
                                   font="Helvetica {} bold".format(taille_police))
        info_label = tk.Label(heat_frame, text="{} {}".format(Loc_Data["18.20"], len(Heatmap_Colors)),
                              font="Helvetica {}".format(taille_police))
        color_selec_scale = tk.Scale(heat_frame, orient="horizontal", length=400,
                                     resolution=1, from_=1, to=len(Heatmap_Colors),
                                     showvalue=False, tickinterval=1,
                                     command=selec_scale_wrapper)
        color_selec_scale.set(1)
        color_selec_canvas = tk.Canvas(heat_frame, width=400, height=60,
                                       bg=Heatmap_Colors[color_selec_scale.get()-1])
        color_suppr_but = tk.Button(heat_frame, text=Loc_Data["18.23"],
                                font="Helvetica {}".format(taille_police),
                                command=suppr_color)
        heat_frame.grid(column=1, row=0, rowspan=2, sticky="ns")
        info_label.grid(column=0, row=0)
        color_selec_scale.grid(column=0, row=1)
        color_selec_canvas.grid(column=0, row=2)
        color_suppr_but.grid(column=0, row=3)
        
        def reset_colors():
            global Heatmap_Colors, Comm_State_Colors, Triplets_State_Colors
            Comm_State_Colors = {
                "not_labeled" : "grey",
                "labeled" : "green",
                "odd" : "red"
            }
            not_labeled_col.update_color()
            labeled_col.update_color()
            odd_col.update_color()
            
            Triplets_State_Colors = {
                "not_curated" : "grey",
                "curated" : "green",
                "ignored" : "red"
            }
            not_curated_col.update_color()
            curated_col.update_color()
            ignored_col.update_color()
            
            Heatmap_Colors = ["#ff0000", "purple", "pink", "saddlebrown", "gold2", "#00c000"]
            color_selec_scale.set(1)
            color_selec_canvas.configure(bg=Heatmap_Colors[0])
            color_selec_scale.configure(to=len(Heatmap_Colors))
            info_label.configure(text="{} {}".format(Loc_Data["18.20"], len(Heatmap_Colors)))
            color_suppr_but.configure(state="active")
            
            save_config()
            fen_colors.update()
        
        reset_but = tk.Button(fen_colors, text=Loc_Data["18.24"],
                              font="Helvetica {}".format(taille_police),
                              command=reset_colors)
        reset_but.grid(column=0, row=2, columnspan=2, sticky="we")
        
        Utils.center_(fen_colors)
        
        fen_colors.protocol("WM_DELETE_WINDOW", escape_apply)
        fen_colors.bind("<Right>", arrow_right_wrapper)
        fen_colors.bind("<Left>", arrow_left_wrapper)
        color_selec_canvas.bind("<ButtonPress>", selec_color)
        
        fen_colors.transient(root)
        fen_colors.wait_visibility()
        fen_colors.grab_set()
        fen_colors.wait_window()
    
    menu_params = tk.Menu(menubar)
    menu_params.add_command(label=Loc_Data["8.2"], command=changer_taille_police)
    menu_params.add_separator()
    menu_params.add_command(label=Loc_Data["8.3"], command=remap_binds)
    menu_params.add_separator()
    menu_params.add_command(label=Loc_Data["8.13"], command=modif_colors)
    menubar.add_cascade(menu=menu_params, label=Loc_Data["8.1"])
    
    def ungrid():
        pad_label.grid_forget()
        
        aspect_frame.grid_forget()
        aspect["debut"].grid_forget()
        aspect["long"].grid_forget()
        aspect_visual.grid_forget()
        opinion_frame.grid_forget()
        opinion["debut"].grid_forget()
        opinion["long"].grid_forget()
        opinion_visual.grid_forget()
        spin["aspect_debut"].grid_forget()
        spin["aspect_L"].grid_forget()
        spin["opinion_debut"].grid_forget()
        spin["opinion_L"].grid_forget()
        sentiment_frame.grid_forget()
        sentiment["negatif"].grid_forget()
        sentiment["neutre"].grid_forget()
        sentiment["positif"].grid_forget()
        plus_vite.grid_forget()
        bouton_moins.grid_forget()
        label_vitesse.grid_forget()
        bouton_plus.grid_forget()
        aspect_selection.grid_forget()
        reset_aspect_but.grid_forget()
        opinion_selection.grid_forget()
        reset_opinion_but.grid_forget()
        emergency_aspect["term_label"].grid_forget()
        emergency_aspect["term_entry"].grid_forget()
        emergency_aspect["id_label"].grid_forget()
        emergency_aspect["id_entry"].grid_forget()
        emergency_opinion["term_label"].grid_forget()
        emergency_opinion["term_entry"].grid_forget()
        emergency_opinion["id_label"].grid_forget()
        emergency_opinion["id_entry"].grid_forget()
        emergency_visual.grid_forget()
        pad_label_for_mode2.grid_forget()
    
    def update_aff_widget_curator(ignore_indexes_reset=True, *args):
        if ignore_indexes_reset == True :
            aspect["L"].set(1)
            aspect["i_debut"].set(-1)
            opinion["L"].set(1)
            opinion["i_debut"].set(-1)
            aspect_value = "{"+Loc_Data["7.2"]+"}"
            opinion_value = "{"+Loc_Data["7.3"]+"}"
            aspect_visual.configure(text=aspect_value)
            opinion_visual.configure(text=opinion_value)
        comm_visuel.tag_remove("aspect", "1.0", "end")
        comm_visuel.tag_remove("opinion", "1.0", "end")
        comm_visuel.tag_add("normal", "1.0", "end")
        
        dic_spin = {"0" : "aspect_debut",
                    "1" : "aspect_L",
                    "2" : "opinion_debut",
                    "3" : "opinion_L"}
        for pos in list(dic_spin.keys()) :
            key = dic_spin[pos]
            spin[key].configure(fg="SystemWindowText")
            spin[key].configure(font="TkTextFont")
        
        ungrid()
        radio_create_curator_trip.grid_forget()
        if user_selec_triplet.get() == "Curateur" :
            if interaction_spin.get() == 0 :
                if mode_vertical.get() == True :
                    radio_create_curator_trip.grid(column=0, row=0)
                else :
                    radio_create_curator_trip.grid(column=0, row=0, columnspan=3)
                
                aspect_frame.grid(column=0, row=1, sticky="we")
                aspect["debut"].grid(column=0, row=0)
                aspect["long"].grid(column=0, row=1)
                aspect_visual.grid(column=0, row=2, columnspan=2)
                
                if mode_vertical.get() == True :
                    opinion_frame.grid(column=0, row=2, sticky="we")
                else :
                    opinion_frame.grid(column=1, row=1, sticky="we")
                opinion["debut"].grid(column=0, row=0)
                opinion["long"].grid(column=0, row=1)
                opinion_visual.grid(column=0, row=2, columnspan=2)
                
                spin["aspect_debut"].grid(column=1, row=0)
                spin["aspect_L"].grid(column=1, row=1)
                spin["opinion_debut"].grid(column=1, row=0)
                spin["opinion_L"].grid(column=1, row=1)
                spin["aspect_debut"]["takefocus"] = True
                spin["aspect_L"]["takefocus"] = True
                spin["opinion_debut"]["takefocus"] = True
                spin["opinion_L"]["takefocus"] = True
                spin["aspect_debut"]["state"] = "normal"
                spin["aspect_L"]["state"] = "normal"
                spin["opinion_debut"]["state"] = "normal"
                spin["opinion_L"]["state"] = "normal"
                
                if mode_vertical.get() == True :
                    sentiment_frame.grid(column=0, row=3, sticky="we")
                    sentiment["negatif"].grid(column=0, row=0)
                    sentiment["neutre"].grid(column=0, row=1)
                    sentiment["positif"].grid(column=0, row=2)
                else :
                    sentiment_frame.grid(column=0, row=2, columnspan=2, sticky="we")
                    sentiment["negatif"].grid(column=0, row=0)
                    sentiment["neutre"].grid(column=1, row=0)
                    sentiment["positif"].grid(column=2, row=0)
            
            elif interaction_spin.get() == 1 :
                if mode_vertical.get() == True :
                    radio_create_curator_trip.grid(column=0, row=0, columnspan=2)
                else :
                    radio_create_curator_trip.grid(column=0, row=0, columnspan=4)
                
                aspect_frame.grid(column=0, row=1, columnspan=2, sticky="we")
                aspect["debut"].grid(column=0, row=0)
                aspect["long"].grid(column=0, row=1)
                aspect_visual.grid(column=0, row=2, columnspan=2)
                
                if mode_vertical.get() == True :
                    opinion_frame.grid(column=0, row=2, columnspan=2, sticky="we")
                else :
                    opinion_frame.grid(column=2, row=1, columnspan=2, sticky="we")
                opinion["debut"].grid(column=0, row=0)
                opinion["long"].grid(column=0, row=1)
                opinion_visual.grid(column=0, row=2, columnspan=2)
                
                spin["aspect_debut"].grid(column=1, row=0)
                spin["aspect_L"].grid(column=1, row=1)
                spin["opinion_debut"].grid(column=1, row=0)
                spin["opinion_L"].grid(column=1, row=1)
                spin["aspect_debut"]["takefocus"] = False
                spin["aspect_L"]["takefocus"] = False
                spin["opinion_debut"]["takefocus"] = False
                spin["opinion_L"]["takefocus"] = False
                spin["aspect_debut"]["state"] = "readonly"
                spin["aspect_L"]["state"] = "readonly"
                spin["opinion_debut"]["state"] = "readonly"
                spin["opinion_L"]["state"] = "readonly"
                
                if mode_vertical.get() == True :
                    sentiment_frame.grid(column=0, row=3, sticky="we")
                    sentiment["negatif"].grid(column=0, row=0)
                    sentiment["neutre"].grid(column=0, row=1)
                    sentiment["positif"].grid(column=0, row=2)
                else :
                    sentiment_frame.grid(column=0, row=2, columnspan=2, sticky="we")
                    sentiment["negatif"].grid(column=0, row=0)
                    sentiment["neutre"].grid(column=1, row=0)
                    sentiment["positif"].grid(column=2, row=0)
                
                if mode_vertical.get() == True :
                    plus_vite.grid(column=1, row=3, sticky="nswe")
                else :
                    plus_vite.grid(column=2, row=2, columnspan=2, sticky="nswe")
                bouton_moins.grid(column=0, row=0)
                label_vitesse.grid(column=1, row=0)
                bouton_plus.grid(column=2, row=0)
            
            elif interaction_spin.get() == 2 :
                radio_create_curator_trip.grid(column=0, row=0, columnspan=2)
                
                aspect_frame.grid(column=0, row=1, sticky="we")
                aspect_selection.grid(column=0, row=0)
                reset_aspect_but.grid(column=0, row=1, columnspan=2)
                aspect_visual.grid(column=0, row=2, columnspan=2)
                
                if mode_vertical.get() == True :
                    opinion_frame.grid(column=0, row=2, sticky="we")
                else :
                    opinion_frame.grid(column=1, row=1, sticky="we")
                opinion_selection.grid(column=0, row=0)
                reset_opinion_but.grid(column=0, row=1, columnspan=2)
                opinion_visual.grid(column=0, row=2, columnspan=2)
                
                if mode_vertical.get() == True :
                    sentiment_frame.grid(column=0, row=3, sticky="we")
                    sentiment["negatif"].grid(column=0, row=0)
                    sentiment["neutre"].grid(column=0, row=1)
                    sentiment["positif"].grid(column=0, row=2)
                else :
                    sentiment_frame.grid(column=0, row=2, columnspan=2, sticky="we")
                    sentiment["negatif"].grid(column=0, row=0)
                    sentiment["neutre"].grid(column=1, row=0)
                    sentiment["positif"].grid(column=2, row=0)
                
                if mode_vertical.get() == True :
                    pad_label_for_mode2.grid(column=1, row=0, rowspan=4)
            
            elif interaction_spin.get() == 3 :
                radio_create_curator_trip.grid(column=0, row=0)
                
                aspect_frame.grid(column=0, row=1, sticky="we")
                emergency_aspect["term_label"].grid(column=0, row=0)
                emergency_aspect["term_entry"].grid(column=1, row=0)
                emergency_aspect["id_label"].grid(column=0, row=1)
                emergency_aspect["id_entry"].grid(column=1, row=1)
                
                if mode_vertical.get() == True :
                    opinion_frame.grid(column=0, row=2, sticky="we")
                else :
                    opinion_frame.grid(column=1, row=1, sticky="we")
                emergency_opinion["term_label"].grid(column=0, row=0)
                emergency_opinion["term_entry"].grid(column=1, row=0)
                emergency_opinion["id_label"].grid(column=0, row=1)
                emergency_opinion["id_entry"].grid(column=1, row=1)
                
                if mode_vertical.get() == True :
                    sentiment_frame.grid(column=0, row=3, sticky="we")
                    sentiment["negatif"].grid(column=0, row=0)
                    sentiment["neutre"].grid(column=0, row=1)
                    sentiment["positif"].grid(column=0, row=2)
                else :
                    sentiment_frame.grid(column=0, row=2, sticky="we")
                    sentiment["negatif"].grid(column=0, row=0)
                    sentiment["neutre"].grid(column=1, row=0)
                    sentiment["positif"].grid(column=2, row=0)
                
                if mode_vertical.get() == True :
                    emergency_visual.grid(column=0, row=4, sticky="we")
                    emergency_visual.configure(wraplength=385)
                else :
                    emergency_visual.grid(column=1, row=2, sticky="we")
                    emergency_visual.configure(wraplength=400)
        else :
            radio_create_curator_trip.grid(column=0, row=0)
            pad_label.grid(column=0, row=1)
        if interaction_spin.get() == 3 and user_selec_triplet.get() == "Curateur" :
            root.unbind("<Key-{}>".format(raccourcis["spin_u"]))
            root.unbind("<Key-{}>".format(raccourcis["spin_d"]))
            root.unbind("<Key-{}>".format(raccourcis["spin_v_u"]))
            root.unbind("<Key-{}>".format(raccourcis["spin_v_d"]))
            root.unbind("<Key-{}>".format(raccourcis["spin_reset_col"]))
            root.unbind("<Key-{}>".format(raccourcis["vit_plus"]))
            root.unbind("<Key-{}>".format(raccourcis["vit_moins"]))
            root.unbind("<Key-{}>".format(raccourcis["reset_trip_selec"]))
        else :
            valid_trip_but["state"] = "active"
            root.bind("<Key-{}>".format(raccourcis["spin_u"]), go_up)
            root.bind("<Key-{}>".format(raccourcis["spin_d"]), go_down)
            root.bind("<Key-{}>".format(raccourcis["spin_v_u"]), value_up)
            root.bind("<Key-{}>".format(raccourcis["spin_v_d"]), value_down)
            root.bind("<Key-{}>".format(raccourcis["spin_reset_col"]), reset_spin_selec)
            root.bind("<Key-{}>".format(raccourcis["vit_plus"]), vitesse_plus)
            root.bind("<Key-{}>".format(raccourcis["vit_moins"]), vitesse_moins)
            root.bind("<Key-{}>".format(raccourcis["reset_trip_selec"]), reset_trip_selec)
        save_config()
    
    def update_aff_vertical(*args):
        users_frame.grid_forget()
        curator_frame.grid_forget()
        if mode_vertical.get() == True :
            users_frame.grid(column=0, row=1, sticky="nswe")
        else :
            users_frame.grid(column=0, row=1, columnspan=2, sticky="nswe")
        if mode_vertical.get() == True :
            curator_frame.grid(column=1, row=1, sticky="nswe")
        else :
            curator_frame.grid(column=0, row=2, columnspan=2, sticky="nswe")
        
        save_config()
        users_visual.update_aff()
        update_aff_widget_curator()
    
    menu_options = tk.Menu(menubar)
    menu_options.add_radiobutton(label=Loc_Data["8.5"], variable=interaction_spin,
                                 value=0, command=update_aff_widget_curator)
    menu_options.add_radiobutton(label=Loc_Data["8.6"], variable=interaction_spin,
                                 value=1, command=update_aff_widget_curator)
    menu_options.add_radiobutton(label=Loc_Data["8.7"], variable=interaction_spin,
                                 value=2, command=update_aff_widget_curator)
    menu_options.add_radiobutton(label=Loc_Data["8.8"], variable=interaction_spin,
                                 value=3, command=update_aff_widget_curator)
    menu_options.add_separator()
    menu_options.add_checkbutton(label=Loc_Data["8.14"], variable=mode_vertical, onvalue=True, offvalue=False,
                                 command=update_aff_vertical)
    menubar.add_cascade(menu=menu_options, label=Loc_Data["8.4"])
    
    def aff_map_bind():
        remap_binds(mode="map")
    
    menu_aide = tk.Menu(menubar)
    menu_aide.add_command(label=Loc_Data["8.10"], command=aff_map_bind)
    menubar.add_cascade(menu=menu_aide, label=Loc_Data["8.9"])
    
    #%% Fonction pour convertir indexe d'un mot (d'une liste) en indexe dans un texte (format ligne.colonne)
    
    def conversion(debut, L, portion=None, alt=False):
        deb, l = 0, 0
        
        for i in range(debut) :
            deb += len(mots[i])
            deb += decalage[i]
        deb += decalage[debut]
        
        l += len(mots[debut])
        if L > 1 :
            for i in range(1, L) :
                try :
                    l += len(mots[debut+i])
                    l += decalage[debut+i]
                except :
                    None
        
        if portion != None :
            sup = l%portion[0]
            l = int(l/portion[0])
            
            deb += l*(portion[1]-1)
            if portion[1] == portion[0] :
                l += sup
        
        i_deb, line_deb, i_fin, line_fin = deb,1,deb+l,1
        for i in range(len(carac_per_line)) :
            if carac_per_line[i] == 0 :
                line_deb += 1
                i_deb -= 1
            elif i_deb - carac_per_line[i] > 0 :
                i_deb -= carac_per_line[i] + 1
                line_deb += 1
            else :
                break
        
        for i in range(len(carac_per_line)) :
            if carac_per_line[i] == 0 :
                line_fin += 1
                i_fin -= 1
            elif i_fin - carac_per_line[i] > 0 :
                i_fin -= carac_per_line[i] + 1
                line_fin += 1
            else :
                break
        
        if alt == False :
            return (i_deb, line_deb, i_fin, line_fin)
        else :
            return (deb, l)
    
    def conversion_crop(index_word, croped_interval, croped_comm):
        deb, l = 0, len(mots[index_word])
        croped_carac_per_line = []
        c = 0
        for carac in croped_comm :
            if carac != "\n" :
                c += 1
            else :
                croped_carac_per_line.append(c)
                c = 0
        
        for i in range(index_word) :
            if i in croped_interval :
                deb += len(mots[i])
                if i != croped_interval[0] :
                    deb += decalage[i]
        deb += decalage[index_word]
        
        i_deb, line_deb, i_fin, line_fin = deb, 1, deb+l, 1
        for i in range(len(croped_carac_per_line)) :
            if croped_carac_per_line[i] == 0 :
                line_deb += 1
                i_deb -= 1
            elif i_deb - croped_carac_per_line[i] > 0 :
                i_deb -= croped_carac_per_line[i] + 1
                line_deb += 1
            else :
                break
        
        for i in range(len(croped_carac_per_line)) :
            if croped_carac_per_line[i] == 0 :
                line_fin += 1
                i_fin -= 1
            elif i_fin - croped_carac_per_line[i] > 0 :
                i_fin -= croped_carac_per_line[i] + 1
                line_fin += 1
            else :
                break
        
        return (i_deb, line_deb, i_fin, line_fin)
    
    #%% Affichage des triplets des annotateurs
    
    users_frame = tk.LabelFrame(root, text=Loc_Data["17.2"],
                                font="Helvetica {} bold".format(taille_police))
    if mode_vertical.get() == True :
        users_frame.grid(column=0, row=1, sticky="nswe")
    else :
        users_frame.grid(column=0, row=1, columnspan=2, sticky="nswe")
    
    user_selec_triplet = tk.StringVar(value="None")
    if curated_trips != [] :
        if type(curated_trips[triplet_similarity]) == tuple :
            user_selec_triplet.set(curated_trips[triplet_similarity][0])
        elif type(curated_trips[triplet_similarity]) == list :
            user_selec_triplet.set("Curateur")
    
    class scroll_frame():
        def update_aff(self):
            for i in range(self.nb_max) :
                if mode_vertical.get() == True :
                    self.users_info[Users[i]]["widget"].configure(width=50, height=7)
                else :
                    self.users_info[Users[i]]["widget"].configure(width=99, height=4)
                
                self.users_info[Users[i]]["frame"].grid_forget()
                self.users_info[Users[i]]["select"].grid_forget()
                self.users_info[Users[i]]["widget"].grid_forget()
                self.users_info[Users[i]]["frame"].unbind("<MouseWheel>")
                self.users_info[Users[i]]["widget"].unbind("<MouseWheel>")
            if self.allow_scroll == True :
                to = self.nb_aff
            else :
                to = self.nb_max
            for i in range(to) :
                self.users_info[Users[self.deb+i]]["frame"].grid(column=0, row=i)
                self.users_info[Users[self.deb+i]]["select"].grid(column=0, row=0)
                self.users_info[Users[self.deb+i]]["widget"].grid(column=1, row=0)
                self.users_info[Users[self.deb+i]]["frame"].bind("<MouseWheel>", self.MouseWheel_wrapper)
                # self.users_info[Users[self.deb+i]]["widget"].bind("<MouseWheel>", self.MouseWheel_wrapper)
        
        def MouseWheel_wrapper(self, event):
            if self.allow_scroll == True :
                sens = -event.delta/abs(event.delta)
                self.deb += sens
                if self.deb < 0 :
                    self.deb = 0
                elif self.deb > self.nb_max-self.nb_aff :
                    self.deb = self.nb_max-self.nb_aff
                self.scroll.set(self.deb)
        
        def scale_wrapper(self, *args):
            if self.allow_scroll == True :
                self.deb = self.scroll.get()
                self.update_aff()
        
        def update_comm(self):
            decalage_index_secu = 3
            index_mot_min = None
            index_mot_max = None
            for user in Users :
                if Triplet_actuel[user] != None :
                    value_min = min([_ for _ in Triplet_actuel[user][3] if _ != -1]+[_ for _ in Triplet_actuel[user][4] if _ != -1])
                    if index_mot_min == None :
                        index_mot_min = value_min
                    elif value_min < index_mot_min :
                        index_mot_min = value_min
                    value_max = max([_ for _ in Triplet_actuel[user][3] if _ != -1]+[_ for _ in Triplet_actuel[user][4] if _ != -1])
                    if index_mot_max == None :
                        index_mot_max = value_max
                    elif value_max > index_mot_max :
                        index_mot_max = value_max
            if index_mot_min != None :
                index_mot_min = max([0, index_mot_min-decalage_index_secu])
            if index_mot_max != None :
                index_mot_max = min([len(mots), index_mot_max+decalage_index_secu])
            
            for i in range(self.nb_max) :
                if id_curation in list(Users_Triplets[Users[i]].keys()) :
                    # commentaire labélisé
                    color = Comm_State_Colors["labeled"]
                elif Langue_Part.lower()+"-"+id_curation in Users_Oddities[Users[i]] :
                    # commentaire ignoré
                    color = Comm_State_Colors["odd"]
                else :
                    # commentaire non labélisé
                    color = Comm_State_Colors["not_labeled"]
                self.users_info[Users[i]]["frame"].configure(background=color)
                self.users_info[Users[i]]["select"].configure(background=color)
                self.users_info[Users[i]]["widget"]["state"] = "normal"
                self.users_info[Users[i]]["widget"].configure(bg="white")
                self.users_info[Users[i]]["frame"].configure(text=Users[i])
                
                if index_mot_min != None and index_mot_max != None :
                    deb, l = conversion(index_mot_min, index_mot_max-index_mot_min+1, alt=True)
                    self.users_info[Users[i]]["widget"].replace("1.0", "end", comm[deb:deb+l])
                    self.users_info[Users[i]]["widget"].tag_add("normal", "1.0", "end")
                    if Triplet_actuel[Users[i]] != None :
                        for word in Triplet_actuel[Users[i]][3] :
                            if word != -1 :
                                i_deb, line_deb, i_fin, line_fin = conversion_crop(word, range(index_mot_min, index_mot_max+1), comm[deb:deb+l])
                                deb_ = "{}.{}".format(line_deb, i_deb)
                                end_ = "{}.{}".format(line_fin, i_fin)
                                self.users_info[Users[i]]["widget"].tag_add("aspect", deb_, end_)
                        for word in Triplet_actuel[Users[i]][4] :
                            if word != -1 :
                                i_deb, line_deb, i_fin, line_fin = conversion_crop(word, range(index_mot_min, index_mot_max+1), comm[deb:deb+l])
                                deb_ = "{}.{}".format(line_deb, i_deb)
                                end_ = "{}.{}".format(line_fin, i_fin)
                                self.users_info[Users[i]]["widget"].tag_add("opinion", deb_, end_)
                        # TODO : voir si les couleurs de fond des textes peuvent modifiées ou non
                        self.users_info[Users[i]]["frame"].configure(text=Users[i]+" ({})".format(Triplet_actuel[Users[i]][2]))
                        if Triplet_actuel[Users[i]][2] == "NEG" :
                            self.users_info[Users[i]]["widget"].configure(bg="#f8c7c8")
                        elif Triplet_actuel[Users[i]][2] == "NEU" :
                            self.users_info[Users[i]]["widget"].configure(bg="gray80")
                        elif Triplet_actuel[Users[i]][2] == "POS" :
                            self.users_info[Users[i]]["widget"].configure(bg="#9deca9")
                else :
                    self.users_info[Users[i]]["widget"].replace("1.0", "end", "")
                    self.users_info[Users[i]]["widget"].tag_add("normal", "1.0", "end")
                self.users_info[Users[i]]["widget"]["state"] = "disabled"
        
        def __init__(self, parent, nb_aff, string_var):
            self.deb = 0
            self.nb_aff = nb_aff
            self.nb_max = len(Users)
            
            self.string_var = string_var
            
            self.allow_scroll = True
            if self.nb_max <= self.nb_aff :
                self.allow_scroll = False
            
            self.parent = parent
            self.users_info = {}
            for i in range(self.nb_max) :
                self.users_info[Users[i]] = {}
                self.users_info[Users[i]]["frame"] = tk.LabelFrame(self.parent, text=Users[i],
                                                                   font="Helvetica {} bold".format(taille_police))
                self.users_info[Users[i]]["select"] = tk.Radiobutton(self.users_info[Users[i]]["frame"],
                                                                     variable=self.string_var, value=Users[i],
                                                                     command=update_aff_widget_curator,
                                                                     takefocus=False)
                self.users_info[Users[i]]["widget"] = tk.Text(self.users_info[Users[i]]["frame"],
                                                              wrap="word")
                self.users_info[Users[i]]["widget"].tag_configure("normal", font="Helvetica {}".format(taille_police_review))
                self.users_info[Users[i]]["widget"].tag_configure("aspect", foreground="orange",
                                                                  font="Helvetica {}".format(taille_police_review))
                self.users_info[Users[i]]["widget"].tag_configure("opinion", foreground="blue",
                                                                  font="Helvetica {}".format(taille_police_review))
            
            self.scroll = tk.Scale(parent, orient="vertical", from_=0, to=self.nb_max-self.nb_aff,
                                   showvalue=False, command=self.scale_wrapper)
            self.scroll.bind("<MouseWheel>", self.MouseWheel_wrapper)
            if self.allow_scroll == True :
                self.scroll.grid(column=1, row=0, rowspan=self.nb_aff, sticky="ns")
            self.update_aff()
    
    users_visual = scroll_frame(users_frame, 3, user_selec_triplet)
    users_visual.update_comm()
    
    bonus = Loc_Data["17.3"]
    if curated_comms[comm_ids_list.index(id_curation)] == 1 :
        bonus = Loc_Data["17.4"]
    comm_frame = tk.LabelFrame(root, text="{} {}-{} ({})".format(Loc_Data["7.5"], Langue_Part, id_curation, bonus),
                               font="Helevitca {} bold".format(taille_police))
    comm_frame.grid(column=2, row=0, rowspan=5, sticky="ns")
    
    comm_visuel = tk.Text(comm_frame, wrap="word", width=85, height=35)
    comm_visuel.tag_configure("normal", font="Helvetica {}".format(taille_police_review))
    comm_visuel.tag_configure("aspect", foreground="orange", font="Helvetica {}".format(taille_police_review))
    comm_visuel.tag_configure("opinion", foreground="blue", font="Helvetica {}".format(taille_police_review))
    comm_visuel.insert("1.0", comm)
    comm_visuel.tag_add("normal", "1.0", "end")
    comm_visuel["state"] = "disabled"
    
    def change_triplet_similarity(sens, force_set=None):
        global triplet_similarity
        if force_set == None :
            triplet_similarity += sens
            if triplet_similarity == -1 :
                triplet_similarity = len(curated_trips)-1
            elif triplet_similarity == len(curated_trips) :
                triplet_similarity = 0
        elif type(force_set) == int :
            triplet_similarity = force_set
        similarity_label.configure(text="{}/{}".format(triplet_similarity+1, len(curated_trips)))
        update_Trip_actuel(id_curation, triplet_similarity)
        users_visual.update_comm()
        heatmap_wrapper()
        similarity_prog.update_aff()
        
        default_curator_entries = True
        if type(curated_trips[triplet_similarity]) == tuple :
            user_selec_triplet.set(curated_trips[triplet_similarity][0])
        elif type(curated_trips[triplet_similarity]) == list :
            user_selec_triplet.set("Curateur")
            default_curator_entries = False
        elif curated_trips[triplet_similarity] == -1 :
            user_selec_triplet.set("Curateur")
        else :
            user_selec_triplet.set("None")
        update_aff_widget_curator(ignore_indexes_reset=False)
        
        comm_visuel.tag_remove("aspect", "1.0", "end")
        comm_visuel.tag_remove("opinion", "1.0", "end")
        comm_visuel.tag_add("normal", "1.0", "end")
        
        if default_curator_entries == True :
            aspect["L"].set(1)
            aspect["i_debut"].set(-1)
            opinion["L"].set(1)
            opinion["i_debut"].set(-1)
            
            aspect_value = "{"+Loc_Data["7.2"]+"}"
            opinion_value = "{"+Loc_Data["7.3"]+"}"
            aspect_visual.configure(text=aspect_value)
            opinion_visual.configure(text=opinion_value)
            reset_aspect()
            reset_opinion()
        else :
            # TODO : refaire le ré-affichage d'un triplet curateur déjà
            #        sélectionné avec le mode 3 (ne sélectionne pas les bons mots)
            aspect["L"].set(len(curated_trips[triplet_similarity][3]))
            aspect["i_debut"].set(curated_trips[triplet_similarity][3][0])
            opinion["L"].set(len(curated_trips[triplet_similarity][4]))
            opinion["i_debut"].set(curated_trips[triplet_similarity][4][0])
            
            if type(curated_trips[triplet_similarity][0]) == list :
                aspect_value = " ".join(curated_trips[triplet_similarity][0])
            else :
                aspect_value = curated_trips[triplet_similarity][0]
            if type(curated_trips[triplet_similarity][0]) == list :
                opinion_value = " ".join(curated_trips[triplet_similarity][1])
            else :
                opinion_value = curated_trips[triplet_similarity][1]
            aspect_visual.configure(text=aspect_value)
            opinion_visual.configure(text=opinion_value)
            
            modif_aspect()
            modif_opinion()
        
        unlock_valid_comm()
    
    def check_omited_is_edited():
        if -1 in curated_trips :
            if triplet_similarity != curated_trips.index(-1) :
                curated_trips.pop()
                change_triplet_similarity(0)
    
    def next_trip_wrapper(*args):
        change_triplet_similarity(1)
        check_omited_is_edited()
    def prev_trip_wrapper(*args):
        change_triplet_similarity(-1)
        check_omited_is_edited()
    
    class similarity_progression_meter():
        def __init__(self, parent, width, height, H):
            self.width = width
            self.height = height
            self.canvas = tk.Canvas(parent, width=width, height=height)
            self.H = H
            
        def grid_widget(self, column, row, columnspan):
            self.canvas.grid(column=column, row=row, columnspan=columnspan,
                             sticky="n")
        
        def update_aff(self):
            self.canvas.delete("selection_actuelle", "state_color")
            deca = 3
            num = len(curated_trips)
            if num != 0 :
                L = int((self.width+3)/num)
                for i in range(num) :
                    if i == triplet_similarity :
                        self.canvas.create_rectangle((i*L+3, 2, (i+1)*L, self.H),
                                                     fill="black", tags=("selection_actuelle"))
                    if curated_trips[i] in [0, -1] :
                        bg = Triplets_State_Colors["not_curated"]
                    elif curated_trips[i] == None :
                        bg = Triplets_State_Colors["ignored"]
                    else :
                        bg = Triplets_State_Colors["curated"]
                    self.canvas.create_rectangle((i*L+3+deca, 2+deca, (i+1)*L-deca, self.H-deca),
                                                 fill=bg, tags=("state_color"))
            
    similarity_prog = similarity_progression_meter(comm_frame, width=656, height=55, H=19)
    next_trip_but = tk.Button(comm_frame, text=Loc_Data["17.5"],
                              font="Helvetica {}".format(taille_police), command=next_trip_wrapper,
                              takefocus=False)
    prev_trip_but = tk.Button(comm_frame, text=Loc_Data["17.6"],
                              font="Helvetica {}".format(taille_police), command=prev_trip_wrapper,
                              takefocus=False)
    similarity_label = tk.Label(comm_frame, font="Helvetica {}".format(taille_police),
                                text="{}/{}".format(triplet_similarity+1, len(Triplets_Similarities[id_curation])))
    if curated_trips == [] :
        similarity_label.configure(text="{}/{}".format(0,0))
    
    comm_scrollbar = tk.Scrollbar(comm_frame, orient="vertical", command=comm_visuel.yview)
    comm_visuel.configure(yscrollcommand=comm_scrollbar.set)
    comm_visuel.grid(column=0, row=0, columnspan=3)
    comm_scrollbar.grid(column=3, row=0, sticky="ns")
    
    similarity_prog.grid_widget(column=0, row=1, columnspan=3)
    next_trip_but.grid(column=2, row=1, sticky="s")
    similarity_label.grid(column=1, row=1, sticky="s")
    prev_trip_but.grid(column=0, row=1, sticky="s")
    
    similarity_prog.update_aff()
    
    #%% Fonctionnalité heatmap pour la visualisation du commentaire en entier
    
    def heatmap_generator(users_triplet):
        # récupérer la liste des indexes de tous les mots utilisés
        word_count = {}
        for user in list(users_triplet.keys()) :
            if users_triplet[user] != None :
                for term in [3,4] :
                    for id_ in users_triplet[user][term] :
                        if id_ != -1 :
                            if str(id_) not in list(word_count.keys()) :
                                word_count[str(id_)] = 1
                            else :
                                word_count[str(id_)] += 1
        # tronquer les compteurs de chaque au nombre d'annotateurs (mesure de sécurité sinon crash)
        for id_ in list(word_count.keys()) :
            if word_count[id_] > len(Users) :
                word_count[id_] = len(Users)
        
        # définir les intervalles pour les couleurs
        colors_inter = []
        if len(Users) == 2 :
            colors_inter.append([1,2])
            colors_inter.append([2,3])
        
        elif len(Users) > 2 and len(Users) <= len(Heatmap_Colors)+1 :
            S = 1
            for i in range(len(Users)-2) :
                colors_inter.append([S, S+1])
                S += 1
            colors_inter.append([S, len(Users)+1])
        
        else :
            ratio = int(len(Users)/len(Heatmap_Colors))
            for i in range(len(Heatmap_Colors)) :
                S = 1
                if i != 0 :
                    S += i*ratio
                if i == len(Heatmap_Colors)-1 :
                    E = len(Users)+1
                else :
                    E = 1+(i+1)*ratio
                colors_inter.append([S, E])
        
        # définir la couleur de chaque indexe
        word_colors = {}
        for id_ in list(word_count.keys()) :
            if len(Users) == 2 :
                if word_count[id_] in range(colors_inter[0][0], colors_inter[0][1]) :
                    word_colors[id_] = 0
                elif word_count[id_] in range(colors_inter[1][0], colors_inter[1][1]) :
                    word_colors[id_] = len(Heatmap_Colors)-1
            else :
                for i in range(len(Heatmap_Colors)) :
                    if word_count[id_] in range(colors_inter[i][0], colors_inter[i][1]) :
                        word_colors[id_] = i
                        break
        
        # supprimer les anciennes couleurs de gradient dans le texte
        tags_to_ignore = ["normal","aspect","opinion","sel"]
        tags_to_delete = [tag for tag in comm_visuel.tag_names() if tag not in tags_to_ignore]
        for tag in tags_to_delete :
            comm_visuel.tag_remove(tag, "1.0", "end")
        comm_visuel.tag_delete(tags_to_delete)
        
        # créer les nouvelles couleurs
        for i in range(len(Heatmap_Colors)) :
            comm_visuel.tag_configure("heat{}".format(i), background=Heatmap_Colors[i])
        
        # appliquer les couleurs aux mots
        for id_ in list(word_colors.keys()) :
            i_deb, line_deb, i_fin, line_fin = conversion(int(id_), 1)
            color = "heat{}".format(word_colors[id_])
            id_deb = "{}.{}".format(line_deb, i_deb)
            id_fin = "{}.{}".format(line_fin, i_fin)
            comm_visuel.tag_add(color, id_deb, id_fin)
    
    class heatmap_widget():
        def __init__(self, parent, width, height):
            self.width = width
            self.height = height
            self.canvas = tk.Canvas(parent, width=width, height=height)
            
            self.H_text = 10
            self.H_num = 35
            self.H_color = 60
            self.W_text = 170
            self.W_deb = 10
            self.W_fin = 640
            
            self.canvas.grid(column=0, row=0)
        
        def draw_legend(self):
            self.canvas.create_text((self.W_text,self.H_text), text=Loc_Data["17.7"],
                                    font="Helevitca 12")
            self.canvas.create_text((self.W_deb, self.H_num), text="1", font="Helevitca {}".format(taille_police))
            self.canvas.create_text((self.W_fin, self.H_num), text=str(len(Users)), font="Helevitca {}".format(taille_police))
            
            if len(Users) == 2 :
                self.canvas.create_rectangle((self.W_deb, self.H_color, self.W_fin/2-10, self.height),
                                             fill=Heatmap_Colors[0])
                self.canvas.create_rectangle((self.W_fin/2+10, self.H_color, self.W_fin+5, self.height),
                                             fill=Heatmap_Colors[len(Heatmap_Colors)-1])
            
            elif len(Users) > 2 and len(Users) <= len(Heatmap_Colors)+1 :
                ratio = int((self.W_fin-self.W_deb)/(len(Users)-1))
                for i in range(1, len(Users)-1) :
                    self.canvas.create_text((self.W_deb+i*ratio, self.H_num), text=str(i+1), font="Helevitca {}".format(taille_police))
                    self.canvas.create_rectangle((self.W_deb+(i-1)*ratio, self.H_color, self.W_deb+i*ratio-30, self.height),
                                                 fill=Heatmap_Colors[i-1])
                self.canvas.create_rectangle((self.W_deb+(i)*ratio, self.H_color, self.W_fin+5, self.height),
                                             fill=Heatmap_Colors[i])
            
            elif len(Users) > len(Heatmap_Colors)+1 :
                ratio = int((self.W_fin-self.W_deb)/len(Heatmap_Colors))
                for i in range(1, len(Heatmap_Colors)) :
                    num = 1 + i*int(len(Users)/len(Heatmap_Colors))
                    self.canvas.create_text((self.W_deb+i*ratio, self.H_num), text=str(num), font="Helevitca {}".format(taille_police))
                    self.canvas.create_rectangle((self.W_deb+(i-1)*ratio, self.H_color, self.W_deb+i*ratio-30, self.height),
                                                 fill=Heatmap_Colors[i-1])
                self.canvas.create_rectangle((self.W_deb+(i)*ratio, self.H_color, self.W_fin+5, self.height),
                                             fill=Heatmap_Colors[i])
    
    def heatmap_wrapper(*args):
        heatmap_canvas.draw_legend()
        heatmap_generator(Triplet_actuel)
    
    heatmap_frame = tk.LabelFrame(comm_frame, text=Loc_Data["17.8"],
                                  font="Helevitca {} bold".format(taille_police))
    heatmap_frame.grid(column=0, row=2, columnspan=3)
    
    heatmap_canvas = heatmap_widget(heatmap_frame, width=656, height=61+15)
    heatmap_wrapper()
    
    #%% Fonctionnalité pour changer le commentaire à valider
    
    nb_comm_val = curated_comms.count(1)
    
    def change_id_curation(sens):
        global id_curation, curated_trips, triplet_similarity, comm, mots, decalage
        global review_lenght, carac_per_line, nb_comm_val, aspect_value, opinion_value
        
        temp = comm_ids_list.index(id_curation)
        new = temp+sens
        if new == -1 :
            new = len(comm_ids_list)-1
        elif new == len(comm_ids_list) :
            new = 0
        id_curation = comm_ids_list[new]
        triplet_similarity = 0
        comm = comms[id_curation]
        mots, decalage, review_lenght, carac_per_line = get_comm_plus(comm)
        update_Trip_actuel(id_curation, triplet_similarity)
        
        if curated_comms[comm_ids_list.index(id_curation)] == 1 :
            data = Utils.load_data(save_file+".HELPER_")
            curated_trips = []
            for line in data :
                if line.split("\|/")[0] == id_curation :
                    for element in line.split("\|/")[1:-1] :
                        if element == "None" :
                            curated_trips.append(None)
                        elif element[0] == "(" :
                            temp = element[1:-1].split(", ")
                            curated_trips.append((temp[0][1:-1], int(temp[1])))
                        elif element[0] == "[" :
                            curated_trips.append(str2trip(element))
                    break
        else :
            curated_trips = [0 for i in range(len(Triplets_Similarities[id_curation]))]
        
        if curated_trips != [] :
            if type(curated_trips[triplet_similarity]) == tuple :
                user_selec_triplet.set(curated_trips[triplet_similarity][0])
            elif type(curated_trips[triplet_similarity]) == list :
                user_selec_triplet.set("Curateur")
            else :
                user_selec_triplet.set("None")
            similarity_label.configure(text="{}/{}".format(triplet_similarity+1, len(Triplets_Similarities[id_curation])))
        else :
            user_selec_triplet.set("None")
            similarity_label.configure(text="{}/{}".format(0, 0))
        
        bonus = Loc_Data["17.3"]
        if curated_comms[comm_ids_list.index(id_curation)] == 1 :
            bonus = Loc_Data["17.4"]
        comm_frame.configure(text="{} {}-{} ({})".format(Loc_Data["7.5"], Langue_Part, id_curation, bonus))
        comm_visuel.tag_remove("aspect", "1.0", "end")
        comm_visuel.tag_remove("opinion", "1.0", "end")
        comm_visuel["state"] = "normal"
        comm_visuel.replace("1.0", "end", comm)
        comm_visuel["state"] = "disabled"
        comm_visuel.tag_add("normal", "1.0", "end")
        users_visual.update_comm()
        
        heatmap_wrapper()
        similarity_prog.update_aff()
        
        prog_lab.configure(text=Loc_Data["17.9"]+" : {}% ({}/{})".format(round(100*nb_comm_val/int(Info_for_validation["nb_comms"]),2),
                                                                         nb_comm_val, Info_for_validation["nb_comms"]))
        pos_label.configure(text=Loc_Data["17.10"]+" {}/{}".format(comm_ids_list.index(id_curation)+1,
                                                                   len(comm_ids_list)))
        
        for key in list(spin.keys()) :
            if "debut" in key :
                spin[key].configure(to=review_lenght["mots"]-1)
            else :
                spin[key].configure(to=review_lenght["mots"])
            spin[key].update()
        aspect["L"].set(1)
        aspect["i_debut"].set(-1)
        opinion["L"].set(1)
        opinion["i_debut"].set(-1)
        
        aspect_value = "{"+Loc_Data["7.2"]+"}"
        opinion_value = "{"+Loc_Data["7.3"]+"}"
        aspect_visual.configure(text=aspect_value)
        opinion_visual.configure(text=opinion_value)
        
        update_aff_widget_curator()
        
        valid_comm_but["state"] = "disabled"
    
    def but_moins_wrapper(*args):
        change_id_curation(-1)
    def but_plus_wrapper(*args):
        change_id_curation(1)
    
    parcours_frame = tk.LabelFrame(root, text=Loc_Data["17.11"],
                                   font="Helvetica {} bold".format(taille_police))
    parcours_frame.grid(column=0, row=0, columnspan=2)
    
    but_moins = tk.Button(parcours_frame, text="<", font="Helvetica 18 bold",
                          command=but_moins_wrapper, takefocus=False)
    prog_bar = tk.ttk.Progressbar(parcours_frame, orient="horizontal", length=550,
                                  mode="determinate", maximum=len(comm_ids_list))
    prog_bar["value"] = nb_comm_val
    prog_lab = tk.Label(parcours_frame, text=Loc_Data["17.9"]+" : {}% ({}/{})".format(round(100*nb_comm_val/int(Info_for_validation["nb_comms"]),2),
                                                                                      nb_comm_val, Info_for_validation["nb_comms"]),
                        font="Helevitca {}".format(taille_police), justify="center")
    pos_label = tk.Label(parcours_frame, text=Loc_Data["17.10"]+" {}/{}".format(comm_ids_list.index(id_curation)+1,
                                                                                len(comm_ids_list)),
                         font="Helevitca {}".format(taille_police), justify="center")
    but_plus = tk.Button(parcours_frame, text=">", font="Helvetica 18 bold",
                          command=but_plus_wrapper, takefocus=False)
    but_moins.grid(column=0, row=0, rowspan=3, padx=10, sticky="ns")
    prog_bar.grid(column=1, row=0)
    prog_lab.grid(column=1, row=1, sticky="we")
    pos_label.grid(column=1, row=2, sticky="we")
    but_plus.grid(column=2, row=0, rowspan=3, padx=10, sticky="ns")
    
    #%% Fonctionnalité pour entrer un triplet curateur si ceux des users ne convient pas
    
    curator_frame = tk.LabelFrame(root, text=Loc_Data["17.12"], font="Helvetica {} bold".format(taille_police))
    if mode_vertical.get() == True :
        curator_frame.grid(column=1, row=1, sticky="nswe")
    else :
        curator_frame.grid(column=0, row=2, columnspan=2, sticky="nswe")
    
    radio_create_curator_trip = tk.Radiobutton(curator_frame, text=Loc_Data["17.13"],
                                               font="Helvetica {}".format(taille_police),
                                               variable=user_selec_triplet, value="Curateur",
                                               command=update_aff_widget_curator,
                                               takefocus=False)
    radio_create_curator_trip.grid(column=0, row=0)
    pad_label = tk.Label(curator_frame, width=55)
    
    def reset_trip_selec(*args):
        user_selec_triplet.set("None")
        update_aff_widget_curator()
    
    #%% Fonctionnalités pour mettre à jour la sélection des aspects/opinions
    
    def modif_value(what=None):
        global aspect_value, opinion_value
        
        debut_aspect = int(aspect["i_debut"].get())
        len_aspect = int(aspect["L"].get())
        debut_opinion = int(opinion["i_debut"].get())
        len_opinion = int(opinion["L"].get())
        
        if debut_aspect > -1 :
            aspect_value = mots[debut_aspect : debut_aspect+len_aspect]
        else :
            aspect_value = "{"+Loc_Data["7.2"]+"}"
        aspect_visual.configure(text=aspect_value)
        if debut_opinion > -1 :
            opinion_value = mots[debut_opinion : debut_opinion+len_opinion]
        else :
            opinion_value = "{"+Loc_Data["7.3"]+"}"
        opinion_visual.configure(text=opinion_value)
        
        if debut_aspect != -1 :
            debut_a, line_deb_a, fin_a, line_fin_a = conversion(debut_aspect, len_aspect)
        if debut_opinion != -1 :
            debut_o, line_deb_o, fin_o, line_fin_o = conversion(debut_opinion, len_opinion)
        
        global comm_visuel, comm_scrollbar
        comm_visuel.tag_remove("aspect", "1.0", "end")
        comm_visuel.tag_remove("opinion", "1.0", "end")
        if debut_aspect != -1 :
            comm_visuel.tag_add("aspect", "{}.{}".format(line_deb_a,debut_a), "{}.{}".format(line_fin_a,fin_a))
        if debut_opinion != -1 :
            comm_visuel.tag_add("opinion", "{}.{}".format(line_deb_o,debut_o), "{}.{}".format(line_fin_o,fin_o))
        
        adapt = {"decal" : 180, "deb" : 200}
        if what == "aspect" :
            if debut_aspect >= adapt["deb"] :
                debut_a, line_deb_a, fin_a, line_fin_a = conversion(debut_aspect-adapt["decal"], 1)
                comm_visuel.yview_pickplace("{}.{}".format(line_deb_a,debut_a))
        elif what == "opinion" :
            if debut_opinion >= adapt["deb"] :
                debut_o, line_deb_o, fin_o, line_fin_o = conversion(debut_opinion-adapt["decal"], 1)
                comm_visuel.yview_pickplace("{}.{}".format(line_deb_o,debut_o))
    
    def modif_aspect():
        modif_value(what="aspect")
    def modif_opinion():
        modif_value(what="opinion")
    
    def reset_term(what=None):
        global previous_manual_selection, manual_selec_terms, aspect_value, opinion_value
        previous_manual_selection = ()
        if what == "aspect" :
            manual_selec_terms["aspect"] = []
            aspect_value = "{"+Loc_Data["7.2"]+"}"
            aspect_visual.configure(text=aspect_value)
            comm_visuel.tag_remove("aspect", "1.0", "end")
        elif what == "opinion" :
            manual_selec_terms["opinion"] = []
            opinion_value = "{"+Loc_Data["7.3"]+"}"
            opinion_visual.configure(text=opinion_value)
            comm_visuel.tag_remove("opinion", "1.0", "end")
        
    def reset_aspect(*args):
        reset_term(what="aspect")
    def reset_opinion(*args):
        reset_term(what="opinion")
    
    emergency_selec_id = {"aspect" : [-1],
                          "opinion" : [-1]}
    def add_button_state_update():
        lock_but = {"aspect" : True, "opinion" : True}
        selection = {
            "aspect" : {
                "terms" : aspect_value,
                "ids" : emergency_selec_id["aspect"]
            },
            "opinion" : {
                "terms" : opinion_value,
                "ids" : emergency_selec_id["opinion"]
            }
        }
        default = {
            "aspect" : {
                "terms" : "{"+Loc_Data["7.2"]+"}",
                "ids" : [-1]
            },
            "opinion" : {
                "terms" : "{"+Loc_Data["7.3"]+"}",
                "ids" : [-1]
            }
        }
        for term_type in list(selection.keys()) :
            cond = selection[term_type]["terms"] == default[term_type]["terms"]
            cond = cond and selection[term_type]["ids"] == default[term_type]["ids"]
            if cond == True :
                lock_but[term_type] = False
            else :
                if type(selection[term_type]["terms"]) == list :
                    cond = len(selection[term_type]["terms"]) == len(selection[term_type]["ids"])
                    cond = cond and selection[term_type]["ids"] != default[term_type]["ids"]
                    if cond == True :
                        lock_but[term_type] = False
        if lock_but["aspect"] or lock_but["opinion"] :
            valid_trip_but["state"] = "disabled"
        else :
            valid_trip_but["state"] = "active"
    def emergency_visual_update(*args):
        global aspect_value, opinion_value, emergency_selec_id
        if emergency_aspect["term_value"].get() == "" :
            aspect_value = "{"+Loc_Data["7.2"]+"}"
        else :
            aspect_value = []
            for word in emergency_aspect["term_value"].get().split(";"):
                if word != "" and word not in aspect_value :
                    aspect_value.append(word)
        if emergency_aspect["id_value"].get() == "" :
            emergency_selec_id["aspect"] = [-1]
        else :
            emergency_selec_id["aspect"] = []
            for id_ in emergency_aspect["id_value"].get().split(";"):
                if id_ != "" and id_ not in emergency_selec_id["aspect"] :
                    emergency_selec_id["aspect"].append(int(id_))
        
        if emergency_opinion["term_value"].get() == "" :
            opinion_value = "{"+Loc_Data["7.3"]+"}"
        else :
            opinion_value = []
            for word in emergency_opinion["term_value"].get().split(";"):
                if word != "" and word not in opinion_value :
                    opinion_value.append(word)
        if emergency_opinion["id_value"].get() == "" :
            emergency_selec_id["opinion"] = [-1]
        else :
            emergency_selec_id["opinion"] = []
            for id_ in emergency_opinion["id_value"].get().split(";"):
                if id_ != "" and id_ not in emergency_selec_id["opinion"] :
                    emergency_selec_id["opinion"].append(int(id_))
        
        visuel = "\|/"
        visuel += str(aspect_value)+"<|>"+str(opinion_value)+"<|>"+sentiment_value.get()+"<|>"
        visuel += str(emergency_selec_id["aspect"])+"<|>"+str(emergency_selec_id["opinion"])
        visuel += "\|/"
        emergency_visual.configure(text=visuel)
        add_button_state_update()
    
    def validate_term_entry(value):
        out = True
        if value != "" :
            carac = value[len(value)-1]
            if not (carac.isalnum() == True or carac == ";") :
                out = False
        if interaction_spin.get() != 3 :
            out = False
        return (out)
    def validate_id_entry(value):
        out = True
        if value != "" :
            carac = value[len(value)-1]
            if not (carac.isnumeric() == True or carac == ";") :
                out = False
        if interaction_spin.get() != 3 :
            out = False
        return (out)
    validate_term_entry_wrapper = (root.register(validate_term_entry), '%P')
    validate_id_entry_wrapper = (root.register(validate_id_entry), '%P')
    
    def sentiment_emergency_update_wrapper():
        if interaction_spin.get() == 3 :
            emergency_visual_update()
    
    #%% Widgets de sélection du triplet curateur
    
    mode2_term_selection = tk.IntVar(value=0)
    pad_label_for_mode2 = tk.Label(curator_frame, width=13)
    
    aspect_frame = tk.LabelFrame(curator_frame, text=Loc_Data["7.7"],
                                 font="Helvetica {} bold".format(taille_police))
    aspect = {"long" : tk.Label(aspect_frame, text=Loc_Data["7.8"],
                                font="Helvetica {}".format(taille_police)),
              "L" : tk.IntVar(value=1),
              "debut" : tk.Label(aspect_frame, text=Loc_Data["7.9"],
                                 font="Helvetica {}".format(taille_police)),
              "i_debut" : tk.IntVar(value=-1)}
    aspect_value = "{"+Loc_Data["7.2"]+"}"
    aspect_visual = tk.Label(aspect_frame, text=aspect_value, borderwidth=1, relief="solid",
                             font="Helvetica {}".format(taille_police), wraplength=350)
    aspect_selection = tk.Radiobutton(aspect_frame, text=Loc_Data["7.10"],
                                      variable=mode2_term_selection, value=0, takefocus=False,
                                      font="Helvetica {}".format(taille_police))
    reset_aspect_but = tk.Button(aspect_frame, text=Loc_Data["7.11"], command=reset_aspect,
                                 font="Helvetica {}".format(taille_police), takefocus=False)
    emergency_aspect = {}
    emergency_aspect["term_value"] = tk.StringVar()
    emergency_aspect["term_label"] = tk.Label(aspect_frame, text=Loc_Data["7.12"],
                                              font="Helvetica {}".format(taille_police))
    emergency_aspect["term_entry"] = tk.Entry(aspect_frame, textvariable=emergency_aspect["term_value"],
                                              validate="all", validatecommand=validate_term_entry_wrapper,
                                              font="Helvetica {}".format(taille_police),
                                              width=17)
    emergency_aspect["term_value"].trace_variable("w", emergency_visual_update)
    emergency_aspect["id_value"] = tk.StringVar()
    emergency_aspect["id_label"] = tk.Label(aspect_frame, text=Loc_Data["7.13"],
                                            font="Helvetica {}".format(taille_police))
    emergency_aspect["id_entry"] = tk.Entry(aspect_frame, textvariable=emergency_aspect["id_value"],
                                            validate="all", validatecommand=validate_id_entry_wrapper,
                                            font="Helvetica {}".format(taille_police),
                                            width=17)
    emergency_aspect["id_value"].trace_variable("w", emergency_visual_update)
    
    
    opinion_frame = tk.LabelFrame(curator_frame, text=Loc_Data["7.14"],
                                  font="Helvetica {} bold".format(taille_police))
    opinion = {"long" : tk.Label(opinion_frame, text=Loc_Data["7.15"],
                                 font="Helvetica {}".format(taille_police)),
              "L" : tk.IntVar(value=1),
              "debut" : tk.Label(opinion_frame, text=Loc_Data["7.16"],
                                 font="Helvetica {}".format(taille_police)),
              "i_debut" : tk.IntVar(value=-1)}
    opinion_value = "{"+Loc_Data["7.3"]+"}"
    opinion_visual = tk.Label(opinion_frame, text=opinion_value, borderwidth=1, relief="solid",
                              font="Helvetica {}".format(taille_police), wraplength=350)
    opinion_selection = tk.Radiobutton(opinion_frame, text=Loc_Data["7.17"],
                                      variable=mode2_term_selection, value=1, takefocus=False,
                                      font="Helvetica {}".format(taille_police))
    reset_opinion_but = tk.Button(opinion_frame, text=Loc_Data["7.18"], command=reset_opinion,
                                 font="Helvetica {}".format(taille_police), takefocus=False)
    emergency_opinion = {}
    emergency_opinion["term_value"] = tk.StringVar()
    emergency_opinion["term_label"] = tk.Label(opinion_frame, text=Loc_Data["7.19"],
                                              font="Helvetica {}".format(taille_police))
    emergency_opinion["term_entry"] = tk.Entry(opinion_frame, textvariable=emergency_opinion["term_value"],
                                              validate="all", validatecommand=validate_term_entry_wrapper,
                                              font="Helvetica {}".format(taille_police),
                                              width=17)
    emergency_opinion["term_value"].trace_variable("w", emergency_visual_update)
    emergency_opinion["id_value"] = tk.StringVar()
    emergency_opinion["id_label"] = tk.Label(opinion_frame, text=Loc_Data["7.20"],
                                            font="Helvetica {}".format(taille_police))
    emergency_opinion["id_entry"] = tk.Entry(opinion_frame, textvariable=emergency_opinion["id_value"],
                                            validate="all", validatecommand=validate_id_entry_wrapper,
                                            font="Helvetica {}".format(taille_police),
                                            width=17)
    emergency_opinion["id_value"].trace_variable("w", emergency_visual_update)
    
    
    spin = {"aspect_debut" : tk.Spinbox(aspect_frame, from_=-1, to=review_lenght["mots"]-1, textvariable=aspect["i_debut"],
                                        command=modif_aspect, wrap=True),
            "aspect_L" : tk.Spinbox(aspect_frame, from_=1, to=review_lenght["mots"], textvariable=aspect["L"],
                                        command=modif_aspect, wrap=True),
            "opinion_debut" : tk.Spinbox(opinion_frame, from_=-1, to=review_lenght["mots"]-1, textvariable=opinion["i_debut"],
                                        command=modif_opinion, wrap=True),
            "opinion_L" : tk.Spinbox(opinion_frame, from_=1, to=review_lenght["mots"], textvariable=opinion["L"],
                                        command=modif_opinion, wrap=True)}
    
    
    sentiment_frame = tk.LabelFrame(curator_frame, text=Loc_Data["7.21"],
                                  font="Helvetica {} bold".format(taille_police))
    sentiment_value = tk.StringVar(value="NEU")
    sentiment = {"negatif" : tk.Radiobutton(sentiment_frame, text=Loc_Data["7.22"], variable=sentiment_value,
                                            value="NEG", font="Helvetica {}".format(taille_police),
                                            command=sentiment_emergency_update_wrapper),
                 "neutre" : tk.Radiobutton(sentiment_frame, text=Loc_Data["7.23"], variable=sentiment_value,
                                           value="NEU", font="Helvetica {}".format(taille_police),
                                           command=sentiment_emergency_update_wrapper),
                 "positif" : tk.Radiobutton(sentiment_frame, text=Loc_Data["7.24"], variable=sentiment_value,
                                            value="POS", font="Helvetica {}".format(taille_police),
                                            command=sentiment_emergency_update_wrapper)}
    
    
    emergency_visual = tk.Label(curator_frame, relief="solid", font="Helvetica 14", justify="center")
    emergency_visual.configure(text="\|/"+aspect_value+"<|>"+opinion_value+"<|>"+sentiment_value.get()+"<|>"+"[-1]"+"<|>"+"[-1]"+"\|/")
    
    
    vitesse = 0
    def vitesse_plus(*args):
        global vitesse
        if interaction_spin.get() == 1 :
            if vitesse+1 < 4 :
                vitesse += 1
                label_vitesse.configure(text="{}".format(10**vitesse))
    def vitesse_moins(*args):
        global vitesse
        if interaction_spin.get() == 1 :
            if vitesse-1 >= 0 :
                vitesse -= 1
                label_vitesse.configure(text="{}".format(10**vitesse))
    plus_vite = tk.LabelFrame(curator_frame, text=Loc_Data["7.25"]+"\n"+Loc_Data["7.26"], font="Helvetica {} bold".format(taille_police),
                              padx=5, pady=5)
    bouton_moins = tk.Button(plus_vite, text="-",font="Helvetica {}".format(taille_police),
                             command=vitesse_moins, takefocus=False, padx=9)
    label_vitesse = tk.Label(plus_vite, text="{}".format(10**vitesse),
                             font="Helvetica {}".format(taille_police), padx=9)
    bouton_plus = tk.Button(plus_vite, text="+",font="Helvetica {}".format(taille_police),
                             command=vitesse_plus, takefocus=False, padx=9)
    
    #%% Fonctionnalité pour entrer un triplet omis par les users
    
    def add_omited_triplet():
        if -1 not in curated_trips :
            curated_trips.append(-1)
            change_triplet_similarity(0, force_set=len(curated_trips)-1)
        else :
            change_triplet_similarity(0, force_set=len(curated_trips)-1)
        user_selec_triplet.set("Curateur")
        update_aff_widget_curator()
    
    add_trip_but = tk.Button(root, text=Loc_Data["17.14"],
                             command=add_omited_triplet, font="Helvetica {}".format(taille_police),
                             takefocus=False)
    add_trip_but.grid(column=0, row=3)
    
    #%% Fonctionnalité pour supprimer un triplet
    
    def translate_TupleTrip_to_ListTrip(TupleTrip):
        return (Users_Triplets[TupleTrip[0]][id_curation][TupleTrip[1]])
    
    def sup_triplets():
        selection = tk.Toplevel(root)
        selection.title(Loc_Data["14.1"])
        
        temp = []
        for item in curated_trips :
            if type(item) == tuple :
                item = translate_TupleTrip_to_ListTrip(item)
            if item == 0 :
                temp.append("{"+Loc_Data["14.9"]+"}")
            elif item == None :
                temp.append("{"+Loc_Data["14.10"]+"}")
            elif item == -1 :
                temp.append("{"+Loc_Data["14.11"]+"}")
            else :
                temp.append(item[:3])
        list_triplets = tk.StringVar(value=temp)
        
        def fonc_annuler(*args):
            selection.grab_release()
            selection.destroy()
        
        def fonc_valider(*args):
            indexes = list(liste_selec.curselection())
            indexes.reverse()
            
            if len(indexes) > 0 :
                global curated_trips
                for element in indexes :
                    if curated_trips[element] == -1  or element >= len(Triplets_Similarities[id_curation]) :
                        curated_trips.remove(curated_trips[element])
                    else :
                        curated_trips[element] = 0
                change_triplet_similarity(0)
                fonc_annuler()
        
        liste_selec = tk.Listbox(selection, height=10, listvariable=list_triplets,
                                 selectmode="extended", width=50)
        liste_selec.configure(font="Helvetica {}".format(taille_police))
        for i in range(0,len(curated_trips),2):
            liste_selec.itemconfigure(i, background='#f0f0ff')
        
        valider = tk.Button(selection, text=Loc_Data["14.3"], font="Helvetica {}".format(taille_police),
                            command=fonc_valider)
        annuler = tk.Button(selection, text=Loc_Data["14.4"], font="Helvetica {}".format(taille_police),
                            command=fonc_annuler)
        
        liste_selec.grid(column=0, row=0, rowspan=2)
        valider.grid(column=1, row=0)
        annuler.grid(column=1, row=1)
        
        Utils.center_(selection)
        
        selection.transient(root)
        selection.wait_visibility()
        selection.grab_set()
        selection.wait_window()
    
    add_trip_but = tk.Button(root, text=Loc_Data["17.15"],
                             command=sup_triplets, font="Helvetica {}".format(taille_police),
                             takefocus=False)
    add_trip_but.grid(column=0, row=4)
    
    #%% Fonctionnalité pour valider le triplet choisi
    
    # TODO : dans le cas où un sélectionne un triplet différent de celui validé dans une
    #        similarité déjà validée, il faut faire en sorte que le triplet déjà validé
    #        soit supprimé avant d'y mettre à sa place le nouveau triplet.
    #        pour le moment, l'ancien n'est pas supprimé et le nouveau et ajouté à la
    #        suite (à vérifier)
    
    def get_terms_indexes():
        def troncate(list_index, len_mots) :
            troncate_index = None
            for i in range(len(list_index)) :
                if list_index[i] == len_mots :
                    troncate_index = i
                    break
            return (list_index[:troncate_index])
        
        if interaction_spin.get() in [0,1] :
            indexes_aspect = [int(aspect["i_debut"].get())]
            indexes_opinion = [int(opinion["i_debut"].get())]
            if aspect_value != "{"+"Aspect inexistant"+"}" :
                for i in range(1, int(aspect["L"].get())) :
                    indexes_aspect.append(int(aspect["i_debut"].get())+i)
            if opinion_value != "{"+"Opinion inexistante"+"}" :
                for i in range(1, int(opinion["L"].get())) :
                    indexes_opinion.append(int(opinion["i_debut"].get())+i)
            indexes_aspect = troncate(indexes_aspect, review_lenght["mots"])
            indexes_opinion = troncate(indexes_opinion, review_lenght["mots"])
        elif interaction_spin.get() == 2 :
            indexes_aspect = manual_selec_terms["aspect"]
            if indexes_aspect == [] :
                indexes_aspect = [-1]
            indexes_opinion = manual_selec_terms["opinion"]
            if indexes_opinion == [] :
                indexes_opinion = [-1]
        elif interaction_spin.get() == 3 :
            indexes_aspect = emergency_selec_id["aspect"]
            indexes_opinion = emergency_selec_id["opinion"]
        
        return (indexes_aspect, indexes_opinion)
    
    def is_newtrip_ok_to_add(new):
        out = False
        if type(new) == tuple :
            new = translate_TupleTrip_to_ListTrip(new)
        if new not in curated_trips :
            if not (new[0] == "{"+Loc_Data["7.2"]+"}" and new[1] == "{"+Loc_Data["7.3"]+"}") :
                cond = True
                for triplet in curated_trips :
                    if triplet not in [0, None, -1] :
                        if type(triplet) == tuple :
                            triplet = translate_TupleTrip_to_ListTrip(triplet)
                        if new[3:4+1] == triplet[3:4+1] :
                            cond = False
                            break
                if cond == True :
                    # vérifier si aspect != opinion
                    if new[3] != new[4] :
                        out = True
                    else :
                        messagebox.showwarning(title=Loc_Data["13.1"],
                                           message=Loc_Data["13.2"]+"\n"+Loc_Data["13.3"]+"\n"+Loc_Data["13.4"])
                else :
                    messagebox.showwarning(title=Loc_Data["13.1"],
                                       message=Loc_Data["13.2"]+"\n"+Loc_Data["13.3"]+"\n"+Loc_Data["13.5"])
            else :
                messagebox.showwarning(title=Loc_Data["13.1"],
                                   message=Loc_Data["13.2"]+"\n"+Loc_Data["13.3"]+"\n"+Loc_Data["13.6"])
        else :
            messagebox.showwarning(title=Loc_Data["13.1"],
                                   message=Loc_Data["13.2"]+"\n"+Loc_Data["13.7"])
        return (out)
    
    def add_triplet():
        source = user_selec_triplet.get()
        triplet_to_add = None
        if source == "Curateur" :
            indexes_aspect, indexes_opinion = get_terms_indexes()
            triplet_to_add = [aspect_value, opinion_value, sentiment_value.get(), indexes_aspect, indexes_opinion]
        elif source in Users :
            for i in range(len(Triplets_Similarities[id_curation][triplet_similarity])) :
                if Triplets_Similarities[id_curation][triplet_similarity][i][0] == source :
                    triplet_to_add = Triplets_Similarities[id_curation][triplet_similarity][i]
                    break
        
        if triplet_to_add != None :
            if is_newtrip_ok_to_add(triplet_to_add) == True :
                curated_trips[triplet_similarity] = triplet_to_add
                change_triplet_similarity(1)
        else :
            curated_trips[triplet_similarity] = None
            change_triplet_similarity(1)
    
    valid_trip_but = tk.Button(root, text=Loc_Data["17.16"],
                               command=add_triplet, font="Helvetica {}".format(taille_police),
                               takefocus=False)
    valid_trip_but.grid(column=1, row=3)
    
    #%% Fonctionnalité pour valider le commentaire
    
    def unlock_valid_comm():
        valid_comm_but["state"] = "disabled"
        if 0 not in curated_trips and -1 not in curated_trips :
            valid_comm_but["state"] = "active"
    
    def get_data_to_write(targetfile_extension):
        out = ""
        data = Utils.load_data(save_file+targetfile_extension)
        
        comm_found = False
        comm_to_add = id_curation + "\|/"
        
        if targetfile_extension == ".HELPER_" :
            for element in curated_trips :
                if type(element) == list :
                    for item in element :
                        comm_to_add += str(item) + "<|>"
                    comm_to_add = comm_to_add[:-3]
                else :
                    comm_to_add += str(element)
                comm_to_add += "\|/"
            
        elif targetfile_extension == ".txt" :
            comm_to_add += " ".join(mots) + "\|/"
            for element in curated_trips :
                source = None
                if type(element) == list :
                    source = element
                elif type(element) == tuple :
                    source = Users_Triplets[element[0]][id_curation][element[1]]
                if source != None :
                    for item in source :
                        comm_to_add += str(item) + "<|>"
                    comm_to_add = comm_to_add[:-3]
                    comm_to_add += "\|/"
            
        print (comm_to_add)
        for line in data :
            if line.split("\|/")[0] == id_curation :
                comm_found = True
                out += comm_to_add + "\n"
            else :
                out += line
        if comm_found == False :
            out += comm_to_add + "\n"
        
        return (out)
    
    def valid_comm_as_curated():
        global curated_comms, nb_comm_val
        for extension in [".HELPER_", ".txt"] :
            to_write = get_data_to_write(extension)
            file = open(save_file+extension, "w", encoding="utf8")
            file.write(to_write)
            file.close()
        
        if curated_comms[comm_ids_list.index(id_curation)] != 1 :
            curated_comms[comm_ids_list.index(id_curation)] = 1
            nb_comm_val += 1
            prog_bar["value"] = nb_comm_val
        change_id_curation(1)
    
    valid_comm_but = tk.Button(root, text=Loc_Data["17.17"],
                               command=valid_comm_as_curated, font="Helvetica {}".format(taille_police),
                               takefocus=False, state="disabled")
    valid_comm_but.grid(column=1, row=4)
    
    #%% Fonctions pour la sélection avec les raccourcis
    
    position = None
    def reset_spin_selec(*args):
        dic_spin = {"0" : "aspect_debut",
                    "1" : "aspect_L",
                    "2" : "opinion_debut",
                    "3" : "opinion_L"}
        for pos in list(dic_spin.keys()) :
            key = dic_spin[pos]
            spin[key].configure(fg="SystemWindowText")
            spin[key].configure(font="TkTextFont")
    
    def navigation_spin(action):
        dic_spin = {"0" : "aspect_debut",
                    "1" : "aspect_L",
                    "2" : "opinion_debut",
                    "3" : "opinion_L"}
        dic_var = {"aspect_debut" : "i_debut",
                   "aspect_L" : "L",
                   "opinion_debut" : "i_debut",
                   "opinion_L" : "L"}
        
        if action == "move" :
            reset_spin_selec()
            spin[dic_spin["{}".format(position)]].configure(fg="red")
            spin[dic_spin["{}".format(position)]].configure(font="TkTextFont 10 bold")
        elif "value_" in action and spin[dic_spin["{}".format(position)]]["fg"] == "red" :
            global aspect, opinion
            pos = "{}".format(position)
            
            value = 0
            if pos in ["0", "1"] :
                value = aspect[dic_var[dic_spin[pos]]].get()
            elif pos in ["2", "3"] :
                value = opinion[dic_var[dic_spin[pos]]].get()
            
            if action == "value_up" :
                if pos in ["0", "2"] :
                    if value+10**vitesse >= review_lenght["mots"] :
                        value = -1
                    else :
                        value += 10**vitesse
                elif pos in ["1", "3"] :
                    if value+10**vitesse >= review_lenght["mots"]+1 :
                        value = 1
                    else :
                        value += 10**vitesse
            elif action == "value_down" :
                if pos in ["0", "2"] :
                    if value-10**vitesse <= -2 :
                        value = review_lenght["mots"]-1
                    else :
                        value -= 10**vitesse
                elif pos in ["1", "3"] :
                    if value-10**vitesse <= 0 :
                        value = review_lenght["mots"]
                    else :
                        value -= 10**vitesse
            
            if pos in ["0", "1"] :
                aspect[dic_var[dic_spin[pos]]].set(value)
                modif_value(what="aspect")
            elif pos in ["2", "3"] :
                opinion[dic_var[dic_spin[pos]]].set(value)
                modif_value(what="opinion")
            
            for key in list(spin.keys()) :
                spin[key].update()
    
    def go_down(*args):
        global position
        if interaction_spin.get() == 1 :
            if position == None :
                position = 1
            elif position < 3 :
                position += 1
            navigation_spin("move")
    def go_up(*args):
        global position
        if interaction_spin.get() == 1 :
            if position == None :
                position = 0
            elif position > 0 :
                position -= 1
            navigation_spin("move")
    def value_up(*args):
        if interaction_spin.get() == 1 :
            navigation_spin("value_up")
    def value_down(*args):
        if interaction_spin.get() == 1 :
            navigation_spin("value_down")
    
    #%% Fonctions pour la sélection à la volée dans le texte
    previous_manual_selection = ()
    manual_selec_terms = {"aspect" : [], "opinion" : []}
    
    def fin_manual_selec(*args):
        if interaction_spin.get() == 2 :
            manual_selec(sur_fin_selec=True)
    
    def textindex_in_selec(deb, fin, deb_selec, fin_selec):
        sortie = False
        
        def TextIndex2Index(item):
            out = item[1]
            if item[0] > 1 :
                for i in range(item[0]-1) :
                    out += carac_per_line[i]
            return (out)
        
        def in_between(x,a,b):
            out = False
            if x >= a and x <= b :
                out = True
            return (out)
        
        deb = TextIndex2Index(deb)
        fin = TextIndex2Index(fin)
        deb_selec = TextIndex2Index(deb_selec)
        fin_selec = TextIndex2Index(fin_selec)
        
        if in_between(deb, deb_selec, fin_selec) == True and in_between(fin, deb_selec, fin_selec) == True :
            sortie = True
        
        return (sortie)
    
    def get_mot_index(selec):
        deb = tuple([int(_) for _ in str(selec[0]).split(".")])
        fin = tuple([int(_) for _ in str(selec[1]).split(".")])
        
        index_out = []
        for k in range(len(mots)) :
            c_deb, l_deb, c_fin, l_fin = conversion(k, 1)
            test_deb = (l_deb,c_deb)
            test_fin = (l_fin,c_fin)
            
            if textindex_in_selec(test_deb, test_fin, deb, fin) == True :
                index_out.append(k)
        
        return (index_out)
    
    def manual_selec(sur_fin_selec=False, *args):
        global previous_manual_selection, manual_selec_terms, aspect_value, opinion_value
        
        if interaction_spin.get() == 2 :
            term_selec_dict = {"0" : "aspect", "1" : "opinion"}
            
            selection = comm_visuel.tag_ranges("sel")
            term_selec = term_selec_dict[str(mode2_term_selection.get())]
            if selection != () and selection != previous_manual_selection :
                if sur_fin_selec == True :
                    # 1- récupérer les indexes des mots sélectionnés
                    index_selec = get_mot_index(selection)
                    # 2- mettre à jour les listes des indexes de l'aspect et de l'opinion
                    #    si le mot n'est pas présent, on l'ajoute, sinon on l'enlève
                    for ind in index_selec :
                        if ind in manual_selec_terms[term_selec] :
                            manual_selec_terms[term_selec].remove(ind)
                        else :
                            manual_selec_terms[term_selec].append(ind)
                        manual_selec_terms[term_selec].sort()
                    # 3- mettre à jour l'affichage coloré dans le texte
                    comm_visuel.tag_remove("mot_i", "1.0", "end")
                    comm_visuel.tag_remove("aspect", "1.0", "end")
                    comm_visuel.tag_remove("opinion", "1.0", "end")
                    for i in range(len(mots)) :
                        debut, line_deb, fin, line_fin = conversion(i, 1)
                        if i in manual_selec_terms["aspect"] :
                            comm_visuel.tag_add("aspect", "{}.{}".format(line_deb,debut), "{}.{}".format(line_fin,fin))
                        elif i in manual_selec_terms["opinion"] :
                            comm_visuel.tag_add("opinion", "{}.{}".format(line_deb,debut), "{}.{}".format(line_fin,fin))
                        else :
                            if i%2 == 1 :
                                comm_visuel.tag_add("mot_i", "{}.{}".format(line_deb,debut), "{}.{}".format(line_fin,fin))
                    # 4- mettre à jour les textes de l'aspect et de l'opinion
                    if term_selec == "aspect" :
                        if len(manual_selec_terms[term_selec]) == 0 :
                            aspect_value = "{"+"Aspect inexistant"+"}"
                        else :
                            aspect_value = [mots[ind] for ind in manual_selec_terms[term_selec]]
                        aspect_visual.configure(text=aspect_value)
                    elif term_selec == "opinion" :
                        if len(manual_selec_terms[term_selec]) == 0 :
                            opinion_value = "{"+"Opinion inexistante"+"}"
                        else :
                            opinion_value = [mots[ind] for ind in manual_selec_terms[term_selec]]
                        opinion_visual.configure(text=opinion_value)
                    
                    previous_manual_selection = ()
                else :
                    previous_manual_selection = selection
    
    #%% Centrage et raccourcis de la fenêtre principale
    
    update_aff_widget_curator()
    
    if interaction_spin.get() != 3 :
        root.bind("<Key-{}>".format(raccourcis["spin_u"]), go_up)
        root.bind("<Key-{}>".format(raccourcis["spin_d"]), go_down)
        root.bind("<Key-{}>".format(raccourcis["spin_v_u"]), value_up)
        root.bind("<Key-{}>".format(raccourcis["spin_v_d"]), value_down)
        root.bind("<Key-{}>".format(raccourcis["spin_reset_col"]), reset_spin_selec)
        root.bind("<Key-{}>".format(raccourcis["vit_plus"]), vitesse_plus)
        root.bind("<Key-{}>".format(raccourcis["vit_moins"]), vitesse_moins)
        root.bind("<Right>", lambda x: None)
        root.bind("<Left>", lambda x: None)
    
    root.bind("<Key-{}>".format(raccourcis["reset_trip_selec"]), reset_trip_selec)
    root.bind("<Shift-Right>", but_plus_wrapper)
    root.bind("<Shift-Left>", but_moins_wrapper)
    root.bind("<Control-Right>", next_trip_wrapper)
    root.bind("<Control-Left>", prev_trip_wrapper)
    comm_visuel.bind("<ButtonRelease>", fin_manual_selec)
    
    Utils.center_(root)
    
    root.mainloop()



