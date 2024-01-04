import os
import tkinter as tk

def ping_ip(ip_address):
    response = os.system("ping -n 1 " + ip_address)
    if response == 0:
        return True
    else:
        return False

def update_window_color(window, ip_address):
    if ping_ip(ip_address):
        window.config(bg='red')
    else:
        window.config(bg='green')

def create_window(ip_address):
    window = tk.Tk()
    window.geometry('200x200')
    update_window_color(window, ip_address)
    window.after(1000, lambda: update_window_color(window, ip_address))  # Update color every second
    window.mainloop()

if __name__ == "__main__":
    ip_address = '8.8.8.8'  # Replace with your IP address
    create_window(ip_address)