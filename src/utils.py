"""
Utility functions for the AllowButtonClicker application.
"""

import logging
import sys
from typing import Optional, Tuple, List
import cv2
import numpy as np
from PIL import Image
import pytesseract


def setup_logging(debug: bool = False, quiet: bool = False) -> logging.Logger:
    """Set up logging configuration."""
    logger = logging.getLogger("AllowButtonClicker")

    # Reset handlers so repeated initializations don't duplicate output
    if logger.handlers:
        logger.handlers.clear()

    if quiet and not debug:
        level = logging.WARNING
    else:
        level = logging.DEBUG if debug else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False

    # When operating in quiet mode, still allow debug overrides but suppress handler output
    if quiet and not debug:
        handler.setLevel(logging.WARNING)

    return logger


def is_blue_color(color: Tuple[int, int, int], tolerance: int = 30) -> bool:
    """
    Check if a color is blue-ish.
    
    Args:
        color: RGB color tuple
        tolerance: Color tolerance for blue detection
    
    Returns:
        True if color is considered blue
    """
    r, g, b = color
    
    # Blue should have higher blue component
    if b < 100:  # Minimum blue threshold
        return False
    
    # Blue should be dominant - at least 20 points higher than others
    if b < max(r, g) + 20:
        return False
    
    # Additional check: blue should be reasonably higher than red+green average
    avg_rg = (r + g) / 2
    if b < avg_rg + 30:
        return False
    
    return True


def find_text_in_image(image: Image.Image, target_text: str, confidence: float = 0.5) -> List[Tuple[int, int]]:
    """
    Find text in an image using OCR.
    
    Args:
        image: PIL Image to search
        target_text: Text to find (case-insensitive)
        confidence: OCR confidence threshold (0.0 to 1.0)
    
    Returns:
        List of (x, y) coordinates where text was found
    """
    try:
        # Convert PIL to OpenCV format
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Preprocess image for better OCR
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # Try multiple preprocessing approaches
        processed_images = [
            gray,  # Original grayscale
            cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],  # Otsu threshold
            cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2),  # Adaptive
        ]
        
        positions = []
        target_lower = target_text.lower()
        
        for processed_img in processed_images:
            try:
                # Use pytesseract to find text with different configs
                configs = [
                    '--psm 8',  # Single word
                    '--psm 7',  # Single text line
                    '--psm 6',  # Single uniform block
                    '--psm 13', # Raw line. Treat the image as a single text line
                ]
                
                for config in configs:
                    try:
                        data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT, config=config)
                        
                        for i, text in enumerate(data['text']):
                            if text.strip():
                                # More flexible text matching
                                text_lower = text.lower().strip()
                                if (target_lower in text_lower or 
                                    text_lower in target_lower or
                                    any(word in text_lower for word in target_lower.split()) or
                                    # Handle common OCR mistakes
                                    text_lower.replace('0', 'o').replace('1', 'l') == target_lower or
                                    target_lower.replace('0', 'o').replace('1', 'l') in text_lower):
                                    
                                    conf = int(data['conf'][i])
                                    if conf >= confidence * 100:  # pytesseract uses 0-100 scale
                                        x = data['left'][i]
                                        y = data['top'][i]
                                        w = data['width'][i]
                                        h = data['height'][i]
                                        
                                        # Return center point
                                        center_x = x + w // 2
                                        center_y = y + h // 2
                                        positions.append((center_x, center_y))
                    except:
                        continue
            except:
                continue
        
        # Remove duplicates (positions within 10 pixels of each other)
        unique_positions = []
        for pos in positions:
            is_unique = True
            for existing_pos in unique_positions:
                if abs(pos[0] - existing_pos[0]) < 10 and abs(pos[1] - existing_pos[1]) < 10:
                    is_unique = False
                    break
            if is_unique:
                unique_positions.append(pos)
        
        return unique_positions
    
    except Exception as e:
        # OCR can fail, return empty list
        return []


def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """
    Preprocess image to improve OCR accuracy.
    
    Args:
        image: Input PIL Image
    
    Returns:
        Preprocessed PIL Image
    """
    # Convert to OpenCV
    img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    # Apply denoising
    denoised = cv2.fastNlMeansDenoising(gray)
    
    # Apply threshold to get better contrast
    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Convert back to PIL
    return Image.fromarray(thresh)


def get_dominant_colors(image: Image.Image, k: int = 3) -> List[Tuple[int, int, int]]:
    """
    Get dominant colors in an image using K-means clustering.
    
    Args:
        image: PIL Image
        k: Number of dominant colors to find
    
    Returns:
        List of RGB tuples representing dominant colors
    """
    # Convert to OpenCV
    img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    # Reshape image to be a list of pixels
    data = img_cv.reshape((-1, 3))
    data = np.float32(data)
    
    # Apply K-means
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(data, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    
    # Convert back to RGB and return as integers
    centers = np.uint8(centers)
    dominant_colors = []
    
    for center in centers:
        # Convert BGR back to RGB
        rgb_color = (int(center[2]), int(center[1]), int(center[0]))
        dominant_colors.append(rgb_color)
    
    return dominant_colors


def check_macos_permissions() -> bool:
    """
    Check if the app has necessary macOS permissions.
    
    Returns:
        True if permissions are likely granted
    """
    try:
        # Try to take a small screenshot
        import pyautogui
        from PIL import ImageGrab
        
        # Test screen capture
        screenshot = ImageGrab.grab(bbox=(0, 0, 100, 100))
        
        # Test mouse movement (without clicking)
        current_pos = pyautogui.position()
        pyautogui.moveTo(current_pos[0] + 1, current_pos[1])
        pyautogui.moveTo(current_pos[0], current_pos[1])
        
        return True
        
    except Exception:
        return False


def display_permission_help():
    """Display help text for macOS permissions."""
    help_text = """
macOS Permissions Required:

1. Screen Recording Permission:
   - System Preferences → Security & Privacy → Privacy → Screen Recording
   - Add Terminal (if running from terminal) or your Python app

2. Accessibility Permission:
   - System Preferences → Security & Privacy → Privacy → Accessibility  
   - Add Terminal (if running from terminal) or your Python app

3. If using PyCharm/VS Code:
   - Add your IDE to both Screen Recording and Accessibility

After granting permissions, restart the application.
"""
    print(help_text)