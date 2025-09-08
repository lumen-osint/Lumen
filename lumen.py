import tkinter as tk
from tkinter import font as tkfont, filedialog
import os
import json
import subprocess
import requests
import phonenumbers
from phonenumbers import geocoder, carrier, timezone, format_number, PhoneNumberFormat
import threading
import sys
from datetime import datetime
from PIL import Image, ImageTk

# --- INIZIO SEZIONE UI ---

# PALETTE COLORI DA SKETCH BOZZA
SIDEBAR_BG = "#000000"
DIVIDER_COLOR = "#292929"
TAB_SELECTED_BG = "#292929"
TAB_UNSELECTED_BG = "#000000"
MAIN_BG = "#000000"
WIDGET_BG = "#000000"
WIDGET_BORDER_COLOR = "#292929"
RESULTS_BG = "#000000"
TEXT_COLOR = "#a8a8a8"
WINDOW_BG = "#000000"

# FONT
FONT_FAMILY = "Helvetica"
FONT_NORMAL = (FONT_FAMILY, 10)
FONT_BOLD = (FONT_FAMILY, 10, "bold")
ICON_FONT = (FONT_FAMILY, 22)

# CLASSE PER I WIDGET CON ANGOLI ARROTONDATI (CON LOGICA DI DISEGNO DEFINITIVA)
class RoundedFrame(tk.Frame):
    def __init__(self, parent, radius=12, border_width=1, border_color=WIDGET_BORDER_COLOR, fill_color=WIDGET_BG, **kwargs):
        super().__init__(parent, bg=parent.cget("bg"), **kwargs)
        self.radius, self.border_width, self.border_color, self.fill_color = radius, border_width, border_color, fill_color
        self.canvas = tk.Canvas(self, bg=parent.cget("bg"), highlightthickness=0)
        self.canvas.place(relwidth=1, relheight=1)
        tk.Misc.lower(self.canvas)
        self.bind("<Configure>", self._draw_border)

    def _draw_border(self, event=None):
        self.canvas.delete("all")
        width, height = self.winfo_width(), self.winfo_height()
        if not width or not height: return
        r, w = self.radius, self.border_width

        if w > 0:
            self.canvas.create_oval(0, 0, r*2, r*2, fill=self.border_color, outline="")
            self.canvas.create_oval(width-r*2, 0, width, r*2, fill=self.border_color, outline="")
            self.canvas.create_oval(0, height-r*2, r*2, height, fill=self.border_color, outline="")
            self.canvas.create_oval(width-r*2, height-r*2, width, height, fill=self.border_color, outline="")
            self.canvas.create_rectangle(r, 0, width-r, height, fill=self.border_color, outline="")
            self.canvas.create_rectangle(0, r, width, height-r, fill=self.border_color, outline="")

        self.canvas.create_oval(w, w, r*2-w, r*2-w, fill=self.fill_color, outline="")
        self.canvas.create_oval(width-r*2+w, w, width-w, r*2-w, fill=self.fill_color, outline="")
        self.canvas.create_oval(w, height-r*2+w, r*2-w, height-w, fill=self.fill_color, outline="")
        self.canvas.create_oval(width-r*2+w, height-r*2+w, width-w, height-w, fill=self.fill_color, outline="")
        self.canvas.create_rectangle(r, w, width-r, height-w, fill=self.fill_color, outline="")
        self.canvas.create_rectangle(w, r, width-w, height-r, fill=self.fill_color, outline="")
        
    def change_fill_color(self, new_color):
        self.fill_color = new_color
        self._draw_border()

# --- MODIFICA #1: NUOVA LOGICA PER SPLASH SCREEN NON BLOCCANTE E COMPATIBILE CON LINUX ---
def create_splash_screen(parent):
    splash_win = tk.Toplevel(parent)
    splash_win.overrideredirect(True)

    splash_width, splash_height = 350, 200
    screen_width, screen_height = splash_win.winfo_screenwidth(), splash_win.winfo_screenheight()
    x, y = (screen_width / 2) - (splash_width / 2), (screen_height / 2) - (splash_height / 2)
    splash_win.geometry(f'{splash_width}x{splash_height}+{int(x)}+{int(y)}')

    # --- INIZIO DELLA MODIFICA PER LA COMPATIBILITÀ ---
    # Controlla il sistema operativo per applicare l'effetto di trasparenza corretto
    if sys.platform == "win32":
        # Metodo per Windows per creare una finestra sagomata (non rettangolare)
        TRANSPARENT_COLOR = '#abcdef' 
        splash_win.config(bg=TRANSPARENT_COLOR)
        splash_win.attributes('-transparentcolor', TRANSPARENT_COLOR)
    else:
        # Metodo per Linux e altri OS che usa -alpha come richiesto.
        # Questo crea una finestra rettangolare semi-trasparente.
        # Impostiamo il colore di sfondo della finestra uguale a quello del frame
        # per evitare che gli angoli appaiano di un colore indesiderato.
        splash_win.config(bg=SIDEBAR_BG)
        splash_win.attributes('-alpha', 0.95) # Valore da 0.0 (trasparente) a 1.0 (opaco)
    # --- FINE DELLA MODIFICA ---

    splash_frame = RoundedFrame(splash_win, radius=25, fill_color=SIDEBAR_BG, border_width=0)
    splash_frame.pack(fill='both', expand=True)

    try:
        splash_logo_original = Image.open("logo.png").convert("RGBA")
        splash_logo_resized = splash_logo_original.resize((64, 64), Image.Resampling.LANCZOS)
        splash_logo_tk = ImageTk.PhotoImage(splash_logo_resized)
        logo_label = tk.Label(splash_frame, image=splash_logo_tk, bg=SIDEBAR_BG)
        logo_label.image = splash_logo_tk
        logo_label.place(relx=0.5, rely=0.5, anchor='center')
    except FileNotFoundError:
        print("logo.png non trovato per lo splash screen.")
    
    return splash_win
# --- FINE MODIFICA #1 ---


# Config file
CONFIG_FILE = 'config.json'
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'r') as f: config = json.load(f)
else:
    config = {
        'breach_api': '', 'truecaller_api': '',
        'visible_tabs': ['Holehe', 'PhoneLookup', 'BreachDirectory', 'Sherlock', 'Truecaller'], 
        'auto_save_enabled': False, 'save_file_path': ''
    }

all_tabs = ['Holehe', 'PhoneLookup', 'BreachDirectory', 'Sherlock', 'Truecaller']
visible_tabs = config.get('visible_tabs', all_tabs)

# Funzioni Helper e Worker (invariate)
def run_command(worker_func, *args):
    threading.Thread(target=worker_func, args=args, daemon=True).start()
def update_results(widget, text):
    widget.config(state='normal'); widget.delete(1.0, 'end'); widget.insert('end', text); widget.config(state='disabled')
def save_result_to_file(search_type, query, result_text):
    if config.get('auto_save_enabled') and config.get('save_file_path'):
        try:
            with open(config['save_file_path'], 'a', encoding='utf-8') as f:
                f.write(f"--- Log Entry: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n"); f.write(f"Search Type: {search_type}\n")
                f.write(f"Query: {query}\n"); f.write("Results:\n"); f.write(result_text); f.write("\n\n")
        except Exception as e: print(f"Error saving to file: {e}")
def holehe_worker(email, results_widget):
    if not email or email == '@gmail.com': return
    update_results(results_widget, 'Running...');
    try:
        proc = subprocess.run(['holehe', '--only-used', email], capture_output=True, text=True, check=False)
        result_text = '\n'.join([l.strip() for l in proc.stdout.splitlines() if l.startswith('[+]')]) or 'No results found.'
        update_results(results_widget, result_text); save_result_to_file("Holehe", email, result_text)
    except Exception as e: update_results(results_widget, f'Error: {e}')
def phone_worker(phone, results_widget):
    if not phone or phone == '+1 (123) 456-7890': return
    update_results(results_widget, 'Running...')
    try:
        parsed = phonenumbers.parse(phone)
        if not phonenumbers.is_valid_number(parsed): update_results(results_widget, 'Invalid phone number.'); return
        result_text = f"Location: {geocoder.description_for_number(parsed, 'en') or 'N/A'}\nCarrier: {carrier.name_for_number(parsed, 'en') or 'N/A'}\nE164: {format_number(parsed, PhoneNumberFormat.E164)}"
        update_results(results_widget, result_text); save_result_to_file("PhoneLookup", phone, result_text)
    except Exception as e: update_results(results_widget, f'Error: {e}')
def breach_worker(query, results_widget):
    if not query or query == 'email or username': return
    update_results(results_widget, 'Running...')
    if not (api_key := config.get('breach_api')): update_results(results_widget, 'BreachDirectory API key not set in settings.'); return
    try:
        response = requests.get('https://breachdirectory.p.rapidapi.com/', headers={'x-rapidapi-key': api_key, 'x-rapidapi-host': 'breachdirectory.p.rapidapi.com'}, params={"func": "auto", "term": query}, timeout=15)
        response.raise_for_status(); data = response.json()
        result_text = "".join([f"Source: {res.get('sources', ['N/A'])[0]}\nPassword: {res.get('password', 'N/A')}\n\n" for res in data['result']]) if data and data.get('result') else 'No breaches found.'
        update_results(results_widget, result_text); save_result_to_file("BreachDirectory", query, result_text)
    except Exception as e: update_results(results_widget, f'API Error: {e}')
def truecaller_worker(phone_number, results_widget):
    if not phone_number or phone_number == 'phone number': return
    update_results(results_widget, 'Running...')
    api_key = config.get('truecaller_api')
    if not api_key: update_results(results_widget, 'Truecaller API key not set in settings.'); return
    cleaned_number = ''.join(filter(str.isdigit, phone_number))
    url = f"https://truecaller-data2.p.rapidapi.com/search/{cleaned_number}"
    headers = {"x-rapidapi-key": api_key, "x-rapidapi-host": "truecaller-data2.p.rapidapi.com"}
    try:
        response = requests.get(url, headers=headers, timeout=15); response.raise_for_status(); data = response.json()
        result_text = json.dumps(data, indent=4, ensure_ascii=False) if data and isinstance(data, dict) else "No results found or invalid response format."
        update_results(results_widget, result_text); save_result_to_file("Truecaller", phone_number, result_text)
    except requests.exceptions.HTTPError as http_err: update_results(results_widget, f'HTTP Error: {http_err}\nResponse: {response.text}')
    except Exception as e: update_results(results_widget, f'API Error: {e}')
def sherlock_worker(username, results_widget):
    if not username or username == 'username': return
    update_results(results_widget, 'Running...')
    try:
        proc = subprocess.run(['sherlock', '--print-found', username], capture_output=True, text=True, check=False)
        result_text = proc.stdout or f"No results found.\n{proc.stderr}"
        update_results(results_widget, result_text); save_result_to_file("Sherlock", username, result_text)
    except Exception as e: update_results(results_widget, f'Error: {e}')
def add_placeholder(entry, placeholder_text):
    def on_focus_in(event):
        if entry.get() == placeholder_text: entry.delete(0, tk.END); entry.config(fg=TEXT_COLOR)
    def on_focus_out(event):
        if not entry.get(): entry.insert(0, placeholder_text); entry.config(fg='grey')
    entry.insert(0, placeholder_text); entry.config(fg='grey'); entry.bind("<FocusIn>", on_focus_in); entry.bind("<FocusOut>", on_focus_out)
def open_settings():
    set_win = tk.Toplevel(root); set_win.title('Settings'); set_win.geometry('450x550'); set_win.configure(bg=WIDGET_BG); set_win.transient(root)
    try: set_win.iconbitmap('logo.png')
    except tk.TclError: print("logo.png non trovato per la finestra impostazioni.")
    tk.Label(set_win, text='BreachDirectory API Key:', bg=WIDGET_BG, fg=TEXT_COLOR, font=FONT_NORMAL).pack(pady=(10,0), padx=10, anchor='w')
    api_entry = tk.Entry(set_win, bg=WIDGET_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, highlightbackground=WIDGET_BORDER_COLOR, highlightthickness=1, relief='flat', width=50)
    api_entry.insert(0, config.get('breach_api', '')); api_entry.pack(pady=5, padx=10, fill='x')
    tk.Label(set_win, text='Truecaller API Key:', bg=WIDGET_BG, fg=TEXT_COLOR, font=FONT_NORMAL).pack(pady=(10,0), padx=10, anchor='w')
    truecaller_api_entry = tk.Entry(set_win, bg=WIDGET_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, highlightbackground=WIDGET_BORDER_COLOR, highlightthickness=1, relief='flat', width=50)
    truecaller_api_entry.insert(0, config.get('truecaller_api', '')); truecaller_api_entry.pack(pady=5, padx=10, fill='x')
    tk.Label(set_win, text='\nVisible Tabs:', bg=WIDGET_BG, fg=TEXT_COLOR, font=FONT_NORMAL).pack(pady=5, padx=10, anchor='w')
    tab_vars = {tab: tk.BooleanVar(value=tab in visible_tabs) for tab in all_tabs}
    for tab, var in tab_vars.items(): tk.Checkbutton(set_win, text=tab, variable=var, bg=WIDGET_BG, fg=TEXT_COLOR, selectcolor=DIVIDER_COLOR, activebackground=WIDGET_BG, activeforeground=TEXT_COLOR, relief='flat', font=FONT_NORMAL).pack(anchor='w', padx=10)
    tk.Label(set_win, text='\nAutomatic Save:', bg=WIDGET_BG, fg=TEXT_COLOR, font=FONT_NORMAL).pack(pady=5, padx=10, anchor='w')
    auto_save_var = tk.BooleanVar(value=config.get('auto_save_enabled', False))
    tk.Checkbutton(set_win, text="Enable automatic saving of results to a file", variable=auto_save_var, bg=WIDGET_BG, fg=TEXT_COLOR, selectcolor=DIVIDER_COLOR, activebackground=WIDGET_BG, activeforeground=TEXT_COLOR, relief='flat', font=FONT_NORMAL).pack(anchor='w', padx=10)
    save_path_frame = tk.Frame(set_win, bg=WIDGET_BG); save_path_frame.pack(fill='x', padx=10, pady=5)
    save_path_var = tk.StringVar(value=config.get('save_file_path', 'No file selected'))
    path_label = tk.Label(save_path_frame, textvariable=save_path_var, bg=WIDGET_BG, fg="grey", font=FONT_NORMAL, wraplength=300, justify='left'); path_label.pack(side='left')
    def choose_file():
        if filepath := filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")]): save_path_var.set(filepath); path_label.config(fg=TEXT_COLOR)
    tk.Button(save_path_frame, text="Browse...", command=choose_file, bg=TAB_SELECTED_BG, fg=TEXT_COLOR, relief='flat', font=FONT_NORMAL).pack(side='right')
    def save_settings():
        config['breach_api'] = api_entry.get(); config['truecaller_api'] = truecaller_api_entry.get(); config['visible_tabs'] = [tab for tab, var in tab_vars.items() if var.get()]; config['auto_save_enabled'] = auto_save_var.get()
        if save_path_var.get() != 'No file selected': config['save_file_path'] = save_path_var.get()
        with open(CONFIG_FILE, 'w') as f: json.dump(config, f, indent=4)
        root.destroy(); os.execv(sys.executable, ['python'] + sys.argv)
    tk.Button(set_win, text='Save & Restart', command=save_settings, bg=TAB_SELECTED_BG, fg=TEXT_COLOR, relief='flat', font=FONT_NORMAL, padx=10, pady=5).pack(pady=20)

# --- MODIFICA #2: RIORGANIZZAZIONE DELLO SCRIPT PRINCIPALE ---
def setup_main_app(root, splash_win):
    # Questa funzione ora contiene TUTTO il codice di costruzione della UI principale
    root.title('Lumen | OsintSuite')
    try:
        root.iconbitmap('logo.png')
    except tk.TclError:
        print("logo.png non trovato.")
    root.configure(bg=WINDOW_BG)
    root.geometry('1100x650')
    root.is_fullscreen = False
    def toggle_fullscreen(event=None): root.is_fullscreen = not root.is_fullscreen; root.attributes("-fullscreen", root.is_fullscreen)
    root.bind("<F11>", toggle_fullscreen)

    app_container = RoundedFrame(root, radius=15, fill_color=MAIN_BG, border_width=0); app_container.pack(fill='both', expand=True, padx=0, pady=0) 
    sidebar = tk.Frame(app_container, bg=SIDEBAR_BG, width=50); sidebar.pack(side='left', fill='y'); sidebar.pack_propagate(False)
    
    try:
        sidebar_logo_image = Image.open("logo.png").convert("RGBA")
        datas = sidebar_logo_image.getdata(); newData = []
        for item in datas: newData.append((item[0], item[1], item[2], int(255 * 0.5))) if item[3] > 0 else newData.append(item)
        sidebar_logo_image.putdata(newData); resized_image = sidebar_logo_image.resize((45, 45), Image.Resampling.LANCZOS)
        home_icon_image = ImageTk.PhotoImage(resized_image)
        home_label = tk.Label(sidebar, image=home_icon_image, bg=SIDEBAR_BG)
        home_label.image = home_icon_image; home_label.pack(pady=(50, 15))
    except FileNotFoundError:
        print("logo.png non trovato per la sidebar.")
    
    gear_label = tk.Label(sidebar, text='\U0001f39b', bg=SIDEBAR_BG, fg=TEXT_COLOR, font=ICON_FONT); gear_label.pack(side='bottom', pady=15); gear_label.bind("<Button-1>", lambda e: open_settings())
    tk.Frame(app_container, bg=DIVIDER_COLOR, width=1).pack(side='left', fill='y')
    main_frame = tk.Frame(app_container, bg=MAIN_BG); main_frame.pack(side='left', fill='both', expand=True, padx=20, pady=10)
    top_bar = tk.Frame(main_frame, bg=MAIN_BG); top_bar.pack(side='top', pady=(10, 20), anchor='n')

    tab_widgets, tab_frames = {}, {}
    current_tab = visible_tabs[0] if visible_tabs else None

    def select_tab(name):
        nonlocal current_tab
        if name not in visible_tabs: return
        current_tab = name
        for w_name, (container, label) in tab_widgets.items():
            is_selected = w_name == name
            container.change_fill_color(TAB_SELECTED_BG if is_selected else TAB_UNSELECTED_BG)
            label.config(font=FONT_BOLD if is_selected else FONT_NORMAL, bg=TAB_SELECTED_BG if is_selected else TAB_UNSELECTED_BG)
        for f_name, frame in tab_frames.items():
            if f_name == name: frame.pack(fill='both', expand=True)
            else: frame.pack_forget()

    for tab_name in all_tabs:
        tab_container = RoundedFrame(top_bar, radius=15, border_width=0, fill_color=TAB_UNSELECTED_BG)
        tab_label = tk.Label(tab_container, text=tab_name, font=FONT_NORMAL, fg=TEXT_COLOR, bg=TAB_UNSELECTED_BG, padx=10, pady=5)
        tab_label.pack(); tab_widgets[tab_name] = (tab_container, tab_label)
        tab_label.bind("<Button-1>", lambda e, n=tab_name: select_tab(n)); tab_container.bind("<Button-1>", lambda e, n=tab_name: select_tab(n))
        frame = tk.Frame(main_frame, bg=MAIN_BG); tab_frames[tab_name] = frame
        input_frame = tk.Frame(frame, bg=MAIN_BG); input_frame.pack(side='top', fill='x', pady=(30, 0))
        avvia_container = RoundedFrame(input_frame, radius=16, border_width=0); avvia_container.pack(side='right')
        avvia_btn = tk.Button(avvia_container, text="Avvia", bg=WIDGET_BG, fg=TEXT_COLOR, relief='flat', font=FONT_NORMAL, activebackground=DIVIDER_COLOR, activeforeground=TEXT_COLOR, padx=20, pady=4); avvia_btn.pack(fill='both', expand=True, padx=1, pady=1)
        entry_container = RoundedFrame(input_frame, radius=16, border_width=1); entry_container.pack(side='left', fill='x', expand=True, padx=(0, 10))
        entry = tk.Entry(entry_container, bg=WIDGET_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, relief='flat', font=FONT_NORMAL, highlightthickness=0); entry.pack(fill='both', expand=True, padx=15, pady=8)
        results_container = RoundedFrame(frame, radius=12, border_width=1); results_container.pack(fill='both', expand=True, pady=(20, 10))
        results = tk.Text(results_container, bg=RESULTS_BG, fg=TEXT_COLOR, relief='flat', font=FONT_NORMAL, highlightthickness=0, insertbackground=TEXT_COLOR, wrap='word', bd=0, state='disabled'); results.pack(fill='both', expand=True, padx=15, pady=15)

        if tab_name == 'Holehe': add_placeholder(entry, '@gmail.com'); avvia_btn.config(command=lambda e=entry, r=results: run_command(holehe_worker, e.get(), r))
        elif tab_name == 'PhoneLookup': add_placeholder(entry, '+1 (123) 456-7890'); avvia_btn.config(command=lambda e=entry, r=results: run_command(phone_worker, e.get(), r))
        elif tab_name == 'BreachDirectory': add_placeholder(entry, 'email or username'); avvia_btn.config(command=lambda e=entry, r=results: run_command(breach_worker, e.get(), r))
        elif tab_name == 'Sherlock': add_placeholder(entry, 'username'); avvia_btn.config(command=lambda e=entry, r=results: run_command(sherlock_worker, e.get(), r))
        elif tab_name == 'Truecaller': add_placeholder(entry, 'phone number'); avvia_btn.config(command=lambda e=entry, r=results: run_command(truecaller_worker, e.get(), r))

    for tab in all_tabs:
        if tab in visible_tabs: tab_widgets[tab][0].pack(side='left', padx=5)

    if current_tab: select_tab(current_tab)

    # Quando tutto è caricato, distruggi la splash e mostra la finestra principale
    splash_win.destroy()
    root.deiconify()

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw() # Tieni la finestra principale nascosta all'inizio

    splash = create_splash_screen(root)
    
    # Avvia il caricamento dell'app principale DOPO che la splash è apparsa
    # Il valore 100 (ms) dà a Tkinter il tempo di renderizzare la splash screen
    root.after(100, setup_main_app, root, splash)
    
    root.mainloop()
