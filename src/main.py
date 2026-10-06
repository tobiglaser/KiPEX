import os
from kipy import KiCad
from kipy.kicad import KiCadVersion
from kipy.errors import ApiError
from kipy.proto.board.board_types_pb2 import BoardLayer
from kipy.board_types import Pad
import json
from gui import App
from translator import Translator
from api_warning import api_warning
from gui_circuit_model import GuiCircuitModel
from util import ensure_fasthenry_path, ensure_settings_exist

if __name__ == "__main__":
    kicad = KiCad()
    if kicad.get_version() < KiCadVersion(10, 0, 5, ""): # see https://www.kicad.org/blog/2026/07/KiCad-10.0.5-Release/
        settings_dir = kicad.get_plugin_settings_path("com_github_tobiglaser_kipex")
    else:
        settings_dir = kicad.get_plugin_settings_path("com.github.tobiglaser.kipex")
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
    
    try:
        board = KiCad().get_board()
        nets = board.get_nets()
        fp_instances = board.get_footprints()
    except ApiError as err:
        if err.code == 7:
            api_warning()
        exit()
    pad_by_name: dict[str, Pad] = {}
    for fpi in fp_instances:
        for pad in fpi.definition.pads:
            fp_name = fpi.reference_field.text.value
            if not fp_name:
                fp_name = "None"
            layers = pad.padstack.layers
            if BoardLayer.BL_F_Cu in layers and BoardLayer.BL_B_Cu in layers:
                # front and back
                pad_name = f"{fp_name}-{pad.number} (Front)"
                pad_by_name[pad_name] = pad
                pad_name = f"{fp_name}-{pad.number} (Back)"
                pad_by_name[pad_name] = pad
            else:
                pad_name = f"{fp_name}-{pad.number}"
                pad_by_name[pad_name] = pad

    GuiCircuitModel.from_KiCad(board)

    app = App(redirect=True, project_name=project_title, settings=settings)
    ensure_fasthenry_path(settings)

    translator = Translator(board, pad_by_name)
    app.set_translator(translator)

    app.run()
    with open(settings_path, 'w') as settings_file:
        settings_file.write(json.dumps(settings, indent=4))





