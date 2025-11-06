# AllowButtonClickApp

An automatic macOS console application that monitors your screen for blue "Allow" buttons and clicks them automatically.

## Features

- 🔍 **Smart Detection**: Uses computer vision and OCR to find blue "Allow" buttons
- 🖱️ **Auto-clicking**: Automatically clicks detected buttons with click cooldown protection
- 🛡️ **Safety Features**: ESC key to stop, click cooldown to prevent spam
- 🐍 **Cross-platform**: Built with Python, optimized for macOS
- 🧪 **Testable**: Includes comprehensive test suite

## Requirements

- macOS 10.14+ (for accessibility features)
- Python 3.8+
- Screen Recording and Accessibility permissions

## Quick Start

**New users** - use the automated runner:

```bash
# 1. Set up everything
python run.py setup

# 2. Check permissions (follow the prompts)
python run.py check

# 3. Test detection (safe mode)
python run.py test

# 4. Run the app (when ready)
python run.py start
```

## Manual Installation

1. **Clone or download this project**
   ```bash
   cd AllowButtonClickApp
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Tesseract for OCR (optional but recommended)**
   ```bash
   # Using Homebrew
   brew install tesseract
   
   # Or using MacPorts
   sudo port install tesseract3
   ```

## macOS Permissions Setup

**Critical**: This app requires special permissions to work on macOS.

### 1. Screen Recording Permission
1. Open **System Preferences** → **Security & Privacy** → **Privacy**
2. Click **Screen Recording** in the left sidebar
3. Click the lock and enter your password
4. Add your **Terminal app** (if running from terminal) or **Python** executable

### 2. Accessibility Permission
1. In the same **Security & Privacy** → **Privacy** panel
2. Click **Accessibility** in the left sidebar
3. Add your **Terminal app** or **Python** executable

### 3. For IDEs (PyCharm, VS Code, etc.)
If running from an IDE, add the IDE itself to both permissions lists.

⚠️ **Important**: Restart the application after granting permissions.

## Usage

### Using the Runner (Recommended)

```bash
python run.py setup     # Install dependencies
python run.py check     # Check permissions
python run.py test      # Test detection (safe)
python run.py start     # Start the app
python run.py tests     # Run test suite
```

### Manual Usage
```bash
# Run the application
python src/allow_clicker.py

# Press Enter to start monitoring
# Press ESC to stop at any time
```

### Command Line Options
```bash
# Enable debug logging
python src/allow_clicker.py --debug

# Test mode (detect but don't click)
python src/allow_clicker.py --test
```

### Test Mode Example
```bash
python src/allow_clicker.py --test
# Output: Found 2 potential Allow buttons:
#   Button 1: (150, 300)
#   Button 2: (450, 500)
```

## How It Works

1. **Screen Capture**: Takes periodic screenshots of your entire screen
2. **Color Detection**: Finds blue-colored rectangular regions (potential buttons)
3. **OCR Text Detection**: Uses Tesseract to find "Allow" text in those regions
4. **Smart Filtering**: Combines color and text detection for accuracy
5. **Safe Clicking**: Clicks with cooldown protection and safety controls

## Testing

Run the test suite to verify functionality:

```bash
# Run all tests
python tests/test_detection.py

# Run with more verbose output
python -m pytest tests/ -v
```

## Configuration

You can modify these settings in `src/allow_clicker.py`:

```python
# Click cooldown (seconds between clicks)
self.click_cooldown = 2.0

# Color detection sensitivity
lower_blue = np.array([100, 50, 50])   # HSV lower bound
upper_blue = np.array([130, 255, 255]) # HSV upper bound

# Button size filters
min_width = 30    # Minimum button width
max_width = 200   # Maximum button width
min_height = 15   # Minimum button height
max_height = 60   # Maximum button height
```

## Troubleshooting

### "Permission denied" or no clicks happening
- Verify Screen Recording and Accessibility permissions are granted
- Restart the application after granting permissions
- Try running from Terminal instead of an IDE

### "Import errors" when running
```bash
# Install missing dependencies
pip install -r requirements.txt

# For OCR support
brew install tesseract
```

### False positives (clicking wrong buttons)
- Use `--test` mode to see what's being detected
- Adjust color detection ranges in the code
- Check that "Allow" text is clearly visible

### App not finding buttons
- Enable debug mode: `--debug`
- Ensure buttons are actually blue colored
- Try adjusting the color detection ranges
- Verify Tesseract is installed for text detection

## Safety Features

- **ESC Key**: Press ESC at any time to stop the application
- **Click Cooldown**: Prevents rapid repeated clicking (2-second default)
- **Limited Detection**: Only clicks first detected button per cycle
- **Test Mode**: Safe testing without actual clicking

## File Structure

```
AllowButtonClickApp/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── src/
│   ├── allow_clicker.py     # Main application
│   └── utils.py             # Utility functions
└── tests/
    └── test_detection.py    # Test suite
```

## Dependencies

- **opencv-python**: Computer vision and image processing
- **numpy**: Numerical operations for image data
- **Pillow**: Image handling and screen capture
- **pyautogui**: Mouse control and clicking
- **pytesseract**: OCR text recognition
- **pynput**: Keyboard event handling for safety stop

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Run the test suite
5. Submit a pull request

## License

This project is open source. Use responsibly and ensure you have permission to automate interactions on systems you don't own.

## Disclaimer

This tool is for legitimate automation purposes. Users are responsible for:
- Ensuring they have permission to automate interactions
- Using the tool ethically and legally
- Understanding the implications of automated clicking
- Testing thoroughly before production use

**Use at your own risk.** The authors are not responsible for any unintended consequences.