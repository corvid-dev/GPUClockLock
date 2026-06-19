# GPU Clock Locker

GPU Clock Locker is a lightweight Windows utility for NVIDIA GPUs that allows you to lock the graphics clock to a percentage of the GPU's reported maximum graphics clock.

Unlike full overclocking utilities, this application focuses on one job: maintaining a stable graphics clock with a simple interface.

## Features

* Automatically detects all NVIDIA GPUs installed in the system.
* Remembers the last selected GPU.
* Lock the graphics clock to a percentage of the GPU's maximum clock.
* Adjustable target from **100% down to 15%** in 5% increments.
* Displays:

  * Current graphics clock
  * Target clock
  * Minimum supported clock
  * Maximum supported clock
* Restores stock clock behavior when Unlock is pressed.
* Automatically restores stock clocks when the application exits.
* Stores configuration in:

```
%APPDATA%\GPU Clock Locker\
```

* No background monitoring or continuous polling.

## Requirements

* Windows
* NVIDIA GPU
* NVIDIA driver with `nvidia-smi`
* Administrator privileges

## Building

Install PyInstaller:

```bash
pip install pyinstaller
```

Build:

```bash
pyinstaller --onefile --windowed --uac-admin --name "GPU Clock Locker" gpu_clock_locker.py
```

The executable will be created in:

```
dist\
```

## Usage

1. Run **GPU Clock Locker** as Administrator.
2. Select the desired GPU.
3. Choose the desired percentage of the GPU's maximum graphics clock.
4. Press **Lock**.
5. Press **Refresh** at any time to update the displayed clock information.
6. Press **Unlock** to restore normal NVIDIA clock management.

Closing the application also restores the GPU to its default clock behavior.

## Notes

This application does **not** overclock your GPU.

Clock values are derived from the maximum graphics clock reported by the NVIDIA driver. Selecting a percentage simply locks the graphics clock to that percentage of the reported maximum.

Example:

| Target | Locked Clock |
| -----: | -----------: |
|   100% |     2100 MHz |
|    95% |     1995 MHz |
|    90% |     1890 MHz |

## Disclaimer

This software is provided as-is without warranty.

Although the application only uses NVIDIA's supported clock-locking interface (`nvidia-smi`), users are responsible for understanding the effects of locking GPU clocks on power consumption, temperatures, and system stability.

## License

MIT License
