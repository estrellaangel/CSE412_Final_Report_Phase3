import TKinterModernThemes as TKMT
import tkinter as tk
from tkinter import messagebox
from database import DatabaseManager
from visualization import ChartManager
from PIL import Image, ImageTk
import io


"""
This is the main.py and will be the start of the program that will define the layout of the 
tkinter progam and the objects found such as buttons etc.
"""
class SaveVisualizationDialog:
    def __init__(self, parent, callback):
        # initialize the save visual class that will prompt the user to enter name
        self.top = tk.Toplevel(parent)
        self.top.title("Save Visualization") # title
        self.callback = callback
        
        tk.Label(self.top, text="Visualization Name:").pack(pady=5) #label for the input
        self.name_entry = tk.Entry(self.top) #actuall box
        self.name_entry.pack(pady=5)
        
        # save button
        tk.Button(self.top, text="Save", command=self.save).pack(pady=10)
        
        # size definention
        self.top.geometry("300x150")
        self.top.transient(parent)
        self.top.grab_set()
    
    def save(self):
        #method to handle save button
        name = self.name_entry.get().strip()
        if name:
            self.callback(name)
            self.top.destroy()
        else:
            messagebox.showerror("Error", " enter a name")

class VisualizationManager:
    # box should popout and give the user options to interact with the visuals db
    def __init__(self, parent, db_manager):
        self.top = tk.Toplevel(parent)
        self.top.title("Visualization Manager")
        self.db_manager = db_manager
        
        # define the fram the list will sit in
        self.list_frame = tk.Frame(self.top)
        self.list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        #the list of visuals 
        self.listbox = tk.Listbox(self.list_frame, width=40)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        
        # fram to hold the option buttons
        self.button_frame = tk.Frame(self.top)
        self.button_frame.pack(side=tk.RIGHT, fill=tk.Y)
        #buttons
        tk.Button(self.button_frame, text="Rename", command=self.rename_viz).pack(pady=5)
        tk.Button(self.button_frame, text="Delete", command=self.delete_viz).pack(pady=5)
        tk.Button(self.button_frame, text="View", command=self.view_viz).pack(pady=5)
        
        self.update_list()
        
        # define the size of window
        self.top.geometry("500x400")
        self.top.transient(parent)
        self.top.grab_set()
    
    def update_list(self):
        #handle update of list
        self.listbox.delete(0, tk.END)
        for name, in self.db_manager.get_visualization_list():
            self.listbox.insert(tk.END, name)
    
    def rename_viz(self):
        #rename a specific visual in the db
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "select a visualization")
            return
        # grab the old name and new name
        old_name = self.listbox.get(selection[0])
        new_name = tk.simpledialog.askstring("Rename", "enter new name:")
        # if theres a new name then get the db manager and change name
        if new_name:
            if self.db_manager.update_visualization_name(old_name, new_name):
                self.update_list()
    
    def delete_viz(self):
        #handle the deletion of a visual from the db
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "select a visualization")
            return
            
        name = self.listbox.get(selection[0])
        if messagebox.askyesno("Confirm", f"Delete visualization '{name}'?"):
            #delete then update
            if self.db_manager.delete_visualization(name):
                self.update_list()
    
    def view_viz(self):
        #handle the view of the image. should open a window and display the picture
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "select a visualization")
            return
            
        name = self.listbox.get(selection[0])
        #grab the selected visual from the db
        img_data = self.db_manager.get_visualization(name)
        
        if img_data:
            #  new window to display visualization
            view_window = tk.Toplevel(self.top)
            view_window.title(f"Visualization: {name}")
            
            #convert bytes to image
            img = Image.open(io.BytesIO(img_data))
            photo = ImageTk.PhotoImage(img)
            
            # display
            label = tk.Label(view_window, image=photo)
            label.image = photo
            label.pack()

class AutocompleteEntry:
    # this is not a priority but hopefully we can handle autocomplete for the cities and zip
    def __init__(self, parent, suggest_command):
        #defien variables for autocompete object
        self.parent = parent
        self.suggest_command = suggest_command
        self.var = tk.StringVar()
        self.entry = self.parent.Entry(textvariable=self.var)
        self.listbox = None
        
        self.entry.bind('<KeyRelease>', self.on_keyrelease)
        self.entry.bind('<FocusOut>', self.on_focus_out)
    
    def on_keyrelease(self, event):
        #handle key realese event
        value = self.var.get()
        if value:
            suggestions = self.suggest_command(value)
            if suggestions:
                self.show_suggestions(suggestions)
            else:
                self.hide_suggestions()
        else:
            self.hide_suggestions()
    
    def on_focus_out(self, event):
        self.entry.master.after(100, self.hide_suggestions)
    
    def show_suggestions(self, suggestions):
        # list the suggested options
        if not self.listbox:
            self.listbox = tk.Listbox(self.entry.master)
            x = self.entry.winfo_x()
            y = self.entry.winfo_y() + self.entry.winfo_height()
            self.listbox.place(x=x, y=y, width=self.entry.winfo_width())
            
            self.listbox.bind('<<ListboxSelect>>', self.on_suggestion_select)
        
        self.listbox.delete(0, tk.END)
        for item in suggestions:
            self.listbox.insert(tk.END, item)
    
    def on_suggestion_select(self, event):
        
        if self.listbox:
            try:
                selection_idx = self.listbox.curselection()
                if selection_idx:  #check if there's a selection
                    selection = self.listbox.get(selection_idx[0])
                    self.var.set(selection)
                    self.hide_suggestions()
            except Exception:
                pass  # ignore
    
    def hide_suggestions(self):
        # close the suggestions box
        if self.listbox:
            self.listbox.destroy()
            self.listbox = None
    
    def get(self):
        #get string
        return self.var.get()
    
    def set(self, value):
        #set string
        self.var.set(value)

class ZillowVisualization(TKMT.ThemedTKinterFrame):
    def __init__(self):
        # start constructor first with dark mode
        super().__init__("Zillow Data Visualization", "azure", "dark")
        
        # set initial window size and min size
        self.master.geometry("1100x800")
        self.master.minsize(1000, 600)
        
        # get the db login
        self.db_manager = DatabaseManager()
        
        # start layout
        self.setup_layout()
        
        # chart manager
        self.chart_manager = ChartManager(self.ax, self.canvas, self.fig, self.accent)
        self.chart_manager.setup_initial_plot()
        
        self.run()
    
    def setup_layout(self):
        """Set main layout and widgets"""
        #Create two main frames 
        # set the ratios so that the chart fram takes up more space the control pannel
        self.control_panel = self.addLabelFrame("Control Panel", row=0, col=0, colspan=1)
        self.chart_frame = self.addLabelFrame("Chart Area", row=0, col=1, colspan=4)
        
        # start control panel
        self.setup_control_panel()
        
        # start matplot integration
        self.canvas, self.fig, self.ax, self.background, self.accent = (
            self.chart_frame.matplotlibFrame("Housing Data")
        )

    def setup_control_panel(self):
        """control panel widgets using TKMT layout """
        # state button
        self.control_panel.Label("State", padx=2, pady=(2, 0))  # Reduced top padding
        states = [""] + self.db_manager.get_states()
        self.state_var = tk.StringVar()
        self.control_panel.Combobox(states, self.state_var, colspan=2, padx=2, pady=1)
        self.state_var.trace_add('write', lambda *args: self.on_state_change())
        
        #City buttond
        self.control_panel.Label("City", padx=2, pady=(2, 0))
        self.city_entry = AutocompleteEntry(
            self.control_panel,
            self.suggest_cities
        )
        self.city_entry.entry.configure(width=25)
        # entry area
        self.city_entry.entry.grid(row=3, column=0, columnspan=2, padx=2, pady=1, sticky='ew')
        
        # Zipcode button
        self.control_panel.Label("Zipcode", padx=2, pady=(2, 0))
        self.zipcode_entry = AutocompleteEntry(
            self.control_panel,
            self.suggest_zipcodes
        )
        self.zipcode_entry.entry.configure(width=25)
        # entry artea
        self.zipcode_entry.entry.grid(row=5, column=0, columnspan=2, padx=2, pady=1, sticky='ew')
        
        # Date range should have two entrys
        self.control_panel.Label("Time Range (YYYY-MM-DD)", padx=2, pady=(2, 0))
        
        # frame for the dates
        date_frame = self.control_panel.addFrame("date_frame", pady=1)
        
        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()
        
        #date entries side by side 
        date_frame.Entry(
            textvariable=self.start_date_var,
            widgetkwargs={"width": 12},
            col=0,
            padx=(2, 1),
            pady=0
        )
        date_frame.Entry(
            textvariable=self.end_date_var,
            widgetkwargs={"width": 12},
            col=1,
            padx=(1, 2),
            pady=0
        )
        
        # make things compact with this
        self.control_panel.Label("", pady=1)
        
        # rest of the buttons to control the visual
        self.control_panel.Button(
            "Update Viz",
            self.update_visualization,
            colspan=2,
            padx=2,
            pady=1
        )
        
        self.control_panel.Button(
            "Clear Filters",
            self.clear_filters,
            colspan=2,
            padx=2,
            pady=1
        )
    
        #checkbox for trend line 
        self.trend_var = tk.BooleanVar()
        self.control_panel.Checkbutton(
            "Show Trend Line",
            self.trend_var,
            command=self.toggle_trend_line,
            colspan=2,
            padx=2,
            pady=1
        )
        
        # Visualization manager buttons to open the windows and save
        self.control_panel.Label("", pady=1)
        self.control_panel.Button(
            "Save Visualization",
            self.save_visualization,
            colspan=2,
            padx=2,
            pady=1
        )
        self.control_panel.Button(
            "Manage Visualizations",
            self.manage_visualizations,
            colspan=2,
            padx=2,
            pady=1
        )
    def save_visualization(self):
        """save visual start"""
        if hasattr(self.chart_manager, 'current_data'):
            SaveVisualizationDialog(self.master, self.do_save_visualization)
        else:
            #handle no visual posted
            messagebox.showwarning("Warning", "No visualization to save")

    def do_save_visualization(self, name):
        """save the visualization final"""
        viz_id = self.db_manager.save_visualization(name, self.fig)
        if viz_id is not None:
            messagebox.showinfo("Success", "Visualization saved successfully")
        else:
            #only show error if save actually failed
            if viz_id is None:
                messagebox.showerror("Error", "Failed to save visualization")

    def manage_visualizations(self):
        """open visualization manager"""
        VisualizationManager(self.master, self.db_manager)
    def toggle_trend_line(self):
        """toggle trend line show"""
        self.chart_manager.toggle_trend_line()

    def suggest_cities(self, partial_name):
        """city suggestions based on the current characters"""
        return self.db_manager.suggest_cities(partial_name, self.state_var.get())
    
    def suggest_zipcodes(self, partial_zipcode):
        """zipcode suggestions based on current numbers"""
        return self.db_manager.suggest_zipcodes(
            partial_zipcode,
            self.state_var.get(),
            self.city_entry.get()
        )
    
    def on_state_change(self):
        """clear the city and zip if state chages since its different nows"""
        self.city_entry.set("")
        self.zipcode_entry.set("")
    
    def clear_filters(self):
        """start over by clearing entries"""
        self.state_var.set("")
        self.city_entry.set("")
        self.zipcode_entry.set("")
        self.start_date_var.set("")
        self.end_date_var.set("")
    
    def update_visualization(self):
        """grab the filters and upadte the global dictionary"""
        # Get non-empty values
        filters = {
            'state': self.state_var.get().strip(),
            'city': self.city_entry.get().strip(),
            'zipcode': self.zipcode_entry.get().strip(),
            'start_date': self.start_date_var.get().strip(),
            'end_date': self.end_date_var.get().strip()
        }
        
        # if filter empty remove it
        filters = {k: v for k, v in filters.items() if v}
        
        # get the data from the db
        data = self.db_manager.fetch_housing_data(**filters)
        #update plot
        self.chart_manager.update_plot(data)

if __name__ == "__main__":
    #start of the program
    app = ZillowVisualization()