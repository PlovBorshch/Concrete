import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3
import os
import datetime
import ctypes
import threading
import sys
import traceback
from PIL import Image, ImageTk, ImageDraw

# --- СИСТЕМНЫЙ ИДЕНТИФИКАТОР ---
try:
    myappid = 'ru.concrete.converter.prime.final'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except:
    pass


# --- ЛОВУШКА ОШИБОК ---
def show_error(etype, value, tb):
    err_msg = "".join(traceback.format_exception(etype, value, tb))
    print(err_msg)
    try:
        # Используем стандартный messagebox для самых критических ошибок,
        # так как наш кастомный диалог может сам быть источником проблемы.
        messagebox.showerror("!! КРИТИЧЕСКИЙ СБОЙ !!", f"ОТКАЗ МОДУЛЯ:\n{value}")
    except:
        pass


sys.excepthook = show_error

# --- КОНФИГУРАЦИЯ СТИЛЯ ---
FONT_MAIN = ("Consolas", 10)
FONT_HEAD = ("Consolas", 10, "bold")

COLORS = {
    "bg_main": "#121212",
    "bg_sec": "#1e1e1e",
    "fg_text": "#d0d0d0",
    "fg_dim": "#555555",
    "accent": "#8b0000",
    "border": "#000000",
    "btn": "#252525",
    "btn_h": "#353535"
}


# --- ИЗМЕНЕНИЕ: Универсальный кастомный диалог ---
class ConcreteDialog(tk.Toplevel):
    def __init__(self, parent, title, message, dialog_type='confirm'):
        super().__init__(parent)
        self.withdraw()

        self.title(title)
        self.result = False
        self.transient(parent)
        self.configure(bg=COLORS["bg_main"])
        self.resizable(False, False)

        try:
            transparent_img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
            self.transparent_icon = ImageTk.PhotoImage(transparent_img)
            self.iconphoto(False, self.transparent_icon)
        except:
            pass

        # Центрирование
        w, h = 400, 160
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        x = px + (pw // 2) - (w // 2)
        y = py + (ph // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.update_idletasks()

        # Темный заголовок
        try:
            hwnd_title = ctypes.windll.user32.GetParent(self.winfo_id())
            value = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd_title, 20, ctypes.byref(value), 4)
        except:
            pass

        # Содержимое
        main_fr = tk.Frame(self, bg=COLORS["bg_main"], padx=20, pady=20)
        main_fr.pack(fill='both', expand=True)

        if hasattr(parent, 'main_icon_img') and parent.main_icon_img:
            tk.Label(main_fr, image=parent.main_icon_img, bg=COLORS["bg_main"]).pack(side='left', anchor='n',
                                                                                     padx=(0, 20))

        right_fr = tk.Frame(main_fr, bg=COLORS["bg_main"])
        right_fr.pack(side='left', fill='both', expand=True)

        tk.Label(right_fr, text=message, font=FONT_MAIN, bg=COLORS["bg_main"], fg=COLORS["fg_text"],
                 wraplength=300, justify='left').pack(fill='x', expand=True, anchor='w')

        btns_fr = tk.Frame(right_fr, bg=COLORS["bg_main"])
        btns_fr.pack(fill='x', side='bottom', pady=(10, 0))

        if dialog_type == 'confirm':
            btns_fr.columnconfigure((0, 1), weight=1)
            ok_btn = tk.Button(btns_fr, text="ПОДТВЕРДИТЬ", font=FONT_HEAD, bg=COLORS["accent"], fg="white",
                               relief='flat', command=self._ok, activebackground='#a00000', activeforeground='white',
                               borderwidth=0, height=2)
            ok_btn.grid(row=0, column=0, sticky='ew', padx=(0, 5))
            cancel_btn = tk.Button(btns_fr, text="ОТМЕНА", font=FONT_HEAD, bg=COLORS["btn"], fg=COLORS["fg_text"],
                                   relief='flat', command=self._cancel, activebackground=COLORS["btn_h"],
                                   activeforeground=COLORS["fg_text"], borderwidth=0, height=2)
            cancel_btn.grid(row=0, column=1, sticky='ew')
        else:  # dialog_type == 'info'
            btns_fr.columnconfigure(0, weight=1)
            info_btn = tk.Button(btns_fr, text="OK", font=FONT_HEAD, bg=COLORS["btn"], fg=COLORS["fg_text"],
                                 relief='flat', command=self._cancel, activebackground=COLORS["btn_h"],
                                 activeforeground=COLORS["fg_text"], borderwidth=0, height=2)
            info_btn.grid(row=0, column=0, sticky='ew')

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.grab_set()
        self.deiconify()
        self.wait_window()

    def _ok(self):
        self.result = True;
        self.destroy()

    def _cancel(self):
        self.result = False;
        self.destroy()


# --- ПРОВЕРКА ЗАВИСИМОСТЕЙ ---
try:
    from PIL import Image, ImageTk
    from tinytag import TinyTag
    from moviepy.editor import VideoFileClip, AudioFileClip
except ImportError as e:
    # Создаем временное рут-окно, чтобы показать кастомный диалог
    root = tk.Tk()
    root.withdraw()
    ConcreteDialog(root, "ОШИБКА", f"ОТСУТСТВУЕТ МОДУЛЬ: {e.name}\nВыполните: pip install {e.name}", dialog_type='info')
    root.destroy()
    sys.exit()


# --- ЯДРО DB ---
class CoreDB:
    def __init__(self, db_name="concrete_data.db"):
        self.lock = threading.Lock()
        with self.lock:
            self.conn = sqlite3.connect(db_name, check_same_thread=False)
            self.cursor = self.conn.cursor()
            self.cursor.execute(
                'CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, file TEXT, op TEXT, status TEXT, time DATETIME DEFAULT CURRENT_TIMESTAMP)')
            self.cursor.execute(
                'CREATE TABLE IF NOT EXISTS index_files(id INTEGER PRIMARY KEY, path TEXT UNIQUE, name TEXT, size TEXT, fmt TEXT, accessed DATETIME DEFAULT CURRENT_TIMESTAMP)')
            self.conn.commit()

    def log(self, file, op, status):
        with self.lock:
            self.cursor.execute('INSERT INTO history (file, op, status) VALUES (?, ?, ?)',
                                (file, op, status))
            self.conn.commit()

    def index(self, path, name, size, fmt):
        with self.lock:
            try:
                self.cursor.execute(
                    'INSERT OR IGNORE INTO index_files (path, name, size, fmt, accessed) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)',
                    (path, name, size, fmt))
                self.cursor.execute('UPDATE index_files SET accessed = CURRENT_TIMESTAMP, size = ?, fmt = ? WHERE path = ?',
                                    (size, fmt, path))
                self.conn.commit()
            except Exception:
                pass

    def clear_h(self):
        with self.lock:
            self.cursor.execute('DELETE FROM history')
            self.conn.commit()

    def clear_i(self):
        with self.lock:
            self.cursor.execute('DELETE FROM index_files')
            self.conn.commit()

    def get_h(self):
        with self.lock:
            return self.cursor.execute('SELECT * FROM history ORDER BY id DESC LIMIT 100').fetchall()

    def get_i(self, q=""):
        with self.lock:
            if q: return self.cursor.execute(
                'SELECT * FROM index_files WHERE name LIKE ? OR path LIKE ? ORDER BY accessed DESC',
                (f"%{q}%", f"%{q}%")).fetchall()
            return self.cursor.execute('SELECT * FROM index_files ORDER BY accessed DESC LIMIT 500').fetchall()

    def close(self):
        with self.lock:
            if self.conn:
                self.conn.close()


# --- ПРОЦЕССОР ---
class Processor:
    @staticmethod
    def scan(path):
        data = {"ФАЙЛ": os.path.basename(path)}
        try:
            st = os.stat(path)
            data["ОБЪЕМ"] = f"{st.st_size / (1024 * 1024):.2f} MB"
            ext = os.path.splitext(path)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.ico', '.gif']:
                with Image.open(path) as img:
                    data["ТИП"] = "ИЗОБРАЖЕНИЕ"
                    data["МАТРИЦА"] = f"{img.width}x{img.height}"
            elif ext in ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.mp4', '.avi', '.mkv', '.webm']:
                tag = TinyTag.get(path)
                data["ТИП"] = "МЕДИА-ПОТОК"
                data["ХРОНО"] = f"{tag.duration:.1f} сек" if tag.duration else "N/A"
            else:
                data["ТИП"] = "НЕИЗВЕСТНО"
        except Exception:
            data["ОШИБКА"] = "Доступ ограничен"
        return data

    @staticmethod
    def get_preview_image(path):
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.ico', '.gif']:
                with Image.open(path) as img:
                    img.load()
                    img.thumbnail((450, 450), Image.Resampling.LANCZOS)
                    return img
            elif ext in ['.mp4', '.avi', '.mkv', '.webm']:
                with VideoFileClip(path) as clip:
                    frame_array = clip.get_frame(1 if clip.duration > 1 else 0)
                    img = Image.fromarray(frame_array)
                    img.thumbnail((450, 450), Image.Resampling.LANCZOS)
                    return img
            return None
        except Exception:
            return None

    @staticmethod
    def get_preview(path):
        # Оставляем этот метод для обратной совместимости, но теперь он использует get_preview_image
        img = Processor.get_preview_image(path)
        if img:
            try:
                return ImageTk.PhotoImage(img)
            except Exception:
                return None
        return None

    @staticmethod
    def convert(path, target):
        try:
            base, ext = os.path.splitext(path)
            out = f"{base}_c.{target.lower()}"
            tgt, ext = target.upper(), ext.lower()
            if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.ico'] and tgt in ['JPG', 'JPEG', 'PNG', 'BMP',
                                                                                     'WEBP', 'ICO']:
                with Image.open(path) as img:
                    if tgt in ['JPEG', 'JPG'] and img.mode in ('RGBA', 'P'): img = img.convert('RGB')
                    img.save(out, tgt)
                return True, out
            elif ext in ['.mp4', '.avi', '.mkv', '.webm', '.gif', '.mp3', '.wav', '.ogg', '.flac']:
                clip = VideoFileClip(path) if ext in ['.mp4', '.avi', '.mkv', '.webm', '.gif'] else AudioFileClip(path)
                try:
                    if tgt == 'MP4':
                        clip.write_videofile(out, codec='libx264', audio_codec='aac', verbose=False, logger=None)
                    elif tgt == 'AVI':
                        clip.write_videofile(out, codec='png', verbose=False, logger=None)
                    elif tgt == 'WEBM':
                        clip.write_videofile(out, codec='libvpx', verbose=False, logger=None)
                    elif tgt == 'GIF':
                        clip.write_gif(out, fps=10, verbose=False, logger=None)
                    elif tgt == 'MP3':
                        (clip.audio if hasattr(clip, 'audio') else clip).write_audiofile(out, verbose=False, logger=None)
                    elif tgt == 'WAV':
                        (clip.audio if hasattr(clip, 'audio') else clip).write_audiofile(out, verbose=False, logger=None)
                    else:
                        return False, "Формат не поддерживается"
                    return True, out
                finally:
                    clip.close()
            return False, "Сбой формата"
        except Exception as e:
            return False, str(e)


# --- ПРИЛОЖЕНИЕ ---
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CONCRETE")
        self.geometry("1100x750")
        self.configure(bg=COLORS["bg_main"])
        self.current_preview_path = None

        self._setup_icon()
        try:
            self.update()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(2)), 4)
        except:
            pass

        self.db = CoreDB()
        self.queue = []
        self._styles()
        self._ui()
        self.refresh()
        self.protocol("WM_DELETE_WINDOW", self.quit)

    def _setup_icon(self):
        self.main_icon_img = None
        try:
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base_path, "icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
                with Image.open(icon_path) as img:
                    resized_img = img.resize((48, 48), Image.Resampling.LANCZOS)
                    self.main_icon_img = ImageTk.PhotoImage(resized_img)
        except Exception as e:
            print(f"Ошибка при загрузке icon.ico: {e}")

    def _styles(self):
        self.option_add('*TCombobox*Listbox.background', COLORS["bg_sec"])
        self.option_add('*TCombobox*Listbox.foreground', COLORS["fg_text"])
        self.option_add('*TCombobox*Listbox.selectBackground', COLORS["accent"])
        self.option_add('*TCombobox*Listbox.borderWidth', '0')
        self.option_add('*TCombobox*Listbox.relief', 'flat')
        self.option_add('*TCombobox*Listbox.highlightThickness', '0')

        s = ttk.Style()
        s.theme_use('clam')
        s.configure(".", background=COLORS["bg_main"], foreground=COLORS["fg_text"], borderwidth=0, font=FONT_MAIN)
        s.configure("TFrame", background=COLORS["bg_main"])
        s.configure("Tab.TButton", background=COLORS["bg_main"], foreground=COLORS["fg_dim"], relief='flat',
                    font=FONT_HEAD)
        s.map("Tab.TButton", background=[("active", COLORS["btn_h"])])
        s.configure("ActiveTab.TButton", background=COLORS["bg_sec"], foreground=COLORS["accent"], relief='flat',
                    font=FONT_HEAD)
        s.configure("TButton", background=COLORS["btn"], foreground=COLORS["fg_text"], borderwidth=0)
        s.map("TButton", background=[("active", COLORS["btn_h"])])

        s.configure("TLabelframe", background=COLORS["bg_main"], bordercolor=COLORS["fg_dim"], borderwidth=1,
                    relief="solid")
        s.configure("TLabelframe.Label", background=COLORS["bg_main"], foreground=COLORS["fg_dim"], font=FONT_HEAD)
        s.configure("Treeview", background=COLORS["bg_sec"], fieldbackground=COLORS["bg_sec"],
                    foreground=COLORS["fg_text"], borderwidth=0)
        s.configure("Treeview.Heading", background=COLORS["btn"], foreground=COLORS["fg_text"], relief='flat')
        s.map("Treeview", background=[("selected", COLORS["accent"])])

        s.configure("TCombobox", fieldbackground=COLORS["bg_sec"], background=COLORS["btn"],
                    foreground=COLORS["fg_text"], arrowcolor=COLORS["fg_text"])
        s.map('TCombobox', fieldbackground=[('readonly', COLORS["bg_sec"])])
        s.configure("Horizontal.TProgressbar", troughcolor=COLORS["bg_sec"], background=COLORS["accent"],
                    bordercolor=COLORS["bg_main"])

    def _ui(self):
        self.bar_fr = tk.Frame(self, bg=COLORS["bg_main"]);
        self.bar_fr.pack(fill='x', pady=5)
        self.btns_fr = tk.Frame(self.bar_fr, bg=COLORS["bg_main"]);
        self.btns_fr.pack()
        self.container = tk.Frame(self, bg=COLORS["bg_sec"]);
        self.container.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        self.pages = {}
        self.tabs = {}
        for name in ['ПРОЦЕСС', 'ИНДЕКС', 'ЖУРНАЛ', 'СИСТЕМА']:
            p = tk.Frame(self.container, bg=COLORS["bg_sec"]);
            p.grid(row=0, column=0, sticky='nsew')
            self.pages[name] = p
            btn = ttk.Button(self.btns_fr, text=name, style="Tab.TButton", command=lambda n=name: self.show_p(n))
            btn.pack(side='left', padx=2)
            self.tabs[name] = btn

        self.container.grid_rowconfigure(0, weight=1);
        self.container.grid_columnconfigure(0, weight=1)
        self._ui_process(self.pages['ПРОЦЕСС']);
        self._ui_index(self.pages['ИНДЕКС']);
        self._ui_history(self.pages['ЖУРНАЛ']);
        self._ui_help(self.pages['СИСТЕМА'])
        self.show_p('ПРОЦЕСС')

    def show_p(self, name):
        self.pages[name].tkraise()
        for k, v in self.tabs.items(): v.config(style="ActiveTab.TButton" if k == name else "Tab.TButton")

    def _ui_process(self, p):
        p.columnconfigure(1, weight=1);
        p.rowconfigure(0, weight=1)
        lt = tk.Frame(p, bg=COLORS["bg_sec"], padx=10, pady=10);
        lt.grid(row=0, column=0, sticky='nswe')

        f_l = ttk.LabelFrame(lt, text="ЗАГРУЗКА");
        f_l.pack(fill='both', expand=True, pady=(0, 10))
        ttk.Button(f_l, text="+ ДОБАВИТЬ В ОЧЕРЕДЬ", command=self.add_f).pack(fill='x', padx=5, pady=5)
        self.lst = tk.Listbox(f_l, bg=COLORS["bg_main"], fg=COLORS["fg_text"], bd=0, highlightthickness=0,
                              selectbackground=COLORS["accent"])
        self.lst.pack(fill='both', expand=True, padx=5, pady=5);
        self.lst.bind('<<ListboxSelect>>', self.on_sel)

        m_l = ttk.LabelFrame(lt, text="МЕТАДАННЫЕ");
        m_l.pack(fill='both', expand=True, pady=(0, 10))
        self.txt = tk.Text(m_l, height=10, bg=COLORS["bg_main"], fg=COLORS["fg_dim"], bd=0, font=FONT_MAIN,
                           state='disabled')
        self.txt.pack(fill='both', expand=True, padx=5, pady=5)

        a_l = ttk.LabelFrame(lt, text="ОПЕРАЦИИ");
        a_l.pack(fill='x')
        self.fmt = ttk.Combobox(a_l, values=["PNG", "JPEG", "WEBP", "MP4", "AVI", "GIF", "MP3", "WAV"],
                                state="readonly")
        self.fmt.set("PNG");
        self.fmt.pack(fill='x', padx=5, pady=5)
        self.b_run = ttk.Button(a_l, text="ЗАПУСК ПРОЦЕССА", command=self.run_c);
        self.b_run.pack(fill='x', padx=5, pady=5)
        self.pbar = ttk.Progressbar(a_l, style="Horizontal.TProgressbar", mode='indeterminate');
        self.pbar.pack(fill='x', padx=5, pady=(0, 5))

        rt = ttk.LabelFrame(p, text="ВИЗУАЛИЗАТОР");
        rt.grid(row=0, column=1, sticky='nswe', padx=10, pady=10)
        self.p_img = tk.Label(rt, text="[ НЕТ СИГНАЛА ]", bg=COLORS["bg_sec"], fg=COLORS["fg_dim"], font=FONT_HEAD)
        self.p_img.pack(fill='both', expand=True)

    def _ui_index(self, p):
        top = tk.Frame(p, bg=COLORS["bg_sec"], padx=10, pady=10);
        top.pack(fill='x')
        self.s_ent = tk.Entry(top, bg=COLORS["bg_main"], fg=COLORS["fg_text"], bd=0, insertbackground="white",
                              font=FONT_MAIN)
        self.s_ent.pack(side='left', fill='x', expand=True, padx=(0, 5))
        ttk.Button(top, text="ПОИСК", width=10, command=self.refresh).pack(side='right')

        self.tv_i = ttk.Treeview(p, columns=('path', 'name', 'size', 'fmt', 'date'), show='headings')
        for c, t in zip(['path', 'name', 'size', 'fmt', 'date'],
                        ['ПУТЬ', 'ФАЙЛ', 'ОБЪЕМ', 'ТИП', 'ДОСТУП']): self.tv_i.heading(c, text=t)
        self.tv_i.pack(fill='both', expand=True, padx=10)
        tk.Button(p, text="!! УНИЧТОЖИТЬ ИНДЕКС !!", bg=COLORS["accent"], fg="white", font=FONT_HEAD, relief='flat',
                  command=self.del_i, activebackground='#a00000').pack(fill='x', padx=10, pady=10)

    def _ui_history(self, p):
        self.tv_h = ttk.Treeview(p, columns=('t', 'f', 'o', 's'), show='headings')
        for c, t in zip(['t', 'f', 'o', 's'], ['ВРЕМЯ', 'ФАЙЛ', 'ОПЕРАЦИЯ', 'СТАТУС']): self.tv_h.heading(c, text=t)
        self.tv_h.pack(fill='both', expand=True, padx=10, pady=10)
        tk.Button(p, text="!! СТЕРЕТЬ ЖУРНАЛ !!", bg=COLORS["accent"], fg="white", font=FONT_HEAD, relief='flat',
                  command=self.del_h, activebackground='#a00000').pack(fill='x', padx=10, pady=10)

    def _ui_help(self, p):
        t = tk.Text(p, bg=COLORS["bg_sec"], fg=COLORS["fg_text"], bd=0, font=FONT_MAIN, padx=20, pady=20, wrap='word')
        t.pack(fill='both', expand=True)
        doc = """Руководство по работе с программой CONCRETE

Данное приложение предназначено для конвертации медиафайлов, а также для ведения истории операций и индексации обработанных файлов.


1. КОНВЕРТАЦИЯ ФАЙЛОВ (ВКЛАДКА ПРОЦЕСС)

   Для начала работы выполните следующие шаги:

   1.1. Нажмите кнопку + ДОБАВИТЬ В ОЧЕРЕДЬ, чтобы выбрать один или несколько файлов для обработки.

   1.2. Выберите файл в списке ЗАГРУЗКА. В блоке МЕТАДАННЫЕ отобразится подробная информация о файле.

   1.3. В блоке ОПЕРАЦИИ выберите конечный формат для конвертации из выпадающего списка.

   1.4. Нажмите ЗАПУСК ПРОЦЕССА. Конвертированный файл будет сохранен в той же директории, что и исходный, с постфиксом _c.


2. ИНДЕКС ФАЙЛОВ (ВКЛАДКА ИНДЕКС)

   На этой вкладке отображается база данных всех файлов, которые когда-либо открывались или были созданы в программе. Используйте поле ПОИСК для быстрой фильтрации списка.


3. ЖУРНАЛ ОПЕРАЦИЙ (ВКЛАДКА ЖУРНАЛ)

   Здесь хранится история всех выполненных операций конвертации с указанием статуса (успех или ошибка), времени и имени файла.


4. ПОДДЕРЖИВАЕМЫЕ ФОРМАТЫ

   - Изображения: JPG, PNG, WEBP, BMP, ICO
   - Видео: MP4, AVI, WEBM, GIF
   - Аудио: MP3, WAV
   - Извлечение аудио из видео: Видеофайл -> MP3"""
        t.insert('1.0', doc);
        t.config(state='disabled')

    def add_f(self):
        fs = filedialog.askopenfilenames()
        if fs:
            self.queue = list(fs);
            self.lst.delete(0, tk.END)
            for f in fs:
                self.lst.insert(tk.END, os.path.basename(f))
                d = Processor.scan(f);
                self.db.index(f, d.get("ФАЙЛ"), d.get("ОБЪЕМ"), d.get("ТИП"))
            if self.queue:
                self.lst.selection_set(0);
                self.on_sel(None)
            self.db.log(f"ПАКЕТ_{len(fs)}", "ЗАГРУЗКА", "OK");
            self.refresh()

    def on_sel(self, e):
        try:
            selection = self.lst.curselection()
            if not selection:
                return
            path = self.queue[selection[0]]
            self.current_preview_path = path

            # Быстрое сканирование метаданных
            d = Processor.scan(path)
            self.txt.config(state='normal')
            self.txt.delete('1.0', tk.END)
            for k, v in d.items(): 
                self.txt.insert(tk.END, f"{k}: {v}\n")
            self.txt.config(state='disabled')

            # Устанавливаем статус загрузки превью
            self.p_img.config(image="", text="[ ЗАГРУЗКА ПРЕВЬЮ... ]")

            # Запускаем фоновую генерацию превью
            threading.Thread(target=self._load_preview_async, args=(path,), daemon=True).start()
        except Exception:
            pass

    def _load_preview_async(self, path):
        # Генерируем изображение в фоновом потоке
        img = Processor.get_preview_image(path)
        # Передаем результат в главный поток через self.after
        self.after(0, lambda: self._update_preview_gui(path, img))

    def _update_preview_gui(self, path, img):
        # Проверяем, что текущий выбранный файл все еще совпадает с обрабатываемым
        if self.current_preview_path == path:
            if img:
                try:
                    self.img_ref = ImageTk.PhotoImage(img)
                    self.p_img.config(image=self.img_ref, text="")
                except Exception:
                    self.img_ref = None
                    self.p_img.config(image="", text="[ ОШИБКА ПРЕДПРОСМОТРА ]")
            else:
                self.img_ref = None
                self.p_img.config(image="", text="[ НЕТ СИГНАЛА ]")

    def run_c(self):
        if not self.queue: return
        self.b_run.config(state='disabled', text="ОБРАБОТКА...");
        self.pbar.start(10)
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self):
        tgt, errs = self.fmt.get(), []
        for f in self.queue:
            ok, msg = Processor.convert(f, tgt)
            self.db.log(os.path.basename(f), f"В->{tgt}", "OK" if ok else "ОШИБКА")
            if not ok:
                errs.append(msg)
            elif os.path.exists(msg):
                d = Processor.scan(msg);
                self.db.index(msg, d.get("ФАЙЛ"), d.get("ОБЪЕМ"), d.get("ТИП"))
        self.after(0, lambda: self._done(errs))

    def _done(self, errs):
        self.pbar.stop();
        self.b_run.config(state='normal', text="ЗАПУСК ПРОЦЕССА");
        self.refresh()
        if errs:
            msg = f"ОБНАРУЖЕНЫ ОШИБКИ: {len(errs)}.\n\nПЕРВАЯ ОШИБКА:\n{errs[0]}"
            ConcreteDialog(self, "ОШИБКИ ВЫПОЛНЕНИЯ", msg, dialog_type='info')
        else:
            ConcreteDialog(self, "СИСТЕМА", "ЗАВЕРШЕНО УСПЕШНО", dialog_type='info')

    def refresh(self):
        try:
            q = self.s_ent.get()
            [self.tv_i.delete(i) for i in self.tv_i.get_children()]
            for r in self.db.get_i(q): self.tv_i.insert('', 'end', values=(r[1], r[2], r[3], r[4], r[5]))

            [self.tv_h.delete(i) for i in self.tv_h.get_children()]
            for r in self.db.get_h(): self.tv_h.insert('', 'end', values=(r[4], r[1], r[2], r[3]))
        except Exception:
            pass

    def del_i(self):
        if ConcreteDialog(self, "ВНИМАНИЕ", "УНИЧТОЖИТЬ ВЕСЬ ИНДЕКС?\n\nЭТО ДЕЙСТВИЕ НЕОБРАТИМО.").result:
            self.db.clear_i();
            self.refresh()

    def del_h(self):
        if ConcreteDialog(self, "ВНИМАНИЕ", "ОЧИСТИТЬ ЖУРНАЛ СОБЫТИЙ?").result:
            self.db.clear_h();
            self.refresh()

    def quit(self):
        try:
            self.db.close()
        except Exception as e:
            print(f"Ошибка при закрытии БД: {e}")
        finally:
            self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()