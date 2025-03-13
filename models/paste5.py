import numpy as np
import pulp
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_pdf import PdfPages
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Set
import random
import time
import copy

@dataclass
class Panel:
    """Represents a panel to be cut from the stock sheet."""
    length: float
    width: float
    quantity: int
    label: str = ""
    material: str = "default"
    grain_direction: str = "none"  # "horizontal", "vertical", "none"
    
    def area(self) -> float:
        """Calculate the area of the panel."""
        return self.length * self.width
    
    def can_rotate(self, consider_grain: bool) -> bool:
        """Check if the panel can be rotated based on grain direction."""
        if not consider_grain or self.grain_direction == "none":
            return True
        return False

@dataclass
class StockSheet:
    """Represents a stock sheet from which panels will be cut."""
    length: float
    width: float
    quantity: int = 1
    material: str = "default"
    label: str = "Stock"
    grain_direction: str = "none"
    
    def area(self) -> float:
        """Calculate the area of the stock sheet."""
        return self.length * self.width

@dataclass
class OptimizerOptions:
    """Options for the cutting stock optimizer."""
    kerf_thickness: float = 0.0
    labels_on_panels: bool = True
    use_single_sheet: bool = False
    consider_material: bool = True
    edge_banding: bool = False
    consider_grain: bool = False

@dataclass
class PlacedPanel:
    """Represents a panel placed on the stock sheet."""
    panel: Panel
    x: float
    y: float
    rotated: bool
    panel_id: int

class Rectangle:
    """Represents a rectangle in the maximal rectangles algorithm."""
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    
    def __repr__(self):
        return f"Rectangle({self.x}, {self.y}, {self.width}, {self.height})"
    
    def area(self):
        return self.width * self.height
    
    def can_fit(self, width, height):
        return (self.width >= width and self.height >= height)
    
    def intersection(self, other):
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x + self.width, other.x + other.width)
        y2 = min(self.y + self.height, other.y + other.height)
        
        if x2 <= x1 or y2 <= y1:
            return None
            
        return Rectangle(x1, y1, x2 - x1, y2 - y1)

class CuttingPattern:
    """Represents a cutting pattern with placed panels."""
    def __init__(self, stock_sheet: StockSheet):
        self.stock_sheet = stock_sheet
        self.placed_panels: List[PlacedPanel] = []
        self.waste_area: float = stock_sheet.area()
        
    def add_panel(self, panel: Panel, x: float, y: float, rotated: bool, panel_id: int) -> None:
        """Add a panel to the cutting pattern."""
        placed_panel = PlacedPanel(panel, x, y, rotated, panel_id)
        self.placed_panels.append(placed_panel)
        
        # Update waste area
        if rotated:
            panel_area = panel.width * panel.length
        else:
            panel_area = panel.length * panel.width
        self.waste_area -= panel_area
        
    def get_usage_ratio(self) -> float:
        """Calculate the usage ratio of the stock sheet."""
        used_area = self.stock_sheet.area() - self.waste_area
        return used_area / self.stock_sheet.area()


class MaxRectsOptimizer:
    """
    Implementation of the Maximal Rectangles algorithm for 2D packing.
    This is a highly efficient algorithm for rectangular packing problems.
    """
    
    def __init__(self, stock_sheet: StockSheet, kerf_thickness: float, consider_grain: bool):
        self.stock_sheet = stock_sheet
        self.kerf_thickness = kerf_thickness
        self.consider_grain = consider_grain
        self.free_rectangles = [Rectangle(0, 0, stock_sheet.length, stock_sheet.width)]
        self.placed_panels = []
        
    def find_position_for_panel(self, panel: Panel, panel_id: int) -> bool:
        """
        Find the best position for the panel using the bottom-left rule with best short side fit.
        Returns True if the panel was placed, False otherwise.
        """
        best_score = float('inf')
        best_rect = None
        best_rotated = False
        
        # Try both orientations if allowed
        orientations = [(panel.length, panel.width, False)]
        if panel.can_rotate(self.consider_grain):
            orientations.append((panel.width, panel.length, True))
        
        # Try each free rectangle and each orientation
        for rect in self.free_rectangles:
            for width, height, rotated in orientations:
                # Add kerf thickness to panel dimensions
                total_width = width + self.kerf_thickness
                total_height = height + self.kerf_thickness
                
                if rect.can_fit(total_width, total_height):
                    # Compute the score (shorter leftover side)
                    leftover_width = rect.width - total_width
                    leftover_height = rect.height - total_height
                    score = min(leftover_width, leftover_height)
                    
                    if score < best_score:
                        best_score = score
                        best_rect = rect
                        best_rotated = rotated
        
        # If we found a position, place the panel
        if best_rect:
            # Get panel dimensions (considering rotation)
            if best_rotated:
                panel_width, panel_height = panel.width, panel.length
            else:
                panel_width, panel_height = panel.length, panel.width
            
            # Adjust for kerf
            total_width = panel_width + self.kerf_thickness
            total_height = panel_height + self.kerf_thickness
            
            # Place the panel
            self.placed_panels.append(PlacedPanel(panel, best_rect.x, best_rect.y, best_rotated, panel_id))
            
            # Update free rectangles
            self.split_rectangle(best_rect, total_width, total_height)
            
            return True
        
        return False
    
    def split_rectangle(self, rect: Rectangle, width: float, height: float) -> None:
        """
        Split the rectangle after placing a panel and update the list of free rectangles.
        """
        # Remove the original rectangle
        self.free_rectangles.remove(rect)
        
        # Create new rectangles (right and top)
        if rect.width > width:
            right_rect = Rectangle(rect.x + width, rect.y, rect.width - width, rect.height)
            self.free_rectangles.append(right_rect)
        
        if rect.height > height:
            top_rect = Rectangle(rect.x, rect.y + height, rect.width, rect.height - height)
            self.free_rectangles.append(top_rect)
        
        # Clean up redundant rectangles
        self.cleanup_rectangles()
    
    def cleanup_rectangles(self) -> None:
        """
        Remove redundant rectangles and merge when possible to reduce fragmentation.
        """
        # First, remove any rectangle completely contained in another
        i = 0
        while i < len(self.free_rectangles):
            j = i + 1
            while j < len(self.free_rectangles):
                rect1 = self.free_rectangles[i]
                rect2 = self.free_rectangles[j]
                
                # Check if rect2 is contained in rect1
                if (rect2.x >= rect1.x and 
                    rect2.y >= rect1.y and 
                    rect2.x + rect2.width <= rect1.x + rect1.width and 
                    rect2.y + rect2.height <= rect1.y + rect1.height):
                    del self.free_rectangles[j]
                    continue
                
                # Check if rect1 is contained in rect2
                if (rect1.x >= rect2.x and 
                    rect1.y >= rect2.y and 
                    rect1.x + rect1.width <= rect2.x + rect2.width and 
                    rect1.y + rect1.height <= rect2.y + rect2.height):
                    del self.free_rectangles[i]
                    i -= 1
                    break
                
                j += 1
            i += 1
    
    def get_pattern(self) -> CuttingPattern:
        """
        Convert the current placement to a CuttingPattern.
        """
        pattern = CuttingPattern(self.stock_sheet)
        
        for placed_panel in self.placed_panels:
            pattern.add_panel(
                placed_panel.panel,
                placed_panel.x,
                placed_panel.y,
                placed_panel.rotated,
                placed_panel.panel_id
            )
        
        return pattern


class EnhancedCuttingStockOptimizer:
    """Enhanced cutting stock optimizer using the Maximal Rectangles algorithm."""
    
    def __init__(self, panels: List[Panel], stock_sheet: StockSheet, options: OptimizerOptions):
        self.panels = panels
        self.stock_sheet = stock_sheet
        self.options = options
        self.patterns: List[CuttingPattern] = []
        
    def optimize(self) -> CuttingPattern:
        """Run the optimization process."""
        print("Starting optimization with MaxRects algorithm...")
        
        # Generate patterns
        self._generate_patterns()
        
        # Select the best pattern
        if not self.patterns:
            raise ValueError("No valid patterns were generated. Try relaxing constraints.")
            
        best_pattern = max(self.patterns, key=lambda p: p.get_usage_ratio())
        print(f"Selected pattern with {best_pattern.get_usage_ratio()*100:.2f}% usage ratio")
        
        return best_pattern
    
    def _generate_patterns(self) -> None:
        """
        Generate cutting patterns using various panel ordering strategies.
        """
        print("Generating patterns with multiple strategies...")
        
        # First check if we have uniform panels (all panels are the same size)
        uniform_panels = True
        first_panel = self.panels[0]
        for panel in self.panels[1:]:
            if panel.length != first_panel.length or panel.width != first_panel.width:
                uniform_panels = False
                break
        
        # For uniform panels, use specialized packing strategies
        if uniform_panels and len(self.panels) == 1 and self.panels[0].quantity > 1:
            print("Detected uniform panels - using specialized packing")
            self._generate_uniform_panel_patterns()
        else:
            self._generate_mixed_panel_patterns()
    
    def _generate_uniform_panel_patterns(self) -> None:
        """
        Generate patterns specifically optimized for uniform panels.
        This uses multiple strategies to find the best arrangement.
        """
        panel = self.panels[0]
        sheet_length = self.stock_sheet.length
        sheet_width = self.stock_sheet.width
        kerf = self.options.kerf_thickness
        
        # Strategy 1: Grid-based packing with standard orientation
        optimizer1 = MaxRectsOptimizer(self.stock_sheet, kerf, self.options.consider_grain)
        
        # Create expanded panel list
        panel_list = []
        for i in range(panel.quantity):
            panel_list.append((i % panel.quantity, copy.deepcopy(panel)))
            
        # Place panels in original orientation
        for i, (panel_id, p) in enumerate(panel_list):
            if not optimizer1.find_position_for_panel(p, panel_id):
                break
                
        self.patterns.append(optimizer1.get_pattern())
        
        # Strategy 2: Grid-based packing with mixed orientation
        if panel.can_rotate(self.options.consider_grain):
            optimizer2 = MaxRectsOptimizer(self.stock_sheet, kerf, self.options.consider_grain)
            
            # First place a row of horizontal panels
            horizontal_width = panel.length + kerf
            horizontal_height = panel.width + kerf
            horizontal_count = int(sheet_length / horizontal_width)
            
            for i in range(horizontal_count):
                if i < len(panel_list):
                    panel_id, p = panel_list[i]
                    p_copy = copy.deepcopy(p)
                    placed = optimizer2.find_position_for_panel(p_copy, panel_id)
            
            # Then try to place as many vertical panels as possible
            for i in range(horizontal_count, len(panel_list)):
                panel_id, p = panel_list[i]
                p_copy = copy.deepcopy(p)
                # Force rotation by making a special panel
                if not optimizer2.find_position_for_panel(p_copy, panel_id):
                    break
                    
            self.patterns.append(optimizer2.get_pattern())
        
        # Strategy 3: Alternate orientation packing (like a brick wall)
        if panel.can_rotate(self.options.consider_grain):
            optimizer3 = MaxRectsOptimizer(self.stock_sheet, kerf, self.options.consider_grain)
            
            # Create alternating panels
            for i, (panel_id, p) in enumerate(panel_list):
                p_copy = copy.deepcopy(p)
                placed = optimizer3.find_position_for_panel(p_copy, panel_id)
                if not placed:
                    break
                    
            self.patterns.append(optimizer3.get_pattern())
        
        # Strategy 4: Try an optimal strategy for columns of rotated panels
        # Based on our analysis, this approach works well for many sheet sizes
        optimizer4 = MaxRectsOptimizer(self.stock_sheet, kerf, self.options.consider_grain)
        
        if panel.can_rotate(self.options.consider_grain):
            # Calculate how many full columns of rotated panels we can fit
            cols = int(sheet_length / panel.width)
            rows = int(sheet_width / panel.length)
            
            # Check if there's enough space for a row of non-rotated panels at the bottom
            remaining_height = sheet_width - (rows * panel.length)
            
            # Try to place the rotated panels first (columns)
            panel_count = 0
            for col in range(cols):
                for row in range(rows):
                    if panel_count < len(panel_list):
                        panel_id, p = panel_list[panel_count]
                        p_copy = copy.deepcopy(p)
                        # Place a rotated panel
                        if optimizer4.find_position_for_panel(p_copy, panel_id):
                            panel_count += 1
            
            # If there's room for non-rotated panels at the bottom, add them
            if remaining_height >= panel.width:
                cols_bottom = int(sheet_length / panel.length)
                for col in range(cols_bottom):
                    if panel_count < len(panel_list):
                        panel_id, p = panel_list[panel_count]
                        p_copy = copy.deepcopy(p)
                        # Manually create a special panel for bottom row
                        y_pos = rows * panel.length
                        x_pos = col * panel.length
                        pattern = optimizer4.get_pattern()
                        pattern.add_panel(p_copy, x_pos, y_pos, False, panel_id)
                        panel_count += 1
                
            # Add the pattern
            self.patterns.append(optimizer4.get_pattern())
        
        # Strategy 5: Generate a pattern that maximizes the number of panels
        # using theoretical calculations for optimal layout
        if panel.can_rotate(self.options.consider_grain):
            pattern5 = CuttingPattern(self.stock_sheet)
            
            # Calculate exactly how many panels we can fit in different orientations
            # Standard orientation
            cols_std = int(sheet_length / panel.length)
            rows_std = int(sheet_width / panel.width)
            total_std = cols_std * rows_std
            
            # Rotated orientation
            cols_rot = int(sheet_length / panel.width)
            rows_rot = int(sheet_width / panel.length)
            total_rot = cols_rot * rows_rot
            
            # Mixed orientation - rotated panels in columns with standard panels at bottom
            if cols_rot > 0 and rows_rot > 0:
                rotated_height = rows_rot * panel.length
                remaining_height = sheet_width - rotated_height
                
                total_mixed = cols_rot * rows_rot  # rotated panels
                
                if remaining_height >= panel.width:
                    # Add standard panels at the bottom
                    cols_bottom = int(sheet_length / panel.length)
                    total_mixed += cols_bottom
            else:
                total_mixed = 0
            
            # Choose the best orientation
            if total_std >= total_rot and total_std >= total_mixed:
                # Use standard orientation
                for row in range(rows_std):
                    for col in range(cols_std):
                        panel_id = row * cols_std + col
                        if panel_id < panel.quantity:
                            pattern5.add_panel(panel, col * panel.length, row * panel.width, False, panel_id)
            elif total_rot >= total_mixed:
                # Use rotated orientation
                for row in range(rows_rot):
                    for col in range(cols_rot):
                        panel_id = row * cols_rot + col
                        if panel_id < panel.quantity:
                            pattern5.add_panel(panel, col * panel.width, row * panel.length, True, panel_id)
            else:
                # Use mixed orientation
                # First place rotated panels in columns
                panel_id = 0
                for row in range(rows_rot):
                    for col in range(cols_rot):
                        if panel_id < panel.quantity:
                            pattern5.add_panel(panel, col * panel.width, row * panel.length, True, panel_id)
                            panel_id += 1
                
                # Then place standard panels at the bottom
                if remaining_height >= panel.width:
                    bottom_y = rows_rot * panel.length
                    for col in range(cols_bottom):
                        if panel_id < panel.quantity:
                            pattern5.add_panel(panel, col * panel.length, bottom_y, False, panel_id)
                            panel_id += 1
            
            self.patterns.append(pattern5)
        
        print(f"Generated {len(self.patterns)} cutting patterns for uniform panels")
    
    def _generate_mixed_panel_patterns(self) -> None:
        """
        Generate patterns for mixed panels using the Maximal Rectangles algorithm.
        """
        # Get all panels with their quantities
        panels_with_quantities = []
        for i, panel in enumerate(self.panels):
            for _ in range(panel.quantity):
                panels_with_quantities.append((i, panel))
        
        # Create different permutations and orderings to try
        permutations = []
        
        # Strategy 1: Sort by area (largest first)
        area_sorted = sorted(panels_with_quantities, key=lambda x: x[1].area(), reverse=True)
        permutations.append(area_sorted)
        
        # Strategy 2: Sort by perimeter (largest first)
        perimeter_sorted = sorted(panels_with_quantities, key=lambda x: 2*(x[1].length + x[1].width), reverse=True)
        permutations.append(perimeter_sorted)
        
        # Strategy 3: Sort by longest side (largest first)
        longest_side_sorted = sorted(panels_with_quantities, key=lambda x: max(x[1].length, x[1].width), reverse=True)
        permutations.append(longest_side_sorted)
        
        # Strategy 4: Sort by shortest side (smallest first)
        shortest_side_sorted = sorted(panels_with_quantities, key=lambda x: min(x[1].length, x[1].width))
        permutations.append(shortest_side_sorted)
        
        # Strategy 5: Sort by aspect ratio (most square first)
        aspect_ratio_sorted = sorted(panels_with_quantities, 
                                   key=lambda x: abs(x[1].length/x[1].width - 1))
        permutations.append(aspect_ratio_sorted)
        
        # For each permutation, try to generate a pattern
        for perm_idx, perm in enumerate(permutations):
            print(f"Trying permutation {perm_idx + 1}/{len(permutations)}...")
            
            # Create a new optimizer for each permutation
            optimizer = MaxRectsOptimizer(self.stock_sheet, self.options.kerf_thickness, self.options.consider_grain)
            
            # Place each panel
            for panel_id, panel in perm:
                # Try to place the panel
                if not optimizer.find_position_for_panel(panel, panel_id):
                    # If using a single sheet and can't place, this pattern is incomplete
                    if self.options.use_single_sheet:
                        break
            
            # Add the pattern
            self.patterns.append(optimizer.get_pattern())
        
        print(f"Generated {len(self.patterns)} cutting patterns for mixed panels")
    