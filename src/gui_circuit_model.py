from dataclasses import dataclass, field

from kipy import KiCad
from kipy.board import Board
from kipy.errors import ApiError
from kipy.proto.board.board_types_pb2 import BoardLayer

from api_warning import api_warning
from translator import MockUpOptions

"""
Convention:
pad name: U1-1, U1-2
net: /A, /+12V
component: U1, U2
pin: 1, 2
"""



@dataclass
class GuiCircuitModel():
    nets:          list[str] = field(default_factory=list, init=False)
    components:    list[str] = field(default_factory=list, init=False)
    padID_by_pad:  dict[str, str] = field(default_factory=dict, init=False)
    net_of_pad:    dict[str, str] = field(default_factory=dict, init=False)
    pads_in_net:   dict[str, list[str]] = field(default_factory=dict, init=False)
    pads_by_padID: dict[str, list[str]] = field(default_factory=dict, init=False)
    net_of_component_pin: dict[tuple[str, str], str] = field(default_factory=dict, init=False)

    pins_of_component: dict[str, list[str]] = field(default_factory=dict, init=False)
    components_in_net: dict[str, set[str]]  = field(default_factory=dict, init=False)
    nets_on_component: dict[str, set[str]]  = field(default_factory=dict, init=False)

    #? layerID_by_layer_name

    @classmethod
    def get_instance(cls) -> GuiCircuitModel:
        if not cls.inst:
            raise Exception("GuiCircuitModel uninitialized")
        return cls.inst

    @classmethod
    def from_KiCad(cls, board: Board) -> GuiCircuitModel:
        inst = cls()
        try:
            nets = board.get_nets()
            fp_instances = board.get_footprints()
        except ApiError as err:
            if err.code == 7:
                api_warning()
            exit()

        for net in nets:
            if not net.name: continue
            inst.nets.append(net.name)
            inst.pads_in_net[net.name] = []
            inst.components_in_net[net.name] = set()

        for fpi in fp_instances:
            fp_name: str = fpi.reference_field.text.value
            if not fp_name:
                fp_name = "None"
            inst.nets_on_component[fp_name] = set()
            inst.pins_of_component[fp_name] = []
            inst.components.append(fp_name)
            for pad in fpi.definition.pads:
                inst.pads_by_padID[pad.id.value] = []
                inst.components_in_net[pad.net.name].add(fp_name)
                inst.pins_of_component[fp_name].append(pad.number)
                inst.nets_on_component[fp_name].add(pad.net.name)
                inst.net_of_component_pin[(fp_name, pad.number)] = pad.net.name

                layers = pad.padstack.layers
                if BoardLayer.BL_F_Cu in layers and BoardLayer.BL_B_Cu in layers:
                    pad_name: str = f"{fp_name}-{pad.number} (Front)"
                    inst.padID_by_pad[pad_name] = pad.id.value
                    inst.pads_by_padID[pad.id.value].append(pad_name)
                    inst.pads_in_net[pad.net.name].append(pad_name)
                    inst.net_of_pad[pad_name] = pad.net.name

                    pad_name: str = f"{fp_name}-{pad.number} (Back)"
                    inst.padID_by_pad[pad_name] = pad.id.value
                    inst.pads_by_padID[pad.id.value].append(pad_name)
                    inst.pads_in_net[pad.net.name].append(pad_name)
                    inst.net_of_pad[pad_name] = pad.net.name
                else:
                    pad_name: str = f"{fp_name}-{pad.number}"
                    inst.padID_by_pad[pad_name] = pad.id.value
                    inst.pads_by_padID[pad.id.value].append(pad_name)
                    inst.pads_in_net[pad.net.name].append(pad_name)
                    inst.net_of_pad[pad_name] = pad.net.name

        # remove nets with less than 2 connecting pads as they are irrelevant to our modelling
        remove = []
        for net, pad_names in inst.pads_in_net.items():
            print(net, ": ", pad_names)
            if len(pad_names) < 2:
                remove.append(net)
        for net in remove:
            inst.pads_in_net.pop(net)
            inst.nets.remove(net)
            for component, nets in inst.nets_on_component.items():
                if net in nets:
                    inst.nets_on_component[component].remove(net)
            print("removed ", net)



        cls.inst = inst
        return inst

    def get_mockup_options_for_components(self, components: list[str]) -> dict[str, list[str]]:
        #TODO
        """ TODO
            Check if has 2 pins -> direct, 3 pins -> middle?, more -> only mockup
            check if has graphic elements on layer,
            beware not text element
        """
        dict = {}
        for c in components:
            dict[c] = [MockUpOptions.direct.name, MockUpOptions.mock_up.name]
        return dict






        pass

    def get_pads_in_net(self, net: str) -> list[str]:
        return self.pads_in_net[net]

    def get_components_in_net(self, net: str) -> list[str]:
        return list(self.components_in_net[net])

    def get_nets_on_component(self, component: str) -> list[str]:
        return list(self.nets_on_component[component])

    def get_nets(self) -> list[str]:
        return self.nets

    def get_components(self) -> list[str]:
        return self.components

    def get_net_of_pad(self, pad: str) -> str:
        return self.net_of_pad[pad]

    def get_net_of_component_pin(self, component: str, pin: str) -> str:
        return self.net_of_component_pin[(component, pin)]

    def get_component_pin_dict(self) -> dict[str, list[str]]:
        return self.pins_of_component