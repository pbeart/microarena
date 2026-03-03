# Microarena
Compete against bots running on a slow emulated RISC-V processor, in Asteroids-like combat 

## Setting up
This project requires [the Spike simulator](https://github.com/riscv-software-src/riscv-isa-sim) repository to be present as a sibling directory to this repository (so that, when in the top-level `microarena` directory, `../riscv-isa-sim` would be the path to the Spike simulator), and for Spike to have been built.

To build the target binary, you can run `CPLUS_INCLUDE_PATH=../../../riscv-isa-sim/ make` (sorry) in `microarena/vm/spike_vm`.

## To run
You should probably use [uv](https://docs.astral.sh/uv/): you can use `uv run python -m microarena.run` to run the sample script, although you will also probably want to modify it, or write your own script.
### On WSL
For some reason, although GUI passthrough can be [set up quite easily](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps), I experienced strange graphical artefacts unless I set the `LIBGL_ALWAYS_SOFTWARE` environment variable, so you should try `LIBGL_ALWAYS_SOFTWARE=1; uv run python -m microarena.run` instead.