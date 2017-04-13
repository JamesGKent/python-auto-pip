#!python3

try:
	import tkinter as tk
	from tkinter import ttk, messagebox
	from tkinter import scrolledtext
except ImportError:
	import Tkinter as tk
	import ttk
	import tkMessageBox as messagebox
	from Tkinter import ScrolledText as scrolledtext
	
import sys, os
import subprocess

startupinfo = subprocess.STARTUPINFO()
startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW # to hide the console

procargs = {"stdout":subprocess.PIPE, "startupinfo":startupinfo, "bufsize":0,} # pipe output, hide console and unbuffered

appfont = ("ariel",14)

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
				messagebox.showerror("Error", "Can only run one update task as a time")

class Updater(tk.Toplevel):
	def __init__(self, parent, version):
		tk.Toplevel.__init__(self, parent)
		self.parent = parent
		self.title("Pip auto updater - Python %s" % version)
		self.version = version
		vercheck = str(int(float(version) * 10))

		self.pkglist = tk.Listbox(self)
		self.pkglist.grid(column=1, row=1, sticky="nesw")

		self.output = scrolledtext.ScrolledText(self, state="disabled")
		self.output.tag_config("output", foreground="blue")
		self.output.grid(column=2, row=1, sticky="nesw")

		self.grid_rowconfigure(1, weight=1)
		self.grid_columnconfigure(1, weight=1)
		self.grid_columnconfigure(2, weight=1)

		self.b1 = ttk.Button(self, text="Scan", command=self.scan)
		self.b1.grid(column=1, row=2, columnspan=2, sticky="nesw")
		
		self.b2 = ttk.Button(self, text="Update Pip", command=self.update_pip)
		self.b2.grid(column=1, row=3, sticky="nesw")
		self.b3 = ttk.Button(self, text="Update All", command=self.update_all)
		self.b3.grid(column=2, row=3, sticky="nesw")
		
		# popup for managing exclusions
		self.popup_coords = None
		self.popup = tk.Menu(self.pkglist, tearoff=0)
		self.popup.add_command(label="add to exclusion list", command=self.add_exclusion)
		self.popup.add_command(label="remove from exclusion list", command=self.remove_exclusion)
		self.pkglist.bind("<Button-3>", self.show_popup)
		
		# windows specific, should fix this
		# find the python installations scripts directory
		self.pypath = None
		for directory in os.listdir("C:\\"):
			if directory.lower().startswith("python"):
				if directory.endswith(vercheck):
					self.pypath = os.path.join("C:\\", directory, "scripts")
					break
		if not self.pypath:
			messagebox.showerror("Error", "Python version %s cannot be found" % version)
			return
		
		# load any exclusions that shouldn't be updated
		self.exclusions = []
		self.exclusions_changed = False
		if os.path.isfile("pip_exclusions.txt"):
			with open("pip_exclusions.txt", mode="r") as exfile:
				for line in exfile.readlines():
					ex = line.rstrip()
					if ex != '':
						self.exclusions.append(ex)

		self.process = None
		self.func = None
		
	def show_popup(self, event): # for managing exclusions
		self.pkglist.select_clear(0,"end") #clear selection
		self.pkglist.select_set(self.pkglist.nearest(event.y - self.pkglist.winfo_y())) # highlight right clicked item
		self.popup.post(event.x_root, event.y_root) # show menu
		
	def add_exclusion(self):
		selection = self.pkglist.curselection()
		if len(selection) > 0:
			pkg = self.pkglist.get(selection[0])
			self.exclusions.append(pkg)
			self.exclusions_changed = True
		
	def remove_exclusion(self):
		selection = self.pkglist.curselection()
		if len(selection) > 0:
			pkg = self.pkglist.get(selection[0])
			self.exclusions.remove(pkg)
			self.exclusions_changed = True
			
	def save_exclusions(self):
		if (len(self.exclusions) > 0) or self.exclusions_changed: # only save if there are exclusions or changes made
			with open("pip_exclusions.txt", mode="w") as ex_file:
				self.exclusions.sort()
				for item in self.exclusions:
					ex_file.write("%s\n" % item)

	def disable_all(self):
		self.b1.configure(state="disabled")
		self.b2.configure(state="disabled")
		self.b3.configure(state="disabled")

	def enable_all(self):
		self.b1.configure(state="normal")
		self.b2.configure(state="normal")
		self.b3.configure(state="normal")

	def log(self, msg, tag=None):
		self.output.configure(state="normal")
		self.output.insert("end", msg, tag)
		self.output.see("end")
		self.output.configure(state="disabled")

	def poll(self):
		if not self.process: # if there is an active process
			return

		output = self.process.stdout.readline().decode('utf8').replace("\r","")
		if self.func[0] == 1: # if scanning for outdated packages
			self.log(output, "output")
			for line in output.split("\n"):
				data = line.split(" ", 1)[0] # strip package name from start of line
				if len(data) > 0:
					self.pkglist.insert("end", data) # add to package list
		elif self.func[0] == 2: # if updating pip
			self.log(output, "output")
			for num in range(0, self.pkglist.size()):
				if self.pkglist.get(num) == "pip":
					self.pkglist.delete(num)
					break
		elif self.func[0] == 3:
			self.log(output, "output")

		if self.process.poll() != None: # if process has terminated
			self.process = None
			if self.func[0] == 3:
				for num in range(0, self.pkglist.size()):
					if self.pkglist.get(num) == self.func[1]:
						self.pkglist.delete(num)
				self.after(10, self.update_all)
			self.func = None
			self.enable_all()
			return
		self.after(10, self.poll)

	def scan(self):
		if not self.func:
			command = "%s list --outdated" % (os.path.join(self.pypath, "pip"),)
			self.log(">%s\n" % command)
			self.process = subprocess.Popen(command, cwd=self.pypath, **procargs)
			self.func = [1, None]
			self.pkglist.delete(0,"end")
			self.disable_all()
			self.after(50, self.poll)
		else: # shouldn't happen, but cover it anyway
			messagebox.showinfo("Wait", "Must wait for previous command to finish before running new one")

	def update_pip(self):
		if not self.func:
			command = "py -%s -m pip install --upgrade pip" % self.version
			self.log(">%s\n" % command)
			self.process = subprocess.Popen(command, **procargs)
			self.func = [2, 'pip']
			self.disable_all()
			self.after(50, self.poll)
		else: # shouldn't happen, but cover it anyway
			messagebox.showinfo("Wait", "Must wait for previous command to finish before running new one")

	def update_all(self):
		if not self.func:
			if "pip" in self.pkglist.get(0,"end"):
				if messagebox.askyesno("Update pip?", "Pip is out of date.\nUpdate this now?"):
					self.update_pip()
				return
			if self.pkglist.size() == 0:
				return
			i = 0
			while True:
				pkg = self.pkglist.get(i)
				if pkg == "pip":
					i += 1
				elif pkg in self.exclusions:
					self.log(">Skipping %s\n" % pkg)
					i += 1
				elif i >= self.pkglist.size():
					return
				else:
					break
			command = "%s install %s --upgrade" % (os.path.join(self.pypath, "pip.exe"), pkg)
			self.log(">%s\n" % command)
			self.process = subprocess.Popen(command, **procargs)
			self.func = [3, pkg]
			self.disable_all()
			self.after(50, self.poll)
		else: # shouldn't happen, but cover it anyway
			messagebox.showinfo("Wait", "Must wait for previous command to finish before running new one")

	def destroy(self):
		self.save_exclusions()
		self.parent.updater = None
		tk.Toplevel.destroy(self)

if __name__ == "__main__":
	launcher = Launcher()
	launcher.mainloop()
