# -*- coding: utf-8 -*-
"""
Created on Wed Jun 15 10:10:43 2022

@author: Florian Cataldi
"""

"""
Ensemble de fonctions utilitaires
"""

import tkinter as tk
from os import listdir, walk
from os.path import isfile, join
from time import sleep
import Custom_funcs
from Other_windows import load_comms_window

#%% Utilitaires généraux

def load_data(filename):
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

def center_(toplevel, dims=None):
    """
    Merci Internet, je vais pas m'embêter à bricoler quelque chose alors qu'il
    y a déjà du propre qui existe
    """
    # possible problème de centrage sur du multi-écran à partir d'un petit écran
    
    toplevel.update_idletasks()
    w = toplevel.winfo_screenwidth()
    h = toplevel.winfo_screenheight()
    size = tuple(int(_) for _ in toplevel.geometry().split('+')[0].split('x'))
    if dims != None : size = dims
    x = w/2 - size[0]/2
    y = h/2 - size[1]/2
    toplevel.geometry("%dx%d+%d+%d" % (size + (x, y)))

#%% Utilitaires pour la localisation

directory = "Localisations"

def get_loc_files():
    locs = [loc.split(".")[0] for loc in listdir(directory) if len(loc.split("."))==2 and loc.split(".")[1]=="LOC_"]
    return (locs)

def select_loc():
    Loc_data = {}
    
    fen_loc = tk.Tk()
    fen_loc.title("Language selection")
    fen_loc.resizable(False, False)
    
    lab = tk.Label(fen_loc, text="Please select a language to use from the available ones :")
    lab.grid(column=0, row=0)
    
    Loc = tk.StringVar()
    selec = tk.ttk.Combobox(fen_loc, textvariable=Loc, height=150, width=20)
    selec["values"] = get_loc_files()
    selec["state"] = "readonly"
    selec.grid(column=0, row=1)
    
    def get_loc(*args):
        loc = selec["values"][selec.current()]+".LOC_"
        fen_loc.update()
        sleep(0.25)
        fen_loc.destroy()
        data = load_data(directory+"/"+loc)
        for line in data :
            if line != "\n" and line[0] != "#" :
                group_line = line.split("=")[0]
                text = line.split("=")[1]
                if text[-1] == "\n" :
                    Loc_data[group_line] = text[:-1]
                else :
                    Loc_data[group_line] = text
    
    selec.bind("<<ComboboxSelected>>", get_loc)
    
    center_(fen_loc)
    
    fen_loc.mainloop()
    
    return (Loc_data, Loc.get())

def get_lang_dict(lang):
    data = load_data(directory+"/"+lang+".LANG_DICT")
    
    dico_lang = {}
    for line in data :
        info = line.split("=")
        dico_lang[info[0]] = info[1][:-1]
    return (dico_lang)

#%% Utilitaires pour les commentaires

def get_comms(mode, lang, params, func_for_invalid_carac):
    return Custom_funcs.GET_COMMS(mode, lang, params, func_for_invalid_carac)

def get_comm_len(comm, lang):
    return (Custom_funcs.GET_COMM_LEN(comm, lang))

#%% Utilitaires pour la création de partitions

def window_for_partitions_creation(func_for_invalid_carac, Loc_Data):
    metadata = get_metadata()
    
    Comms_infos = {}
    Paths = {}
    for lang in metadata["AvailableLanguage"] :
        Comms_infos[lang] = {"text" : [], "len" : []}
        Paths[lang] = metadata["InputFilename"]+"_"+lang+".txt"
    
    load_lens_comms = load_comms_window(metadata["AvailableLanguage"], None, Loc_Data,
                                        "partition", (Paths, Comms_infos, None),
                                        func_for_invalid_carac)
    load_lens_comms.run_window()
    def create_parts_preview(progress_bar=None):
        assignement = {}
        repartition = {}
        for lang in metadata["AvailableLanguage"] :
            assignement[lang] = [None for i in range(len(Comms_infos[lang]["len"]))]
            P, C = 0, 0
            
            if ignored[lang] == False :
                for k in range(2) :
                    for i in range(len(Comms_infos[lang]["len"])) :
                        if assignement[lang][i] == None :
                            if k == 0 :
                                if L_comm[lang] != None :
                                    if Comms_infos[lang]["len"][i] <= L_comm[lang] :
                                        assignement[lang][i] = P
                                        C += 1
                                else :
                                    assignement[lang][i] = P
                                    C += 1
                                if C == nb_comms[lang] :
                                    P += 1
                                    C = 0
                            elif k == 1 :
                                assignement[lang][i] = P
                                C += 1
                                if C == seuil[lang] :
                                    P += 1
                                    C = 0
                    P += 1
                    C = 0
            
            repartition[lang] = {}
            if progress_bar == None :
                for p in range(P) :
                    num = assignement[lang].count(p)
                    if num != 0 :
                        if num not in list(repartition[lang].keys()) :
                            repartition[lang][num] = [p, None]
                        else :
                            repartition[lang][num][1] = p
                
                message = lang.capitalize()+" :\n"
                for key in list(repartition[lang].keys()) :
                    if repartition[lang][key][1] != None :
                        message += "part{}-{} : {} {}\n".format(repartition[lang][key][0],
                                                                repartition[lang][key][1],
                                                                key, Loc_Data["1.9"])
                    else :
                        message += "part{} : {} {}\n".format(repartition[lang][key][0], key, Loc_Data["1.9"])
                message += "\ntotal : {} {}".format(len(Comms_infos[lang]["len"]), Loc_Data["1.9"])
                previews[lang].configure(text=message)
            
            else :
                for p in range(P) :
                    repartition[lang][str(p)] = ["", 0]
                if ignored[lang] == False :
                    for i in range(len(assignement[lang])) :
                        repartition[lang][str(assignement[lang][i])][0] += Comms_infos[lang]["text"][i]
                        repartition[lang][str(assignement[lang][i])][1] += 1
                        progress_bar.update()
                for p in range(P-1, -1, -1) :
                    if repartition[lang][str(p)][1] == 0 :
                        repartition[lang].pop(str(p))
        if progress_bar != None :
            return (repartition)
    
    def create_partitions():
        preview_button.grid_forget()
        validation_button.grid_forget()
        for lang in metadata["AvailableLanguage"] :
            nb_entry["state"] = "readonly"
            L_entry["state"] = "readonly"
            seuil_entry["state"] = "readonly"
            ignore["state"] = "disabled"
            
        
        pbar.grid(column=2,row=0, rowspan=2)
        info_text = tk.Label(fen_part, text="Triage des commentaires en cours ...",
                             width=28, justify="center")
        info_text.grid(column=1,row=0,rowspan=2)
        
        dims = [int(_) for _ in fen_part.geometry().split("+")[0].split("x")]
        dims[0] += 25
        center_(fen_part, tuple(dims))
        
        pbar.start()
        
        repartition = create_parts_preview(progress_bar=pbar)
        
        info_text.configure(text="Ecriture des partitions en cours ...")
        for langue in metadata["AvailableLanguage"] :
            Data_info = ""
            if ignored[lang] == False :
                for part in list(repartition[langue].keys()) :
                    Data_info += "part{}={}\n".format(part, repartition[langue][part][1])
                    filename = metadata["InputDataDir"]+metadata["InputFilename"]+"_{}_part{}.txt".format(langue,part)
                    if isfile(filename) == False :
                        open(filename, "x", encoding="utf8").close()
                    else :
                        open(filename, "w", encoding="utf8").close()
                    file = open(filename, "w", encoding="utf8")
                    file.write(repartition[langue][part][0])
                    file.close()
                    pbar.update()
            Data_info += "whole={}\n".format(len(Comms_infos[lang]["text"]))
            filename = metadata["InputDataDir"]+"Comms_num_{}.DATA_INFO_".format(langue)
            if isfile(filename) == False :
                open(filename, "x", encoding="utf8").close()
            else :
                open(filename, "w", encoding="utf8").close()
            file = open(filename, "a", encoding="utf8")
            file.write(Data_info)
            file.close()
            pbar.update()
        pbar.stop()
        info_text.configure(text="Les partitions ont été crées !"+"\n"+"Fermeture dans"+" 3")
        sleep(1.0)
        fen_part.update()
        info_text.configure(text="Les partitions ont été crées !"+"\n"+"Fermeture dans"+" 2")
        sleep(1.0)
        fen_part.update()
        info_text.configure(text="Les partitions ont été crées !"+"\n"+"Fermeture dans"+" 1")
        sleep(1.0)
        fen_part.update()
        info_text.configure(text="Les partitions ont été crées !"+"\n"+"Fermeture")
        fen_part.destroy()
    
    
    fen_part = tk.Tk()
    fen_part.title(Loc_Data["1.1"])
    fen_part.resizable(False, False)
    
    def unlock_confirm():
        unlock_ok = True
        if ig_val.get() == False :
            if nb_entry.get() == "" :
                unlock_ok = False
        if unlock_ok == True :
            confirm_but["state"] = "active"
    
    def unlock_create():
        c = 0
        for lang in metadata["AvailableLanguage"] :
            if confirmed[lang] == True :
                c += 1
        if c == len(metadata["AvailableLanguage"]) :
            validation_button["state"] = "active"
    
    def validate_entry(value):
        unlock_confirm()
        return (value.isnumeric() or value == "")
    validate_entry_wrapper = (fen_part.register(validate_entry), '%P')
    
    def block_entry():
        if ig_val.get() == True :
            nb_comms[Lang.get()] = None
            nb_entry.delete(0, "end")
            nb_entry["takefocus"] = False
            nb_entry["state"] = "readonly"
            
            L_comm[Lang.get()] = None
            L_entry.delete(0, "end")
            L_entry["takefocus"] = False
            L_entry["state"] = "readonly"
            
            L_comm[Lang.get()] = None
            seuil_entry.delete(0, "end")
            seuil_entry["takefocus"] = False
            seuil_entry["state"] = "readonly"
        else :
            nb_entry["takefocus"] = True
            nb_entry["state"] = "normal"
            L_entry["takefocus"] = True
            L_entry["state"] = "normal"
            seuil_entry["takefocus"] = True
            seuil_entry["state"] = "normal"
        unlock_confirm()
    
    def change_lang(*args):
        ind = int(lang_scale.get())-1
        if ind == len(metadata["AvailableLanguage"]) :
            ind = 0
        Lang.set(metadata["AvailableLanguage"][ind])
        rule_frame.configure(text=Lang.get().capitalize())
        nb_entry.delete(0, "end")
        L_entry.delete(0, "end")
        seuil_entry.delete(0, "end")
        if nb_comms[Lang.get()] != None :
            nb_entry.insert(0, str(nb_comms[Lang.get()]))
        if L_comm[Lang.get()] != None :
            L_entry.insert(0, str(L_comm[Lang.get()]))
        if seuil[Lang.get()] != None :
            seuil_entry.insert(0, str(seuil[Lang.get()]))
    
    def confirm_rule():
        if nb_entry.get() != "" :
            nb_comms[Lang.get()] = int(nb_entry.get())
        if L_entry.get() != "" :
            L_comm[Lang.get()] = int(L_entry.get())
        ignored[Lang.get()] = ig_val.get()
        if seuil_entry.get() != "" :
            seuil[Lang.get()] = int(seuil_entry.get())
        confirmed[Lang.get()] = True
        ind = metadata["AvailableLanguage"].index(Lang.get())
        if ind == len(metadata["AvailableLanguage"]) :
            ind = 0
        lang_scale.set(ind+2)
        ig_val.set(False)
        change_lang()
        unlock_create()
    
    nb_comms = {}
    L_comm = {}
    ignored = {}
    seuil = {}
    confirmed = {}
    for lang in metadata["AvailableLanguage"] :
        nb_comms[lang] = None
        L_comm[lang] = None
        ignored[lang] = None
        seuil[lang] = None
        confirmed[lang] = False
    Lang = tk.StringVar(value=metadata["AvailableLanguage"][0])
    
    rule_frame = tk.LabelFrame(fen_part, text=Lang.get().capitalize(), padx=5, pady=5)
    nb_text = tk.Label(rule_frame, text=Loc_Data["1.2"])
    nb_entry = tk.Entry(rule_frame, validate="all", validatecommand=validate_entry_wrapper)
    L_text = tk.Label(rule_frame, text=Loc_Data["1.3"])
    L_entry = tk.Entry(rule_frame, validate="all", validatecommand=validate_entry_wrapper)
    seuil_text = tk.Label(rule_frame, text=Loc_Data["1.4"])
    seuil_entry = tk.Entry(rule_frame, validate="all", validatecommand=validate_entry_wrapper)
    ig_val = tk.BooleanVar()
    ignore = tk.Checkbutton(rule_frame, text=Loc_Data["1.5"], variable=ig_val, takefocus=False,
                            command=block_entry)
    lang_scale = tk.Scale(rule_frame, orient="horizontal", length=400, from_=1,
                          to=len(metadata["AvailableLanguage"]), label="Langue # :",
                          command=change_lang)
    confirm_but = tk.Button(rule_frame, text=Loc_Data["1.6"], state="disabled",
                            command=confirm_rule, takefocus=False)
    
    rule_frame.grid(column=0, row=0)
    nb_text.grid(column=0, row=0)
    nb_entry.grid(column=1, row=0)
    L_text.grid(column=0, row=1)
    L_entry.grid(column=1, row=1)
    seuil_text.grid(column=0, row=2)
    seuil_entry.grid(column=1, row=2)
    ignore.grid(column=0, row=3, columnspan=2)
    lang_scale.grid(column=0, row=4, columnspan=2)
    confirm_but.grid(column=0, row=4, columnspan=2, sticky="n")
    
    def change_preview(*args):
        for lang in metadata["AvailableLanguage"] :
            previews[lang].grid_forget()
        lang = metadata["AvailableLanguage"][scroll_scale.get()-1]
        previews[lang].grid(column=1, row=0)
    
    preview_frame = tk.LabelFrame(fen_part, text="Preview", padx=5, pady=5)
    scroll_scale = tk.Scale(preview_frame, orient="vertical", length=150, from_=1,
                          to=len(metadata["AvailableLanguage"]),
                          command=change_preview)
    previews = {}
    for lang in metadata["AvailableLanguage"] :
        previews[lang] = tk.Label(preview_frame, text=" "*50)
    
    preview_frame.grid(column=0, row=1)
    previews[Lang.get()].grid(column=1, row=0)
    scroll_scale.grid(column=0, row=0)
    
    
    preview_button = tk.Button(fen_part, text=Loc_Data["1.7"],
                                command=create_parts_preview, takefocus=False)
    validation_button = tk.Button(fen_part, text=Loc_Data["1.8"], command=create_partitions,
                                  takefocus=False)
    validation_button["state"] = "disabled"
    
    preview_button.grid(column=1, row=0)
    validation_button.grid(column=1, row=1)
    
    pbar = tk.ttk.Progressbar(fen_part, orient="vertical", length=150,
                              mode="indeterminate")
    
    center_(fen_part)
    
    fen_part.mainloop()

#%% Utilitaires pour le choix des partitions

def get_num_comm(partition, langue):
    metadata = get_metadata()
    path = metadata["InputDataDir"]+"Comms_num_{}.DATA_INFO_".format(langue)
    temp = load_data(path)
    data = [_[:-1].split("=")[1] for _ in temp]
    num = None
    if partition == "" :
        num = data[len(data)-1]
    else :
        num = data[partition]
    return (num)

def get_all_files():
    metadata = get_metadata()
    files = {}
    for lang in metadata["AvailableLanguage"] :
        files[lang] = []
    
    all_files = [f for f in listdir(metadata["InputDataDir"])
                 if isfile(join(metadata["InputDataDir"], f)) and
                 f.split(".")[1] == "txt" and
                 f[:len(metadata["InputFilename"])]==metadata["InputFilename"]]
    for file in all_files :
        info = file.split(".")[0][len(metadata["InputFilename"])+1:].split("_")
        if len(info) == 1 :
            files[info[0]].append("")
        else :
            files[info[0]].append(info[1])
    
    return (files)

def get_partition():
    metadata = get_metadata()
    available_partitions = {}
    num_comms_per_partition = {}
    parts = {}
    
    all_files = get_all_files()
    
    for lang in metadata["AvailableLanguage"] :
        available_partitions[lang] = []
        num_comms_per_partition[lang] = []
        parts[lang] = []
        for file in all_files[lang] :
            filename = metadata["InputFilename"]+"_"+lang
            if file != "" :
                filename += "_"+file
                file = int(file[4:])
            parts[lang].append(file)
            available_partitions[lang].append(filename+".txt")
            num_comms_per_partition[lang].append(get_num_comm(file,lang))
    
    return (available_partitions, num_comms_per_partition, parts)

def get_part_selec(Loc_Data) :
    metadata = get_metadata()
    output = [{}, {}, 0]
    
    fen_part = tk.Tk()
    fen_part.title(Loc_Data["3.1"])
    fen_part.resizable(False, False)
    
    data, num_comms, parts = get_partition()
    part_var = {}
    c = 0
    for lang in metadata["AvailableLanguage"] :
        if data[lang] != [] :
            part_var[lang] = {"value" : tk.StringVar(value=Loc_Data["3.2"]+" {}".format(lang.capitalize()))}
            part_var[lang]["widget"] = tk.ttk.Combobox(fen_part, textvariable=part_var[lang]["value"], height=150, width=50)
            part_var[lang]["num"] = tk.Label(fen_part,width=20, justify="center")
            part_var[lang]["widget"]["values"] = data[lang]
            part_var[lang]["widget"]["state"] = "readonly"
            part_var[lang]["widget"].grid(column=0, row=c)
            part_var[lang]["num"].grid(column=1, row=c)
            c += 1
    
    def validation(var):
        for lang in list(part_var.keys()) :
            var[0][lang] = part_var[lang]["value"].get()
            var[1][lang] = str(parts[lang][part_var[lang]["widget"].current()])
            var[2] += int(num_comms[lang][part_var[lang]["widget"].current()])
        fen_part.destroy()
    def validation_wrapper():
        return (validation(output))
    
    validation_button = tk.Button(fen_part, text=Loc_Data["3.3"], command=validation_wrapper)
    validation_button["state"] = "disabled"
    if c%2 == 1 :
        # nombre de langue impaire
        button_row = int(c/2)
        button_rowspan = 1
    else  :
        # nombre de langue paire
        button_row = int(c/2)-1
        button_rowspan = 2
    validation_button.grid(column=2, row=button_row, rowspan=button_rowspan)
    
    def unlock_button():
        unlock_ok = True
        for lang in list(part_var.keys()) :
            if part_var[lang]["widget"].current() == -1 :
                unlock_ok = False
        if unlock_ok == True :
            validation_button["state"] = "active"
    def update_text():
        for lang in metadata["AvailableLanguage"] :
            if part_var[lang]["widget"].current() != -1 :
                num = num_comms[lang][part_var[lang]["widget"].current()]
                part_var[lang]["num"].configure(text="{} ".format(num)+Loc_Data["3.4"])
    def combobox_wrapper(*args):
        unlock_button()
        update_text()
    
    for lang in list(part_var.keys()) :
        part_var[lang]["widget"].bind("<<ComboboxSelected>>", combobox_wrapper)
    
    center_(fen_part)
    
    fen_part.mainloop()
    
    return (output)

#%% Utilitaires pour le choix de la partition à valider

def is_part(part):
    out = False
    metadata = get_metadata()
    if part in metadata["AvailableLanguage"] :
        out = True
    else :
        elems = part.split("_")
        while "" in elems :
            elems.remove("")
        if len(elems) == 2 and elems[1][:4] == "part" :
            try :
                int(elems[1][4:])
                out = True
            except :
                None
    return (out)
    
def get_available_parts():
    metadata = get_metadata()
    available = None
    users = next(walk(metadata["OutputDataDir"]))[1]
    
    temp = {}
    all_parts = []
    for user in users :
        temp[user] = []
        files = next(walk(metadata["OutputDataDir"]+"/"+user))[2]
        for file in files :
            file = file.split(".")[0]
            if "Comms_labeled_" in file :
                part = file[len(metadata["InputFilename"]):]
                if is_part(part) == True :
                    if part not in temp[user] :
                        temp[user].append(part)
                    if part not in all_parts :
                        all_parts.append(part)
        if temp[user] == [] :
            temp.pop(user)
    
    for part in all_parts :
        nb_users = 0
        for user in users :
            if part in temp[user] :
                nb_users += 1
        if nb_users >= 2 :
            if available == None :
                available = {}
            available[part] = []
            for user in users :
                if part in temp[user] :
                    available[part].append(user)
    
    return (available)

def get_part_for_val(Loc_Data):
    output = {"part" : "", "users" : [], "nb_comms" : 0}
    
    parts = get_available_parts()
    
    def unlock_button(*args):
        if combo.current() != -1 :
            valid_but["state"] = "active"
    
    def valid():
        output["part"] = list(parts.keys())[combo.current()]
        output["users"] = parts[output["part"]]
        
        langue = output["part"].split("_")[0]
        partition = int(output["part"].split("_")[1][4:])
        output["nb_comms"] = get_num_comm(partition, langue)
        fen_part.destroy()
    
    fen_part = tk.Tk()
    fen_part.title(Loc_Data["6.1"])
    fen_part.resizable(False, False)
    
    if parts == None :
        message = Loc_Data["6.2"]+"\n"
        message += Loc_Data["6.3"]
        status = tk.Label(fen_part, text=message, font="Helvetica 14 bold")
        status.grid()
    else :
        texte = tk.Label(fen_part, text=Loc_Data["6.4"])
        combo = tk.ttk.Combobox(fen_part, values=list(parts.keys()), state="readonly")
        valid_but = tk.Button(fen_part, text=Loc_Data["6.5"], state="disabled",
                              command=valid)
        
        texte.grid(column=0, row=0)
        combo.grid(column=1, row=0)
        valid_but.grid(column=2, row=0, padx=5)
    
        combo.bind("<<ComboboxSelected>>", unlock_button)
    
    center_(fen_part)
    
    fen_part.mainloop()
    
    return (output)


