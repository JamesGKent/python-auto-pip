#!python3

try:
	import tkinter as tk
	from tkinter import ttk, messagebox
	from tkinter import scrolledtext
	from threading import Thread
except ImportError:
	import Tkinter as tk
	import ttk
	import tkMessageBox as messagebox
	import ScrolledText as scrolledtext
	from threading import Thread
	
import sys, os
import subprocess

startupinfo = subprocess.STARTUPINFO()
startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW # to hide the console

procargs = {"stdout":subprocess.PIPE, "startupinfo":startupinfo, "bufsize":0,} # pipe output, hide console and unbuffered

appfont = ("ariel",14)

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

class Launcher(tk.Tk):
	def __init__(self):
		tk.Tk.__init__(self)
		self.title("Pip auto update launcher")
		self.style = ttk.Style()
		self.style.configure('.', font=appfont)
		tk.Label(self, text="Python version:")
		self.verbox = ttk.Combobox(self)
		self.verbox.pack(fill="x", expand=True)

		ttk.Button(self, text="Run", command=self.launch).pack(fill="x", expand=True)

		self.updater = None
		
		self.find_versions()

	def find_versions(self):
		versions = []
		for directory in os.listdir("C:\\"): # windows specific, need to find better way to find python installs
			if directory.lower().startswith("python"):
				ver = directory[6:] # get numbers from enf of python name
				if len(ver) == 2:
					version = "Python %s.%s" % (ver[0],ver[1])
					versions.append(version)
		self.verbox.configure(values=versions, state="readonly")

	def launch(self):
		i = self.verbox.current()
		if i != -1: # if there is a selection
			version = self.verbox.get()[7:]
			if not self.updater:
				self.updater = Updater(self, version)
			else:
				messagebox.showerror("Error", "Can only run one update task as a time", parent=self)

class Updater(tk.Toplevel):
	def __init__(self, parent, version):
		tk.Toplevel.__init__(self, parent)
		self.parent = parent
		self.title("Pip auto updater - Python %s" % version)
		self.version = version
		vercheck = str(int(float(version) * 10))
		
		tk.Label(self, text="Exclusions:").grid(column=1, row=1, sticky="nesw")
		self.excl_list = tk.Listbox(self)
		self.excl_list.grid(column=1, row=2, sticky="nesw")
		
		tk.Label(self, text="Outdated:").grid(column=2, row=1, sticky="nesw")
		self.pkglist = tk.Listbox(self)
		self.pkglist.grid(column=2, row=2, sticky="nesw")

		self.output = scrolledtext.ScrolledText(self, state="disabled")
		self.output.tag_config("output", foreground="blue")
		self.output.tag_config("stderr", foreground="red")
		self.output.grid(column=3, row=2, columnspan=2, sticky="nesw")
		
		self.link_man = HyperlinkManager(self.output)

		self.grid_rowconfigure(2, weight=1)
		self.grid_columnconfigure(1, weight=1)
		self.grid_columnconfigure(2, weight=1)
		self.grid_columnconfigure(3, weight=5)
		self.grid_columnconfigure(4, weight=5)
		
		f = tk.Frame(self)
		f.grid(column=1, row=3, columnspan=2, rowspan=2, sticky="nesw")
		f.grid_columnconfigure(1, weight=1)
		self.search_box = tk.Entry(f)
		self.search_box.bind("<Return>", self.search)
		self.search_box.grid(column=1, row=1, sticky="nesw")
		self.b4 = ttk.Button(f, text="Search", command=self.search, width=6)
		self.b4.grid(column=2, row=1, sticky="nesw")

		self.b1 = ttk.Button(self, text="Scan", command=self.scan)
		self.b1.grid(column=3, row=3, columnspan=2, sticky="nesw")
		
		self.b2 = ttk.Button(self, text="Update Pip", command=self.update_pip)
		self.b2.grid(column=3, row=4, sticky="nesw")
		self.b3 = ttk.Button(self, text="Update All", command=self.update_all)
		self.b3.grid(column=4, row=4, sticky="nesw")
		
		# popups for managing exclusions
		self.popup_add = tk.Menu(self.pkglist, tearoff=0)
		self.popup_add.add_command(label="add to exclusion list", command=self.add_exclusion)
		self.popup_remove = tk.Menu(self.pkglist, tearoff=0)
		self.popup_remove.add_command(label="remove from exclusion list", command=self.remove_exclusion)
		self.pkglist.bind("<Button-3>", self.show_popup_add)
		self.excl_list.bind("<Button-3>", self.show_popup_remove)
		
		# windows specific, should fix this...
		# find the python installations scripts directory
		self.pypath = None
		for directory in os.listdir("C:\\"):
			if directory.lower().startswith("python"):
				if directory.endswith(vercheck):
					self.pypath = os.path.join("C:\\", directory, "scripts")
					break
		if not self.pypath:
			messagebox.showerror("Error", "Python version %s cannot be found" % version, parent=self)
			return
		
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
		self.b1.configure(state="disabled")
		self.b2.configure(state="disabled")
		self.b3.configure(state="disabled")
		self.b4.configure(state="disabled")
		self.search_box.configure(state="disabled")

	def enable_all(self):
		self.b1.configure(state="normal")
		self.b2.configure(state="normal")
		self.b3.configure(state="normal")
		self.b4.configure(state="normal")
		self.search_box.configure(state="normal")

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
				output = data.decode('utf8')#.replace('\r','')
				if output != '':
					output = output.replace('\r', '')
					if self.func[0] == 1:
						self.log(output, 'output')
						if output == '\n':
							pkgname = line.split(' ', 1)[0] # strip package name from start of line
							if (len(pkgname) > 0) and (pkgname != 'Package') and (pkgname.replace('-','') != ''):
								self.pkglist.insert("end", pkgname) # add to package list
							line = ''
						else:
							line += output
					elif self.func[0] == 4:
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
		if self.func[0] == 3:
			for num in range(0, self.pkglist.size()):
				if self.pkglist.get(num) == self.func[1]:
					self.pkglist.delete(num)
					break
			self.after(10, self.update_all)
		self.func = None
		self.enable_all()
		
	def search(self, event=None):
		if not self.func:
			command = "%s search %s" % (os.path.join(self.pypath, "pip"), self.search_box.get())
			self.log(">%s\n" % command)
			self.process = subprocess.Popen(command, cwd=self.pypath, **procargs)
			self.func = [4, None]
			self.start_poll()
		else: # shouldn't happen, but cover it anyway
			messagebox.showinfo("Wait", "Must wait for previous command to finish before running new one", parent=self)
			
	def install(self, package):
		if not self.func:
			result = messagebox.askyesno("Install?", "Install package: %s" % package, parent=self)
			if result:
				print("Install")
				command = "%s install %s" % (os.path.join(self.pypath, "pip"), package)
				self.log(">%s\n" % command)
				self.process = subprocess.Popen(command, cwd=self.pypath, **procargs)
				self.func = [5, None]
				self.start_poll()

	def scan(self):
		if not self.func:
			command = "%s list --outdated --format=columns" % (os.path.join(self.pypath, "pip"),)
			self.log(">%s\n" % command)
			self.process = subprocess.Popen(command, cwd=self.pypath, **procargs)
			self.func = [1, None]
			self.pkglist.delete(0,"end")
			self.start_poll()
		else: # shouldn't happen, but cover it anyway
			messagebox.showinfo("Wait", "Must wait for previous command to finish before running new one", parent=self)

	def update_pip(self):
		if not self.func:
			command = "py -%s -m pip install --upgrade pip" % self.version
			self.log(">%s\n" % command)
			self.process = subprocess.Popen(command, **procargs)
			self.func = [2, 'pip']
			self.start_poll()
			for num in range(0, self.pkglist.size()):
				if self.pkglist.get(num) == "pip":
					self.pkglist.delete(num)
					break
		else: # shouldn't happen, but cover it anyway
			messagebox.showinfo("Wait", "Must wait for previous command to finish before running new one", parent=self)

	def update_all(self):
		if not self.func:
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
					#i += 1
				elif i >= self.pkglist.size():
					return
				else:
					break
			command = "%s install %s --upgrade" % (os.path.join(self.pypath, "pip.exe"), pkg)
			self.log(">%s\n" % command)
			self.process = subprocess.Popen(command, **procargs)
			self.func = [3, pkg]
			self.start_poll()
		else: # shouldn't happen, but cover it anyway
			messagebox.showinfo("Wait", "Must wait for previous command to finish before running new one", parent=self)

	def destroy(self):
		self.save_exclusions()
		self.parent.updater = None
		tk.Toplevel.destroy(self)

if __name__ == "__main__":
	launcher = Launcher()
	launcher.mainloop()
