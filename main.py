import os
from dataclasses import dataclass, asdict
import os
import sys
import threading
import dearpygui.dearpygui as dpg
import dearpygui_ext.logger as logger
from glob import glob

OLD_AP = "\\Old\\"
NEW_AP = "\\New\\"
RES_AP = "\\Result\\"
SCENE_AP = "\\SceneFile\\"
LIB_AP = "\\Lib\\"
SINGLE_FILE_ID = "11500000"


lock_mode:bool = False
mode:bool = False
scene_text = ""
dialog_tag = ""
scene_path = ""
assets_path = ""
old_path = ""
new_path = ""
old_text = ""
result_path = ""
entries = []
_log:logger.mvLogger

last_module_entries = []
modules = []


@dataclass
class Entry:
    file_path:str
    old_guid:str
    new_guid:str
    old_file_id:str = ""

    def to_dict(self):
        return {k: str(v) for k, v in asdict(self).items()}



def is_old_dll(module) -> bool:
    return module.endswith(".dll")

def absolute_file_paths(directory):
    for dirpath,_,filenames in os.walk(directory):
        for f in filenames:
            yield os.path.abspath(os.path.join(dirpath, f))

def collect_olds_and_paths(module:str):
    old_path = module

    result = [y for x in os.walk(old_path) for y in glob(os.path.join(x[0], '*.meta'))]
    
    for path in result:
        guid:str
        with open(path) as f:
            f.readline()
            second_line = f.readline()
            guid = second_line[6:][:-1]
        file_path = path.removeprefix(old_path)
        e = Entry(file_path, guid, "")
        last_module_entries.append(e)

def collect_news_and_paths_dll(module:str):

    import clr

    for path in absolute_file_paths(sys.path[0] + LIB_AP):
        clr.AddReference(path)




    from ReflectLib import ReflectClass
    main = ReflectClass()

    m_new_path = module.replace(old_path, new_path).removesuffix(".dll")
    result = [y for x in os.walk(m_new_path) for y in glob(os.path.join(x[0], '*.cs'))]
    for file in result:
        #print(f"working on {file}")

        meta = file + ".meta"
        file_path = file.removeprefix(m_new_path)
        guid:str
        with open(meta) as f:
            f.readline()
            second_line = f.readline()
            guid = second_line[6:][:-1]
        for n in main.GetNamespaceMemberNames(file):
            id = get_id(n)
            e = Entry(file_path, "", guid, id)
            last_module_entries.append(e)
            #print(f"{e.file_path}: {id} {e.old_guid} -> {e.new_guid}")

def entries_to_json():
    import json
    file = None
    path = result_path + "results_new.json"
    try:
        file = open(path, "r+")
        file.truncate(0)
    except:
        file = open(path, "x")
    
    file.write(json.dumps([x.to_dict() for x in entries], indent = 2))
    file.close()
    log_trace(f"Wrote entries to {path}")

def collect_old_guids_dll(module:str):
    meta = module+".meta"
    guid = get_meta_guid(meta)

    for e in last_module_entries:
        e.old_guid = guid
        log_info(f"Collected {module.removeprefix(old_path)}\{e.file_path} guid {e.new_guid}" )


def get_meta_guid(file_path:str):
    with open(file_path) as f:
        f.readline()
        second_line = f.readline()
        guid = second_line[6:][:-1]
        return guid




# hypothesis end

def get_id(namespacename) -> int:
    from Crypto.Hash import MD4
    s = "s\0\0\0"+namespacename
    hashObject = MD4.new(s.encode())
    digest = hashObject.digest()
    raw_bytes = digest[:4]
    id = int.from_bytes(raw_bytes, "little", signed = True)
    return id


def collect_news(module:str):


    e:Entry
    for_remove = []
    for e in last_module_entries:
        path = module.replace(OLD_AP, NEW_AP) + e.file_path
        guid:str
        try:
            with open(path) as f:
                f.readline()
                second_line = f.readline()
                guid = second_line[6:][:-1]
            e.new_guid = guid
            
            #print(f"{e.file_path}: {e.old_guid} -> {e.new_guid}")
            #print(guid)
            log_info(f"Collected {module.removeprefix(old_path)}\{e.file_path} guid {e.new_guid}" )
        except:
            for_remove.append(e)

def work_on_scene():
    global scene_text
    text = scene_text
    for e in last_module_entries:
        if len(e.new_guid) > 0:
            text = text.replace(e.old_guid, e.new_guid)
   
    if text == old_text:
        raise Exception()
    scene_text = text

def work_on_scene_all():

    log_trace(f"Starting working on scene {scene_path}")

    scene = scene_path
    with open(scene, encoding="utf-8") as f:
        scene_text = f.read()
        old_text = scene_text

    text = scene_text
    old_text = text
    for e in entries:

        if e.old_guid not in text:
            continue
        old_format = f"fileID: {e.old_file_id}, guid: {e.old_guid}"
        if old_format not in text:
            old_format = f"fileID: {SINGLE_FILE_ID}, guid: {e.old_guid}"
        new_format = f"fileID: {SINGLE_FILE_ID}, guid: {e.new_guid}"
        text = text.replace(old_format, new_format)




        log_info(f"Found old guid of {e.file_path}. Replacing.")
   
    if text == old_text:
        #breakpoint()
        log_critical("Scene is unchanged. It probably doesn't have old guids in it.")
    
    scene_text = text

    def try_create(new_file_path:str) -> bool:
        try:
            with open(new_file_path, "x", encoding="utf-8") as new:
                #breakpoint()
                new.write(scene_text)

            return True
        except:
            #breakpoint()
            return False
    global mode
    if not mode:
        new_file_path:str = result_path + os.path.split(scene_path)[1]
        changed_file_path = new_file_path
        index = 0
        while not try_create(changed_file_path):
            log_critical(f"{changed_file_path} already exists. adding (n) to name")
            #breakpoint()
            from pathlib import Path
            ext = os.path.splitext(new_file_path)[1]
            changed_file_path = f"{new_file_path.removesuffix(ext)}({index}){ext}"
            index+=1





def work_on_prefabs_dir():
    #breakpoint()
    path = assets_path
    prefabs = [y for x in os.walk(path) for y in glob(os.path.join(x[0], '*.prefab'))]
    assets = [y for x in os.walk(path) for y in glob(os.path.join(x[0], '*.asset'))]
    mats = [y for x in os.walk(path) for y in glob(os.path.join(x[0], '*.mat'))]
    anims = [y for x in os.walk(path) for y in glob(os.path.join(x[0], '*.anim'))]
    result = prefabs + assets + mats + anims

    def write_prefab(prefab:str):
        text:str
        old_text:str
        log_info(f"Progress {result.index(prefab)} / {len(result)} File: {prefab.removeprefix(assets_path)}")

        with open(prefab, encoding="utf-8") as f:
            text = f.read()
            old_text = text 
        for e in entries:
            old_format = f"fileID: {e.old_file_id}, guid: {e.old_guid}"
            if old_format not in text:
                old_format = f"fileID: {SINGLE_FILE_ID}, guid: {e.old_guid}"
            


            new_format = f"fileID: {SINGLE_FILE_ID}, guid :{e.new_guid}"
            text = text.replace(old_format, new_format)
            

        if text == old_text:
            pass

        with open(prefab, "w", encoding="utf-8") as new:
            new.write(text)


    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        executor.map(write_prefab, result)
        executor.shutdown()


    

    
def get_modules():
    for d in os.listdir(old_path):
        dir:str = old_path + d
        if os.path.isdir(dir) and os.path.isdir(new_path + d.removeprefix(old_path)):
            modules.append(dir)
        elif d.endswith(".dll") and os.path.exists(dir + ".meta"):
            if not os.path.isdir(new_path + d.removeprefix(old_path).removesuffix(".dll")):
                print("no corresponding folder, is it bad?")

            modules.append(dir)

def log_info(text:str):
    print(text)
    _log.log_info(text)


def log_critical(text:str):
    print(text)
    _log.log_critical(text)

def log_trace(text):
    print(text)
    _log.log(text)


def run():
    global scene_path
    global old_path
    global new_path
    global assets_path
    global old_text
    global entries
    global result_path
    global last_module_entries
    global modules

    scene_path = dpg.get_value("scenepath")
    assets_path = dpg.get_value("assetspath")
    old_path = dpg.get_value("oldpath")
    new_path = dpg.get_value("newpath")
    
    result_path = dpg.get_value("resultpath")

    entries.clear()
    last_module_entries.clear()
    get_modules()
    log_trace(f"Starting collecting modules")
    m:str
    threads = []

    modules_collected = 0

    def collect_module(m):
        log_trace(f"Collecting module {m}")
        last_module_entries.clear()
        if not is_old_dll(m):
            collect_olds_and_paths(m)
            collect_news(m)
        else:
            collect_news_and_paths_dll(m)
            collect_old_guids_dll(m)

        global entries
        entries+=last_module_entries
        nonlocal modules_collected
        modules_collected+=1



    for m in modules:
        t = threading.Thread(target=collect_module, args=[m], daemon=True)
        t.start()

    import time
    while modules_collected < len(modules):
        time.sleep(0.05)
        

    entries_to_json()

    if mode:
        work_on_prefabs_dir()
    else:
        work_on_scene_all()

        
    log_trace("Complete!")

        
dpg.create_context()


def run_callback(sender, app_data):
    run()

def enable_children_recursive(tag:str, value:bool):

    children = dpg.get_item_children(tag)
    for i in children:
        for v in children[i]:
            try:
                dpg.configure_item(v, enabled = value)
            except:
                pass
            finally:
                enable_children_recursive(v, value)



def file_callback(sender, app_data:dict):
    print(app_data)
    path = app_data["file_path_name"]
    dpg.set_value(dialog_tag, path)

    # reenable
    global lock_mode
    lock_mode = False
    enable_children_recursive("mainwindow", True)
    


def file_cancel_callback(sender, app_data):
    print('Cancel was clicked.')
    print("Sender: ", sender)
    print("App Data: ", app_data)

        # reenable
    global lock_mode
    lock_mode = False
    enable_children_recursive("mainwindow", True)

with dpg.file_dialog(
    directory_selector=False,
    show=False, callback=file_callback, tag="file_dialog_id",
    cancel_callback=file_cancel_callback, width=700 ,height=600):

    dpg.add_file_extension(".unity")


with dpg.file_dialog(
    directory_selector=True,
    show=False, callback=file_callback, tag="dir_dialog_id",
    cancel_callback=file_cancel_callback, width=700 ,height=600):
    pass



def create_dir_input(header:str, input_tag:str, *, dir:bool = False, default_value:str = ""):
    with dpg.group(horizontal=True):
        dpg.add_text(header)
        dpg.add_input_text(tag=input_tag)
        dpg.set_value(input_tag, default_value)

        def this_callback():
            global dialog_tag
            dialog_tag = input_tag

            # disable all other controls
            global lock_mode
            lock_mode = True
            enable_children_recursive("mainwindow", False)

            dpg.show_item("file_dialog_id" if not dir else "dir_dialog_id")
        dpg.add_button(label="Select...", callback=this_callback)

dpg.create_viewport(title='UnityGuidReplacer', width=800, height=850)
dpg.setup_dearpygui()

with dpg.theme() as disabled_theme:
    with dpg.theme_component(dpg.mvInputFloat, enabled_state=False):
        dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 0, 0])
        dpg.add_theme_color(dpg.mvThemeCol_Button, [255, 0, 0])

    with dpg.theme_component(dpg.mvInputInt, enabled_state=False):
        dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 0, 0])
        dpg.add_theme_color(dpg.mvThemeCol_Button, [255, 0, 0])

dpg.bind_theme(disabled_theme)

with dpg.theme() as global_theme:
    for comp_type in (dpg.mvMenuItem, dpg.mvButton, dpg.mvText):
        with dpg.theme_component(comp_type, enabled_state=False):
            dpg.add_theme_color(dpg.mvThemeCol_Text, (0.50 * 255, 0.50 * 255, 0.50 * 255, 1.00 * 255))


dpg.bind_theme(global_theme)





with dpg.window(label="Example Window", tag="mainwindow"):

    def tabbar_callback(caller, app_data):
        global mode
        global lock_mode
        new_mode = dpg.get_item_info(app_data) == dpg.get_item_info("tb_as")

        print(f"New tab {new_mode}")
        if lock_mode:
            print("forcing value")
            dpg.set_value("tb", "tb_as" if mode else "tb_sc")
        else:
            mode = new_mode

    
    with dpg.tab_bar(label="tabbar", tag="tb", callback=tabbar_callback):

        with dpg.tab(label="scene", tag="tb_sc"):
            create_dir_input("Scene:", "scenepath")
            create_dir_input("Result Folder:", "resultpath", dir=True, default_value=sys.path[0] + RES_AP)
        
        print(dpg.get_item_info("tb_sc"))

        with dpg.tab(label="assets", tag="tb_as"):
            create_dir_input("Assets:", "assetspath", dir=True)
    
    create_dir_input("Old Modules Folder:", "oldpath", dir=True, default_value=sys.path[0] + OLD_AP)
    create_dir_input("New Modules Folder:", "newpath", dir=True, default_value=sys.path[0] + NEW_AP)
        
    dpg.add_button(label="Run", width= 100, height=50, callback=run_callback)

    _log=logger.mvLogger("mainwindow")
    _log.flush_count = 10000000000
    dpg.configure_item(_log.child_id, autosize_y = False)
    dpg.set_item_height(_log.child_id, 550)




if __name__ == "__main__":
    dpg.show_viewport()
    dpg.set_primary_window("mainwindow", True)
    dpg.start_dearpygui()
    dpg.destroy_context()


