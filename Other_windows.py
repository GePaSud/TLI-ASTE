# -*- coding: utf-8 -*-
"""
Created on Thu Jun 23 11:07:06 2022

@author: Florian Cataldi
"""

"""
Ensemble des fenêtres du GUI
"""

import tkinter as tk
from tkinter import messagebox, ttk
from os import walk, mkdir
import Utils

class load_comms_window():
    def __init__(self, Languagues, Total_num_comms, Loc_Data, mode, params, func_for_invalid_carac):
        self.Loc_Data = Loc_Data
        self.Languagues = Languagues
        self.mode = mode
        self.params = params
        self.func_for_invalid_carac = func_for_invalid_carac
        
        self.root = tk.Tk()
        if self.mode == "labelisation" :
            self.prog_label = tk.Label(self.root)
        if self.mode != "partition" :
            self.pbar_comms = ttk.Progressbar(self.root, orient="horizontal", length=500,
                                              mode="determinate", maximum=Total_num_comms)
        else :
            self.pbar_comms = ttk.Progressbar(self.root, orient="horizontal", length=500,
                                              mode="indeterminate")
        self.comm_butt = tk.Button(self.root, text=Loc_Data["4.2"], command=self.Get_comms)
    
    def key_handler(*args):
        print ("-"*20)
        event = args[1]
        print (event)
        print (event.char, event.keysym, event.keycode)
        print ("-"*20)
    
    def Get_comms(self, *args) :
        self.root.title(self.Loc_Data["4.3"])
        self.comm_butt.destroy()
        if self.mode in ["labelisation", "validation", "partition"] :
            if self.mode == "labelisation" :
                Params = [_ for _ in self.params]
                Params.append(self.pbar_comms)
                for lang in self.Languagues :
                    message = "{} {} ({}/{})".format(self.Loc_Data["4.4"], Params[0][lang],
                                                     self.Languagues.index(lang)+1,
                                                     len(self.Languagues))
                    self.prog_label.configure(text=message)
                    Utils.get_comms(self.mode, lang, Params, self.func_for_invalid_carac)
            elif self.mode == "validation" :
                Params = [_ for _ in self.params]
                Params.append(self.pbar_comms)
                Utils.get_comms(self.mode, self.Languagues, Params, self.func_for_invalid_carac)
            elif self.mode == "partition" :
                Params = [_ for _ in self.params[:2]]
                Params.append(self.pbar_comms)
                self.pbar_comms.start()
                for lang in self.Languagues :
                    Utils.get_comms(self.mode, lang, Params, self.func_for_invalid_carac)
                self.pbar_comms.stop()
        self.root.destroy()
    
    def run_window(self):
        self.root.title(self.Loc_Data["4.1"])
        self.root.resizable(False, False)
        
        if self.mode == "labelisation" :
            self.prog_label.grid(column=0, row=0)
            self.pbar_comms.grid(column=0,row=1)
            self.comm_butt.grid(column=0,row=2)
        elif self.mode == "validation" or self.mode == "partition" :
            self.pbar_comms.grid(column=0,row=0)
            self.comm_butt.grid(column=0,row=1)
        
        Utils.center_(self.root)
        
        self.root.bind("<Key-Return>", self.Get_comms)
        self.root.bind("<Key>", self.key_handler)
        
        self.root.mainloop()

class verif_carac_window():
    def __init__(self, Loc_Data, Total_num_comms, Paths, func_for_invalid_carac):
        self.root = tk.Tk()
        self.pbar = ttk.Progressbar(self.root, orient="horizontal", length=500,
                                    mode="determinate", maximum=Total_num_comms*2)
        self.comm_butt = tk.Button(self.root, text=Loc_Data["5.2"], command=self.check_carac)
        self.stat_label = tk.Label(self.root, justify="center")
        
        self.Loc_Data = Loc_Data
        self.Paths = Paths
        self.func_for_invalid_carac = func_for_invalid_carac
    
    def check_carac(self, *args):
        def fin_check():
            self.root.destroy()
        
        self.comm_butt["state"] = "disabled"
        
        comms = {}
        for lang in Utils.get_metadata()["AvailableLanguage"] :
            comms[lang] = {}
            Utils.get_comms("labelisation", lang,
                            (self.Paths, comms, self.pbar),
                            self.func_for_invalid_carac)
        
        nb_inconnus = {"carac" : 0,
                       "comm" : 0}
        nb_max = {"carac" : 0,
                  "comm" : 0}
        for lang in Utils.get_metadata()["AvailableLanguage"] :
            source = comms[lang]
            for key in list(source.keys()) :
                comm = source[key]
                nb_max["comm"] += 1
                found_in_comm = False
                for carac in comm :
                    nb_max["carac"] += 1
                    unicode = int(hex(ord(carac)),0)
                    if unicode > 0xffff :
                        nb_inconnus["carac"] += 1
                        if found_in_comm == False :
                            found_in_comm = True
                            nb_inconnus["comm"] += 1
                self.pbar.step()
                self.pbar.update()
        
        proportions = {"carac" : nb_inconnus["carac"]/nb_max["carac"],
                       "comm" : nb_inconnus["comm"]/nb_max["comm"]}
        texte = self.Loc_Data["5.3"]+"\n"+self.Loc_Data["5.4"]+"\n"
        texte += self.Loc_Data["5.5"]+" "
        texte += str(round(100*proportions["carac"],15))+"% ("
        texte += str(nb_inconnus["carac"])+"/"+str(nb_max["carac"])+")\n"
        texte += self.Loc_Data["5.6"]+" "
        texte += str(round(100*proportions["comm"],2))+"% ("
        texte += str(nb_inconnus["comm"])+"/"+str(nb_max["comm"])+")"
        self.stat_label.configure(text=texte)
        dims = [int(_) for _ in self.root.geometry().split("+")[0].split("x")]
        dims[1] += 45
        Utils.center_(self.root, tuple(dims))
        
        self.comm_butt.configure(text=self.Loc_Data["5.7"])
        self.comm_butt.configure(command=fin_check)
        self.comm_butt["state"] = "active"

    def run_window(self):
        self.root.title(self.Loc_Data["5.1"])
        self.root.resizable(False, False)
        
        self.pbar.grid(column=0,row=0,columnspan=2)
        self.comm_butt.grid(column=0,row=1)
        self.stat_label.grid(column=1,row=1)
        
        Utils.center_(self.root)

        self.root.bind("<Key-Return>", self.check_carac)

        self.root.mainloop()

class selec_user_window():
    def __init__(self, Loc_Data):
        self.metadata = Utils.get_metadata()
        self.Loc_Data = Loc_Data
        self.output = ""
        
        self.root = tk.Tk()
        self.user_list = tk.ttk.Combobox(self.root, values=self.get_users(),
                                         state="readonly")
        self.valid_but = tk.Button(self.root, text=Loc_Data["2.2"],
                                   command=self.set_user, state="disabled")
        self.sep = tk.ttk.Separator(self.root, orient="vertical")
        self.new_but = tk.Button(self.root, text=Loc_Data["2.3"],
                                 command=self.create_user_wrapper)
    
    def get_users(self):
        path = self.metadata["OutputDataDir"]
        return (next(walk(path))[1])
    def create_user(self,fen, name):
        path = self.metadata["OutputDataDir"]
        if name not in self.get_users() :
            mkdir(path+name)
            fen.destroy()
            self.user_list["values"] = self.get_users()
        else :
            texte = "{} {} {}\n{}".format(self.Loc_Data["2.5"], name, self.Loc_Data["2.6"], self.Loc_Data["2.7"])
            messagebox.showerror(title=self.Loc_Data["2.4"],
                                 message=texte)
    def create_user_wrapper(self):
        def creat_user_subwrapper():
            self.create_user(fen_new, name.get())
        
        fen_new = tk.Toplevel(self.root)
        fen_new.title(self.Loc_Data["2.8"])
        
        name = tk.StringVar()
        name_entry = tk.Entry(fen_new, textvariable=name)
        valid_but = tk.Button(fen_new, text=self.Loc_Data["2.9"],
                              command=creat_user_subwrapper)
        
        name_entry.grid(column=0, row=0)
        valid_but.grid(column=0, row=1, pady=10)
        
        Utils.center_(fen_new)
        
        fen_new.transient(self.root)
        fen_new.wait_visibility()
        fen_new.grab_set()
        fen_new.wait_window()
    
    def unlock_val(self, *args):
        if self.user_list.current() != -1 :
            self.valid_but["state"] = "active"
        else :
            self.valid_but["state"] = "disabled"
    def set_user(self):
        self.output = self.get_users()[self.user_list.current()]
        self.root.destroy()
        
    
    def run_window(self):
        self.root.title(self.Loc_Data["2.1"])
        self.root.resizable(False, False)
        
        self.user_list.grid(column=0, row=0)
        self.valid_but.grid(column=0, row=1)
        self.sep.grid(column=1, row=0, rowspan=2, sticky="ns", padx=10)
        self.new_but.grid(column=2, row=0, rowspan=2, sticky="ns")
        
        Utils.center_(self.root)
        
        self.user_list.bind("<<ComboboxSelected>>", self.unlock_val)
        
        self.root.mainloop()
        
        return (self.output)
