import os
from kipy import KiCad
from kipy.proto.board.board_types_pb2 import BoardLayer
from kipy.board_types import Pad
import json
from gui import App
from translator import Translator

from util import ensure_fasthenry_path, ensure_settings_exist

if __name__ == "__main__":
    kicad = KiCad()
    settings_dir = kicad.get_plugin_settings_path("com_github_tobiglaser_kipex")
    working_dir = kicad.get_project(kicad.get_board().document).path
    working_dir = os.path.join(working_dir, "KiPEX")
    project_title = kicad.get_project(kicad.get_board().document).name
    print(working_dir)
    if not os.path.exists(working_dir):
        os.mkdir(working_dir)
    os.chdir(working_dir)
    print(os.getcwd())

    ensure_settings_exist(settings_dir, "settings.json")
    settings_path = os.path.join(settings_dir, "settings.json")
    with open(settings_path) as settings_file:
        settings = json.load(settings_file)
    
    board = KiCad().get_board()
    nets = board.get_nets()
    pads = board.get_pads()
    fp_instances = board.get_footprints()
    net_pad_name_dict: dict[str, list[str]] = {}
    pads_by_id: dict[str, Pad] = {}
    pad_id_by_name: dict[str, str] = {}
    pad_names_by_id: dict[str, list[str]] = {}
    pad_by_name: dict[str, Pad] = {}
    for net in nets:
        net_pad_name_dict[net.name] = []
    for fpi in fp_instances:
        for pad in fpi.definition.pads:
            fp_name = fpi.reference_field.text.value
            if not fp_name:
                fp_name = "None"
            #pad_name = f"{fp_name}-{pad.number}"
            #pad_id_by_name[pad_name] = pad.id.value
            #pad_name_by_id[pad.id.value] = pad_name

            layers = pad.padstack.layers
            pad_names_by_id[pad.id.value] = []
            if BoardLayer.BL_F_Cu in layers and BoardLayer.BL_B_Cu in layers:
                # front and back
                pad_name = f"{fp_name}-{pad.number} (Front)"
                pad_id_by_name[pad_name] = pad.id.value
                pad_names_by_id[pad.id.value].append(pad_name)
                pad_by_name[pad_name] = pad
                net_pad_name_dict[pad.net.name].append(pad_name)
                pad_name = f"{fp_name}-{pad.number} (Back)"
                pad_id_by_name[pad_name] = pad.id.value
                pad_names_by_id[pad.id.value].append(pad_name)
                net_pad_name_dict[pad.net.name].append(pad_name)
                pad_by_name[pad_name] = pad
                pass
            else:
                pad_name = f"{fp_name}-{pad.number}"
                pad_id_by_name[pad_name] = pad.id.value
                if BoardLayer.BL_F_Cu in layers:
                    layer = BoardLayer.BL_F_Cu
                else:
                    layer = BoardLayer.BL_B_Cu
                pad_names_by_id[pad.id.value].append(pad_name)
                net_pad_name_dict[pad.net.name].append(pad_name)
                pad_by_name[pad_name] = pad
                pass

    for pad in pads:
        pads_by_id[pad.id.value] = pad
        print(pad)

    remove = []
    for key, value in net_pad_name_dict.items():
        print(key, ": ", value)
        if len(value) < 2:
            remove.append(key)
    for key in remove:
        net_pad_name_dict.pop(key)
        print("removed ", key)

    app = App(redirect=True, project_name=project_title, settings=settings)
    ensure_fasthenry_path(settings)
    app.set_net_pads(net_pad_name_dict)

    translator = Translator(board, pad_by_name)
    app.set_translator(translator)

    app.run()
    with open(settings_path, 'w') as settings_file:
        settings_file.write(json.dumps(settings, indent=4))





