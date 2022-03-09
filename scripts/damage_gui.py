import io
import os
import subprocess
import shutil

import fcheck
import PySimpleGUI as sg

if sg.running_mac():
    import plistlib
    ttk_theme = 'aqua'
    sg.set_options(font='System 14')
else:
    import shlex
    import tempfile
    ttk_theme =  'vista'
    sg.set_options(font='Arial 9')

PROGNAME = (os.path.splitext(os.path.basename(__file__))[0])
global prefdict

sg.theme('systemDefaultForReal')

def pref_path()->tuple:
    '''
    Returns path to preferences directory and preferences
    file name as a tuple
    '''
    if sg.running_linux():
        return (os.path.expanduser('~/.config/damage'),
                'damage.json')
    if sg.running_mac():
        return (os.path.expanduser('~/Library/Preferences'), 'ca.ubc.library.damage.prefs.plist')
    if sg.running_windows():
        return (os.path.expanduser('~/AppData/Local/damage'), 'damage.json')

def get_prefs()->None:
    '''
    Gets preferences from JSON or default dict. If no preferences
    file is found, one is written
    '''
    global prefdict
    fpath, fname = pref_path()
    preffile = fpath + os.sep +fname
    try:
        if sg.running_mac():
            with open(preffile, 'rb') as fn:
                prefdict = plistlib.load(fn)
        if sg.running_linux() or sg.running_windows():
            with open(preffile) as fn:
                prefdict = sg.json.load(fn)

    except FileNotFoundError:
        prefdict = dict(flat=False,
                        recurse=False,
                        digest='md5',
                        out='txt',
                        short=True,
                        headers=True,
                        nonascii=True
                        )

def set_prefs()->None:
    '''
    Sets preferences
    '''
    fpath, fname = pref_path()
    preffile = fpath + os.sep + fname
    os.makedirs(fpath, exist_ok=True)
    if sg.running_mac():
        with open(preffile, 'wb') as fn:
            plistlib.dump(prefdict, fn)
    if sg.running_linux() or sg.running_windows():
        with open(preffile, 'w') as fn:
            sg.json.dump(prefdict, fn)

def damage(flist, **kwargs)->str:
    '''
    Text output from Damage utility
    '''
    if not flist:
        return None
    output = []
    for fil in flist:
        testme = fcheck.Checker(fil)
        output.append(testme.manifest(**kwargs))

    return '\n'.join(output)

def damage_table(flist, **kwargs)->(list, str):
    '''
    Create data for a tabular display
    '''
    output = []
    kwargs['header'] = True
    testme = fcheck.Checker(flist[0], **kwargs)
    #headers = testme.manifest(**kwargs)).split('\n')[0].split(',')
    #headers = [x.strip('"') for x in headers]
    output.append(testme.manifest(**kwargs))

    for fil in flist[1:]:
        kwargs['header'] = False
        testme=Checker(fil, **kwargs)
        output.append(testme.manifest(**kwargs))
    data = output.split('\n')
    data =[x.split(',') for x in data]
    data = [[y.strip('"')] for y in x for x in data]
    return data, output

def prefs_window()->sg.Window:
    '''Opens a preferences popup'''
    #All the options
    hashes =['md5','sha1', 'sha224', 'sha256', 'sha384', 'sha512',
             'blake2b', 'blake2s']
    outputs = ['txt','csv', 'json']
    layout = [[sg.Text('Damage Preferences', font='_ 18 bold')],
             [sg.Checkbox('Shorten file paths in output',
                           key= '-SHORT-',
                           default=prefdict['short'], )],
             [sg.Checkbox('Text file rectangularity check',
                           key= '-FLAT-',
                           default=prefdict['flat'], )],
             [sg.Checkbox('Recursively add files from directories',
                           key='-RECURSE-', default=prefdict['recurse'])],
             [sg.Text('Hash type'),
              sg.Combo(values=hashes, default_value=prefdict['digest'],
                       key='-DIGEST-', readonly=True)],
             [sg.Text('Output format'),
              sg.Combo(values=outputs, default_value=prefdict['out'],
                       key='-OUT-', readonly=True)],
             [sg.Ok(bind_return_key=True)]]
    pwindow = sg.Window(title='Preferences',
                     resizable=True,
                     layout=layout,
                     ttk_theme=ttk_theme,
                     use_ttk_buttons=True,
                     keep_on_top=True,
                     modal=True, finalize=True)
    pevent, pvalues = pwindow.read()
    if pevent:
        for key in ['short', 'flat', 'recurse', 'digest', 'out']:
            prefdict[key] = pvalues[f'-{key.upper()}-']

    set_prefs()
    pwindow.close()

def platform_menu():
    if running_mac():
        pass
        #Goddamn it

def popup_files_chooser_mac(initialdir=None)->list:
    '''
    popup files chooser broken on Mac. This is the editted replacement.
    '''
    root = sg.tk.Toplevel()
    try:
        root.attributes('-alpha', 0)  # hide window while building it. makes for smoother 'paint'
        # if not running_mac():
        try:
            root.wm_overrideredirect(True)
        except Exception as e:
            print('* Error performing wm_overrideredirect in get file *', e)
        root.withdraw()
    except:
        pass
    #filename = sg.tk.filedialog.askopenfilenames(filetypes=[('All','*.*')],
    #                                          initialdir=os.path.expanduser('~'),
    #                                          #initialfile=default_path,
    #                                          parent=root if not sg.running_mac() else None)
    #                                          #defaultextension=default_extension)  # show the 'get file' dialog box
    filenames = sg.tk.filedialog.askopenfilenames(parent=root if not sg.running_mac() else None,
                                                  initialdir=initialdir)
    root.destroy()
    return filenames

def get_folder_files(direc:str, recursive:bool=False, hidden:bool=False)->list:
    '''
    Gets files in a folder, recursive or no
    direc : str
        path to directory
    recursive : bool
        Return a recursive result. Default False
    hidden : bool
        Show hidden files. Default False
    '''
    if not direc:#Possible if window call cancelled, as I have discovered
        #return None
        return []
    if not recursive:
        flist = [[direc, x] for x in os.listdir(os.path.expanduser(direc))
                 if os.path.isfile(os.path.expanduser(direc)+os.sep+x)]
    if recursive:
        flist = [[a, d] for a, b, c in os.walk(os.path.expanduser(direc)) for d in c]
    if not hidden:
        flist=[x for x in flist if not x[1].startswith('.')]
    return flist

def send_to_file(outstring)->None:
    '''
    Sends output to file
    '''
    #Because TK is just easier
    outfile = sg.tk.filedialog.asksaveasfile(title='Save Output', 
                                       initialfile=f'output.{prefdict["out"]}',
                                       confirmoverwrite=True)
    if outfile:
        outfile.write(outstring)
        outfile.close()

def send_to_printer(outstring:str)->None:
    '''
    Sends output to lpr on Mac/linux and to default printer in Windows
    Data is unformatted. If you want formatting save to a file and use
    a text editor. Assumes UTF-8 for Mac/linux.
    '''
    outstring = io.StringIO(outstring)
    if sg.running_mac() or sg.running_linux():
        lpr =  subprocess.Popen(shutil.which('lpr'), stdin=subprocess.PIPE)
        lpr.stdin.write(bytes(outstring, 'utf-8'))

    if sg.running_windows():
        outfile = tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                              suffix='.txt', delete=False)
        outfile.write(outstring)
        outfile.close()

        #List of all printers names and shows default one
        #wmic printer get name,default
        #https://stackoverflow.com/questions/13311201/get-default-printer-name-from-command-line
        subout = subprocess.run(shlex.split('wmic printer get name,default'),
                                capture_output=True)
        #the following only makes sense of you look at the output of the 
        #windows shell command above. stout is binary, hence decode.
        printerinfo = [[x[:6].strip(), x[6:].strip()] for x in 
                        subout.stdout.decode().split('\n')[1:]]
        default_printer = [x for x in printerinfo if x[0] == 'TRUE'][0][1]
        subprocess.run(['print', f'/D:{default_printer}', outfile.name])
        #tempfile must be removed manually because of delete=False above
        os.remove(outfile.name)

def main_window()->sg.Window:
    '''
    The main damage window
    '''
    #def get_folder_items()->list:
    #    '''
    #    Get all items from a folder listing
    #    '''

    menu = sg.Menu([[PROGNAME, ['Preferences::tk::mac::ShowPreferences']],
                    ['File',['Add &Files',
                             'Add Fol&der',
                             '---',
                             '!&Save Output to File',
                             '!&Print Output::-PRINT-']],
                    ['Edit', ['&Copy',
                              '&Paste']],
                    ['Help', ['About']]],
                    key='-MENUBAR-')

    lbox = sg.Listbox(values=[], key='-SELECT-',
                          enable_events=True,
                          size=20,
                          select_mode=sg.LISTBOX_SELECT_MODE_EXTENDED,
                          horizontal_scroll=True,
                          expand_y=True,
                          expand_x=True)
    left = [[lbox],
            [sg.Input(visible=False, enable_events=True, key='-IN-'),
             sg.FilesBrowse(button_text='Add Files', target='-IN-'),
             sg.Input(visible=False, enable_events=True, key='-IFOLD-'),
             sg.FolderBrowse(button_text='Add Folder', key='-FOLDER-', target='-IFOLD-'),
             sg.Button(button_text='Remove Files',
                       enable_events=True, key='-DELETE-')]]

    right = [[sg.Multiline(key='-OUTPUT-',
                           size=40,
                           expand_x=True,
                           expand_y=True)],
             [sg.Text(expand_x=True),
              sg.Button('Generate Manifest',
                         key='-MANIFEST-') ]]

    layout = [[menu],
                [sg.Frame(title='File Section',
                         layout=left,
                         size=(400,800),
                         expand_y=True,
                         expand_x=True),
            sg.Frame(title='Output Section',
                     size=(800,800),
                     layout=right,
                     expand_y=True,
                     expand_x=True)]]

    print(prefdict.get('main_size'))
    window = sg.Window(title='Damage', layout=layout, resizable=True,
                      size = prefdict.get('main_size', (None, None)),
                      ttk_theme=ttk_theme,
                      use_ttk_buttons=True,
                      location= prefdict.get('main_location', (None, None)),
                      finalize=True, enable_close_attempted_event=True)
    lbox.Widget.config(borderwidth=0)
    window.set_min_size((875,400))
    return window

def main()->None:
    '''
    Main loop
    '''
    #TODO Force exclude mac .app bundles or have is_file check 
    #TODO Icon
    #TODO About
    #TODO Help
    #TODO CSV tabular output
    #TODO platform specific menu shortcuts

    get_prefs()
    window  = main_window()
    menulayout = window['-MENUBAR-'].MenuDefinition
    #I shouldn't have had to find that out by examining the class definition, FFS
    #vars(window['-MENUBAR-')
    while True:
        event, values = window.read()
        #sg.Print(relative_location=(500,0))
        #sg.Print(prefdict)

        if event in (sg.WINDOW_CLOSE_ATTEMPTED_EVENT,):
            prefdict['main_size'] = window.size
            prefdict['main_location'] = window.current_location()
            set_prefs()
            break

        if event == '-IN-':
            #sg.Print(f"Values=| {values['-IN-']} |", c='white on red')
            if len(values['-IN-']): # No way to set None, so empty is '', or len() == 0.
                upd_list = (window['-SELECT-'].get_list_values() +
                           [x for x in values['-IN-'].split(';') if
                            x not in window['-SELECT-'].get_list_values()])
                upd_list = [x for x in upd_list if os.path.isfile(x)]
                window['-SELECT-'].update(upd_list)
                window['-IN-'].update(value='')

        if event in ('-IFOLD-', 'Add Folder'):
            if event == 'Add Folder':
                newfiles = get_folder_files(sg.popup_get_folder('', no_window=True))
            else:
                newfiles = get_folder_files(values['-IFOLD-'], prefdict['recurse'])
                #sg.Print(newfiles, c='red on yellow')
            upd_list = (window['-SELECT-'].get_list_values() +
                   [x[0]+os.sep+x[1] for x in newfiles if
                    x[0]+os.sep+x[1] not in window['-SELECT-'].get_list_values()])
            upd_list = [x for x in upd_list if os.path.isfile(x)]
            window['-SELECT-'].update(upd_list)

        if event == '-DELETE-':
            nlist = [x for x in window['-SELECT-'].get_list_values() if
                    x not in values['-SELECT-']]
            window['-SELECT-'].update(nlist)
            #print(nlist)

        if event == '-MANIFEST-':
            try:
                delme = ''
                upd_list = window['-SELECT-'].get_list_values()
                if upd_list == ['']:
                    upd_list = []
                window['-OUTPUT-'].update('')
                if upd_list:
                    txt = damage(upd_list, **prefdict)
                    if prefdict['short'] and len(upd_list) > 1:
                        delme = os.path.commonpath(upd_list) + os.sep
                        window['-OUTPUT-'].update(txt.replace(delme,''))
                    elif prefdict['short'] and len(upd_list) == 1:
                        delme = os.path.split(upd_list[0])[0] + os.sep
                    txt = txt.replace(delme,'')
                    window['-OUTPUT-'].update(txt)

            except (ValueError, NameError, AttributeError):
                window['-OUTPUT-'].update('')

        if event == 'Preferences::tk::mac::ShowPreferences':
            prefs_window()
            window['-OUTPUT-'].update('')

        if window['-OUTPUT-'].get():
            #update menu
            menulayout[1][1][3] = '&Save Output to File'
            menulayout[1][1][4] = '&Print Output::-PRINT-'
            window['-MENUBAR-'].update(menulayout)
        else:
            menulayout[1][1][3] = '!&Save Output to File'
            menulayout[1][1][4] = '!&Print Output::-PRINT-'
            window['-MENUBAR-'].update(menulayout)

        #Menubar events
        if event == 'Add Files':
            if sg.running_mac():#Mac will crash using sg.popup_get_file
                newfiles = popup_files_chooser_mac()
            else:
                newfiles = sg.popup_get_file('', no_window=True, file_types = sg.FILE_TYPES_ALL_TYPES)
            upd_list = (window['-SELECT-'].get_list_values() +
                   [x for x in newfiles if
                    x not in window['-SELECT-'].get_list_values()])
            window['-SELECT-'].update(upd_list)
        
        if event == 'Save Output to File':
            send_to_file(values['-OUTPUT-'])
            
    window.close()

if __name__ == '__main__':
    main()


'''
#https://stackoverflow.com/questions/12723818/print-to-standard-printer-from-python
#printing
#MAC and Linux
import io
import subprocess
import shutil

fil = io.BytesIO(b'aljfdladjfa')
lpr = subprocess.Popen(shutil.which('lpr'), stdin=subprocess.PIPE)
lpr.stdin.write(fil.read())
'''


'''
#THIS PRINTS ON WINDOWS!
import os
import shlex #see splitting expression here: https://docs.python.org/3/library/subprocess.html
import tempfile
#import win32print
#https://pypi.org/project/pywin32/
#pywin32 comes with win32print
#text will be unformatted
outfile = tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False)
outfile.write('your data here')
outfile.close()

#get a list of printers on windows:
subout = subprocess.run(shlex.split('wmic printer get name,default'), capture_output=True)
printerinfo = [[x[:6].strip(), x[6:].strip()] for x in subout.stdout.decode().split('\n')[1:]]
default_printer = [x for x in printerinfo if x[0] == 'TRUE'][0][1]

#List of all printers names and shows default one
#wmic printer get name,default
#https://stackoverflow.com/questions/13311201/get-default-printer-name-from-command-line
#subprocess.run(['print', f'/D:{win32print.GetDefaultPrinter()}', outfile.name])

subprocess.run(['print', f'/D:default_printer}', outfile.name])
os.remove(outfile.name)
'''
