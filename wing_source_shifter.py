# -- coding utf-8 --
import json
import copy
import os
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

class WingMatrixApp
    def __init__(self, root)
        self.root = root
        self.root.title(Матриця маршрутизації Wing Snapshot)
        self.root.geometry(850x950)
        self.root.minsize(800, 800)
        self.root.configure(bg=#282828)  # темний фон
        
        # Дані та історія
        self.data = None
        self.file_path = None
        self.history = []      # Стек станів для Undo
        self.redo_stack = []   # Стек станів для Redo
        
        self.io_in = {}
        self.groups = []
        self.current_grp = tk.StringVar()
        
        # Стан виділення і DND
        self.selected_indices = set()
        self.last_clicked_idx = None
        self.drag_start_idx = None
        self.drag_active = False
        self.drag_delta = None      
        self.preview_target = None  
        
        self.labels = {} 
        self.MAX_SLOTS = 64
        
        # Збереження
        self.overwrite = tk.BooleanVar(value=False)
        self.prefix = tk.StringVar(value=_shifted)
        
        self.setup_ui()
        self.update_ui_state(loaded=False)
        # Виклик refresh_grid() на старті прибирає моргання сітки
        self.refresh_grid()

    # ==========================================
    # ДОПОМІЖНІ ФУНКЦІЇ (РОБОТА З КОЛЬОРОМ)
    # ==========================================
    def blend_colors(self, hex_bg, hex_fg, alpha)
        Змішує два hex-кольори з урахуванням прозорості (alpha від 0 до 1).
        if not hex_bg.startswith(#)
            hex_bg = #282828
            
        bg = hex_bg.lstrip('#')
        fg = hex_fg.lstrip('#')
        
        if len(bg) != 6 or len(fg) != 6
            return hex_bg

        r_bg, g_bg, b_bg = int(bg[02], 16), int(bg[24], 16), int(bg[46], 16)
        r_fg, g_fg, b_fg = int(fg[02], 16), int(fg[24], 16), int(fg[46], 16)

        r = int(r_bg  (1 - alpha) + r_fg  alpha)
        g = int(g_bg  (1 - alpha) + g_fg  alpha)
        b = int(b_bg  (1 - alpha) + b_fg  alpha)

        return f#{r02x}{g02x}{b02x}

    # ==========================================
    # ІНТЕРФЕЙС
    # ==========================================
    def setup_ui(self)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#282828')
        style.configure('TLabel', background='#282828', foreground='white', font=(Arial, 10))
        style.configure('TLabelFrame', background='#282828', foreground='white')
        style.configure('TButton', background='#625531', foreground='white', borderwidth=1)
        style.map('TButton', background=[('active', '#7a6a40')])
        style.configure('TCheckbutton', background='#282828', foreground='white')
        
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # --- Верхня панель Файл та UndoRedo ---
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.btn_select = ttk.Button(top_frame, text=Відкрити Snapshot..., command=self.select_file)
        self.btn_select.pack(side=tk.LEFT, padx=(0, 10))
        
        self.file_label = ttk.Label(top_frame, text=Файл не вибрано, foreground=gray)
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.btn_redo = ttk.Button(top_frame, text=Redo , command=self.redo, width=8)
        self.btn_redo.pack(side=tk.RIGHT, padx=(5, 0))
        self.btn_undo = ttk.Button(top_frame, text= Undo, command=self.undo, width=8)
        self.btn_undo.pack(side=tk.RIGHT)
        
        # --- Панель керування Група ---
        ctrl_frame = ttk.Frame(main_frame)
        ctrl_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(ctrl_frame, text=Source Group, font=(Arial, 10, bold)).pack(side=tk.LEFT, padx=(0, 5))
        self.grp_cb = ttk.Combobox(ctrl_frame, textvariable=self.current_grp, state=readonly, width=15)
        self.grp_cb.pack(side=tk.LEFT)
        self.grp_cb.bind(ComboboxSelected, self.on_group_change)
        
        # --- Сітка джерел (Матриця 4x16) ---
        grid_outer_frame = ttk.LabelFrame(main_frame, text= Матриця джерел (Drag & Drop  Правий клік) , padding=5)
        grid_outer_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.grid_frame = tk.Frame(grid_outer_frame, bg=#282828)
        self.grid_frame.pack(fill=tk.BOTH, expand=True)
        
        # Напис для порожнього стану
        self.empty_label = tk.Label(self.grid_frame, text=Виберіть або перетягніть файл снепшота, bg=#282828, fg=#888888, font=(Arial, 12))
        self.empty_label.place(relx=0.5, rely=0.5, anchor=center)
        
        for col in range(4)
            self.grid_frame.columnconfigure(col, weight=1, uniform=col)
        for row in range(16)
            self.grid_frame.rowconfigure(row, weight=1, uniform=row)
            
        for i in range(1, self.MAX_SLOTS + 1)
            col = (i - 1)  16
            row = (i - 1) % 16
            
            lbl = tk.Label(self.grid_frame, text=f{i} , bg=#282828, relief=ridge, borderwidth=1, anchor=w, padx=5, font=(Consolas, 9))
            # Не викликаємо lbl.grid() тут, щоб уникнути моргання при старті
            
            lbl.bind(ButtonPress-1, lambda e, idx=i self.on_mouse_down(e, idx))
            lbl.bind(B1-Motion, self.on_mouse_drag)
            lbl.bind(ButtonRelease-1, self.on_mouse_release)
            lbl.bind(Enter, lambda e, idx=i self.on_mouse_enter(e, idx))
            lbl.bind(Leave, lambda e, idx=i self.on_mouse_leave(e, idx))
            lbl.bind(Button-3, lambda e, idx=i self.show_context_menu(e, idx))
            
            # Зберігаємо базовий колір для коректного зняття підсвітки
            lbl.base_bg = #282828
            self.labels[i] = lbl
            
            # Зберігаємо координати сітки в самому віджеті для подальшого використання
            lbl.grid_info_data = {'row' row, 'column' col, 'sticky' nsew, 'padx' 1, 'pady' 1}

        # --- Консоль логів ---
        console_frame = ttk.LabelFrame(main_frame, text= Історія дій , padding=5)
        console_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.console = tk.Text(console_frame, height=6, bg=#282828, fg=#00ff00, font=(Consolas, 10), wrap=tk.WORD, state=disabled)
        self.console.pack(fill=tk.X)
        
        # --- Нижня панель збереження ---
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.overwrite_cb = ttk.Checkbutton(bottom_frame, text=Перезаписати вихідний файл, variable=self.overwrite, command=self.toggle_prefix)
        self.overwrite_cb.pack(side=tk.LEFT, padx=(0, 10))
        
        self.prefix_label = ttk.Label(bottom_frame, text=Префікс)
        self.prefix_label.pack(side=tk.LEFT, padx=(0, 5))
        self.prefix_entry = ttk.Entry(bottom_frame, textvariable=self.prefix, width=15)
        self.prefix_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_save = ttk.Button(bottom_frame, text=Зберегти Snapshot, command=self.save_file)
        self.btn_save.pack(side=tk.RIGHT, ipadx=20, ipady=5)

    def toggle_prefix(self)
        if self.overwrite.get()
            self.prefix_entry.config(state=disabled)
        else
            self.prefix_entry.config(state=normal)

    # ==========================================
    # ЛОГІКА ФАЙЛУ ТА ІСТОРІЇ
    # ==========================================
    def update_ui_state(self, loaded)
        state = readonly if loaded else disabled
        self.grp_cb.config(state=state)
        btn_state = normal if loaded else disabled
        self.btn_save.config(state=btn_state)
        self.overwrite_cb.config(state=btn_state)
        if loaded and not self.overwrite.get()
            self.prefix_entry.config(state=normal)
        else
            self.prefix_entry.config(state=disabled)
        self.update_undo_redo_btns()

    def update_undo_redo_btns(self)
        self.btn_undo.config(state=normal if self.history else disabled)
        self.btn_redo.config(state=normal if self.redo_stack else disabled)

    def select_file(self)
        path = filedialog.askopenfilename(filetypes=[(Snapshot files, .snap), (All files, .)])
        if path
            self.load_file(path)

    def load_file(self, path)
        try
            with open(path, 'r', encoding='utf-8') as f
                self.data = json.loads(f.read())
            self.file_path = path
            self.file_label.config(text=os.path.basename(path), foreground=white)
            
            self.io_in = self.data.get(ae_data, {}).get(io, {}).get(in, {})
            self.groups = sorted(self.io_in.keys())
            self.grp_cb['values'] = self.groups
            
            if self.groups
                self.current_grp.set(self.groups[0])
                
            self.history.clear()
            self.redo_stack.clear()
            self.clear_console()
            self.log_action(Файл завантажено. Готовий до роботи.)
            
            self.empty_label.place_forget() # Ховаємо стартовий напис
            self.update_ui_state(loaded=True)
            self.refresh_grid()
        except Exception as e
            messagebox.showerror(Помилка, fНе вдалося завантажити файлn{e})

    def save_state(self, log_message)
        self.history.append((copy.deepcopy(self.data), self.get_console_text()))
        self.redo_stack.clear()
        self.log_action(log_message)
        self.update_undo_redo_btns()

    def undo(self)
        if not self.history return
        self.redo_stack.append((copy.deepcopy(self.data), self.get_console_text()))
        prev_data, prev_log = self.history.pop()
        self.data = prev_data
        self.io_in = self.data.get(ae_data, {}).get(io, {}).get(in, {})
        self.set_console_text(prev_log)
        self.log_action(СКАСУВАННЯ (Undo))
        self.refresh_grid()
        self.update_undo_redo_btns()

    def redo(self)
        if not self.redo_stack return
        self.history.append((copy.deepcopy(self.data), self.get_console_text()))
        next_data, next_log = self.redo_stack.pop()
        self.data = next_data
        self.io_in = self.data.get(ae_data, {}).get(io, {}).get(in, {})
        self.set_console_text(next_log)
        self.log_action(ПОВЕРНЕННЯ (Redo))
        self.refresh_grid()
        self.update_undo_redo_btns()

    def save_file(self)
        if not self.data return
        if self.overwrite.get()
            save_path = self.file_path
        else
            prefix = self.prefix.get().strip()
            if not prefix
                prefix = _shifted
            base = os.path.splitext(self.file_path)[0]
            save_path = base + prefix + .snap
        
        try
            with open(save_path, 'w', encoding='utf-8') as f
                json.dump(self.data, f, separators=(',', ''))
            self.log_action(fФайл збережено {os.path.basename(save_path)})
            messagebox.showinfo(Збережено, fСнепшот збереженоn{save_path})
        except Exception as e
            messagebox.showerror(Помилка, str(e))

    # ==========================================
    # КОНТЕКСТНЕ МЕНЮ (ПРАВИЙ КЛІК)
    # ==========================================
    def show_context_menu(self, event, idx)
        grp = self.current_grp.get()
        if not grp or not self.data return
        
        if idx not in self.selected_indices
            self.selected_indices = {idx}
            self.refresh_grid()

        menu = tk.Menu(self.root, tearoff=0, bg=#282828, fg=white)
        menu.add_command(label=Перейменувати..., command=lambda self.rename_source(grp, idx))
        menu.add_separator()
        
        color_menu = tk.Menu(menu, tearoff=0, bg=#282828, fg=white)
        colors = {
            1 #FFB81A, 2 #F2DD00, 3 #25C3FF, 4 #0180FF, 5 #3E63CC,
            6 #5A33FF, 7 #A533FF, 8 #FF33F6, 9 #E02040, 10 #FF5A30,
            11 #FF7A7A, 12 #C06A1F, 13 #96CC00, 14 #01B23E, 15 #33E6A5,
            16 #00CED1, 17 #707070, 18 #E0E0E0
        }
        for col_id, hex_color in colors.items()
            color_name = self.get_color_name(col_id)
            color_menu.add_command(label=f{color_name} (ID {col_id}), command=lambda c=col_id self.change_source_color(grp, idx, c))
        menu.add_cascade(label=Змінити колір, menu=color_menu)
        
        menu.add_separator()
        menu.add_command(label=Видалити (Очистити), command=lambda self.delete_source(grp, idx))
        
        menu.tk_popup(event.x_root, event.y_root)

    def get_color_name(self, col_id)
        names = {
            1 Помаранчевий, 2 Жовтий, 3 Блакитний, 4 Синій, 5 Середньо-синій,
            6 Фіолетово-синій, 7 Фіолетовий, 8 Рожевий, 9 Червоний, 10 Кораловий,
            11 Світло-червоний, 12 Коричневий, 13 Салатовий, 14 Зелений, 15 М'ятний,
            16 Темно-бірюзовий, 17 Сірий, 18 Світло-сірий
        }
        return names.get(col_id, fКолір {col_id})

    def change_source_color(self, grp, idx, col_id)
        grp_data = self.io_in[grp]
        if str(idx) not in grp_data
            grp_data[str(idx)] = self.get_empty_source()
        current_name = self.get_source_name(grp_data, idx)
        self.save_state(fЗміна кольору слота {idx} {current_name or 'порожньо'} - колір {col_id})
        grp_data[str(idx)][col] = col_id
        self.refresh_grid()

    def rename_source(self, grp, idx)
        grp_data = self.io_in[grp]
        current_name = self.get_source_name(grp_data, idx)
        
        new_name = simpledialog.askstring(Перейменування, fВведіть нове ім'я для {grp} {idx}, initialvalue=current_name, parent=self.root)
        
        if new_name is not None and new_name != current_name
            self.save_state(fПерейменування {idx} [{current_name or 'порожньо'}] - [{new_name}])
            if str(idx) not in grp_data
                grp_data[str(idx)] = self.get_empty_source()
            grp_data[str(idx)][name] = new_name
            self.refresh_grid()

    def delete_source(self, grp, idx)
        grp_data = self.io_in[grp]
        current_name = self.get_source_name(grp_data, idx)
        
        if len(self.selected_indices)  1 and idx in self.selected_indices
            if messagebox.askyesno(Підтвердження, fОчистити виділені слоти ({len(self.selected_indices)} шт.))
                self.save_state(fОчищення (Delete) {len(self.selected_indices)} слотів)
                for s_idx in self.selected_indices
                    grp_data[str(s_idx)] = self.get_empty_source()
                self.refresh_grid()
        else
            if str(idx) not in grp_data or (not current_name and grp_data[str(idx)].get(icon, 1) == 1)
                return
            if messagebox.askyesno(Підтвердження, fОчистити слот {idx} ({current_name}))
                self.save_state(fОчищення (Delete) {idx} [{current_name}])
                grp_data[str(idx)] = self.get_empty_source()
                self.refresh_grid()

    # ==========================================
    # КОНСОЛЬ
    # ==========================================
    def log_action(self, msg)
        timestamp = datetime.datetime.now().strftime(%H%M%S)
        grp = self.current_grp.get() or SYS
        full_msg = f{timestamp}  {grp}  {msg}n
        
        self.console.config(state=normal)
        self.console.insert(tk.END, full_msg)
        self.console.see(tk.END)
        self.console.config(state=disabled)

    def get_console_text(self)
        return self.console.get(1.0, tk.END)

    def set_console_text(self, text)
        self.console.config(state=normal)
        self.console.delete(1.0, tk.END)
        self.console.insert(tk.END, text)
        self.console.config(state=disabled)

    def clear_console(self)
        self.console.config(state=normal)
        self.console.delete(1.0, tk.END)
        self.console.config(state=disabled)

    # ==========================================
    # ВІДМАЛЬОВКА ТА DND ЛОГІКА
    # ==========================================
    def on_group_change(self, event=None)
        self.selected_indices.clear()
        self.refresh_grid()

    def get_source_name(self, grp_data, idx)
        name = grp_data.get(str(idx), {}).get(name, )
        return name.strip()

    def get_source_color(self, grp_data, idx)
        col_id = grp_data.get(str(idx), {}).get(col, 1)
        colors = {
            1 #FFB81A, 2 #F2DD00, 3 #25C3FF, 4 #0180FF, 5 #3E63CC,
            6 #5A33FF, 7 #A533FF, 8 #FF33F6, 9 #E02040, 10 #FF5A30,
            11 #FF7A7A, 12 #C06A1F, 13 #96CC00, 14 #01B23E, 15 #33E6A5,
            16 #00CED1, 17 #707070, 18 #E0E0E0
        }
        return colors.get(col_id, #282828) # Порожнім слотам віддаємо колір фону

    def get_group_max_idx(self, grp)
        grp_data = self.io_in.get(grp, {})
        indices = [int(k) for k in grp_data.keys()]
        return max(indices) if indices else 0

    def refresh_grid(self)
        grp = self.current_grp.get()
        # Якщо нічого не завантажено, ховаємо комірки
        if not grp or grp not in self.io_in
            for i in range(1, self.MAX_SLOTS + 1)
                self.labels[i].grid_remove()
            return
        
        grp_data = self.io_in[grp]
        max_idx = self.get_group_max_idx(grp)
        
        for i in range(1, self.MAX_SLOTS + 1)
            lbl = self.labels[i]
            if i  max_idx
                lbl.grid_remove()
                continue
            else
                lbl.grid(lbl.grid_info_data)
            
            preview_name = None
            preview_color = None
            
            if self.drag_active and self.drag_delta is not None
                target_src = i - self.drag_delta
                if target_src in self.selected_indices
                    preview_name = self.get_source_name(grp_data, target_src)
                    preview_color = self.get_source_color(grp_data, target_src)
                elif i in self.selected_indices
                    preview_name = 
                    preview_color = #282828
            
            if preview_name is not None
                display_text = f{i} {preview_name} if preview_name else f{i} (порожньо)
                base_bg = preview_color if preview_name else #282828
                text_color = black if preview_name else #888888
            else
                name = self.get_source_name(grp_data, i)
                display_text = f{i} {name} if name else f{i} (порожньо)
                base_bg = self.get_source_color(grp_data, i) if name else #282828
                text_color = black if name else #888888
            
            lbl.config(text=display_text, fg=text_color)
            lbl.base_bg = base_bg # Зберігаємо базовий колір для on_mouse_leave
            
            # Виділення змішуємо 35% білого з базовим кольором
            if i in self.selected_indices and not (self.drag_active and i in self.selected_indices)
                selected_bg = self.blend_colors(base_bg, #ffffff, 0.35)
                lbl.config(bg=selected_bg)
            else
                lbl.config(bg=base_bg)
    
    def on_mouse_enter(self, event, idx)
        if not self.drag_active
            lbl = self.labels[idx]
            if idx not in self.selected_indices
                # Наведення змішуємо 25% білого з базовим кольором
                hover_bg = self.blend_colors(lbl.base_bg, #ffffff, 0.25)
                lbl.config(bg=hover_bg)
    
    def on_mouse_leave(self, event, idx)
        if not self.drag_active
            lbl = self.labels[idx]
            if idx not in self.selected_indices
                lbl.config(bg=lbl.base_bg)

    def on_mouse_down(self, event, idx)
        if not self.data return
        
        if event.state & 0x0004
            if idx in self.selected_indices
                self.selected_indices.remove(idx)
            else
                self.selected_indices.add(idx)
        elif event.state & 0x0001 and self.last_clicked_idx
            start = min(self.last_clicked_idx, idx)
            end = max(self.last_clicked_idx, idx)
            self.selected_indices.update(range(start, end + 1))
        else
            if idx not in self.selected_indices
                self.selected_indices = {idx}

        self.last_clicked_idx = idx
        self.drag_start_idx = idx
        self.drag_active = True
        self.drag_delta = None
        self.preview_target = None
        self.refresh_grid()

    def on_mouse_drag(self, event)
        if not self.drag_active return
        idx = self.get_index_under_mouse()
        if idx is not None
            base_idx = min(self.selected_indices) if self.selected_indices else self.drag_start_idx
            self.drag_delta = idx - base_idx
            self.preview_target = idx
            self.refresh_grid()

    def on_mouse_release(self, event)
        if not self.drag_active return
        self.drag_active = False
        delta = self.drag_delta
        self.drag_delta = None
        self.preview_target = None
        
        if delta is not None and delta != 0
            self.process_drop(delta)
        
        self.refresh_grid()

    def get_index_under_mouse(self)
        x, y = self.root.winfo_pointerx(), self.root.winfo_pointery()
        for idx, lbl in self.labels.items()
            if not lbl.winfo_ismapped()
                continue
            lx = lbl.winfo_rootx()
            ly = lbl.winfo_rooty()
            lw = lbl.winfo_width()
            lh = lbl.winfo_height()
            if lx = x = lx + lw and ly = y = ly + lh
                return idx
        return None

    # ==========================================
    # ВИКОНАННЯ DND (MOVE)
    # ==========================================
    def process_drop(self, delta)
        if not self.selected_indices or delta == 0 return
        
        new_positions = [i + delta for i in self.selected_indices]
        if min(new_positions)  1 or max(new_positions)  self.MAX_SLOTS
            messagebox.showwarning(Помилка, Переміщення виходить за межі слотів (1-64).)
            return

        grp = self.current_grp.get()
        grp_data = self.io_in[grp]
        
        conflicts = []
        for src_idx in sorted(self.selected_indices)
            dst_idx = src_idx + delta
            if dst_idx not in self.selected_indices
                dst_name = self.get_source_name(grp_data, dst_idx)
                if dst_name
                    src_name = self.get_source_name(grp_data, src_idx) or (порожньо)
                    conflicts.append(fСлот {dst_idx} [{dst_name}] буде замінено на [{src_name}])
        
        if conflicts
            msg = Замінити джерелаnn + n.join(conflicts)
            if not messagebox.askyesno(Підтвердження заміни, msg)
                return

        log_parts = []
        for i in sorted(self.selected_indices)
            s_name = self.get_source_name(grp_data, i)
            log_parts.append(f{i}{s_name if s_name else '()'} -- {i+delta})
        log_msg = fПеренесення  + , .join(log_parts)

        self.save_state(log_msg)
        new_data = self.data
        new_grp_data = new_data[ae_data][io][in][grp]
        
        mapping = {}
        buffer = {}
        for src_idx in self.selected_indices
            buffer[src_idx] = copy.deepcopy(new_grp_data.get(str(src_idx), self.get_empty_source()))
            mapping[src_idx] = src_idx + delta
            
        for src_idx in self.selected_indices
            if src_idx not in mapping.values()
                new_grp_data[str(src_idx)] = self.get_empty_source()
                
        for src_idx, item_data in buffer.items()
            dst_idx = src_idx + delta
            new_grp_data[str(dst_idx)] = item_data
            
        self.update_routing(new_data, grp, mapping)
        self.selected_indices = set(mapping.values())
        self.refresh_grid()

    def get_empty_source(self)
        return {mode M, g 0, vph False, mute False, pol False, col 1, name , icon 1, tags , rmt OFF, rcvc False}

    def update_routing(self, new_data, grp, mapping)
        for section in [ch, aux]
            section_data = new_data.get(ae_data, {}).get(section, {})
            for ch_val in section_data.values()
                conn = ch_val.get(in, {}).get(conn, {})
                if conn.get(grp) == grp and conn.get(in) in mapping
                    conn[in] = mapping[conn.get(in)]
                if conn.get(altgrp) == grp and conn.get(altin) in mapping
                    conn[altin] = mapping[conn.get(altin)]

if __name__ == __main__
    root = tk.Tk()
    app = WingMatrixApp(root)
    root.mainloop()