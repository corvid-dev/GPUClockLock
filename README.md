# GPUClockLock

A lightweight Windows utility for locking NVIDIA GPU graphics clocks to a percentage of the GPU's maximum reported clock. No overclocking - just stable, controlled clock speeds with a simple interface.

## Requirements

- Windows
- NVIDIA GPU
- NVIDIA driver with `nvidia-smi`
- Administrator privileges

## Dependencies

```
pip install pyinstaller
```

## Running from source

```
python GPUClockLock.py
```

## Building an executable

```
pyinstaller --onefile --windowed --uac-admin --icon=GPUClockLockIcon.ico --add-data "GPUClockLockIcon.ico;." --name "GPUClockLock" GPUClockLock.py
```

Output will be in the `dist/` folder.

## Usage

1. Run **GPUClockLock** as Administrator
2. Select the desired GPU from the dropdown
3. Choose a target percentage of the GPU's maximum graphics clock
4. Press **Lock**
5. Press **Unlock** to restore normal NVIDIA clock management
6. Press **Refresh** to update displayed clock information

Closing the application automatically unlocks the GPU.

## Notes

- Clock values are derived from the maximum graphics clock reported by the NVIDIA driver
- Target range is 100% down to 15% in 5% increments
- Settings are saved automatically to `%APPDATA%\GPUClockLock\`

## Disclaimer

Provided as-is without warranty. Users are responsible for understanding the effects of locking GPU clocks on power consumption, temperatures, and system stability.

## License

MIT
