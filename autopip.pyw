#!python3

import ctypes, sys

def is_admin():
	try:
		return ctypes.windll.shell32.IsUserAnAdmin()
	except:
		return False

if not is_admin():
	ctypes.windll.shell32.ShellExecuteW(None, 'runas', sys.executable, __file__, None, 1)
	sys.exit(1)

try:
	import tkinter as tk
	from tkinter import ttk, messagebox, filedialog
	from tkinter import scrolledtext
	from threading import Thread
except ImportError:
	import Tkinter as tk
	import ttk
	import tkMessageBox as messagebox
	import tkFileDialog as filedialog
	import ScrolledText as scrolledtext
	from threading import Thread

try:
	import winreg
except ImportError:
	winreg = None
	
import os
import subprocess

startupinfo = subprocess.STARTUPINFO()
startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW # to hide the console

procargs = {"stdout":subprocess.PIPE, "stderr":subprocess.PIPE, "startupinfo":startupinfo, "bufsize":0,} # pipe output, hide console and unbuffered

appfont = ("ariel",14)

class PythonInstalls():
	def __init__(self):
		self.installs = {}
		self.selected = None
		
	def __search_key(self, key):
		subkeys, values, lastmod = winreg.QueryInfoKey(key)

		for i in range(0, subkeys):
			ver = winreg.EnumKey(key, i)
			subkey = winreg.OpenKey(key, '%s' % ver)
			self.installs[ver] = winreg.QueryValue(subkey, 'InstallPath')
		
	def __search_keys(self):
		for key in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
			for path in ['SOFTWARE\\Python\\PythonCore', 'SOFTWARE\\Wow6432Node\\Python\\PythonCore']:
				try:
					k = winreg.OpenKey(key, path)
					self.__search_key(k)
				except FileNotFoundError:
					pass
			
	def find(self):
		if winreg:
			self.__search_keys()
		else: # assume both are present, let user decide
			self.installs = {'2':'python2', '3':'python3'}
		res = list(self.installs.keys())
		res.sort()
		return res
		
	def select(self, version):
		self.selected = version
	
	def path(self, version=None):
		if version == None:
			version = self.selected
		if version in self.installs:
			return self.installs[version]
		if len(version) > 7:
			return self.installs[version[7:]]
			
	def scriptspath(self, version=None):
		if version == None:
			version = self.selected
		p = self.path(version)
		if winreg:
			if p:
				return os.path.join(p, 'Scripts')
		else: # TO DO
			pass
			
	def pip(self, version=None):
		if version == None:
			version = self.selected
		if winreg:
			return os.path.join(self.scriptspath(version), 'pip')
		else: # assume only one ver of each major version
			if sys.version_info[0] == 3:
				return 'pip3'
			else:
				return 'pip'
			
	def python(self, version=None):
		if version == None:
			version = self.selected
		if winreg:
			return os.path.join(self.path(version), 'python')
		else: # assume only one ver of each major version
			if sys.version_info[0] == 3:
				return 'python3'
			else:
				return 'python2'

class HyperlinkManager(object):
    """A class to easily add clickable hyperlinks to Text areas.
    Usage:
      callback = lambda : webbrowser.open("http://www.google.com/")
      text = tk.Text(...)
      hyperman = tkHyperlinkManager.HyperlinkManager(text)
      text.insert(tk.INSERT, "click me", hyperman.add(callback))
    From http://effbot.org/zone/tkinter-text-hyperlink.htm
    """
    def __init__(self, text):
        self.text = text
        self.text.tag_config("hyper", foreground="blue", underline=1)
        self.text.tag_bind("hyper", "<Enter>", self._enter)
        self.text.tag_bind("hyper", "<Leave>", self._leave)
        self.text.tag_bind("hyper", "<Button-1>", self._click)
        self.reset()

    def reset(self):
        self.links = {}

    def add(self, action):
        """Adds an action to the manager.
        :param action: A func to call.
        :return: A clickable tag to use in the text widget.
        """
        tag = "hyper-%d" % len(self.links)
        self.links[tag] = action
        return ("hyper", tag)

    def _enter(self, event):
        self.text.config(cursor="hand2")

    def _leave(self, event):
        self.text.config(cursor="")

    def _click(self, event):
        for tag in self.text.tag_names(tk.CURRENT):
            if (tag[:6] == "hyper-"):
                self.links[tag]()
                return

SCAN = 1
UPDATE_PIP = 2
UPDATE_ALL = 3
UPDATE = 4
SEARCH = 5
INSTALL = 6

class Updater(tk.Tk):
	def __init__(self):
		tk.Tk.__init__(self)
		self.title("Pip auto updater")
		self.style = ttk.Style()
		self.style.configure('.', font=appfont)
		
		tk.Label(self, text="Python version:").grid(column=1, row=1, sticky="nesw")
		self.verbox = ttk.Combobox(self)
		self.verbox.grid(column=2, row=1, sticky="nesw")
		self.verbox.bind("<<ComboboxSelected>>", self.select_version)
		
		tk.Label(self, text="Exclusions:").grid(column=1, row=2, sticky="nesw")
		self.excl_list = tk.Listbox(self)
		self.excl_list.grid(column=1, row=3, sticky="nesw")
		
		tk.Label(self, text="Outdated:").grid(column=2, row=2, sticky="nesw")
		self.pkglist = tk.Listbox(self)
		self.pkglist.grid(column=2, row=3, sticky="nesw")

		self.output = scrolledtext.ScrolledText(self, state="disabled")
		self.output.tag_config("output", foreground="blue")
		self.output.tag_config("stderr", foreground="red")
		self.output.grid(column=3, row=3, columnspan=2, sticky="nesw")
		
		self.link_man = HyperlinkManager(self.output)

		self.grid_rowconfigure(3, weight=1)
		self.grid_columnconfigure(1, weight=1)
		self.grid_columnconfigure(2, weight=1)
		self.grid_columnconfigure(3, weight=5)
		self.grid_columnconfigure(4, weight=5)
		
		f = tk.Frame(self)
		f.grid(column=1, row=4, columnspan=2, rowspan=2, sticky="nesw")
		f.grid_columnconfigure(1, weight=1)
		self.search_box = ttk.Entry(f, font=appfont)
		self.search_box.bind("<Return>", self.search)
		self.search_box.grid(column=1, row=1, sticky="nesw")
		self.b4 = ttk.Button(f, text="Search", command=self.search, width=6)
		self.b4.grid(column=2, row=1, sticky="nesw")
		
		self.b5 = ttk.Button(f, text="Install from wheel file", command=self.install_wheel)
		self.b5.grid(column=1, row=2, columnspan=2, sticky="nesw")

		self.b1 = ttk.Button(self, text="Scan", command=self.scan)
		self.b1.grid(column=3, row=4, columnspan=2, sticky="nesw")
		
		self.b2 = ttk.Button(self, text="Update Pip", command=self.update_pip)
		self.b2.grid(column=3, row=5, sticky="nesw")
		self.b3 = ttk.Button(self, text="Update All", command=self.update_all)
		self.b3.grid(column=4, row=5, sticky="nesw")
		
		# popups for managing exclusions
		self.popup_add = tk.Menu(self.pkglist, tearoff=0)
		self.popup_add.add_command(label="add to exclusion list", command=self.add_exclusion)
		self.popup_remove = tk.Menu(self.pkglist, tearoff=0)
		self.popup_remove.add_command(label="remove from exclusion list", command=self.remove_exclusion)
		self.pkglist.bind("<Button-3>", self.show_popup_add)
		self.excl_list.bind("<Button-3>", self.show_popup_remove)
		
		# load any exclusions that shouldn't be updated
		self.exclusions_changed = False
		if os.path.isfile("pip_exclusions.txt"):
			with open("pip_exclusions.txt", mode="r") as exfile:
				for line in exfile.readlines():
					ex = line.rstrip()
					if ex != '':
						self.excl_list.insert("end", ex)

		self.process = None
		self.thread = None
		self.func = None
		
		self.installs = PythonInstalls()
		self.find_versions()
		try:
			self.verbox.current(0) # select first install by default
			self.select_version()
		except tk.TclError:
			messagebox.showerror("Error", "Unable to locate any python installations", parent=self)
		
	def find_versions(self):
		versions = self.installs.find()
		named_versions = []
		for ver in versions:
			version = "Python %s" % ver
			named_versions.append(version)
		self.verbox.configure(values=named_versions, state="readonly")
		
	def select_version(self, event=None):
		i = self.verbox.current()
		if i != -1: # if there is a selection
			self.version = self.verbox.get()
			self.title("Pip auto updater - %s" % self.version)
			self.installs.select(self.version)
			pypath = self.installs.path()
			if not pypath:
				messagebox.showerror("Error", "%s cannot be found" % self.version, parent=self)
				return
		else:
			self.title("Pip auto updater")
		
	def show_popup_add(self, event): # for managing exclusions
		self.pkglist.select_clear(0,"end") #clear selection
		self.pkglist.select_set(self.pkglist.nearest(event.y)) # highlight right clicked item
		self.popup_add.post(event.x_root, event.y_root) # show menu
		
	def show_popup_remove(self, event): # for managing exclusions
		self.excl_list.select_clear(0,"end") #clear selection
		self.excl_list.select_set(self.excl_list.nearest(event.y)) # highlight right clicked item
		self.popup_remove.post(event.x_root, event.y_root) # show menu
		
	def add_exclusion(self):
		selection = self.pkglist.curselection()
		if len(selection) > 0:
			pkg = self.pkglist.get(selection[0])
			if pkg not in self.excl_list.get(0, "end"):
				self.excl_list.insert("end", pkg)
				self.exclusions_changed = True
		
	def remove_exclusion(self):
		selection = self.excl_list.curselection()
		if len(selection) > 0:
			self.excl_list.delete(selection)
			self.exclusions_changed = True
			
	def save_exclusions(self):
		exclusions = list(self.excl_list.get(0, "end"))
		if (len(exclusions) > 0) or self.exclusions_changed: # only save if there are exclusions or changes made
			with open("pip_exclusions.txt", mode="w") as ex_file:
				exclusions.sort()
				for item in exclusions:
					ex_file.write("%s\n" % item)

	def disable_all(self):
		for control in [self.verbox, self.b1, self.b2, self.b3, self.b4, self.b5, self.search_box]:
			control.configure(state='disabled')

	def enable_all(self):
		self.verbox.configure(state='readonly')
		for control in [self.b1, self.b2, self.b3, self.b4, self.b5, self.search_box]:
			control.configure(state='normal')

	def log(self, msg, tag=None):
		self.output.configure(state="normal")
		self.output.insert("end", msg, tag)
		self.output.see("end")
		self.output.configure(state="disabled")

	def start_poll(self):
		self.disable_all()
		self.thread = Thread(target=self.poll)
		self.thread.daemon = True
		self.thread.start()
		
	def poll(self):
		line = ''
		while True:
			data = self.process.stdout.read(1)
			try:
				output = data.decode('utf8')
				if output != '':
					output = output.replace('\r', '')
					if self.func[0] == SCAN:
						if output == '\n':
							pkgname, description = line.split(' ', 1)
							if (len(pkgname) > 0) and (pkgname != 'Package') and (pkgname.replace('-','') != ''):
								self.pkglist.insert("end", pkgname) # add to package list
								tag = self.link_man.add(lambda p=pkgname: self.update(p))
							else:
								tag = 'output'
							self.log(pkgname, tag)
							self.log(' %s\n' % description, 'output')
							line = ''
						else:
							line += output
					elif self.func[0] == SEARCH:
						if output == '\n':
							pkgname, description = line.split(' ', 1)
							self.log(pkgname, self.link_man.add(lambda p=pkgname: self.install(p)))
							self.log(' %s\n' % description, 'output')
							line = ''
						else:
							line += output
					else:
						self.log(output, 'output')
				else:
					if self.process.poll() != None:
						break
			except:
				print(data)
		while True:
			data = self.process.stderr.read(1)
			try:
				output = data.decode('utf8')
				if output != '':
					output = output.replace('\r', '')
					self.log(output, 'stderr')
				else:
					break
			except:
				pass

		if self.process.poll() == 0:
			if self.func[0] == UPDATE_ALL or self.func[0] == UPDATE:
				for num in range(0, self.pkglist.size()):
					if self.pkglist.get(num) == self.func[1]:
						self.pkglist.delete(num)
						break
			if self.func[0] == UPDATE_ALL:
				self.after(10, self.update_all)

		self.func = None
		self.enable_all()
		
	def run_command(self, command, func):
		if not self.func:
			self.log(">%s\n" % command)
			self.process = subprocess.Popen(command, cwd=self.installs.path(), **procargs)
			self.func = func
			self.start_poll()
		else: # shouldn't happen, but cover it anyway
			messagebox.showinfo("Wait", "Must wait for previous command to finish before running new one", parent=self)
		
	def search(self, event=None):
		val = self.search_box.get()
		if val.strip() != '':
			self.run_command("%s search %s" % (self.installs.pip(), val), [SEARCH, None])
		else:
			messagebox.showinfo("Error", "No package to search for", parent=self)
			
	def install(self, package):
		result = messagebox.askyesno("Install?", "Install package: %s" % package, parent=self)
		if result:
			self.run_command("%s install %s" % (self.installs.pip(), package), [INSTALL, None])
				
	def install_wheel(self):
		res = filedialog.askopenfilename(filetypes=(('Wheel files', '*.whl'),), parent=self, title="Select wheel")
		if res:
			self.install("\"%s\"" % res) # add quotes in case spaces in path

	def scan(self):
		self.run_command("%s list --outdated --format=columns" % self.installs.pip(), [SCAN, None])
		self.pkglist.delete(0,"end")

	def update_pip(self):
		self.run_command("%s -m pip install --upgrade pip" % self.installs.python(), [UPDATE_PIP, 'pip'])
		for num in range(0, self.pkglist.size()):
			if self.pkglist.get(num) == "pip":
				self.pkglist.delete(num)
				break

	def update_all(self):
		if "pip" in self.pkglist.get(0,"end"):
			if messagebox.askyesno("Update pip?", "Pip is out of date.\nUpdate this now?", parent=self):
				self.update_pip()
			return
		if self.pkglist.size() == 0:
			return
		i = 0
		while True:
			pkg = self.pkglist.get(i)
			if pkg == "pip":
				i += 1
			elif pkg in self.excl_list.get(0, "end"):
				self.log(">Skipping %s\n" % pkg)
				self.pkglist.delete(i)
			elif i >= self.pkglist.size():
				return
			else:
				break
		self.run_command("%s install %s --upgrade" % (self.installs.pip(), pkg), [UPDATE_ALL, pkg])
			
	def update(self, package):
		result = messagebox.askyesno("Update?", "Update package: %s" % package, parent=self)
		if result:
			self.run_command("%s install %s --upgrade" % (self.installs.pip(), package), [UPDATE, package])

	def destroy(self):
		self.save_exclusions()
		tk.Tk.destroy(self)

if __name__ == "__main__":
	updater = Updater()
	updater.mainloop()
