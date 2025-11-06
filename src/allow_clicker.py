#!/usr/bin/env python3
"""
AllowButtonClickApp - Automatic Blue "Allow" Button Clicker for macOS

This script continuously monitors the screen for blue "Allow" buttons and
automatically clicks them when found.
"""

import cv2
import numpy as np
import pyautogui
import time
import sys
import threading
import signal
from typing import Optional, Tuple, List
from pynput import keyboard
from PIL import Image, ImageGrab
import logging

from utils import setup_logging, is_blue_color, find_text_in_image, get_dominant_colors


class AllowButtonClicker:
    def __init__(self, debug: bool = False, quiet: bool = False):
        self.running = False
        self.debug = debug
        self.quiet = quiet
        self.logger = setup_logging(debug, quiet)
        self.last_click_time = 0
        self.click_cooldown = 2.0  # Prevent rapid clicking
        self.screen_size = pyautogui.size()
        self.capture_size: Optional[Tuple[int, int]] = None
        self._scan_start_x_ratio = 0.55  # Focus on right-most ~45% of the screen
        self._scan_start_y_ratio = 0.4   # Focus on bottom ~60% of the screen
        self._last_scan_box: Optional[Tuple[int, int, int, int]] = None
        
        # Safety: ESC key to stop
        self.listener = None
        self._setup_signal_handlers()
        
        # Disable pyautogui failsafe for smooth operation
        pyautogui.FAILSAFE = False
        
        if not self.quiet or self.debug:
            self.logger.info("AllowButtonClicker initialized. Press ESC or Ctrl+C to stop.")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            if not self.quiet or self.debug:
                self.logger.info(f"Received signal {signum} - stopping...")
            self.running = False  # Set flag first
            try:
                self.stop()
            finally:
                # Force exit if normal stop doesn't work
                import os
                os._exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    
    def _on_key_press(self, key):
        """Handle keyboard events for safety stop."""
        try:
            if key == keyboard.Key.esc:
                if not self.quiet or self.debug:
                    self.logger.info("ESC pressed - stopping...")
                self.stop()
                return False  # Stop the listener
        except AttributeError:
            pass
    
    def start(self):
        """Start monitoring and clicking."""
        self.running = True
        
        # Start keyboard listener
        self.listener = keyboard.Listener(on_press=self._on_key_press)
        self.listener.start()
        
        if not self.quiet or self.debug:
            self.logger.info("Starting screen monitoring...")
        
        try:
            self._monitor_loop()
        except KeyboardInterrupt:
            if not self.quiet or self.debug:
                self.logger.info("Interrupted by user")
        except Exception as e:
            self.logger.error(f"Error in start: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop monitoring."""
        if not self.quiet or self.debug:
            self.logger.info("Stopping monitoring...")
        self.running = False
        
        # Stop keyboard listener
        if self.listener and self.listener.running:
            try:
                self.listener.stop()
                self.listener.join(timeout=1.0)  # Wait up to 1 second for clean shutdown
            except Exception as e:
                self.logger.debug(f"Error stopping listener: {e}")
        
        if not self.quiet or self.debug:
            self.logger.info("Stopped monitoring")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                # Check if we should stop
                if not self.running:
                    break
                    
                # Take screenshot
                screenshot = ImageGrab.grab()
                self.capture_size = screenshot.size
                
                # Find allow buttons
                buttons = self._find_allow_buttons(screenshot)
                
                if buttons:
                    for button_center in buttons:
                        if self._should_click():
                            self._click_button(button_center)
                            self.last_click_time = time.time()
                            break  # Only click one button per cycle
                
                # Small delay to prevent excessive CPU usage and allow signal processing
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                if not self.quiet or self.debug:
                    self.logger.info("Interrupted by user in monitor loop")
                break
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")
                time.sleep(1)
    
    def _get_scan_region(self, screen_size: Tuple[int, int]) -> Tuple[int, int, int, int]:
        """Compute the bottom-right scan region bounding box."""
        width, height = screen_size

        if width <= 0 or height <= 0:
            return (0, 0, width, height)

        left = min(width - 1, max(0, int(width * self._scan_start_x_ratio)))
        top = min(height - 1, max(0, int(height * self._scan_start_y_ratio)))
        right = width
        bottom = height

        # Ensure the region has at least minimal size; fallback to full screen otherwise
        if right - left < 50 or bottom - top < 50:
            return (0, 0, width, height)

        return (left, top, right, bottom)

    def _find_allow_buttons(self, screenshot: Image.Image) -> List[Tuple[int, int]]:
        """
        Find blue "Allow" buttons in the screenshot.
        Returns list of (x, y) coordinates for button centers.
        """
        # Track capture size for coordinate scaling
        self.capture_size = screenshot.size

        scan_box = self._get_scan_region(screenshot.size)
        self._last_scan_box = scan_box

        if self.debug:
            self.logger.debug(f"Scanning region (left={scan_box[0]}, top={scan_box[1]}, right={scan_box[2]}, bottom={scan_box[3]})")

        scan_image = screenshot.crop(scan_box)
        offset_x, offset_y = scan_box[0], scan_box[1]

        # Convert PIL image to OpenCV format
        img_cv = cv2.cvtColor(np.array(scan_image), cv2.COLOR_RGB2BGR)
        
        candidates = []
        
        # Method 1: Color-based detection for blue buttons
        blue_regions = self._find_blue_regions(img_cv)
        if self.debug:
            self.logger.debug(f"Found {len(blue_regions)} blue regions")
        
        # Method 2: Direct text search across entire image
        allow_text_regions = [
            (offset_x + tx, offset_y + ty) for tx, ty in find_text_in_image(scan_image, "Allow", confidence=0.4)
        ]
        if self.debug:
            self.logger.debug(f"Found {len(allow_text_regions)} 'Allow' text regions")
        
        # Method 3: Search for common OCR mistakes
        text_variations = ["Al1ow", "A11ow"]
        for variation in text_variations:
            var_regions = [
                (offset_x + vx, offset_y + vy)
                for vx, vy in find_text_in_image(scan_image, variation, confidence=0.3)
            ]
            allow_text_regions.extend(var_regions)

        # Collect contextual clues (e.g. Copilot banners in the terminal)
        copilot_regions = [
            (offset_x + cx, offset_y + cy)
            for cx, cy in find_text_in_image(scan_image, "Copilot", confidence=0.3)
        ]
        text_only_candidates: List[Tuple[int, int]] = []
        
        # Combine Method 1 & 2: Check blue regions for "Allow" text
        for region in blue_regions:
            x, y, w, h = region
            # Expand region slightly to catch text near edges
            padding = 5
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(scan_image.width, x + w + padding)
            y2 = min(scan_image.height, y + h + padding)

            roi = scan_image.crop((x1, y1, x2, y2))
            
            # Try to find "Allow" text in this blue region
            found_text = False
            for variation in text_variations:
                if find_text_in_image(roi, variation, confidence=0.2):
                    found_text = True
                    break
            
            if found_text:
                center_x = offset_x + x + w // 2
                center_y = offset_y + y + h // 2
                candidates.append((center_x, center_y))
                
                if self.debug:
                    self.logger.debug(f"Found Allow button (color+text) at ({center_x}, {center_y})")
        
        # Method 4: Text-based candidates (even without perfect blue color)
        for text_pos in allow_text_regions:
            tx, ty = text_pos
            # Check if this position is near any blue-ish color
            try:
                # Sample a small area around the text
                sample_size = 20
                x1 = max(0, tx - sample_size)
                y1 = max(0, ty - sample_size)  
                x2 = min(screenshot.width, tx + sample_size)
                y2 = min(screenshot.height, ty + sample_size)
                
                sample_region = screenshot.crop((x1, y1, x2, y2))
                dominant_colors = get_dominant_colors(sample_region, k=3)
                
                # Check if any dominant color is blue-ish
                has_blue = any(is_blue_color(color, tolerance=50) for color in dominant_colors)
                
                if has_blue:
                    candidates.append((tx, ty))
                    if self.debug:
                        self.logger.debug(f"Found Allow button (text+blue area) at ({tx}, {ty})")
                else:
                    if self._is_valid_text_only_candidate((tx, ty), screenshot.size, copilot_regions):
                        text_only_candidates.append((tx, ty))
                        if self.debug:
                            self.logger.debug(
                                f"Found Allow button (text-only fallback) at ({tx}, {ty})"
                            )
                        
            except Exception as e:
                if self.debug:
                    self.logger.debug(f"Error checking text region: {e}")
                if self._is_valid_text_only_candidate((tx, ty), screenshot.size, copilot_regions):
                    text_only_candidates.append((tx, ty))
                    if self.debug:
                        self.logger.debug(
                            f"Added Allow button candidate via exception fallback at ({tx}, {ty})"
                        )
        
        # Method 5: Fallback - assume blue regions in likely button areas might be "Allow" buttons
        # This works even without OCR
        if not candidates:
            if self.debug:
                self.logger.debug("No OCR matches found, trying fallback method...")
            
            # Look for blue regions that match typical "Allow" button characteristics
            for region in blue_regions:
                x, y, w, h = region
                global_x = offset_x + x
                global_y = offset_y + y
                
                # Check if it's in a likely button location (not top menu bars, not tiny icons)
                if global_y > 100 and w >= 30 and h >= 15:  # Not in top menu area, reasonable size
                    
                    # Check if it's in bottom-right area (common for permission dialogs)
                    screen_w, screen_h = screenshot.width, screenshot.height
                    is_bottom_right = (global_x > screen_w * 0.6 and global_y > screen_h * 0.6)
                    
                    # Check if it's roughly button-shaped
                    aspect_ratio = w / h
                    is_button_shaped = 1.5 <= aspect_ratio <= 5
                    
                    # Check if it's medium-sized (not a tiny icon or huge banner)
                    is_medium_size = 30 <= w <= 150 and 15 <= h <= 50
                    
                    if (is_bottom_right or is_button_shaped) and is_medium_size:
                        center_x = offset_x + x + w // 2
                        center_y = offset_y + y + h // 2
                        candidates.append((center_x, center_y))
                        
                        if self.debug:
                            self.logger.debug(f"Found likely Allow button (fallback) at ({center_x}, {center_y})")
        
        # Include fallback text-based candidates
        candidates.extend(text_only_candidates)

        # Remove duplicates and return limited results
        unique_candidates = []
        for candidate in candidates:
            is_unique = True
            for existing in unique_candidates:
                if abs(candidate[0] - existing[0]) < 30 and abs(candidate[1] - existing[1]) < 30:
                    is_unique = False
                    break
            if is_unique:
                unique_candidates.append(candidate)
        
        if self.debug and unique_candidates:
            self.logger.debug(f"Final candidates: {unique_candidates}")
        
        return unique_candidates[:3]  # Return max 3 buttons to avoid spam clicking

    def _scale_position(self, position: Tuple[int, int]) -> Tuple[int, int]:
        """Scale Retina/high-DPI screenshot coordinates to actual screen coordinates."""
        if not self.capture_size:
            return position

        capture_w, capture_h = self.capture_size
        screen_w, screen_h = self.screen_size

        if capture_w == 0 or capture_h == 0:
            return position

        scale_x = screen_w / capture_w
        scale_y = screen_h / capture_h

        scaled_x = position[0] * scale_x
        scaled_y = position[1] * scale_y

        return (int(scaled_x), int(scaled_y))

    def _is_valid_text_only_candidate(
        self,
        position: Tuple[int, int],
        screen_size: Tuple[int, int],
        context_points: List[Tuple[int, int]],
    ) -> bool:
        """Heuristic checks for text-only Allow detections without a strong blue signal."""
        x, y = position
        screen_w, screen_h = screen_size

        # Avoid menu bar / title bar area entirely
        if y < 80:
            return False

        # Accept if the text sits near other Copilot/banner text
        for cx, cy in context_points:
            if abs(cx - x) <= 240 and abs(cy - y) <= 160:
                return True

        # Terminal banners and dialogs typically appear in the lower portion of the screen
        if y >= int(screen_h * 0.35):
            return True

        # Dialog buttons often appear on the right half of the window
        if x >= int(screen_w * 0.55) and y >= int(screen_h * 0.2):
            return True

        return False
    
    def _find_blue_regions(self, img_cv: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Find blue-ish rectangular regions that could be buttons."""
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
        
        # Expanded blue color range to catch more button styles
        # Range 1: Standard blues
        lower_blue1 = np.array([100, 50, 50])
        upper_blue1 = np.array([130, 255, 255])
        
        # Range 2: Lighter blues (like VS Code buttons)
        lower_blue2 = np.array([90, 30, 80])
        upper_blue2 = np.array([140, 255, 255])
        
        # Create masks for both ranges
        mask1 = cv2.inRange(hsv, lower_blue1, upper_blue1)
        mask2 = cv2.inRange(hsv, lower_blue2, upper_blue2)
        
        # Combine masks
        mask = cv2.bitwise_or(mask1, mask2)
        
        # Clean up the mask
        kernel = np.ones((2, 2), np.uint8)  # Smaller kernel for small buttons
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # More lenient size filters for smaller buttons
            if 20 <= w <= 300 and 10 <= h <= 80:  # Relaxed size constraints
                aspect_ratio = w / h
                if 0.8 <= aspect_ratio <= 8:  # More flexible aspect ratio
                    area = cv2.contourArea(contour)
                    if area >= 100:  # Minimum area to avoid noise
                        regions.append((x, y, w, h))
                        if self.debug:
                            self.logger.debug(f"Found blue region: ({x}, {y}) size {w}x{h}, area {area}")
        
        return regions
    
    def _should_click(self) -> bool:
        """Check if enough time has passed since last click."""
        current_time = time.time()
        return (current_time - self.last_click_time) >= self.click_cooldown
    
    def _click_button(self, position: Tuple[int, int]):
        """Click the button at given position."""
        screen_x, screen_y = self._scale_position(position)
        
        try:
            # Move mouse and click
            pyautogui.moveTo(screen_x, screen_y, duration=0.2)
            time.sleep(0.1)  # Small pause
            pyautogui.click()
            
            if not self.quiet or self.debug:
                self.logger.info(
                    f"Clicked Allow button at ({screen_x}, {screen_y}) (source coords: {position})"
                )
            
        except Exception as e:
            self.logger.error(f"Failed to click button: {e}")


def click_button_once(position: Tuple[int, int], logger=None, capture_size: Optional[Tuple[int, int]] = None):
    """Standalone function to click a button once."""
    screen_w, screen_h = pyautogui.size()
    if capture_size and capture_size[0] and capture_size[1]:
        scale_x = screen_w / capture_size[0]
        scale_y = screen_h / capture_size[1]
        x = position[0] * scale_x
        y = position[1] * scale_y
    else:
        x, y = position
    
    try:
        if logger:
            logger.info(f"Moving to ({x}, {y}) and clicking...")
        
        # Move mouse and click
        pyautogui.moveTo(x, y, duration=0.3)
        time.sleep(0.2)  # Pause to ensure movement completes
        pyautogui.click()
        time.sleep(0.1)  # Brief pause after click
        
        if logger:
            logger.info(f"Successfully clicked Allow button at ({x}, {y})")
        else:
            print(f"Successfully clicked Allow button at ({x}, {y})")
            
        return True
        
    except Exception as e:
        error_msg = f"Failed to click button: {e}"
        if logger:
            logger.error(error_msg)
        else:
            print(error_msg)
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Automatic Blue Allow Button Clicker")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--test", action="store_true", help="Test mode - find buttons but don't click")
    parser.add_argument("--click-once", action="store_true", help="Find and click once, then exit")
    parser.add_argument("--interactive", action="store_true", help="Show prompts and console output")
    parser.add_argument("--quiet", action="store_true", help="Suppress console output (overrides interactive mode)")
    
    args = parser.parse_args()

    quiet_mode = args.quiet or (not args.debug and not args.interactive)

    if not quiet_mode:
        print("=== Allow Button Clicker ===")
        print("This app will automatically click blue 'Allow' buttons.")
        print("Press ESC to stop at any time.")
        print("Make sure you've granted accessibility permissions!")
        print("")
    
    if args.interactive and not args.test and not args.click_once:
        input("Press Enter to start monitoring...")

    clicker = AllowButtonClicker(debug=args.debug, quiet=quiet_mode)
    
    if args.test:
        if not quiet_mode:
            print("Test mode: Taking one screenshot to detect buttons...")
        screenshot = ImageGrab.grab()
        buttons = clicker._find_allow_buttons(screenshot)
        if not quiet_mode:
            print(f"Found {len(buttons)} potential Allow buttons:")
            for i, (x, y) in enumerate(buttons):
                print(f"  Button {i+1}: ({x}, {y})")
    elif args.click_once:
        if not quiet_mode:
            print("Click-once mode: Finding and clicking the first Allow button...")
        
        # Setup minimal logging for click-once mode
        logger = setup_logging(args.debug, quiet=quiet_mode)
        
        # Take screenshot
        screenshot = ImageGrab.grab()
        
        # Find buttons using the clicker's detection method
        clicker = AllowButtonClicker(debug=args.debug, quiet=quiet_mode)
        buttons = clicker._find_allow_buttons(screenshot)
        
        if buttons:
            # Filter buttons to prefer ones in the main screen area
            screen_width, screen_height = screenshot.size
            main_area_buttons = []
            edge_buttons = []
            
            for x, y in buttons:
                # Consider buttons in the main area of the screen (not at edges)
                if (50 < x < screen_width - 50 and 50 < y < screen_height - 50):
                    main_area_buttons.append((x, y))
                else:
                    edge_buttons.append((x, y))
            
            # Prefer main area buttons over edge buttons
            target_buttons = main_area_buttons if main_area_buttons else edge_buttons
            
            if target_buttons:
                x, y = target_buttons[0]  # Take the first main area button
                if not quiet_mode:
                    print(f"Clicking Allow button at ({x}, {y}) (screen size: {screen_width}x{screen_height})")
                
                # Use the standalone click function
                success = click_button_once((x, y), logger, capture_size=screenshot.size)
                
                if not quiet_mode:
                    if success:
                        print("Clicked successfully!")
                    else:
                        print("Click failed!")
                if not success:
                    sys.exit(1)
            else:
                if not quiet_mode:
                    print("No suitable Allow buttons found.")
                sys.exit(1)
        else:
            if not quiet_mode:
                print("No Allow buttons found.")
            sys.exit(1)
    else:
        clicker.start()


if __name__ == "__main__":
    main()