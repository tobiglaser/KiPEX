# Parasitic Extraction Addon for KiCad (KiPEX)

KiPEX is an AddOn for KiCad, enabling fast and simple calculation of resistance and inductance of PCB copper features.
Calculations are performed with FastHerny.
KiPEX serves as a translation layer between KiCad and FastHenry.
The GUI enables users to focus on their design process while the interaction with FastHenry is abstracted away.
More advanced options are still made available through a options dialogs.

## Try KiPEX today!
KiPEX is not yet published on the official KiCad official repository.
To allow quick development and testing, we created a custom repository.
To enable it, click the "Manage ..."-Button in the top right of your KiCad Plugin and Content Manager and paste the following link.
Afterwards, select the newly added repo and install as usual.
```
https://tobiglaser.de/kicad-tests/repository.json
```
*This repo hosts nightly builds with all the grief and joy associated.

## Net Mode
Any number of copper nets can be selected for calculation.
On each net, one source and one sink port must be defined.
As natural points of connection, component pads are suggested as port options.
For THT Pads, top or bottom side can be selected.  
For a given frequency, a SPICE model can be generated, where each net is represented by an RL pair.
In the model, inductances are coupled with by the factor, calculated from the mutual inductances.

## 🚧 WIP: Loop Mode
Our research has shown, that when trying to simulate multiple nets that comprise a current loop,
the sum of the partial inductances is far overestimated compared to simulating a simplified loop of the same extends.
This mode should enable accurate calculation of power loop inductances and parasitic coupling into gate loop.
For this, a number of footprints and nets may be selected for KiPEX to connect into a single loop.
Complex component footprints like power MOSFETS can be extended with simplified internal conductor geometry,
while for simpler components like resistors, pad to pad options are provided.

## FastHenry
For a ready compiled Version of FastHenry see [FastHenry Binary](https://github.com/tobiglaser/FastHenry2-Sam/releases/latest).  
For more information on FastHenry see the [documentation](https://www.fastfieldsolvers.com/documentation.htm) and
[publications](https://www.fastfieldsolvers.com/publications.htm) sites of [FastFieldSolvers](https://www.fastfieldsolvers.com/fasthenry2.htm).

## Limitations and further work
When looking to derive the inductance of a current loop, a return path must always be constructed.
Otherwise the inductance may be grossly overestimated.
This is due to the way FastHenry works.
Currently the **Loop mode** is being worked on, to help ease this problem.

### Upcoming:
- The translation is currently limited to 2-layer PCBs.
  More complex stackups will be made available in conjunction with options for via translation.
- Filamentization of traces is currently fixed to enable calculation of the skin-effect at the maximum set frequency.
  This needlessly increases the model complexity for every lower frequency calculation performed.
  In future, different options may be made available to e.g. dynamically adjust filamentation.
