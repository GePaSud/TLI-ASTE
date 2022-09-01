# -*- coding: utf-8 -*-
"""
Created on Thu Mar  3 10:17:17 2022

@author: Florian Cataldi
"""

"""
GUI pour labelisation des triplets dans les commentaires

Labelisation Window
"""

# plus qu'à mettre en place :
#   - trouver comment gérer les unicodes après U+FFFF (les émojis et +)
#       -> ignorer commentaire contenant le caractère non supporté
#          (cf. ne représente que 0.76% des commentaires)

#   - améliorer l'ergonomie avec des raccourcis clavier et autres fonctionnalités et menus
#       - ... (à voir si besoin)
#       - revoir la fonctionnalité pour modifier des comms (càd le déplacement entre comms)
#           -> mettre en place une sorte de recherche des IDs des comms

#   - ajouter de <<l'accessibilité>> au grand public avec les fonctionnalités suivantes :



import tkinter as tk
from tkinter import messagebox
from time import sleep
from os.path import isfile
from os import walk, mkdir
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
    "in"  : Metadata["InputDataDir"]
}

if WrkDir["in"].split("/")[1] not in next(walk("Data"))[1] :
    mkdir(WrkDir["in"])
if WrkDir["out"].split("/")[1] not in next(walk("Data"))[1] :
    mkdir(WrkDir["out"])

#%% Vérification de la présence des fichiers d'informations des fichiers d'entrée

create_partitions = False
for lang in Metadata["AvailableLanguage"] :
    if isfile(WrkDir["in"]+"Comms_num_{}.DATA_INFO_".format(lang)) == False :
        create_partitions = True
        break
if create_partitions == True :
    Utils.window_for_partitions_creation(check_carac_non_supporte, Loc_Data)

#%% Sélection de l'utilisateur
selec_user = wnds.selec_user_window(Loc_Data)
User = selec_user.run_window()
 
WrkDir["out"] += User+"/"

#%% Récupération des partitions à labéliser

Paths, Partitions, Total_num_comms = Utils.get_part_selec(Loc_Data)

#%% Chargement des identifiants des commentaires jugés incohérents

def load_oddities():
    try :
        file = open(WrkDir["out"]+"oddities.txt", encoding="utf8")
        file.close()
    except :
        file = open(WrkDir["out"]+"oddities.txt", "x", encoding="utf8")
        file.close()
    
    data = Utils.load_data(WrkDir["out"]+"oddities.txt")
    list_oddities = []
    
    for oddity in data :
        list_oddities.append(oddity[:-1])
    
    return (list_oddities)
oddities = load_oddities()

#%% Vérification des caractères non affichable par Tkinter

verif_carac = wnds.verif_carac_window(Loc_Data, Total_num_comms, Paths, check_carac_non_supporte)
verif_carac.run_window()

#%% Chargement des commentaires à labéliser

comms = {}
for langue in Metadata["AvailableLanguage"] :
    comms[langue] = {}

chargement_comms = wnds.load_comms_window(Metadata["AvailableLanguage"], Total_num_comms, Loc_Data,
                                          "labelisation", (Paths, comms), check_carac_non_supporte)
chargement_comms.run_window()

#%% Initialisation de la progression de labélisation
file_name = {}
indexe_courant = {}
indexe_progression = {}

for langue in Metadata["AvailableLanguage"] :
    bonus = ""
    if Partitions[langue] != "" :
        bonus = "_part"+Partitions[langue]
    file_name[langue] = WrkDir["out"]+"Comms_labeled_{}{}.txt".format(langue, bonus)
    try :
        file = open(file_name[langue], "r", encoding="utf8")
        file.close()
    except :
        file = open(file_name[langue], "x", encoding="utf8")
        file.close()
    indexe_courant[langue] = 0
    indexe_progression[langue] = {"done" : [],"todo" : []}

def get_progression():
    
    def sort_index(unsorted_index):
        temp = [int(element) for element in unsorted_index]
        temp.sort()
        sorted_index = [str(element) for element in temp]
        return (sorted_index)
    
    global indexe_progression
    
    separateur = "\|/"
    for lang in Metadata["AvailableLanguage"] :
        data = Utils.load_data(file_name[lang])
        
        indexe_progression[lang]["todo"] = list(comms[lang].keys())
        id_done = []
        for line in data :
            temp = line.split(separateur)[0]
            if temp not in id_done :
                id_done.append(temp)
        
        for element in id_done :
            if element not in indexe_progression[lang]["done"] :
                indexe_progression[lang]["done"].append(element)
            if element in indexe_progression[lang]["todo"] :
                indexe_progression[lang]["todo"].remove(element)
        
        odds_to_remove = []
        for id_ in indexe_progression[lang]["todo"] :
            comm_identifier = lang+"-"+id_
            if comm_identifier in oddities :
                odds_to_remove.append(id_)
                
        for element in odds_to_remove :
            indexe_progression[lang]["todo"].remove(element)
        
        for key in list(indexe_progression[lang].keys()) :
            indexe_progression[lang][key] = sort_index(indexe_progression[lang][key])

get_progression()

#%% Initialisation du commentaire de départ

Lang_done = {}
mode_relecture = True
for lang in Metadata["AvailableLanguage"] :
    if len(indexe_progression[lang]["todo"]) == 0 :
        Lang_done[lang] = True
        indexe_courant[lang] = indexe_progression[lang]["done"][0]
    else :
        Lang_done[lang] = False
        indexe_courant[lang] = indexe_progression[lang]["todo"][0]
    mode_relecture = mode_relecture and Lang_done[lang]

lang_to_begin = 0
for i in range(len(Metadata["AvailableLanguage"])) :
    lang = Metadata["AvailableLanguage"][i]
    if Lang_done[lang] == True :
        lang_to_begin += 1
if lang_to_begin == len(Metadata["AvailableLanguage"]) :
    lang_to_begin == 0
lang_to_begin = Metadata["AvailableLanguage"][lang_to_begin]
comm = comms[lang_to_begin][indexe_courant[lang_to_begin]]

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
root.title(Loc_Data["7.1"])
#root.resizable(False, False)
root.option_add('*tearOff', False)
root.geometry("1785x780")

#%% Récupération des paramètres du GUI ou création par défaut

taille_police = 14
taille_police_review = 18
interaction_spin = tk.IntVar(value=0)
raccourcis = {"principal" : {},
              "parcours_comm" : {},
              "suppres_triplets" : {}}
raccourcis["principal"] = {"p_comm" : "p",
                           "c_lang" : "l",
                           "v_trip" : "v",
                           "add_trip" : "F1",
                           "sup_trip" : "F2",
                           "val_trip" : "Return",
                           "spin_u" : "z",
                           "spin_l" : "q",
                           "spin_d" : "s",
                           "spin_r" : "d",
                           "spin_v_u" : "r",
                           "spin_v_d" : "f",
                           "spin_reset_col" : "x",
                           "vit_plus" : "e",
                           "vit_moins" : "a"}
raccourcis["parcours_comm"] = {"valider" : "Return",
                               "annuler" : "Escape"}
raccourcis["suppres_triplets"] = {"valider" : "Return",
                                  "annuler" : "Escape"}
try :
    file = open("Parametres/labelisation.CONFIG_", "r")
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
        elif temp[0][:10] == "raccourcis" :
            temp_ = temp[0].split(".")
            raccourcis[temp_[1]][temp_[2]] = value
    file.close()
except :
    file = open("Parametres/labelisation.CONFIG_", "x")
    default_settings = "taille_police=14\n"
    default_settings += "taille_police_review=18\n"
    default_settings += "interaction_spin=0\n"
    default_settings += "raccourcis.principal.p_comm=p\n"
    default_settings += "raccourcis.principal.c_lang=l\n"
    default_settings += "raccourcis.principal.v_trip=v\n"
    default_settings += "raccourcis.principal.add_trip=F1\n"
    default_settings += "raccourcis.principal.sup_trip=F2\n"
    default_settings += "raccourcis.principal.val_trip=Return\n"
    default_settings += "raccourcis.principal.spin_u=z\n"
    default_settings += "raccourcis.principal.spin_l=q\n"
    default_settings += "raccourcis.principal.spin_d=s\n"
    default_settings += "raccourcis.principal.spin_r=d\n"
    default_settings += "raccourcis.principal.spin_v_u=r\n"
    default_settings += "raccourcis.principal.spin_v_d=f\n"
    default_settings += "raccourcis.principal.spin_reset_col=x\n"
    default_settings += "raccourcis.principal.vit_plus=e\n"
    default_settings += "raccourcis.principal.vit_moins=a\n"
    default_settings += "raccourcis.parcours_comm.valider=Return\n"
    default_settings += "raccourcis.parcours_comm.annuler=Escape\n"
    default_settings += "raccourcis.suppres_triplets.valider=Return\n"
    default_settings += "raccourcis.suppres_triplets.annuler=Escape\n"
    file.write(default_settings)
    file.close()

def save_config():
    settings = "taille_police={}\n".format(taille_police)
    settings += "taille_police_review={}\n".format(taille_police_review)
    settings += "interaction_spin={}\n".format(interaction_spin.get())
    for fen in list(raccourcis.keys()) :
        for bind in list(raccourcis[fen].keys()) :
            settings += "raccourcis.{}.{}={}\n".format(fen,bind,raccourcis[fen][bind])
    
    file = open("Parametres/labelisation.CONFIG_", "w")
    file.write(settings)
    file.close()

#%% Création des menus du GUI

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
                                     add_button,sup_button,val_button,lang_button,
                                     list_trip, aspect_selection,reset_aspect_but,
                                     emergency_aspect["term_label"],emergency_aspect["term_entry"],
                                     emergency_aspect["id_label"],emergency_aspect["id_entry"],
                                     opinion_selection,opinion_selection,
                                     emergency_opinion["term_label"],emergency_opinion["term_entry"],
                                     emergency_opinion["id_label"],emergency_opinion["id_entry"],
                                     bouton_moins,bouton_plus,label_vitesse,modif_button],
                        "bold" : [review,triplet_selec,aspect_frame,plus_vite,
                                  opinion_frame,sentiment_label,triplet_visu]}
        for widget in taille_texte["normal"] :
            widget.configure(font="Helvetica {}".format(taille_police))
        for widget in taille_texte["bold"] :
            widget.configure(font="Helvetica {} bold".format(taille_police))
        
        cherche.tag_configure("aspect", font="Helvetica {}".format(taille_police_review))
        cherche.tag_configure("opinion", font="Helvetica {}".format(taille_police_review))
        cherche.tag_configure("normal", font="Helvetica {}".format(taille_police_review))
        
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
        action_name = action.split(".")
        out = None
        if action_name[0] == "principal" :
            if action_name[1] == "p_comm" :
                out = p_comm_but
            elif action_name[1] == "c_lang" :
                out = c_lang_but
            elif action_name[1] == "v_trip" :
                out = v_trip_but
            elif action_name[1] == "add_trip" :
                out = add_trip_but
            elif action_name[1] == "sup_trip" :
                out = sup_trip_but
            elif action_name[1] == "val_trip" :
                out = val_trip_but
            elif action_name[1] == "spin_u" :
                out = spin_u_but
            elif action_name[1] == "spin_l" :
                out = spin_l_but
            elif action_name[1] == "spin_d" :
                out = spin_d_but
            elif action_name[1] == "spin_r" :
                out = spin_r_but
            elif action_name[1] == "spin_v_u" :
                out = spin_v_u_but
            elif action_name[1] == "spin_v_d" :
                out = spin_v_d_but
            elif action_name[1] == "spin_reset_col" :
                out = spin_reset_col_but
            elif action_name[1] == "vit_plus" :
                out = vitesse_plus_but
            elif action_name[1] == "vit_moins" :
                out = vitesse_moins_but
        elif action_name[0] == "parcours_comm" :
            if action_name[1] == "valider" :
                out = val_comm_but
            elif action_name[1] == "annuler" :
                out = anul_comm_but
        elif action_name[0] == "suppres_triplets" :
            if action_name[1] == "valider" :
                out = val_suptrip_but
            elif action_name[1] == "annuler" :
                out = anul_suptrip_but
        
        return (out)
    
    def get_bind_callback(action):
        action_name = action.split(".")
        out = None
        if action_name[0] == "principal" :
            if action_name[1] == "p_comm" :
                out = parcourir_comms
            elif action_name[1] == "c_lang" :
                out = changer_lang
            elif action_name[1] == "v_trip" :
                out = visualisation_triplets
            elif action_name[1] == "add_trip" :
                out = add_triplet
            elif action_name[1] == "sup_trip" :
                out = sup_triplet
            elif action_name[1] == "val_trip" :
                out = val_triplets
            elif action_name[1] == "spin_u" :
                out = go_up
            elif action_name[1] == "spin_l" :
                out = go_left
            elif action_name[1] == "spin_d" :
                out = go_down
            elif action_name[1] == "spin_r" :
                out = go_right
            elif action_name[1] == "spin_v_u" :
                out = value_up
            elif action_name[1] == "spin_v_d" :
                out = value_down
            elif action_name[1] == "spin_reset_col" :
                out = reset_spin_selec
            elif action_name[1] == "vit_plus" :
                out = vitesse_plus
            elif action_name[1] == "vit_moins" :
                out = vitesse_moins
        
        return (out)
    
    def update_aff():
        for fen in list(raccourcis.keys()) :
            for bind in list(raccourcis[fen].keys()) :
                get_widget_but(fen+"."+bind).configure(text=check_nick(raccourcis[fen][bind]))
    
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
        action_name = action.split(".")
        
        def in_raccourcis(key, fen):
            out = False
            info = None
            
            for bind in list(raccourcis[fen].keys()) :
                if key == raccourcis[fen][bind] :
                    out = True
                    info = "{}.{}".format(fen, bind)
                    break
            
            return (out, info)
        
        def fonc_get_key(event):
            touche = event.keysym
            
            if touche in possible_keys :
                cond, info = in_raccourcis(touche, action_name[0])
                if cond == False :
                    if action_name[0] == "principal" :
                        root.unbind("<Key-{}>".format(raccourcis[action_name[0]][action_name[1]]))
                    raccourcis[action_name[0]][action_name[1]] = touche
                    if action_name[0] == "principal" :
                        root.bind("<Key-{}>".format(raccourcis[action_name[0]][action_name[1]]),
                                  get_bind_callback(action))
                    update_aff()
                    blink([get_widget_but(action)],1,500,"light green")
                    save_config()
                else :
                    blink([get_widget_but(action), get_widget_but(info)],10,50)
            
            fen_binds.unbind("<Key>")
        fen_binds.bind("<Key>", fonc_get_key)
    
    def bind_p_comm():
        change_bind("principal.p_comm")
    def bind_c_lang():
        change_bind("principal.c_lang")
    def bind_v_trip():
        change_bind("principal.v_trip")
    def bind_add_trip():
        change_bind("principal.add_trip")
    def bind_sup_trip():
        change_bind("principal.sup_trip")
    def bind_val_trip():
        change_bind("principal.val_trip")
    def bind_vit_plus():
        change_bind("principal.vit_plus")
    def bind_vit_moins():
        change_bind("principal.vit_moins")
    
    def bind_spin_u():
        change_bind("principal.spin_u")
    def bind_spin_l():
        change_bind("principal.spin_l")
    def bind_spin_d():
        change_bind("principal.spin_d")
    def bind_spin_r():
        change_bind("principal.spin_r")
    def bind_spin_v_u():
        change_bind("principal.spin_v_u")
    def bind_spin_v_d():
        change_bind("principal.spin_v_d")
    def bind_spin_reset_col():
        change_bind("principal.spin_reset_col")
    
    def bind_val_comm():
        change_bind("parcours_comm.valider")
    def bind_anul_comm():
        change_bind("parcours_comm.annuler")
    
    def bind_val_suptrip():
        change_bind("suppres_triplets.valider")
    def bind_anul_suptrip():
        change_bind("suppres_triplets.annuler")
    
    principal = tk.LabelFrame(fen_binds,text=Loc_Data["10.2"],font="Helvetica {} bold".format(taille_police))
    principal.grid(column=0, row=0, rowspan=2)
    
    parcours_comm = tk.LabelFrame(fen_binds,text=Loc_Data["10.3"],font="Helvetica {} bold".format(taille_police))
    parcours_comm.grid(column=1, row=0)
    
    suppres_triplets = tk.LabelFrame(fen_binds,text=Loc_Data["10.23"],font="Helvetica {} bold".format(taille_police))
    suppres_triplets.grid(column=1, row=1)
    
    p_comm_lab = tk.Label(principal,text=Loc_Data["10.4"],font="Helvetica {}".format(taille_police))
    c_lang_lab = tk.Label(principal,text=Loc_Data["10.5"],font="Helvetica {}".format(taille_police))
    v_trip_lab = tk.Label(principal,text=Loc_Data["10.6"],font="Helvetica {}".format(taille_police))
    add_trip_lab = tk.Label(principal,text=Loc_Data["10.7"],font="Helvetica {}".format(taille_police))
    sup_trip_lab = tk.Label(principal,text=Loc_Data["10.8"],font="Helvetica {}".format(taille_police))
    val_trip_lab = tk.Label(principal,text=Loc_Data["10.9"],font="Helvetica {}".format(taille_police))
    vit_plus_lab = tk.Label(principal,text=Loc_Data["10.10"],font="Helvetica {}".format(taille_police))
    vit_moins_lab = tk.Label(principal,text=Loc_Data["10.11"],font="Helvetica {}".format(taille_police))
    p_comm_lab.grid(column=0, row=0)
    c_lang_lab.grid(column=0, row=1)
    v_trip_lab.grid(column=0, row=2)
    add_trip_lab.grid(column=0, row=3)
    sup_trip_lab.grid(column=0, row=4)
    val_trip_lab.grid(column=0, row=5)
    tk.ttk.Separator(principal,orient="horizontal").grid(column=0,row=7,columnspan=5,sticky="we")
    vit_plus_lab.grid(column=0, row=8)
    vit_moins_lab.grid(column=0, row=9)
    
    separateur = tk.ttk.Separator(principal, orient="vertical")
    separateur.grid(column=2, row=0, rowspan=7, sticky="ns")
    
    spin_u_lab = tk.Label(principal,text=Loc_Data["10.12"],font="Helvetica {}".format(taille_police))
    spin_l_lab = tk.Label(principal,text=Loc_Data["10.13"],font="Helvetica {}".format(taille_police))
    spin_d_lab = tk.Label(principal,text=Loc_Data["10.14"],font="Helvetica {}".format(taille_police))
    spin_r_lab = tk.Label(principal,text=Loc_Data["10.15"],font="Helvetica {}".format(taille_police))
    spin_v_u_lab = tk.Label(principal,text=Loc_Data["10.16"],
                            font="Helvetica {}".format(taille_police))
    spin_v_d_lab = tk.Label(principal,text=Loc_Data["10.17"],
                            font="Helvetica {}".format(taille_police))
    spin_reset_col_lab = tk.Label(principal,text=Loc_Data["10.18"],
                                  font="Helvetica {}".format(taille_police))
    spin_u_lab.grid(column=3, row=0)
    spin_l_lab.grid(column=3, row=1)
    spin_d_lab.grid(column=3, row=2)
    spin_r_lab.grid(column=3, row=3)
    spin_v_u_lab.grid(column=3, row=4)
    spin_v_d_lab.grid(column=3, row=5)
    spin_reset_col_lab.grid(column=3, row=6)
    
    val_comm_lab = tk.Label(parcours_comm,text=Loc_Data["10.19"],
                            font="Helvetica {}".format(taille_police))
    anul_comm_lab = tk.Label(parcours_comm,text=Loc_Data["10.20"],
                            font="Helvetica {}".format(taille_police))
    val_comm_lab.grid(column=0, row=0)
    anul_comm_lab.grid(column=0, row=1)
    
    val_suptrip_lab = tk.Label(suppres_triplets,text=Loc_Data["10.21"],
                            font="Helvetica {}".format(taille_police))
    anul_suptrip_lab = tk.Label(suppres_triplets,text=Loc_Data["10.20"],
                            font="Helvetica {}".format(taille_police))
    val_suptrip_lab.grid(column=0, row=0)
    anul_suptrip_lab.grid(column=0, row=1)
    
    if mode == "remap" :
        p_comm_but = tk.Button(principal,font="Helvetica {}".format(taille_police),
                               command=bind_p_comm)
        c_lang_but = tk.Button(principal,font="Helvetica {}".format(taille_police),
                               command=bind_c_lang)
        v_trip_but = tk.Button(principal,font="Helvetica {}".format(taille_police),
                               command=bind_v_trip)
        add_trip_but = tk.Button(principal,font="Helvetica {}".format(taille_police),
                               command=bind_add_trip)
        sup_trip_but = tk.Button(principal,font="Helvetica {}".format(taille_police),
                               command=bind_sup_trip)
        val_trip_but = tk.Button(principal,font="Helvetica {}".format(taille_police),
                               command=bind_val_trip)
        vitesse_plus_but = tk.Button(principal,font="Helvetica {}".format(taille_police),
                               command=bind_vit_plus)
        vitesse_moins_but = tk.Button(principal,font="Helvetica {}".format(taille_police),
                               command=bind_vit_moins)
        
        spin_u_but = tk.Button(principal,font="Helvetica {}".format(taille_police),
                               command=bind_spin_u)
        spin_l_but = tk.Button(principal,font="Helvetica {}".format(taille_police),
                               command=bind_spin_l)
        spin_d_but = tk.Button(principal,font="Helvetica {}".format(taille_police),
                               command=bind_spin_d)
        spin_r_but = tk.Button(principal,font="Helvetica {}".format(taille_police),
                               command=bind_spin_r)
        spin_v_u_but = tk.Button(principal,font="Helvetica {}".format(taille_police),
                               command=bind_spin_v_u)
        spin_v_d_but = tk.Button(principal,font="Helvetica {}".format(taille_police),
                               command=bind_spin_v_d)
        spin_reset_col_but = tk.Button(principal,font="Helvetica {}".format(taille_police),
                               command=bind_spin_reset_col)
        
        val_comm_but = tk.Button(parcours_comm,font="Helvetica {}".format(taille_police),
                               command=bind_val_comm)
        anul_comm_but = tk.Button(parcours_comm,font="Helvetica {}".format(taille_police),
                               command=bind_anul_comm)
        
        val_suptrip_but = tk.Button(suppres_triplets,font="Helvetica {}".format(taille_police),
                               command=bind_val_suptrip)
        anul_suptrip_but = tk.Button(suppres_triplets,font="Helvetica {}".format(taille_police),
                               command=bind_anul_suptrip)
    elif mode == "map" :
        p_comm_but = tk.Label(principal,font="Helvetica {}".format(taille_police))
        c_lang_but = tk.Label(principal,font="Helvetica {}".format(taille_police))
        v_trip_but = tk.Label(principal,font="Helvetica {}".format(taille_police))
        add_trip_but = tk.Label(principal,font="Helvetica {}".format(taille_police))
        sup_trip_but = tk.Label(principal,font="Helvetica {}".format(taille_police))
        val_trip_but = tk.Label(principal,font="Helvetica {}".format(taille_police))
        vitesse_plus_but = tk.Label(principal,font="Helvetica {}".format(taille_police))
        vitesse_moins_but = tk.Label(principal,font="Helvetica {}".format(taille_police))
        
        spin_u_but = tk.Label(principal,font="Helvetica {}".format(taille_police))
        spin_l_but = tk.Label(principal,font="Helvetica {}".format(taille_police))
        spin_d_but = tk.Label(principal,font="Helvetica {}".format(taille_police))
        spin_r_but = tk.Label(principal,font="Helvetica {}".format(taille_police))
        spin_v_u_but = tk.Label(principal,font="Helvetica {}".format(taille_police))
        spin_v_d_but = tk.Label(principal,font="Helvetica {}".format(taille_police))
        spin_reset_col_but = tk.Label(principal,font="Helvetica {}".format(taille_police))
        
        val_comm_but = tk.Label(parcours_comm,font="Helvetica {}".format(taille_police))
        anul_comm_but = tk.Label(parcours_comm,font="Helvetica {}".format(taille_police))
        
        val_suptrip_but = tk.Label(suppres_triplets,font="Helvetica {}".format(taille_police))
        anul_suptrip_but = tk.Label(suppres_triplets,font="Helvetica {}".format(taille_police))
    
    p_comm_but.grid(column=1, row=0)
    c_lang_but.grid(column=1, row=1)
    v_trip_but.grid(column=1, row=2)
    add_trip_but.grid(column=1, row=3)
    sup_trip_but.grid(column=1, row=4)
    val_trip_but.grid(column=1, row=5)
    vitesse_plus_but.grid(column=1, row=8)
    vitesse_moins_but.grid(column=1, row=9)
    
    spin_u_but.grid(column=4, row=0)
    spin_l_but.grid(column=4, row=1)
    spin_d_but.grid(column=4, row=2)
    spin_r_but.grid(column=4, row=3)
    spin_v_u_but.grid(column=4, row=4)
    spin_v_d_but.grid(column=4, row=5)
    spin_reset_col_but.grid(column=4, row=6)
    
    val_comm_but.grid(column=1, row=0)
    anul_comm_but.grid(column=1, row=1)
    
    val_suptrip_but.grid(column=1, row=0)
    anul_suptrip_but.grid(column=1, row=1)
    
    update_aff()
    
    Utils.center_(fen_binds)
    
    fen_binds.transient(root)
    fen_binds.wait_visibility()
    fen_binds.grab_set()
    fen_binds.wait_window()

menu_params = tk.Menu(menubar)
menu_params.add_command(label=Loc_Data["8.2"], command=changer_taille_police)
menu_params.add_separator()
menu_params.add_command(label=Loc_Data["8.3"], command=remap_binds)
menubar.add_cascade(menu=menu_params, label=Loc_Data["8.1"])

def inter_spin():
    global cherche, scrollbar, aspect_value, opinion_value, aspect, opinion
    if interaction_spin.get() == 1 :
        # cas où ne veut pas écrire/cliquer dans les spinbox
        spin["aspect_debut"]["state"] = "readonly"
        spin["aspect_L"]["state"] = "readonly"
        spin["opinion_debut"]["state"] = "readonly"
        spin["opinion_L"]["state"] = "readonly"
        spin["aspect_debut"]["takefocus"] = False
        spin["aspect_L"]["takefocus"] = False
        spin["opinion_debut"]["takefocus"] = False
        spin["opinion_L"]["takefocus"] = False
        
        spin["aspect_debut"].grid(column=1, row=0)
        spin["aspect_L"].grid(column=1, row=1)
        spin["opinion_debut"].grid(column=1, row=0)
        spin["opinion_L"].grid(column=1, row=1)
        aspect["long"].grid(column=0, row=1)
        aspect["debut"].grid(column=0, row=0)
        opinion["long"].grid(column=0, row=1)
        opinion["debut"].grid(column=0, row=0)
        aspect_visual.grid(column=0, row=2, columnspan=2)
        opinion_visual.grid(column=0, row=2, columnspan=2)
        
        plus_vite.grid(column=0, row=1)
        bouton_moins.grid(column=0, row=2)
        label_vitesse.grid(column=0, row=1)
        bouton_plus.grid(column=0, row=0)
        
        modif_button.grid(column=1, row=1)
        
        emergency_visual.grid_forget()
        emergency_aspect["term_label"].grid_forget()
        emergency_aspect["term_entry"].grid_forget()
        emergency_aspect["id_label"].grid_forget()
        emergency_aspect["id_entry"].grid_forget()
        emergency_opinion["term_label"].grid_forget()
        emergency_opinion["term_entry"].grid_forget()
        emergency_opinion["id_label"].grid_forget()
        emergency_opinion["id_entry"].grid_forget()
        emergency_aspect["term_entry"].delete(0, "end")
        emergency_aspect["id_entry"].delete(0, "end")
        emergency_opinion["term_entry"].delete(0, "end")
        emergency_opinion["id_entry"].delete(0, "end")
        
        aspect_selection.grid_forget()
        opinion_selection.grid_forget()
        reset_aspect_but.grid_forget()
        reset_opinion_but.grid_forget()
        
        aspect_value = "{"+Loc_Data["7.2"]+"}"
        opinion_value = "{"+Loc_Data["7.3"]+"}"
        aspect_visual.configure(text=aspect_value)
        opinion_visual.configure(text=opinion_value)
        aspect["L"].set(1)
        aspect["i_debut"].set(-1)
        opinion["L"].set(1)
        opinion["i_debut"].set(-1)
        
        cherche.destroy()
        scrollbar.destroy()
        cherche, scrollbar = crea_texte()
        cherche.update()
        
    elif interaction_spin.get() == 0 :
        # cas où veut écrire/cliquer dans les spinbox
        spin["aspect_debut"]["state"] = "normal"
        spin["aspect_L"]["state"] = "normal"
        spin["opinion_debut"]["state"] = "normal"
        spin["opinion_L"]["state"] = "normal"
        spin["aspect_debut"]["takefocus"] = True
        spin["aspect_L"]["takefocus"] = True
        spin["opinion_debut"]["takefocus"] = True
        spin["opinion_L"]["takefocus"] = True
        
        spin["aspect_debut"].grid(column=1, row=0)
        spin["aspect_L"].grid(column=1, row=1)
        spin["opinion_debut"].grid(column=1, row=0)
        spin["opinion_L"].grid(column=1, row=1)
        aspect["long"].grid(column=0, row=1)
        aspect["debut"].grid(column=0, row=0)
        opinion["long"].grid(column=0, row=1)
        opinion["debut"].grid(column=0, row=0)
        aspect_visual.grid(column=0, row=2, columnspan=2)
        opinion_visual.grid(column=0, row=2, columnspan=2)
        
        modif_button.grid(column=1, row=1)
        
        emergency_visual.grid_forget()
        emergency_aspect["term_label"].grid_forget()
        emergency_aspect["term_entry"].grid_forget()
        emergency_aspect["id_label"].grid_forget()
        emergency_aspect["id_entry"].grid_forget()
        emergency_opinion["term_label"].grid_forget()
        emergency_opinion["term_entry"].grid_forget()
        emergency_opinion["id_label"].grid_forget()
        emergency_opinion["id_entry"].grid_forget()
        emergency_aspect["term_entry"].delete(0, "end")
        emergency_aspect["id_entry"].delete(0, "end")
        emergency_opinion["term_entry"].delete(0, "end")
        emergency_opinion["id_entry"].delete(0, "end")
        
        plus_vite.grid_forget()
        bouton_moins.grid_forget()
        label_vitesse.grid_forget()
        bouton_plus.grid_forget()
        
        aspect_selection.grid_forget()
        opinion_selection.grid_forget()
        reset_aspect_but.grid_forget()
        reset_opinion_but.grid_forget()
        
        reset_spin_selec()
        
        aspect_value = "{"+Loc_Data["7.2"]+"}"
        opinion_value = "{"+Loc_Data["7.3"]+"}"
        aspect_visual.configure(text=aspect_value)
        opinion_visual.configure(text=opinion_value)
        aspect["L"].set(1)
        aspect["i_debut"].set(-1)
        opinion["L"].set(1)
        opinion["i_debut"].set(-1)
        
        cherche.destroy()
        scrollbar.destroy()
        cherche, scrollbar = crea_texte()
        cherche.update()
    
    elif interaction_spin.get() == 2 :
        # cas où veut sélectionner à la main dans le texte les aspects et les opinions
        aspect_selection.grid(column=0, row=0)
        opinion_selection.grid(column=1, row=0)
        reset_aspect_but.grid(column=0, row=1, columnspan=2)
        reset_opinion_but.grid(column=0, row=1, columnspan=2)
        aspect_visual.grid(column=0, row=2, columnspan=2)
        opinion_visual.grid(column=0, row=2, columnspan=2)
        
        spin["aspect_debut"].grid_forget()
        spin["aspect_L"].grid_forget()
        spin["opinion_debut"].grid_forget()
        spin["opinion_L"].grid_forget()
        aspect["long"].grid_forget()
        aspect["debut"].grid_forget()
        opinion["long"].grid_forget()
        opinion["debut"].grid_forget()
        
        emergency_visual.grid_forget()
        emergency_aspect["term_label"].grid_forget()
        emergency_aspect["term_entry"].grid_forget()
        emergency_aspect["id_label"].grid_forget()
        emergency_aspect["id_entry"].grid_forget()
        emergency_opinion["term_label"].grid_forget()
        emergency_opinion["term_entry"].grid_forget()
        emergency_opinion["id_label"].grid_forget()
        emergency_opinion["id_entry"].grid_forget()
        emergency_aspect["term_entry"].delete(0, "end")
        emergency_aspect["id_entry"].delete(0, "end")
        emergency_opinion["term_entry"].delete(0, "end")
        emergency_opinion["id_entry"].delete(0, "end")
        
        modif_button.grid_forget()
        
        plus_vite.grid_forget()
        bouton_moins.grid_forget()
        label_vitesse.grid_forget()
        bouton_plus.grid_forget()
        
        reset_spin_selec()
        
        aspect_value = "{"+Loc_Data["7.2"]+"}"
        opinion_value = "{"+Loc_Data["7.3"]+"}"
        aspect_visual.configure(text=aspect_value)
        opinion_visual.configure(text=opinion_value)
        aspect["L"].set(1)
        aspect["i_debut"].set(-1)
        opinion["L"].set(1)
        opinion["i_debut"].set(-1)
        
        cherche.destroy()
        scrollbar.destroy()
        cherche, scrollbar = crea_texte()
        cherche.update()
        cherche.bind("<ButtonRelease>", fin_manual_selec)
        
        cherche.tag_configure("mot_i", font="Helvetica {}".format(taille_police_review),
                              foreground="hotpink")
        for i in range(len(mots)) :
            if i%2 == 1 :
                    debut_a, line_deb_a, fin_a, line_fin_a = conversion(i, 1)
                    cherche.tag_add("mot_i", "{}.{}".format(line_deb_a,debut_a), "{}.{}".format(line_fin_a,fin_a))
        
    
    elif interaction_spin.get() == 3 :
        # mode de secours pour ajout manuel directement dans les triplets du comm
        emergency_visual.grid(column=0, row=4, columnspan=3, sticky="we")
        emergency_aspect["term_label"].grid(column=0, row=0)
        emergency_aspect["term_entry"].grid(column=1, row=0)
        emergency_aspect["id_label"].grid(column=0, row=1)
        emergency_aspect["id_entry"].grid(column=1, row=1)
        emergency_opinion["term_label"].grid(column=0, row=0)
        emergency_opinion["term_entry"].grid(column=1, row=0)
        emergency_opinion["id_label"].grid(column=0, row=1)
        emergency_opinion["id_entry"].grid(column=1, row=1)
        emergency_aspect["term_entry"].delete(0, "end")
        emergency_aspect["id_entry"].delete(0, "end")
        emergency_opinion["term_entry"].delete(0, "end")
        emergency_opinion["id_entry"].delete(0, "end")
        
        aspect_selection.grid_forget()
        opinion_selection.grid_forget()
        reset_aspect_but.grid_forget()
        reset_opinion_but.grid_forget()
        
        spin["aspect_debut"].grid_forget()
        spin["aspect_L"].grid_forget()
        spin["opinion_debut"].grid_forget()
        spin["opinion_L"].grid_forget()
        aspect["long"].grid_forget()
        aspect["debut"].grid_forget()
        opinion["long"].grid_forget()
        opinion["debut"].grid_forget()
        aspect_visual.grid_forget()
        opinion_visual.grid_forget()
        
        modif_button.grid_forget()
        
        plus_vite.grid_forget()
        bouton_moins.grid_forget()
        label_vitesse.grid_forget()
        bouton_plus.grid_forget()
        
        reset_spin_selec()
        
        cherche.destroy()
        scrollbar.destroy()
        cherche, scrollbar = crea_texte()
        cherche.update()
        
        cherche.tag_configure("mot_i", font="Helvetica {}".format(taille_police_review),
                              foreground="hotpink")
        for i in range(len(mots)) :
            if i%2 == 1 :
                    debut_a, line_deb_a, fin_a, line_fin_a = conversion(i, 1)
                    cherche.tag_add("mot_i", "{}.{}".format(line_deb_a,debut_a), "{}.{}".format(line_fin_a,fin_a))
    
    if interaction_spin.get() != 3 :
        root.bind("<Key-{}>".format(raccourcis["principal"]["p_comm"]), parcourir_comms)
        root.bind("<Key-{}>".format(raccourcis["principal"]["c_lang"]), changer_lang)
        root.bind("<Key-{}>".format(raccourcis["principal"]["v_trip"]), visualisation_triplets)
        root.bind("<Key-{}>".format(raccourcis["principal"]["val_trip"]), val_triplets)
        root.bind("<Key-{}>".format(raccourcis["principal"]["add_trip"]), add_triplet)
        root.bind("<Key-{}>".format(raccourcis["principal"]["sup_trip"]), sup_triplet)
        root.bind("<Key-{}>".format(raccourcis["principal"]["spin_u"]), go_up)
        root.bind("<Key-{}>".format(raccourcis["principal"]["spin_l"]), go_left)
        root.bind("<Key-{}>".format(raccourcis["principal"]["spin_d"]), go_down)
        root.bind("<Key-{}>".format(raccourcis["principal"]["spin_r"]), go_right)
        root.bind("<Key-{}>".format(raccourcis["principal"]["spin_v_u"]), value_up)
        root.bind("<Key-{}>".format(raccourcis["principal"]["spin_v_d"]), value_down)
        root.bind("<Key-{}>".format(raccourcis["principal"]["spin_reset_col"]), reset_spin_selec)
        root.bind("<Key-{}>".format(raccourcis["principal"]["vit_plus"]), vitesse_plus)
        root.bind("<Key-{}>".format(raccourcis["principal"]["vit_moins"]), vitesse_moins)
    else :
        root.unbind("<Key-{}>".format(raccourcis["principal"]["p_comm"]))
        root.unbind("<Key-{}>".format(raccourcis["principal"]["c_lang"]))
        root.unbind("<Key-{}>".format(raccourcis["principal"]["v_trip"]))
        root.unbind("<Key-{}>".format(raccourcis["principal"]["val_trip"]))
        root.unbind("<Key-{}>".format(raccourcis["principal"]["add_trip"]))
        root.unbind("<Key-{}>".format(raccourcis["principal"]["sup_trip"]))
        root.unbind("<Key-{}>".format(raccourcis["principal"]["spin_u"]))
        root.unbind("<Key-{}>".format(raccourcis["principal"]["spin_l"]))
        root.unbind("<Key-{}>".format(raccourcis["principal"]["spin_d"]))
        root.unbind("<Key-{}>".format(raccourcis["principal"]["spin_r"]))
        root.unbind("<Key-{}>".format(raccourcis["principal"]["spin_v_u"]))
        root.unbind("<Key-{}>".format(raccourcis["principal"]["spin_v_d"]))
        root.unbind("<Key-{}>".format(raccourcis["principal"]["spin_reset_col"]))
        root.unbind("<Key-{}>".format(raccourcis["principal"]["vit_plus"]))
        root.unbind("<Key-{}>".format(raccourcis["principal"]["vit_moins"]))
    
    save_config()

menu_options = tk.Menu(menubar)
menu_options.add_radiobutton(label=Loc_Data["8.5"], variable=interaction_spin,
                             value=0, command=inter_spin)
menu_options.add_radiobutton(label=Loc_Data["8.6"], variable=interaction_spin,
                             value=1, command=inter_spin)
menu_options.add_radiobutton(label=Loc_Data["8.7"], variable=interaction_spin,
                             value=2, command=inter_spin)
menu_options.add_radiobutton(label=Loc_Data["8.8"], variable=interaction_spin,
                             value=3, command=inter_spin)
menubar.add_cascade(menu=menu_options, label=Loc_Data["8.4"])

def aff_map_bind():
    remap_binds(mode="map")

compteurs = {}
for lang in Metadata["AvailableLanguage"] :
    compteurs[lang] = {"comms" : 0, "trips" : 0}

def aff_compteurs():
    fen_compteurs = tk.Toplevel(root)
    fen_compteurs.title(Loc_Data["11.1"])
    
    texte = tk.Label(fen_compteurs, text=Loc_Data["11.2"],
                     font="Helvetica {}".format(taille_police), pady=5)
    texte.grid(column=0, row=0, columnspan=3)
    
    
    Dico_lang = Utils.get_lang_dict(Loc_lang)
    r = 1
    c = 0
    widgets_compteurs = {}
    for lang in Metadata["AvailableLanguage"] :
        widgets_compteurs[lang] = {}
        widgets_compteurs[lang]["frame"] = tk.LabelFrame(fen_compteurs, text="En"+" "+Dico_lang[lang]+":",
                                                         font="Helvetica {} bold".format(taille_police), padx=5, pady=5)
        widgets_compteurs[lang]["comms"] = tk.Label(widgets_compteurs[lang]["frame"], text=Loc_Data["11.3"]+" : {}".format(compteurs[lang]["comms"]),
                                                    font="Helvetica {}".format(taille_police), pady=5)
        widgets_compteurs[lang]["trips"] = tk.Label(widgets_compteurs[lang]["frame"], text=Loc_Data["11.4"]+" : {}".format(compteurs[lang]["trips"]),
                                                    font="Helvetica {}".format(taille_police), pady=5)
        widgets_compteurs[lang]["frame"].grid(column=c, row=r)
        widgets_compteurs[lang]["comms"].grid(column=0, row=0)
        widgets_compteurs[lang]["trips"].grid(column=0, row=1)
        c += 1
        if c == 3 :
            r += 1
            c = 0
    
    def quit_fen(*args):
        fen_compteurs.destroy()
    
    Utils.center_(fen_compteurs)
    
    fen_compteurs.bind("<Key-Escape>", quit_fen)
    
    fen_compteurs.transient(root)
    fen_compteurs.wait_visibility()
    fen_compteurs.grab_set()
    fen_compteurs.wait_window()

def update_oddities(comm_identifier):
    global oddities
    oddities.append(comm_identifier)
    
    file = open(WrkDir["out"]+"oddities.txt", "a", encoding="utf8")
    file.write(comm_identifier+"\n")
    file.close()
    
    get_progression()
    indexe_courant["fr"] = indexe_progression["fr"]["todo"][0]
    indexe_courant["en"] = indexe_progression["en"]["todo"][0]
    
    global comm
    comm = comms[lang_comm.lower()][indexe_courant[lang_comm.lower()]]
    
    global bonus_relecture
    if mode_relecture == True or indexe_courant[lang_comm.lower()] in indexe_progression[lang_comm.lower()]["done"] :
        bonus_relecture = " - "+Loc_Data["7.4"]
    else :
        bonus_relecture = ""
    review.configure(text=Loc_Data["7.5"]+" - {} (ID {}){}".format(lang_comm, indexe_courant[lang_comm.lower()],
                     bonus_relecture))
    aspect_visual.configure(text="")
    opinion_visual.configure(text="")
    
    global labeled_triplets
    labeled_triplets.clear()
    list_trip.configure(text="\n"*10)
    
    global aspect, opinion
    aspect["L"].set(1)
    aspect["i_debut"].set(0)
    opinion["L"].set(1)
    opinion["i_debut"].set(0)
    
    global mots, decalage, review_lenght, carac_per_line
    mots, decalage, review_lenght, carac_per_line = get_comm_plus(comm)
    for key in list(spin.keys()) :
        if "debut" in key :
            spin[key].configure(to=review_lenght["mots"]-1)
        else :
            spin[key].configure(to=review_lenght["mots"])
        spin[key].update()
    
    global cherche, scrollbar
    cherche.destroy()
    scrollbar.destroy()
    cherche, scrollbar = crea_texte()
    cherche.bind("<ButtonRelease>", fin_manual_selec)
    cherche.update()
    if interaction_spin.get() == 2 :
        cherche.tag_configure("mot_i", font="Helvetica {}".format(taille_police_review),
                              foreground="hotpink")
        for i in range(len(mots)) :
            if i%2 == 1 :
                debut_a, line_deb_a, fin_a, line_fin_a = conversion(i, 1)
                cherche.tag_add("mot_i", "{}.{}".format(line_deb_a,debut_a), "{}.{}".format(line_fin_a,fin_a))

def decl_odd_comm():
    comm_identifier = lang_comm.lower()+"-"+indexe_courant[lang_comm.lower()]
    message_text = Loc_Data["12.1"]+" {} ".format(comm_identifier)+Loc_Data["12.2"]
    out = messagebox.askyesno(message=message_text, icon="question", title="Confirmation de déclaration")
    if out == True :
        update_oddities(comm_identifier)

menu_aide = tk.Menu(menubar)
menu_aide.add_command(label=Loc_Data["8.10"], command=aff_map_bind)
menu_aide.add_command(label=Loc_Data["8.11"], command=aff_compteurs)
menu_aide.add_separator()
menu_aide.add_command(label=Loc_Data["8.12"], command=decl_odd_comm)
menubar.add_cascade(menu=menu_aide, label=Loc_Data["8.9"])

#%% Fonction pour mettre à jour le compteur de commentaires & triplets

def update_compteurs(from_save=False, **kwargs) :
    global compteurs
    if from_save == False :
        if "nb_trips" in list(kwargs.keys()) and "langue" in list(kwargs.keys()) :
            if type(kwargs["nb_trips"]) == int and type(kwargs["langue"]) :
                if kwargs["nb_trips"] > 0 :
                    compteurs[kwargs["langue"]]["comms"] += 1
                    compteurs[kwargs["langue"]]["trips"] += kwargs["nb_trips"]
    
    else :
        for langue in Metadata["AvailableLanguage"] :
            data = Utils.load_data(file_name[langue])
            
            for line in data :
                if line != "\n" :
                    compteurs[langue]["comms"] += 1
                    compteurs[langue]["trips"] += len(line.split("\|/")[2:-1])
update_compteurs(from_save=True)

#%% Widget de visualisation du commentaire

lang_comm = Metadata["AvailableLanguage"][0].capitalize()
bonus_relecture = ""
if mode_relecture == True or indexe_courant[lang_comm.lower()] in indexe_progression[lang_comm.lower()]["done"] :
    bonus_relecture = " - "+Loc_Data["7.4"]
review = tk.LabelFrame(root, text=Loc_Data["7.5"]+" - {} (ID {}){}".format(lang_comm, indexe_courant[lang_comm.lower()],
                       bonus_relecture),
                       font="Helvetica {} bold".format(taille_police), padx=5)
review.grid(column=2, row=0, rowspan=3)

def crea_texte(master=review):
    widget = tk.Text(master, wrap="word")
    
    widget.tag_configure("aspect", foreground="orange", font="Helvetica {}".format(taille_police_review))
    widget.tag_configure("opinion", foreground="blue", font="Helvetica {}".format(taille_police_review))
    widget.tag_configure("normal", font="Helvetica {}".format(taille_police_review))
    
    # https://www.utf8-chartable.de/unicode-utf8-table.pl
    # https://fr.wikipedia.org/wiki/UTF-8
    # n'a pas l'air d'aimer les émojis (point de code à 4 hexa max au lieu de 6)
    # tcl/tk ne peut gérer pour le moment que les les Unicode allant de
    # U+0000 à U+FFFF (càd le Plan multilingue de base cf.
    # https://fr.wikipedia.org/wiki/Table_des_caract%C3%A8res_Unicode_(0000-FFFF) )
    widget.insert("1.0", comm)
    widget["state"] = "disabled"
    widget.tag_add("normal", "1.0", "end")
    
    if master == review :
        widget.configure(width=85)
        widget.configure(height=45)
        widget.grid(column=0, row=0, sticky="nw")
        
        scroll = tk.Scrollbar(master, orient="vertical", command=widget.yview)
        widget.configure(yscrollcommand=scroll.set)
        scroll.grid(column=1, row=0, sticky="ns")
        return (widget, scroll)
    else :
        widget.configure(width=160)
        widget.configure(height=40)
        widget.grid(column=0, row=2, columnspan=2)
        return (widget)
cherche, scrollbar = crea_texte()

#%% Création des Widgets de sélection

triplet_selec = tk.LabelFrame(root, text=Loc_Data["7.6"],
                              font="Helvetica {} bold".format(taille_police), padx=5, pady=5)
triplet_selec.grid(column=0, row=0, columnspan=2)

mode2_term_selection = tk.IntVar(value=0)

aspect_frame = tk.LabelFrame(triplet_selec, text=Loc_Data["7.7"],
                             font="Helvetica {} bold".format(taille_police))
aspect = {"long" : tk.Label(aspect_frame, text=Loc_Data["7.8"],
                            font="Helvetica {}".format(taille_police), pady=5),
          "L" : tk.IntVar(value=1),
          "debut" : tk.Label(aspect_frame, text=Loc_Data["7.9"],
                             font="Helvetica {}".format(taille_police), pady=5),
          "i_debut" : tk.IntVar(value=-1)}
aspect_selection = tk.Radiobutton(aspect_frame, text=Loc_Data["7.10"],
                                  variable=mode2_term_selection, value=0, takefocus=False,
                                  font="Helvetica {}".format(taille_police))
aspect_value = "{"+Loc_Data["7.2"]+"}"
aspect_visual = tk.Label(aspect_frame, text=aspect_value, borderwidth=1, relief="solid",
                         font="Helvetica {}".format(taille_police), wraplength=200)

def reset_term(what=None):
    global previous_manual_selection, manual_selec_terms, aspect_value, opinion_value
    previous_manual_selection = ()
    if what == "aspect" :
        manual_selec_terms["aspect"] = []
        aspect_value = "{"+Loc_Data["7.2"]+"}"
        aspect_visual.configure(text=aspect_value)
        cherche.tag_remove("aspect", "1.0", "end")
    elif what == "opinion" :
        manual_selec_terms["opinion"] = []
        opinion_value = "{"+Loc_Data["7.3"]+"}"
        opinion_visual.configure(text=opinion_value)
        cherche.tag_remove("opinion", "1.0", "end")
    
    cherche.tag_configure("mot_i", font="Helvetica {}".format(taille_police_review),
                          foreground="hotpink")
    for i in range(len(mots)) :
        if i%2 == 1 :
            debut_a, line_deb_a, fin_a, line_fin_a = conversion(i, 1)
            cherche.tag_add("mot_i", "{}.{}".format(line_deb_a,debut_a), "{}.{}".format(line_fin_a,fin_a))
    
def reset_aspect(*args):
    reset_term(what="aspect")

reset_aspect_but = tk.Button(aspect_frame, text=Loc_Data["7.11"], command=reset_aspect,
                             font="Helvetica {}".format(taille_police), takefocus=False)
    
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
        add_button["state"] = "disabled"
    else :
        add_button["state"] = "active"
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

def sentiment_emergency_update_wrapper():
    if interaction_spin.get() == 3 :
        emergency_visual_update()

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

emergency_aspect = {}
emergency_aspect["term_value"] = tk.StringVar()
emergency_aspect["term_label"] = tk.Label(aspect_frame, text=Loc_Data["7.12"],
                                          font="Helvetica {}".format(taille_police))
emergency_aspect["term_entry"] = tk.Entry(aspect_frame, textvariable=emergency_aspect["term_value"],
                                          validate="all", validatecommand=validate_term_entry_wrapper,
                                          font="Helvetica {}".format(taille_police))
emergency_aspect["term_value"].trace_variable("w", emergency_visual_update)
emergency_aspect["id_value"] = tk.StringVar()
emergency_aspect["id_label"] = tk.Label(aspect_frame, text=Loc_Data["7.13"],
                                        font="Helvetica {}".format(taille_police))
emergency_aspect["id_entry"] = tk.Entry(aspect_frame, textvariable=emergency_aspect["id_value"],
                                        validate="all", validatecommand=validate_id_entry_wrapper,
                                        font="Helvetica {}".format(taille_police))
emergency_aspect["id_value"].trace_variable("w", emergency_visual_update)

aspect_frame.grid(column=0, row=0, rowspan=3)
if interaction_spin.get() not in [2,3] :
    aspect["long"].grid(column=0, row=1)
    aspect["debut"].grid(column=0, row=0)
if interaction_spin.get() == 2 :
    aspect_selection.grid(column=0, row=0)
    reset_aspect_but.grid(column=0, row=1, columnspan=2)
if interaction_spin.get() != 3 :
    aspect_visual.grid(column=0, row=2, columnspan=2)
else :
    emergency_aspect["term_label"].grid(column=0, row=0)
    emergency_aspect["term_entry"].grid(column=1, row=0)
    emergency_aspect["id_label"].grid(column=0, row=1)
    emergency_aspect["id_entry"].grid(column=1, row=1)

opinion_frame = tk.LabelFrame(triplet_selec, text=Loc_Data["7.14"],
                              font="Helvetica {} bold".format(taille_police))
opinion = {"long" : tk.Label(opinion_frame, text=Loc_Data["7.15"],
                             font="Helvetica {}".format(taille_police)),
          "L" : tk.IntVar(value=1),
          "debut" : tk.Label(opinion_frame, text=Loc_Data["7.16"],
                             font="Helvetica {}".format(taille_police)),
          "i_debut" : tk.IntVar(value=-1)}
opinion_selection = tk.Radiobutton(opinion_frame, text=Loc_Data["7.17"],
                                  variable=mode2_term_selection, value=1, takefocus=False,
                                  font="Helvetica {}".format(taille_police))
opinion_value = "{"+Loc_Data["7.3"]+"}"
opinion_visual = tk.Label(opinion_frame, text=opinion_value, borderwidth=1, relief="solid",
                          font="Helvetica {}".format(taille_police), wraplength=200)

def reset_opinion(*args):
    reset_term(what="opinion")

reset_opinion_but = tk.Button(opinion_frame, text=Loc_Data["7.18"], command=reset_opinion,
                             font="Helvetica {}".format(taille_police), takefocus=False)

emergency_opinion = {}
emergency_opinion["term_value"] = tk.StringVar()
emergency_opinion["term_label"] = tk.Label(opinion_frame, text=Loc_Data["7.19"],
                                          font="Helvetica {}".format(taille_police))
emergency_opinion["term_entry"] = tk.Entry(opinion_frame, textvariable=emergency_opinion["term_value"],
                                          validate="all", validatecommand=validate_term_entry_wrapper,
                                          font="Helvetica {}".format(taille_police))
emergency_opinion["term_value"].trace_variable("w", emergency_visual_update)
emergency_opinion["id_value"] = tk.StringVar()
emergency_opinion["id_label"] = tk.Label(opinion_frame, text=Loc_Data["7.20"],
                                        font="Helvetica {}".format(taille_police))
emergency_opinion["id_entry"] = tk.Entry(opinion_frame, textvariable=emergency_opinion["id_value"],
                                        validate="all", validatecommand=validate_id_entry_wrapper,
                                        font="Helvetica {}".format(taille_police))
emergency_opinion["id_value"].trace_variable("w", emergency_visual_update)

opinion_frame.grid(column=1, row=0, rowspan=3)
if interaction_spin.get() not in [2,3] :
    opinion["long"].grid(column=0, row=1)
    opinion["debut"].grid(column=0, row=0)
if interaction_spin.get() == 2 :
    opinion_selection.grid(column=0, row=0)
    reset_opinion_but.grid(column=0, row=1, columnspan=2)
if interaction_spin.get() != 3 :
    opinion_visual.grid(column=0, row=2, columnspan=2)
else :
    emergency_opinion["term_label"].grid(column=0, row=0)
    emergency_opinion["term_entry"].grid(column=1, row=0)
    emergency_opinion["id_label"].grid(column=0, row=1)
    emergency_opinion["id_entry"].grid(column=1, row=1)

def conversion(debut, L, portion=None):
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
    
    return (i_deb, line_deb, i_fin, line_fin)

if interaction_spin.get() == 2 :
    cherche.tag_configure("mot_i", font="Helvetica {}".format(taille_police_review),
                          foreground="hotpink")
    for i in range(len(mots)) :
        if i%2 == 1 :
            debut_a, line_deb_a, fin_a, line_fin_a = conversion(i, 1)
            cherche.tag_add("mot_i", "{}.{}".format(line_deb_a,debut_a), "{}.{}".format(line_fin_a,fin_a))

changement_ok = True

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
    
    global cherche, scrollbar
    cherche.destroy()
    scrollbar.destroy()
    cherche, scrollbar = crea_texte()
    cherche.bind("<ButtonRelease>", fin_manual_selec)
    if debut_aspect != -1 :
        cherche.tag_add("aspect", "{}.{}".format(line_deb_a,debut_a), "{}.{}".format(line_fin_a,fin_a))
    if debut_opinion != -1 :
        cherche.tag_add("opinion", "{}.{}".format(line_deb_o,debut_o), "{}.{}".format(line_fin_o,fin_o))
    
    adapt = {"decal" : 180, "deb" : 200}
    if what == "aspect" :
        if debut_aspect >= adapt["deb"] :
            debut_a, line_deb_a, fin_a, line_fin_a = conversion(debut_aspect-adapt["decal"], 1)
            cherche.yview_pickplace("{}.{}".format(line_deb_a,debut_a))
    elif what == "opinion" :
        if debut_opinion >= adapt["deb"] :
            debut_o, line_deb_o, fin_o, line_fin_o = conversion(debut_opinion-adapt["decal"], 1)
            cherche.yview_pickplace("{}.{}".format(line_deb_o,debut_o))

def modif_aspect():
    modif_value(what="aspect")
def modif_opinion():
    modif_value(what="opinion")

spin = {"aspect_debut" : tk.Spinbox(aspect_frame, from_=-1, to=review_lenght["mots"]-1, textvariable=aspect["i_debut"],
                                    command=modif_aspect, wrap=True),
        "aspect_L" : tk.Spinbox(aspect_frame, from_=1, to=review_lenght["mots"], textvariable=aspect["L"],
                                    command=modif_aspect, wrap=True),
        "opinion_debut" : tk.Spinbox(opinion_frame, from_=-1, to=review_lenght["mots"]-1, textvariable=opinion["i_debut"],
                                    command=modif_opinion, wrap=True),
        "opinion_L" : tk.Spinbox(opinion_frame, from_=1, to=review_lenght["mots"], textvariable=opinion["L"],
                                    command=modif_opinion, wrap=True)}
if interaction_spin.get() not in [2,3] :
    spin["aspect_debut"].grid(column=1, row=0)
    spin["aspect_L"].grid(column=1, row=1)
    spin["opinion_debut"].grid(column=1, row=0)
    spin["opinion_L"].grid(column=1, row=1)
if interaction_spin.get() == 1 :
    spin["aspect_debut"]["state"] = "readonly"
    spin["aspect_L"]["state"] = "readonly"
    spin["opinion_debut"]["state"] = "readonly"
    spin["opinion_L"]["state"] = "readonly"
    spin["aspect_debut"]["takefocus"] = False
    spin["aspect_L"]["takefocus"] = False
    spin["opinion_debut"]["takefocus"] = False
    spin["opinion_L"]["takefocus"] = False

sentiment_value = tk.StringVar(value="NEU")
sentiment = {"negatif" : tk.Radiobutton(triplet_selec, text=Loc_Data["7.22"], variable=sentiment_value,
                                        value="NEG", font="Helvetica {}".format(taille_police),
                                        command=sentiment_emergency_update_wrapper),
             "neutre" : tk.Radiobutton(triplet_selec, text=Loc_Data["7.23"], variable=sentiment_value,
                                       value="NEU", font="Helvetica {}".format(taille_police),
                                       command=sentiment_emergency_update_wrapper),
             "positif" : tk.Radiobutton(triplet_selec, text=Loc_Data["7.24"], variable=sentiment_value,
                                        value="POS", font="Helvetica {}".format(taille_police),
                                        command=sentiment_emergency_update_wrapper)}
sentiment_label = tk.Label(triplet_selec, text=Loc_Data["7.21"],
                           font="Helvetica {} bold".format(taille_police), padx=5)
sentiment_label.grid(column=2, row=0)
sentiment["negatif"].grid(column=2, row=1)
sentiment["neutre"].grid(column=2, row=2)
sentiment["positif"].grid(column=2, row=3)

emergency_visual = tk.Label(triplet_selec, relief="solid", font="Helvetica 14", justify="center")
emergency_visual.configure(text="\|/"+aspect_value+"<|>"+opinion_value+"<|>"+sentiment_value.get()+"<|>"+"[-1]"+"<|>"+"[-1]"+"\|/")
if interaction_spin.get() == 3 :
    emergency_visual.grid(column=0, row=4, columnspan=3, sticky="we")

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

plus_vite = tk.LabelFrame(root, text=Loc_Data["7.25"]+"\n"+Loc_Data["7.26"], font="Helvetica {} bold".format(taille_police),
                             padx=5, pady=5)
bouton_moins = tk.Button(plus_vite, text="-",font="Helvetica {}".format(taille_police),
                         command=vitesse_moins, takefocus=False, padx=60)
label_vitesse = tk.Label(plus_vite, text="{}".format(10**vitesse), padx=60,
                         font="Helvetica {}".format(taille_police))
bouton_plus = tk.Button(plus_vite, text="+",font="Helvetica {}".format(taille_police),
                         command=vitesse_plus, takefocus=False, padx=60)
if interaction_spin.get() == 1 :
    plus_vite.grid(column=0, row=1)
    bouton_moins.grid(column=0, row=2)
    label_vitesse.grid(column=0, row=1)
    bouton_plus.grid(column=0, row=0)

triplet_visu = tk.LabelFrame(root, text=Loc_Data["7.27"], font="Helvetica {} bold".format(taille_police),
                             padx=5, pady=5)
triplet_visu.grid(column=1, row=1)
list_trip = tk.Label(triplet_visu, text="\n"*10, wraplength=550, width=48,
                     font="Helvetica {}".format(taille_police))
list_trip.grid(column=0, row=0, columnspan=3)

labeled_triplets = []

#%% Fonctions de gestion des triplets dans un commentaire :
#   - ajout
#   - suppression
#   - modification

def add_triplet(*args): # TODO : ajouter une sécu sur les mots à la fois aspect et opinion
    """
    permet de :
        - ajouter des triplets à une variable interne utilisée plus tard lors
          la sauvegarde du travail fait sur le commentaire
        - ajouter ces mêmes triplets dans une liste visible sur l'interface
        - gérer les possibles erreurs faites lors de la sélection des triplets
    """
    global changement_ok
    if changement_ok == True :
        changement_ok = False
    
    def troncate(list_index, len_mots) :
        troncate_index = None
        for i in range(len(list_index)) :
            if list_index[i] == len_mots :
                troncate_index = i
                break
        return (list_index[:troncate_index])
    
    global labeled_triplets, aspect_value, opinion_value, manual_selec_terms
    
    if sentiment_value.get() != "" and aspect_value != "" and opinion_value != "" :
        if interaction_spin.get() in [0,1] :
            indexes_aspect = [int(aspect["i_debut"].get())]
            indexes_opinion = [int(opinion["i_debut"].get())]
            if aspect_value != "{"+Loc_Data["7.2"]+"}" :
                for i in range(1, int(aspect["L"].get())) :
                    indexes_aspect.append(int(aspect["i_debut"].get())+i)
            if opinion_value != "{"+Loc_Data["7.3"]+"}" :
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
        
        new = [aspect_value, opinion_value, sentiment_value.get(), indexes_aspect, indexes_opinion]
        if new not in labeled_triplets :
            if not (aspect_value == "{"+Loc_Data["7.2"]+"}" and opinion_value == "{"+Loc_Data["7.3"]+"}") :
                cond = True
                for triplet in labeled_triplets :
                    if new[3:4+1] == triplet[3:4+1] :
                        cond = False
                        break
                if cond == True :
                    # vérifier si aspect != opinion
                    if indexes_aspect != indexes_opinion :
                        labeled_triplets.insert(0, new)
                        
                        texte_list_trip = "{}, {}, {}".format(aspect_value, opinion_value, sentiment_value.get())
                        for i in range(9) :
                            try :
                                a = labeled_triplets[i+1][0]
                                b = labeled_triplets[i+1][1]
                                c = labeled_triplets[i+1][2]
                                texte_list_trip += "\n{}, {}, {}".format(a, b, c)
                            except :
                                texte_list_trip += "\n"
                        list_trip.configure(text=texte_list_trip)
                        
                        if interaction_spin.get() in [0,1] :
                            # aspect["L"].set(1)
                            # aspect["i_debut"].set(-1)
                            # opinion["L"].set(1)
                            # opinion["i_debut"].set(-1)
                            None
                        elif interaction_spin.get() == 2 :
                            reset_aspect()
                            reset_opinion()
                            mode2_term_selection.set(0)
                        elif interaction_spin.get() == 3 :
                            emergency_aspect["term_entry"].delete(0, "end")
                            emergency_aspect["id_entry"].delete(0, "end")
                            emergency_opinion["term_entry"].delete(0, "end")
                            emergency_opinion["id_entry"].delete(0, "end")
                    
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
        
    else :
        if sentiment_value.get() == "" :
            messagebox.showwarning(title=Loc_Data["13.1"], message=Loc_Data["13.3"]+"\n"+Loc_Data["13.8"])
        elif aspect_value == "" or opinion_value == "" :
            messagebox.showwarning(title=Loc_Data["13.1"], message=Loc_Data["13.3"]+"\n"+Loc_Data["13.9"])

def sup_triplet(*args, modif=False):
    """
    même chose que add_triplet mais pour la suppression
    se fait sur une fenêtre à part
    utilisé pour faire également la modification
    """
    
    global changement_ok
    if changement_ok == True :
        changement_ok = False
    
    global labeled_triplets
    
    temp = []
    for item in labeled_triplets :
        temp.append(item[:3])
    list_triplets = tk.StringVar(value=temp)
    
    def fonc_annuler(*args):
        selection.grab_release()
        selection.destroy()
    
    def fonc_valider(*args):
        indexes = list(liste_selec.curselection())
        
        if len(indexes) > 0 :
            message_text = Loc_Data["14.6"]
            for element in indexes :
                message_text += "\n\t{}".format(temp[element])
            out = messagebox.askyesno(message=message_text, icon="question", title=Loc_Data["14.5"])
            if out == True :
                indexes.reverse()
                for element in indexes :
                    labeled_triplets.remove(labeled_triplets[element])
                
                try :
                    texte_list_trip = "{}, {}, {}".format(labeled_triplets[0][0],
                                       labeled_triplets[0][1], labeled_triplets[0][2])
                except :
                    texte_list_trip = "\n"
                for i in range(5) :
                    try :
                        a = labeled_triplets[i+1][0]
                        b = labeled_triplets[i+1][1]
                        c = labeled_triplets[i+1][2]
                        texte_list_trip += "\n{}, {}, {}".format(a, b, c)
                    except :
                        texte_list_trip += "\n"
                list_trip.configure(text=texte_list_trip)
            fonc_annuler()
    
    def fonc_modifier(*args):
        indexes = list(liste_selec.curselection())
        
        if len(indexes) > 0 :
            message_text = Loc_Data["14.8"]
            for element in indexes :
                message_text += "\n\t{}".format(temp[element])
            out = messagebox.askyesno(message=message_text, icon="question", title=Loc_Data["14.7"])
            if out == True :
                # ajouter support pour le mode de sélection 2
                
                global aspect, opinion
                aspect["L"].set(len(labeled_triplets[indexes[0]][3]))
                aspect["i_debut"].set(labeled_triplets[indexes[0]][3][0])
                opinion["L"].set(len(labeled_triplets[indexes[0]][4]))
                opinion["i_debut"].set(labeled_triplets[indexes[0]][4][0])
                
                modif_aspect()
                modif_opinion()
                
                labeled_triplets.remove(labeled_triplets[indexes[0]])
                try :
                    texte_list_trip = "{}, {}, {}".format(labeled_triplets[0][0],
                                       labeled_triplets[0][1], labeled_triplets[0][2])
                except :
                    texte_list_trip = "\n"
                for i in range(9) :
                    try :
                        a = labeled_triplets[i+1][0]
                        b = labeled_triplets[i+1][1]
                        c = labeled_triplets[i+1][2]
                        texte_list_trip += "\n{}, {}, {}".format(a, b, c)
                    except :
                        texte_list_trip += "\n"
                list_trip.configure(text=texte_list_trip)
            fonc_annuler()
        
    
    selection = tk.Toplevel(root)
    if modif == False :
        selection.title(Loc_Data["14.1"])
        select_mode = "extended"
    else :
        selection.title(Loc_Data["14.2"])
        select_mode = "browse"
    #selection.resizable(False, False)
    
    liste_selec = tk.Listbox(selection, height=10, listvariable=list_triplets,
                             selectmode=select_mode, width=50)
    liste_selec.configure(font="Helvetica {}".format(taille_police))
    if modif == False :
        valider = tk.Button(selection, text=Loc_Data["14.3"], font="Helvetica {}".format(taille_police),
                            command=fonc_valider)
    else :
        valider = tk.Button(selection, text=Loc_Data["14.3"], font="Helvetica {}".format(taille_police),
                            command=fonc_modifier)
    annuler = tk.Button(selection, text=Loc_Data["14.4"], font="Helvetica {}".format(taille_police),
                        command=fonc_annuler)
    for i in range(0,len(labeled_triplets),2):
        liste_selec.itemconfigure(i, background='#f0f0ff')
    
    liste_selec.grid(column=0, row=0, rowspan=2)
    valider.grid(column=1, row=0)
    annuler.grid(column=1, row=1)
    
    Utils.center_(selection)
    
    selection.bind("<Key-{}>".format(raccourcis["suppres_triplets"]["annuler"]), fonc_annuler)
    selection.bind("<Key-{}>".format(raccourcis["suppres_triplets"]["valider"]), fonc_valider)
    
    selection.transient(root)
    selection.wait_visibility()
    selection.grab_set()
    selection.wait_window()

def modif_triplet(*args):
    sup_triplet(modif=True)

add_button = tk.Button(triplet_visu, text=Loc_Data["7.28"], command=add_triplet,
                       font="Helvetica {}".format(taille_police),takefocus=False)
modif_button = tk.Button(triplet_visu, text=Loc_Data["7.29"], command=modif_triplet,
                       font="Helvetica {}".format(taille_police),takefocus=False)
sup_button = tk.Button(triplet_visu, text=Loc_Data["7.30"], command=sup_triplet,
                       font="Helvetica {}".format(taille_police),takefocus=False)
add_button.grid(column=0, row=1)
if interaction_spin.get() not in [2,3] :
    modif_button.grid(column=1, row=1)
sup_button.grid(column=2, row=1)

#%% Fonctions pour la visualisation d'un commentaire pour
#   - commentaire en cours
#   - nouveau commentaire à sauvegarder
#   - nouvelle version d'un commentaire déjà sauvergardé

def get_versions():
    version = []
    data = Utils.load_data(file_name[lang_comm.lower()])
    
    for line in data :
        if line.split("\|/")[0] == indexe_courant[lang_comm.lower()] :
            line = line.split("\|/")
            for element in line[2:] :
                if element != "\n" :
                    temp_trip = []
                    
                    element = element.split("<|>")
                    for k in [0,1] :
                        temp_list = []
                        temp = element[k][1:len(element[k])-1].split(",")
                        temp_list.append(temp[0][1:len(temp[0])-1])
                        for i in range(1,len(temp)) :
                            temp_list.append(temp[i][2:len(temp[i])-1])
                        temp_trip.append(temp_list)
                    
                    temp_trip.append(element[2])
                    
                    for k in [3,4] :
                        temp_list = []
                        temp = element[k][1:len(element[k])-1].split(",")
                        temp_list.append(int(temp[0]))
                        for i in range(1,len(temp)) :
                            temp_list.append(int(temp[i][1:]))
                        temp_trip.append(temp_list)
                    
                    version.append(temp_trip)
            break
    return (version)

def rearrange_triplets(triplets):
    def extract_first_index_of_aspect(item):
        return (item[3][0])
    def extract_first_index_of_opinion(item):
        return (item[4][0])
    
    out = sorted(sorted(triplets, key=extract_first_index_of_aspect), key=extract_first_index_of_opinion)
    return (out)

def visualisation_triplets(*args):
    liste_fonds = {"POS" : "powderblue",
                   "NEU" : "peachpuff",
                   "NEG" : "tan"}
    
    def get_possible_colors(num_triplet, sentiment):
        liste_couleurs = [
            "darkblue",
            "darkgreen",
            "crimson",
            "deeppink4"
        ]
        color = liste_couleurs[num_triplet%len(liste_couleurs)]
        return (color, liste_fonds[sentiment])
    
    def affichage_triplet(liste_triplets):
        try :
            global visu
            visu.destroy()
        except :
            None
        visu = crea_texte(master=visu_triplets_fen)
        
        superpositions = {}
        for trip in liste_triplets :
            for item in trip[3] :
                if str(item) not in list(superpositions.keys()) :
                    superpositions[str(item)] = 1
                else :
                    superpositions[str(item)] += 1
            for item in trip[4] :
                if str(item) not in list(superpositions.keys()) :
                    superpositions[str(item)] = 1
                else :
                    superpositions[str(item)] += 1
        part = {}
        for key in list(superpositions.keys()) :
            if superpositions[key] > 1 :
                part[key] = 1
        
        ordered_triplets = rearrange_triplets(liste_triplets)
        for i in range(len(ordered_triplets)) :
            trip = ordered_triplets[i]
            indice_aspect = trip[3]
            indice_opinion = trip[4]
            value_sentiment = trip[2]
            
            color, fond = get_possible_colors(i, value_sentiment)
            
            visu.tag_configure(str(i)+"a", foreground=color, background=fond,
                               font="Helvetica {} italic".format(taille_police_review))
            visu.tag_configure(str(i)+"o", foreground=color, background=fond,
                               font="Helvetica {} bold".format(taille_police_review))
            
            for mot in indice_aspect :
                if mot != -1 :
                    if superpositions[str(mot)] == 1 :
                        debut_a, line_deb_a, fin_a, line_fin_a = conversion(mot, 1)
                        visu.tag_add(str(i)+"a", "{}.{}".format(line_deb_a,debut_a), "{}.{}".format(line_fin_a,fin_a))
                    else :
                        debut_a, line_deb_a, fin_a, line_fin_a = conversion(mot, 1, portion=[superpositions[str(mot)],part[str(mot)]])
                        visu.tag_add(str(i)+"a", "{}.{}".format(line_deb_a,debut_a), "{}.{}".format(line_fin_a,fin_a))
                        if part[str(mot)] < superpositions[str(mot)] :
                            part[str(mot)] += 1
            for mot in indice_opinion :
                if mot != -1 :
                    if superpositions[str(mot)] == 1 :
                        debut_a, line_deb_a, fin_a, line_fin_a = conversion(mot, 1)
                        visu.tag_add(str(i)+"o", "{}.{}".format(line_deb_a,debut_a), "{}.{}".format(line_fin_a,fin_a))
                    else :
                        debut_a, line_deb_a, fin_a, line_fin_a = conversion(mot, 1, portion=[superpositions[str(mot)],part[str(mot)]])
                        visu.tag_add(str(i)+"o", "{}.{}".format(line_deb_a,debut_a), "{}.{}".format(line_fin_a,fin_a))
                        if part[str(mot)] < superpositions[str(mot)] :
                            part[str(mot)] += 1
    
    def fonc_annuler():
        visu_triplets_fen.grab_release()
        visu_triplets_fen.destroy()
    def fonc_valider():
        global confirmation
        confirmation = True
        fonc_annuler()
    
    def change_version():
        texte = version_but["text"]
        version_name = texte[len(texte)-8:len(texte)-1]
        if version_name[0] == " " :
            version_name = version_name[1:]
        
        if version_name == Loc_Data["15.3"] :
            version_name = Loc_Data["15.4"]
        elif version_name == Loc_Data["15.4"] :
            version_name = Loc_Data["15.3"]
        version_but.configure(text=Loc_Data["15.2"]+" {})".format(version_name))
        
        version = {Loc_Data["15.4"] : get_versions(),
                   Loc_Data["15.3"] : labeled_triplets}
        affichage_triplet(version[version_name])
    
    def valider_version():
        texte = version_but["text"]
        version_name = texte[len(texte)-8:len(texte)-1]
        if version_name[0] == " " :
            version_name = version_name[1:]
        
        message_text = Loc_Data["15.14"]+" "
        if version_name == Loc_Data["15.4"] :
            message_text += Loc_Data["15.15"]+" "
        elif version_name == Loc_Data["15.3"] :
            message_text += Loc_Data["15.16"]+" "
        message_text += Loc_Data["15.17"]
        out = messagebox.askyesno(message=message_text, icon="question",
                                  title=Loc_Data["15.18"])
        global doublon_dealing
        if out == True and version_name == Loc_Data["15.4"] :
            doublon_dealing = -1
        elif out == True and version_name == Loc_Data["15.3"] :
            doublon_dealing = 1
        
        fonc_annuler()
    
    visu_triplets_fen = tk.Toplevel()
    visu_triplets_fen.title(Loc_Data["15.1"])
    #visu_triplets_fen.resizable(False, False)
    
    affichage_triplet(labeled_triplets)
    
    version_but = tk.Button(visu_triplets_fen, text=Loc_Data["15.2"]+" "+Loc_Data["15.3"]+")",
                            command=change_version, font="Helvetica {}".format(taille_police))
    valider_but = tk.Button(visu_triplets_fen, text=Loc_Data["15.5"],
                            command=valider_version, font="Helvetica {}".format(taille_police))
    
    OK_but = tk.Button(visu_triplets_fen, text=Loc_Data["15.6"],
                            command=fonc_valider, font="Helvetica {}".format(taille_police))
    annuler_but = tk.Button(visu_triplets_fen, text=Loc_Data["15.7"],
                            command=fonc_annuler, font="Helvetica {}".format(taille_police))
    
    if "validation_doublon" in args :
        version_but.grid(column=0, row=1)
        valider_but.grid(column=1, row=1)
    elif "confirmation" in args :
        OK_but.grid(column=0, row=1)
        annuler_but.grid(column=1, row=1)
    
    legende_frame = tk.LabelFrame(visu_triplets_fen, text=Loc_Data["15.19"],
                                  font="Helvetica {} bold".format(taille_police))
    legende = tk.Text(legende_frame, wrap="word", width=160, height=10)
    legende_frame.grid(column=0, row=0, columnspan=2)
    legende.grid(column=0, row=0)
    legende.tag_configure("positif", font="Helvetica {}".format(taille_police),
                          background=liste_fonds["POS"])
    legende.tag_configure("negatif", font="Helvetica {}".format(taille_police),
                          background=liste_fonds["NEG"])
    legende.tag_configure("neutre", font="Helvetica {}".format(taille_police),
                          background=liste_fonds["NEU"])
    legende.tag_configure("normal", font="Helvetica {}".format(taille_police))
    
    legende.insert("1.0", Loc_Data["15.8"]+"\n", "normal")
    legende.insert("2.0", "XXXXXXX", "positif")
    legende.insert("2.end", " : "+Loc_Data["15.9"]+"\n", "normal")
    legende.insert("3.0", "XXXXXXX", "negatif")
    legende.insert("3.end", " : "+Loc_Data["15.10"]+"\n", "normal")
    legende.insert("4.0", "XXXXXXX", "neutre")
    legende.insert("4.end", " : "+Loc_Data["15.11"]+"\n", "normal")
    legende.insert("5.0", Loc_Data["15.12"]+"\n", "normal")
    legende.insert("6.0", Loc_Data["15.13"], "normal")
    
    Utils.center_(visu_triplets_fen)
    
    visu_triplets_fen.transient(root)
    visu_triplets_fen.wait_visibility()
    visu_triplets_fen.grab_set()
    visu_triplets_fen.wait_window()

doublon_dealing = None
confirmation = False

#%% Fonctions pour sauvegarder le commentaire labélisé

def save_update(out_to_save):
    saved = True
    try :
        file = open(file_name[lang_comm.lower()], "a", encoding="utf8")
        file.write(out_to_save+"\n")
        file.close()
    except :
        saved = False
    
    if saved == True :
        get_progression()
        for langue in Metadata["AvailableLanguage"] :
            indexe_courant[langue] = indexe_progression[langue]["todo"][0]
        
        global comm
        comm = comms[lang_comm.lower()][indexe_courant[lang_comm.lower()]]
        
        global bonus_relecture
        if mode_relecture == True or indexe_courant[lang_comm.lower()] in indexe_progression[lang_comm.lower()]["done"] :
            bonus_relecture = " - "+Loc_Data["7.4"]
        else :
            bonus_relecture = ""
        review.configure(text=Loc_Data["7.5"]+" - {} (ID {}){}".format(lang_comm, indexe_courant[lang_comm.lower()],
                         bonus_relecture))
        aspect_visual.configure(text="")
        opinion_visual.configure(text="")
        
        global labeled_triplets
        labeled_triplets.clear()
        list_trip.configure(text="\n"*10)
        
        global aspect, opinion
        aspect["L"].set(1)
        aspect["i_debut"].set(-1)
        opinion["L"].set(1)
        opinion["i_debut"].set(-1)
        reset_aspect()
        reset_opinion()
        
        global mots, decalage, review_lenght, carac_per_line
        mots, decalage, review_lenght, carac_per_line = get_comm_plus(comm)
        for key in list(spin.keys()) :
            if "debut" in key :
                spin[key].configure(to=review_lenght["mots"]-1)
            else :
                spin[key].configure(to=review_lenght["mots"])
            spin[key].update()
        
        global cherche, scrollbar
        cherche.destroy()
        scrollbar.destroy()
        cherche, scrollbar = crea_texte()
        cherche.bind("<ButtonRelease>", fin_manual_selec)
        cherche.update()
        if interaction_spin.get() == 2 :
            cherche.tag_configure("mot_i", font="Helvetica {}".format(taille_police_review),
                                  foreground="hotpink")
            for i in range(len(mots)) :
                if i%2 == 1 :
                    debut_a, line_deb_a, fin_a, line_fin_a = conversion(i, 1)
                    cherche.tag_add("mot_i", "{}.{}".format(line_deb_a,debut_a), "{}.{}".format(line_fin_a,fin_a))
    
    else :
        messagebox.showerror(title=Loc_Data["13.10"],
                             message=Loc_Data["13.11"])

def val_triplets(*args) :
    if len(labeled_triplets) != 0 :
        global indexe_courant, mots
        separateur = "\|/"
        
        out_to_save = indexe_courant[lang_comm.lower()] + separateur
        
        out_to_save += mots[0]
        for i in range(1, len(mots)) :
            out_to_save += " " + mots[i]
        out_to_save += separateur
        
        c_trip = 0
        for element in labeled_triplets :
            #temp = str(element)
            temp = ""
            for item in element :
                temp += str(item) + "<|>"
            out_to_save += temp[:len(temp)-3]
            out_to_save += separateur
            c_trip += 1
        
        
        print ("À sauvegarder :")
        print (out_to_save)
        print ("-"*20)
        
        global doublon_dealing, confirmation, changement_ok
        if indexe_courant[lang_comm.lower()] in indexe_progression[lang_comm.lower()]["done"] :
            visualisation_triplets("validation_doublon")
        else :
            doublon_dealing = 0
        
        if doublon_dealing == 0 :
            # cas normal où on sauvergade les triplets qui viennent juste d'être labélisé
            # peut entraîner la création de doublon si on fait pas gaffe
            visualisation_triplets("confirmation")
            if confirmation == True :
                save_update(out_to_save)
                update_compteurs(nb_trips=c_trip, langue=lang_comm.lower())
            
        elif doublon_dealing == 1 :
            # cas avec doublon où on sauvegarde le nouveau
            #   -> on cherche l'ancien,
            #      on le supprime,
            #      on réécrit le fichier sans l'ancien
            #      et puis on enregistre le nouveau en l'ajoutant à la fin
            data = Utils.load_data(file_name[lang_comm.lower()])
            
            for line in data :
                indexe = line.split("\|/")[0]
                if indexe == indexe_courant[lang_comm.lower()] :
                    data.remove(line)
            
            new_data = ""
            for line in data :
                new_data += line
            file = open(file_name[lang_comm.lower()], "w", encoding="utf8")
            file.write(new_data)
            file.close()
            
            global compteurs
            compteurs = {}
            for lang in Metadata["AvailableLanguage"] :
                compteurs[lang] = {"comms" : 0, "trips" : 0}
            update_compteurs(from_save=True)
            
            save_update(out_to_save)
            update_compteurs(nb_trips=c_trip, langue=lang_comm.lower())
            
        elif doublon_dealing == -1 :
            # cas avec un doublon où on garde l'ancien
            #   -> on ne fait rien
            None
        doublon_dealing = None
        confirmation = False
        changement_ok = True
        
    else :
        messagebox.showwarning(title=Loc_Data["13.10"],
                               message=Loc_Data["13.12"])

val_button = tk.Button(root, text=Loc_Data["7.31"]+"\n"+Loc_Data["7.32"],
                       font="Helvetica {}".format(taille_police), command=val_triplets,
                       takefocus=False)
val_button.grid(column=0, row=2)

#%% Fonctionnalité pour changer de langue
Index_Lang = 0
def changer_lang(*args):
    global changement_ok
    do_changement = True
    if changement_ok == False :
        do_changement = False
        out = messagebox.askyesno(
            message=Loc_Data["7.35"]+"\n"+Loc_Data["7.36"],
            icon="warning", title=Loc_Data["7.34"])
        if out == True :
            do_changement = True
    
    if do_changement == True :
        changement_ok = True
        
        global lang_comm, comm, Index_Lang
        Index_Lang += 1
        if Index_Lang == len(Metadata["AvailableLanguage"]) :
            Index_Lang = 0
        langue = Metadata["AvailableLanguage"][Index_Lang]
        lang_comm = langue.capitalize()
        comm = comms[langue][indexe_courant[langue]]
        
        global bonus_relecture
        if mode_relecture == True or indexe_courant[lang_comm.lower()] in indexe_progression[lang_comm.lower()]["done"] :
            bonus_relecture = " - "+Loc_Data["7.4"]
        else :
            bonus_relecture = ""
        review.configure(text=Loc_Data["7.5"]+" - {} (ID {}){}".format(lang_comm, indexe_courant[lang_comm.lower()], bonus_relecture))
        aspect_visual.configure(text="")
        opinion_visual.configure(text="")
        
        global aspect, opinion
        aspect["L"].set(1)
        aspect["i_debut"].set(-1)
        opinion["L"].set(1)
        opinion["i_debut"].set(-1)
        reset_aspect()
        reset_opinion()
        
        global labeled_triplets
        labeled_triplets.clear()
        list_trip.configure(text="\n"*10)
        
        global mots, decalage, review_lenght, carac_per_line
        mots, decalage, review_lenght, carac_per_line = get_comm_plus(comm)
        for key in list(spin.keys()) :
            if "debut" in key :
                spin[key].configure(to=review_lenght["mots"]-1)
            else :
                spin[key].configure(to=review_lenght["mots"])
            spin[key].update()
        
        global cherche, scrollbar
        cherche.destroy()
        scrollbar.destroy()
        cherche, scrollbar = crea_texte()
        if interaction_spin.get() == 2 :
            cherche.tag_configure("mot_i", font="Helvetica {}".format(taille_police_review),
                                  foreground="hotpink")
            for i in range(len(mots)) :
                if i%2 == 1 :
                    debut_a, line_deb_a, fin_a, line_fin_a = conversion(i, 1)
                    cherche.tag_add("mot_i", "{}.{}".format(line_deb_a,debut_a), "{}.{}".format(line_fin_a,fin_a))

lang_button = tk.Button(root, text=Loc_Data["7.33"],
                        font="Helvetica {}".format(taille_police), command=changer_lang,
                        takefocus=False)
lang_button.grid(column=1, row=2)

#%% Fonctions pour parcourir les commentaires

def loader_past_values(comm_id, langue):
    """
    permet de charger les anciennes valeurs sauvegardées du commentaire donné (ID + langue à préciser)
    """
    def str2trip(string):
        out = []
        temp = string.split("<|>")
        for i in range(len(temp)) :
            if i in [0,1] :
                to_add = []
                for elem in temp[i][1:-1].split(", ") :
                    to_add.append(elem[1:-1])
                out.append(to_add)
            elif i == 2 :
                out.append(temp[i])
            elif i in [3,4] :
                to_add = []
                for elem in temp[i][1:-1].split(", ") :
                    to_add.append(int(elem))
                out.append(to_add)
        return (out)
    
    triplets = []
    data = Utils.load_data(file_name[langue])
    
    for line in data :
        data_ = line.split("\|/")
        id_ = int(data_[0])
        if int(comm_id) == id_ :
            for i in range(2,len(data_)):
                if data_[i] != "\n" :
                    triplet = str2trip(data_[i])
                    triplets.append(triplet)
    
    global labeled_triplets
    for old in triplets :
        labeled_triplets.insert(0, old)
        texte_list_trip = "{}, {}, {}".format(old[0], old[1], old[2])
        for i in range(9) :
            try :
                a = labeled_triplets[i+1][0]
                b = labeled_triplets[i+1][1]
                c = labeled_triplets[i+1][2]
                texte_list_trip += "\n{}, {}, {}".format(a, b, c)
            except :
                texte_list_trip += "\n"
        list_trip.configure(text=texte_list_trip)

def parcourir_comms(*args, **kwargs):
    # TODO : faire en sorte que le widget d'entrée de l'ID affiche les IDs possibles commençant par ce qui est écrit
    global changement_ok
    do_changement = True
    if changement_ok == False :
        do_changement = False
        out = messagebox.askyesno(
            message=Loc_Data["7.35"]+"\n"+Loc_Data["7.36"],
            icon="warning", title=Loc_Data["7.34"])
        if out == True :
            do_changement = True
    
    if do_changement == True :
        changement_ok = True
        
        def fonc_annuler(*args):
            selection_comm.grab_release()
            selection_comm.destroy()
        
        def switch_lang():
            i = i_lang.get()
            i += 1
            if i == len(Metadata["AvailableLanguage"]) :
                i = 0
            lang = Metadata["AvailableLanguage"][i]
            lang_butt.configure(text=lang.capitalize())
            state_["todo"].configure(text=Loc_Data["16.2"]+" ({})".format(len(indexe_progression[lang]["todo"])))
            state_["done"].configure(text=Loc_Data["16.3"]+" ({})".format(len(indexe_progression[lang]["done"])))
            i_lang.set(value=i)
        
        def fonc_valider(*args, **kwargs):
            global lang_comm
            if kwargs == {} :
                num_id = entry_id.get()
                Langue = lang_butt["text"].lower()
                state = state_value.get()
            else :
                num_id = kwargs["num_id"]
                Langue = lang_comm.lower()
                state = "done"
            if num_id in indexe_progression[Langue][state] :
                global indexe_courant
                indexe_courant[Langue] = num_id
                
                global comm
                lang_comm = Langue.capitalize()
                comm = comms[Langue][indexe_courant[Langue]]
                
                global bonus_relecture
                if mode_relecture == True or indexe_courant[lang_comm.lower()] in indexe_progression[lang_comm.lower()]["done"] :
                    bonus_relecture = " - "+Loc_Data["7.4"]
                else :
                    bonus_relecture = ""
                review.configure(text=Loc_Data["7.5"]+" - {} (ID {}){}".format(lang_comm, indexe_courant[lang_comm.lower()], bonus_relecture))
                aspect_visual.configure(text="")
                opinion_visual.configure(text="")
                
                global aspect, opinion
                aspect["L"].set(1)
                aspect["i_debut"].set(0)
                opinion["L"].set(1)
                opinion["i_debut"].set(0)
                
                global mots, decalage, review_lenght, carac_per_line
                mots, decalage, review_lenght, carac_per_line = get_comm_plus(comm)
                for key in list(spin.keys()) :
                    if "debut" in key :
                        spin[key].configure(to=review_lenght["mots"]-1)
                    else :
                        spin[key].configure(to=review_lenght["mots"])
                    spin[key].update()
                
                global labeled_triplets
                labeled_triplets.clear()
                list_trip.configure(text="\n"*10)
                
                loader_past_values(num_id, Langue)
                
                global cherche, scrollbar
                cherche.destroy()
                scrollbar.destroy()
                cherche, scrollbar = crea_texte()
                if interaction_spin.get() == 2 :
                    cherche.tag_configure("mot_i", font="Helvetica {}".format(taille_police_review),
                                          foreground="hotpink")
                    for i in range(len(mots)) :
                        if i%2 == 1 :
                            debut_a, line_deb_a, fin_a, line_fin_a = conversion(i, 1)
                            cherche.tag_add("mot_i", "{}.{}".format(line_deb_a,debut_a), "{}.{}".format(line_fin_a,fin_a))
                
                if kwargs == {} :
                    fonc_annuler()
            else :
                messagebox.showwarning(title=Loc_Data["13.13"],
                                       message=Loc_Data["13.14"])
        
        if kwargs == {} :
            selection_comm = tk.Toplevel()
            selection_comm.title(Loc_Data["16.1"])
            #selection_comm.resizable(False, False)
            
            i_lang = tk.IntVar(value=0)
            lang_butt = tk.Button(selection_comm, text=lang_comm, font="Helvetica 12", command=switch_lang)
            lang_butt.grid(column=0, row=0, rowspan=3)
            
            state_value = tk.StringVar(value="done")
            state_ = {"todo" : tk.Radiobutton(selection_comm, text=Loc_Data["16.2"]+" ({})".format(len(indexe_progression[lang_butt["text"].lower()]["todo"])),
                                              variable=state_value, value="todo",
                                              font="Helvetica {}".format(taille_police)),
                      "done" : tk.Radiobutton(selection_comm, text=Loc_Data["16.3"]+" ({})".format(len(indexe_progression[lang_butt["text"].lower()]["done"])),
                                              variable=state_value, value="done",
                                              font="Helvetica {}".format(taille_police))}
            state_label = tk.Label(selection_comm, text=Loc_Data["16.4"],
                                   font="Helvetica {} bold".format(taille_police), padx=5)
            state_label.grid(column=1, row=0)
            state_["todo"].grid(column=1, row=1)
            state_["done"].grid(column=1, row=2)
            
            entry_id = tk.Entry(selection_comm, width=15)
            entry_id.grid(column=2, row=0)
            
            val_butt = tk.Button(selection_comm, text=Loc_Data["16.5"],
                                 command=fonc_valider)
            val_butt.grid(column=2, row=1, rowspan=2)
            
            Utils.center_(selection_comm)
            
            selection_comm.bind("<Key-{}>".format(raccourcis["parcours_comm"]["annuler"]), fonc_annuler)
            selection_comm.bind("<Key-{}>".format(raccourcis["parcours_comm"]["valider"]), fonc_valider)
            
            selection_comm.transient(root)
            selection_comm.wait_visibility()
            selection_comm.grab_set()
            selection_comm.wait_window()
        
        elif "next_" in list(kwargs.keys()) or "prev_" in list(kwargs.keys()) :
            i = indexe_progression[lang_comm.lower()]["done"].index(indexe_courant[lang_comm.lower()])
            if "next_" in list(kwargs.keys()) and kwargs["next_"] == True :
                if i+1 <= len(indexe_progression[lang_comm.lower()]["done"]) :
                    i += 1
            elif "prev_" in list(kwargs.keys()) and kwargs["prev_"] == True :
                if i-1 >= 0 :
                    i -= 1
            num_id = indexe_progression[lang_comm.lower()]["done"][i]
            fonc_valider(num_id=num_id)

#%% Fonctions pour la "correction"

def next_comm_old_values(*args):
    parcourir_comms(next_ = True)
def prev_comm_old_values(*args):
    parcourir_comms(prev_ = True)

#%% Fonctions pour la sélection avec les raccourcis

position = [None,None]
def reset_spin_selec(*args):
    dic_spin = {"0.1" : "aspect_debut",
                "0.0" : "aspect_L",
                "1.1" : "opinion_debut",
                "1.0" : "opinion_L"}
    for pos in list(dic_spin.keys()) :
        key = dic_spin[pos]
        spin[key].configure(fg="SystemWindowText")
        spin[key].configure(font="TkTextFont")

def navigation_spin(action):
    dic_spin = {"0.1" : "aspect_debut",
                "0.0" : "aspect_L",
                "1.1" : "opinion_debut",
                "1.0" : "opinion_L"}
    dic_var = {"aspect_debut" : "i_debut",
               "aspect_L" : "L",
               "opinion_debut" : "i_debut",
               "opinion_L" : "L"}
    
    if action == "move" :
        reset_spin_selec()
        spin[dic_spin["{}.{}".format(position[0],position[1])]].configure(fg="red")
        spin[dic_spin["{}.{}".format(position[0],position[1])]].configure(font="TkTextFont 10 bold")
    elif "value_" in action and spin[dic_spin["{}.{}".format(position[0],position[1])]]["fg"] == "red" :
        global aspect, opinion
        pos = "{}.{}".format(position[0],position[1])
        
        value = 0
        if pos in ["0.1", "0.0"] :
            value = aspect[dic_var[dic_spin[pos]]].get()
        elif pos in ["1.1", "1.0"] :
            value = opinion[dic_var[dic_spin[pos]]].get()
        
        if action == "value_up" :
            if pos in ["0.1", "1.1"] :
                if value+10**vitesse >= review_lenght["mots"] :
                    value = -1
                else :
                    value += 10**vitesse
            elif pos in ["0.0", "1.0"] :
                if value+10**vitesse >= review_lenght["mots"]+1 :
                    value = 1
                else :
                    value += 10**vitesse
        elif action == "value_down" :
            if pos in ["0.1", "1.1"] :
                if value-10**vitesse <= -2 :
                    value = review_lenght["mots"]-1
                else :
                    value -= 10**vitesse
            elif pos in ["0.0", "1.0"] :
                if value-10**vitesse <= 0 :
                    value = review_lenght["mots"]
                else :
                    value -= 10**vitesse
        
        if pos in ["0.1", "0.0"] :
            aspect[dic_var[dic_spin[pos]]].set(value)
            modif_value(what="aspect")
        elif pos in ["1.1", "1.0"] :
            opinion[dic_var[dic_spin[pos]]].set(value)
            modif_value(what="opinion")
        
        for key in list(spin.keys()) :
            spin[key].update()

def go_up(*args):
    global position
    if interaction_spin.get() == 1 :
        if position == [None,None] :
            position = [0,1]
        elif position[1] < 1 :
            position[1] += 1
        navigation_spin("move")
def go_down(*args):
    global position
    if interaction_spin.get() == 1 :
        if position == [None,None] :
            position = [0,0]
        elif position[1] > 0 :
            position[1] -= 1
        navigation_spin("move")
def go_right(*args):
    global position
    if interaction_spin.get() == 1 :
        if position == [None,None] :
            position = [1,1]
        elif position[0] < 1 :
            position[0] += 1
        navigation_spin("move")
def go_left(*args):
    global position
    if interaction_spin.get() == 1 :
        if position == [None,None] :
            position = [0,1]
        elif position[0] > 0 :
            position[0] -= 1
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
        
        selection = cherche.tag_ranges("sel")
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
                cherche.tag_remove("mot_i", "1.0", "end")
                cherche.tag_remove("aspect", "1.0", "end")
                cherche.tag_remove("opinion", "1.0", "end")
                for i in range(len(mots)) :
                    debut, line_deb, fin, line_fin = conversion(i, 1)
                    if i in manual_selec_terms["aspect"] :
                        cherche.tag_add("aspect", "{}.{}".format(line_deb,debut), "{}.{}".format(line_fin,fin))
                    elif i in manual_selec_terms["opinion"] :
                        cherche.tag_add("opinion", "{}.{}".format(line_deb,debut), "{}.{}".format(line_fin,fin))
                    else :
                        if i%2 == 1 :
                            cherche.tag_add("mot_i", "{}.{}".format(line_deb,debut), "{}.{}".format(line_fin,fin))
                # 4- mettre à jour les textes de l'aspect et de l'opinion
                if term_selec == "aspect" :
                    if len(manual_selec_terms[term_selec]) == 0 :
                        aspect_value = "{"+Loc_Data["7.2"]+"}"
                    else :
                        aspect_value = [mots[ind] for ind in manual_selec_terms[term_selec]]
                    aspect_visual.configure(text=aspect_value)
                elif term_selec == "opinion" :
                    if len(manual_selec_terms[term_selec]) == 0 :
                        opinion_value = "{"+Loc_Data["7.3"]+"}"
                    else :
                        opinion_value = [mots[ind] for ind in manual_selec_terms[term_selec]]
                    opinion_visual.configure(text=opinion_value)
                
                previous_manual_selection = ()
            else :
                previous_manual_selection = selection

#%% Centrage et raccourcis de la fenêtre principale

Utils.center_(root)

if interaction_spin.get() != 3 :
    root.bind("<Key-{}>".format(raccourcis["principal"]["p_comm"]), parcourir_comms)
    root.bind("<Key-{}>".format(raccourcis["principal"]["c_lang"]), changer_lang)
    root.bind("<Key-{}>".format(raccourcis["principal"]["v_trip"]), visualisation_triplets)
    root.bind("<Key-{}>".format(raccourcis["principal"]["val_trip"]), val_triplets)
    root.bind("<Key-{}>".format(raccourcis["principal"]["add_trip"]), add_triplet)
    root.bind("<Key-{}>".format(raccourcis["principal"]["sup_trip"]), sup_triplet)
    root.bind("<Key-{}>".format(raccourcis["principal"]["spin_u"]), go_up)
    root.bind("<Key-{}>".format(raccourcis["principal"]["spin_l"]), go_left)
    root.bind("<Key-{}>".format(raccourcis["principal"]["spin_d"]), go_down)
    root.bind("<Key-{}>".format(raccourcis["principal"]["spin_r"]), go_right)
    root.bind("<Key-{}>".format(raccourcis["principal"]["spin_v_u"]), value_up)
    root.bind("<Key-{}>".format(raccourcis["principal"]["spin_v_d"]), value_down)
    root.bind("<Key-{}>".format(raccourcis["principal"]["spin_reset_col"]), reset_spin_selec)
    root.bind("<Key-{}>".format(raccourcis["principal"]["vit_plus"]), vitesse_plus)
    root.bind("<Key-{}>".format(raccourcis["principal"]["vit_moins"]), vitesse_moins)

root.bind("<Control-Right>", next_comm_old_values)
root.bind("<Control-Left>", prev_comm_old_values)

cherche.bind("<ButtonRelease>", fin_manual_selec)

root.mainloop()

#%% Suppression des commentaires incohérents précédemment labélisés

print ("\nSuppression des oddities dans les fichiers de sauvegarde ...")
for langue in Metadata["AvailableLanguage"] :
    Data = Utils.load_data(file_name[langue])
    data = ""
    for line in Data :
        data += line
    File = open(file_name[langue], "w", encoding="utf8")
    File.write(data)
    File.close()

#%%
