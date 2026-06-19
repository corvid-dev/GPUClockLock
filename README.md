# GPUClockLock

A lightweight Windows utility for locking NVIDIA GPU graphics clocks to a percentage of the GPU's maximum reported clock.

Unlike full overclocking utilities, this application focuses on one job: maintaining a stable graphics clock with a simple interface.

## Requirements

- Windows
- NVIDIA GPU
- NVIDIA driver with `nvidia-smi`
- Administrator privileges

## Dependencies

```
pip install pyinstaller
```

## Building

```
pyinstaller --onefile --windowed --uac-admin --icon=GPUClockLockIcon.ico --add-data "GPUClockLockIcon.ico;." --name "GPUClockLock" GPUClockLock.py
```

Output will be in the `dist/` folder.

## Usage

1. Run **GPUClockLock** as Administrator
2. Select the desired GPU
3. Choose a target percentage of the GPU's maximum graphics clock
4. Press **Lock**
5. Press **Unlock** to restore normal NVIDIA clock management
6. Press **Refresh** at any time to update displayed clock information

Closing the application automatically restores the GPU to its default clock behavior.

## Features

- Detects all NVIDIA GPUs in the system
- Lock graphics clock from 100% down to 15% in 5% increments
- Displays current, target, minimum, and maximum clock speeds
- Remembers last selected GPU and target percentage
- No background monitoring or continuous polling
- Automatically unlocks on exit

## Configuration

Settings are saved to:

```
%APPDATA%\GPUClockLock\
```

## Notes

This application does not overclock your GPU. Clock values are derived from the maximum graphics clock reported by the NVIDIA driver.

Example:

| Target | Locked Clock |
| -----: | -----------: |
|   100% |     2100 MHz |
|    95% |     1995 MHz |
|    90% |     1890 MHz |

## Disclaimer

Provided as-is without warranty. Users are responsible for understanding the effects of locking GPU clocks on power consumption, temperatures, and system stability.

## License

MIT
