# TLI-ASTE
## _Triplets Labelling GUI for Aspect Sentiment Triplet Extraction (ASTE) tasks_
version 1.0.0

TLI-ASTE is a 100% Python-based interface based on Tkinter. This interface allows the labelling of triplets contained in reviews in order to establish a dataset adapted to NLP tasks of the ASTE type.

---
## Cautionary notes
Even if some features can be customised to fit your data, TLI-ASTE is only used for labelling triplets and is not supposed to do any pre-processing on your data. If you still want to do pre-processing when loading the data through the interface, do so at your own risk: some reviews may be badly displayed/processed/cut off.

If pre-processing is necessary, it is recommended that you do it before your data is loaded by the interface.

---
## Installation and preparation for the first launch
### Prerequisites:
The default Python environment provided with Anaconda is sufficient. For those who want to install the bare minimum, the interface uses only 4 modules: ``` tkinter```, ```numpy```, ```os``` and ```time```.

TLI-ASTE has been tested for Python 3.7.3 (version Anaconda3-2019.03) and 3.9.12 (version Anaconda3-2022.05). The interface should normally work with your current version of Python but if it does not, you can revert to one of the tested versions.

### Preparation for the first launch:
Before launching TLI-ASTE for the first time, some functions in the Custom_funcs.py file must be defined by the user to be adapted to the data used. More detailed information is available in the template provided.
- ```GET_COMMS(mode, lang, params, func_for_invalid_carac)```: Mandatory function. Allows to load the reviews according to the chosen mode and language. The parameters to be used are passed via params and func_for_invalid_carac is the function to check if incompatible characters are present in the review.
- ```GET_COMM_LEN(comm, lang)```: Mandatory function. Simply retrieves the length of a review from the file line.
- ```Word_Sep(text)```: Optional function. Defines how words will be extracted from the text. In case this function does not exist or is not defined or returns a None, a default function will be used instead. This function is described in the Help folder

Then you have to configure the ```metadata.CONFIG_``` file. Preferably use an editor like Notepad++ and fill in the empty fields after the ```=``` without spaces as follows:
- ```InputFilename``` : the name of the text file containing all the reviews to be labelled
- ```AvailableLanguage``` : list of the languages of the reviews separated by '';'' without space before and after
- ```InputDataDir``` : relative path of the folder containing the files of reviews to be labelled
- ```OutputDataDir``` : relative path of the folder containing the labelled reviews files
- ```CuratedDataDir``` : relative path of the folder containing the files of validated reviews 

Warning: all the files containing the reviews to be labelled have the same name with one difference, which is the language of the comments. These files in InputDataDir are therefore of the form  ```(InputFilename)_(langue).txt```

Example of configuration of ```metadata.CONFIG_``` :
My files containing the reviews to be labelled are called _MyData_ and I have reviews in 3 languages: French, English and Italian. These files are called respectively ```MyData_fr.txt```, ```MyData_en.txt``` and ```MyData_it.txt```. I decide to call the folder containing the files of the reviews to be labelled, the one containing the files of the labelled reviews and the one containing the files of the validated reviews respectively ```ToLabelFiles```, ```LabeledFiles``` and ```ValidatedFiles```. Therefore, the metadata.CONFIG_ file must be configured as follows:
```sh
InputFilename=MyData
AvailableLanguage=fr;en;it
InputDataDir=Data/ToLabelFiles/
OutputDataDir=Data/LabeledFiles/
CuratedDataDir=Data/ValidatedFiles/
```

All that remains to be done is to place the comment files to be labelled in the folder _(InputDataDir)_ and prepare the localisation files before the interface is ready to be launched. The texts displayed can change according to the user's preferences and the languages available in the Localisations folder. For each language, 2 files must be specified:
- ```(language).LOC_```: a file containing each line of interface text independent of the reviews
- ```(language).LANG_DICT``` : a file which gives the full name of the languages specified in ```metadata.CONFIG_```.

For the moment, only English and French are available by default but if you wish, you can add your own language by creating the two necessary files as follows:
- ```(language).LOC_``` : translate each line after the ```=``` without any space after, respecting punctuation and spacing
- ```(language).LANG_DICT``` : specify per line in the form ''(short version)=(full version)'' for each language in ```metadata.CONFIG_``` (example for ''en'' in English : ''en=English'')

---
## Quick user guide
TLI-ASTE has 2 interfaces: one for labelling and another for validation. It is important to note that the work done on a review for both interfaces is only saved when the review is validated. More information is available in the help files dedicated to each interface in the Help folder.

When launching any interface, a window will ask you to select the location to be used along the current session.
### Labelling interface:
Before arriving at the labelling interface, several small windows will appear in this order:
- Partition creation window: Only runs if the partition information files are not present in the folder (InputDataDir). It proposes by language to define or not a rule of separation of the reviews in smaller files in order to facilitate the separation of the work between several users. The operations of creating the partitions and pre-loading the reviews can take several minutes, so please be patient.
- User selection window: Offers the possibility to create users if needed. Each user's work is separate and independent from other users.
- Partition selection window: For each review language to be labelled, select one of the available partitions.
- Incompatible characters check window: This window reads all previously loaded reviews and informs you of the proportion of characters incompatible with Tkinter. Each review with one or more of these characters will be ignored in the following step.
- Review loading window: Loads all reviews from the selected partitions into memory.

You are now on the interface, ready to label the triplets. To do so, you have 4 selection modes:
- Selection with spinboxes interacting with the mouse
- Selection with shortcuts
- Selection on the fly in text
- Backup mode

To add a triplet, simply press the dedicated button or shortcut after filling in the aspect, opinion and feeling information. You can manage your triplets by deleting or modifying erroneous triplets.

You can manage your reviews by moving quickly between unlabelled and labelled reviews if you need to modify them. You can also declare a review inconsistent if it doesn't fit, doesn't make sense or has no triplets.

You can change your preferences in the settings, and you can see your labelling statistics at any moment if needed.

### Validation interface :
Before reaching the validation interface, several small windows will appear in this order:
- Partition selection window: You have to select a partition to validate among all the ones that have at least 2 users working on them. If no partition is available, you will not go any further.
- Review loading window: Loads all reviews of the selected partitions into memory.

You are now on the interface, ready to validate the triplets. On the left are the users' triplets and the curator's triplet if he needs to create one, while on the right is the review with a heatmap representing the number of users who selected each word.

To validate a triplet and move on to the next one in the review, just click on one of the user or curator buttons, enter the curator triplet if the option has been checked, and click on the triplet validation button. There is also the possibility to select nothing if none of the proposed triples are consistent.

To validate a comment, you must validate at least all the triples present in the review. A coloured "progress bar" on the right between the comment and the heatmap legend indicates where you are in the review and the status of each triplet.

Selecting a curator triplet is done in the same way as in the labelling interface.

You can change the colours of the heatmap, the colours indicating the status of a triplet and the colours of the labelled by users status of the review in a dedicated menu.

---
## Customisation
With the different menus, it is possible to modify the shortcuts as you wish, to modify the size of the texts to make the interface more readable if necessary and to change the colour codes used in the validation interface.

With the Custom_funcs.py script, TLI-ASTE adapts to your dataset as well as possible. The GET_COMMS function will allow you to load the data by applying the general treatments you want or need.

---
## Known issues
- Tkinter, in the version used (tk 8.6.11), does not support and cannot display characters whose unicode exceeds 4 digits. The usable characters are limited to U+0000 to U+FFFF included.
- The use of classic notepad such as Windows' can lead to the appearance of special characters that will generate problems later on. For example, Windows' Notepad adds the special character ```\ufeff``` at the beginning of a file.
- In the labelling interface, after using a shortcut that opens a window, the same window opens in as many additional copies as it is used if the shortcut is used again before clicking/interacting with the first open window.
- In the labelling interface, once a partition/language has been fully labelled, the interface does not update. A manual review change is required.
