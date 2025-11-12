"""
Enhanced tkinter window that visualizes tables from tables.json
with booking status, highlighting, and refresh capabilities
"""
import tkinter as tk
from tkinter import ttk
import json
import os
from datetime import datetime, date


class TableVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Restaurant Table Layout - Enhanced Viewer")
        
        # State variables
        self.selected_table_id = None
        self.show_bookings = tk.BooleanVar(value=False)
        self.selected_date = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self.selected_time = tk.StringVar(value=datetime.now().strftime("%H:%M"))
        self.bookings = []
        self.tables = []
        
        # Create control panel
        self.create_control_panel()
        
        # Create canvas
        self.canvas = tk.Canvas(root, width=800, height=600, bg="#f5f5f5", 
                               highlightthickness=1, highlightbackground="#cccccc")
        self.canvas.pack(padx=10, pady=10)
        
        # Bind click event
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        
        # Create status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(root, textvariable=self.status_var, 
                             relief=tk.SUNKEN, anchor=tk.W, bg="#e0e0e0")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Load and draw
        self.refresh()
    
    def create_control_panel(self):
        """Create the control panel with buttons and options"""
        panel = tk.Frame(self.root, bg="#e8e8e8", pady=5)
        panel.pack(fill=tk.X, padx=10, pady=(10, 0))
        
        # Refresh button
        refresh_btn = tk.Button(panel, text="🔄 Refresh", command=self.refresh,
                               bg="#4CAF50", fg="white", padx=10, pady=5)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Show bookings checkbox
        show_bookings_cb = tk.Checkbutton(panel, text="Show Bookings", 
                                         variable=self.show_bookings,
                                         command=self.refresh,
                                         bg="#e8e8e8")
        show_bookings_cb.pack(side=tk.LEFT, padx=10)
        
        # Date selector
        tk.Label(panel, text="Date:", bg="#e8e8e8").pack(side=tk.LEFT, padx=(10, 0))
        date_entry = tk.Entry(panel, textvariable=self.selected_date, width=12)
        date_entry.pack(side=tk.LEFT, padx=5)
        
        # Time selector
        tk.Label(panel, text="Time:", bg="#e8e8e8").pack(side=tk.LEFT, padx=(10, 0))
        time_entry = tk.Entry(panel, textvariable=self.selected_time, width=8)
        time_entry.pack(side=tk.LEFT, padx=5)
        
        # Legend
        legend_frame = tk.Frame(self.root, bg="#f8f8f8", pady=5)
        legend_frame.pack(fill=tk.X, padx=10, pady=(5, 0))
        
        tk.Label(legend_frame, text="Legend:", bg="#f8f8f8", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=10)
        
        # Available
        tk.Label(legend_frame, text="●", fg="#4CAF50", bg="#f8f8f8", font=("Arial", 14)).pack(side=tk.LEFT)
        tk.Label(legend_frame, text="Available", bg="#f8f8f8", font=("Arial", 9)).pack(side=tk.LEFT, padx=(0, 15))
        
        # Booked
        tk.Label(legend_frame, text="●", fg="#f44336", bg="#f8f8f8", font=("Arial", 14)).pack(side=tk.LEFT)
        tk.Label(legend_frame, text="Booked", bg="#f8f8f8", font=("Arial", 9)).pack(side=tk.LEFT, padx=(0, 15))
        
        # Selected
        tk.Label(legend_frame, text="●", fg="#FFC107", bg="#f8f8f8", font=("Arial", 14)).pack(side=tk.LEFT)
        tk.Label(legend_frame, text="Selected", bg="#f8f8f8", font=("Arial", 9)).pack(side=tk.LEFT)
    
    def load_tables(self):
        """Load tables from tables.json"""
        tables_file = "tables.json"
        if os.path.exists(tables_file):
            with open(tables_file, "r") as f:
                return json.load(f)
        else:
            return []
    
    def load_bookings(self, booking_date):
        """Load bookings for a specific date"""
        filename = f"bookings_{booking_date}.json"
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return json.load(f)
        else:
            return []
    
    def is_table_booked(self, table_id, check_date, check_time):
        """Check if a table is booked at a specific date/time"""
        if not self.show_bookings.get():
            return False
        
        for booking in self.bookings:
            if booking.get('table_id') == table_id:
                # Check if booking date matches
                if booking.get('date') != check_date:
                    continue
                
                # Check if time overlaps
                start_time = booking.get('start_time', '00:00')
                end_time = booking.get('end_time', '23:59')
                
                if start_time <= check_time <= end_time:
                    return True
        
        return False
    
    def get_table_color(self, table_id, is_booked, is_selected):
        """Determine the color for a table based on its status"""
        if is_selected:
            return "#FFF9C4"  # Light yellow for selected
        elif is_booked:
            return "#FFCDD2"  # Light red for booked
        else:
            return "#C8E6C9"  # Light green for available
    
    def get_table_border_color(self, table_id, is_booked, is_selected):
        """Determine the border color for a table"""
        if is_selected:
            return "#FFC107"  # Amber for selected
        elif is_booked:
            return "#f44336"  # Red for booked
        else:
            return "#4CAF50"  # Green for available
    
    def draw_table(self, table):
        """Draw a single table with status-based coloring"""
        x = table.get("x", 0)
        y = table.get("y", 0)
        width = table.get("width", 80)
        height = table.get("height", 80)
        table_id = table.get("id", "?")
        seats = table.get("seats", 0)
        
        # Check if table is booked or selected
        is_booked = self.is_table_booked(table_id, self.selected_date.get(), self.selected_time.get())
        is_selected = (table_id == self.selected_table_id)
        
        # Get colors
        fill_color = self.get_table_color(table_id, is_booked, is_selected)
        border_color = self.get_table_border_color(table_id, is_booked, is_selected)
        
        # Draw shadow
        self.canvas.create_rectangle(
            x + 3, y + 3, x + width + 3, y + height + 3,
            fill="#cccccc",
            outline="",
            tags=("table", f"table_{table_id}")
        )
        
        # Main rectangle
        border_width = 3 if is_selected else 2
        rect = self.canvas.create_rectangle(
            x, y, x + width, y + height,
            fill=fill_color,
            outline=border_color,
            width=border_width,
            tags=("table", f"table_{table_id}", "clickable")
        )
        
        # Draw table ID
        text_color = "#333333"
        text_id = self.canvas.create_text(
            x + width / 2,
            y + height / 2 - 15,
            text=f"Table {table_id}",
            font=("Arial", 12, "bold"),
            fill=text_color,
            tags=("table", f"table_{table_id}", "clickable")
        )
        
        # Draw seat count
        text_seats = self.canvas.create_text(
            x + width / 2,
            y + height / 2 + 5,
            text=f"🪑 {seats} seats",
            font=("Arial", 10),
            fill="#666666",
            tags=("table", f"table_{table_id}", "clickable")
        )
        
        # Draw status if showing bookings
        if self.show_bookings.get():
            status_text = "BOOKED" if is_booked else "Available"
            status_color = "#c62828" if is_booked else "#2e7d32"
            self.canvas.create_text(
                x + width / 2,
                y + height / 2 + 25,
                text=status_text,
                font=("Arial", 8, "bold"),
                fill=status_color,
                tags=("table", f"table_{table_id}", "clickable")
            )
    
    def draw_no_go_zones(self):
        """Draw no-go zones from constraints"""
        constraints_file = "restaurant_constraints.json"
        if not os.path.exists(constraints_file):
            return
        
        with open(constraints_file, "r") as f:
            constraints = json.load(f)
        
        no_go_zones = constraints.get("no_go_zones", [])
        
        for zone in no_go_zones:
            x = zone.get("x", 0)
            y = zone.get("y", 0)
            width = zone.get("width", 0)
            height = zone.get("height", 0)
            name = zone.get("name", "No-Go")
            
            # Draw semi-transparent red rectangle
            self.canvas.create_rectangle(
                x, y, x + width, y + height,
                fill="#ffebee",
                outline="#e57373",
                width=1,
                stipple="gray50",
                tags="no_go"
            )
            
            # Draw label
            self.canvas.create_text(
                x + width / 2,
                y + height / 2,
                text=name,
                font=("Arial", 8, "italic"),
                fill="#c62828",
                tags="no_go"
            )
    
    def on_canvas_click(self, event):
        """Handle canvas click events"""
        # Find clicked item
        items = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        
        for item in items:
            tags = self.canvas.gettags(item)
            if "clickable" in tags:
                # Extract table ID from tags
                for tag in tags:
                    if tag.startswith("table_"):
                        table_id_str = tag.replace("table_", "")
                        try:
                            clicked_table_id = int(table_id_str)
                            
                            # Toggle selection
                            if self.selected_table_id == clicked_table_id:
                                self.selected_table_id = None
                                self.status_var.set("Deselected table")
                            else:
                                self.selected_table_id = clicked_table_id
                                # Find table details
                                table = next((t for t in self.tables if t['id'] == clicked_table_id), None)
                                if table:
                                    is_booked = self.is_table_booked(clicked_table_id, 
                                                                     self.selected_date.get(), 
                                                                     self.selected_time.get())
                                    status = "BOOKED" if is_booked else "Available"
                                    self.status_var.set(
                                        f"Selected: Table {clicked_table_id} - {table['seats']} seats - {status}"
                                    )
                            
                            # Redraw to show selection
                            self.refresh()
                            return
                        except ValueError:
                            pass
    
    def refresh(self):
        """Clear canvas and redraw everything"""
        self.canvas.delete("all")
        
        # Load data
        self.tables = self.load_tables()
        self.bookings = self.load_bookings(self.selected_date.get())
        
        if not self.tables:
            # Show message if no tables
            self.canvas.create_text(
                400, 300,
                text="No tables found in tables.json",
                font=("Arial", 14),
                fill="#999999"
            )
            self.status_var.set("No tables loaded")
            return
        
        # Draw no-go zones first (so they're in background)
        self.draw_no_go_zones()
        
        # Draw each table
        for table in self.tables:
            self.draw_table(table)
        
        # Add title
        booking_info = ""
        if self.show_bookings.get():
            booked_count = sum(1 for t in self.tables 
                             if self.is_table_booked(t['id'], 
                                                    self.selected_date.get(), 
                                                    self.selected_time.get()))
            booking_info = f" | {booked_count} booked at {self.selected_time.get()}"
        
        self.canvas.create_text(
            400, 20,
            text=f"🍽️ Restaurant Layout ({len(self.tables)} tables{booking_info})",
            font=("Arial", 16, "bold"),
            fill="#333333"
        )
        
        # Update status
        if self.show_bookings.get():
            self.status_var.set(f"Viewing bookings for {self.selected_date.get()} at {self.selected_time.get()}")
        else:
            self.status_var.set(f"Loaded {len(self.tables)} tables - Click to select")


def main():
    root = tk.Tk()
    app = TableVisualizer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
