import os
import tkinter as tk
import subprocess

PING_INTERVAL = 6  # Time between pings in seconds

def ping_ip(ip_address):
    try:
        output = subprocess.check_output("ping -n 1 -w 500 " + ip_address, shell=True, stderr=subprocess.STDOUT)
        return True, output.decode(errors='replace')
    except subprocess.CalledProcessError as e:
        return False, e.output.decode(errors='replace')

def update_window_color(window, ip_address, message_widget):
    success, output = ping_ip(ip_address)
    if success:
        window.config(bg='red')
        message_widget.config(state='normal')
        message_widget.insert(tk.END, output)
        message_widget.config(state='disabled')
    else:
        window.config(bg='green')
        message_widget.config(state='normal')
        message_widget.insert(tk.END, output)
        message_widget.config(state='disabled')
    window.after(2000, lambda: clear_message_widget(message_widget))  # Clear message after 2 seconds
    if window.timer_id is not None:
        window.after_cancel(window.timer_id)  # Cancel the previous timer
    window.timer_id = window.after(PING_INTERVAL * 1000, lambda: update_window_color(window, ip_address, message_widget))  # Set a new timer

def update_countdown(label):
    countdown = int(label.cget("text"))
    countdown -= 1
    label.config(text=str(countdown))
    if countdown > 0:
        label.after(1000, lambda: update_countdown(label))  # Update countdown every second
    else:
        label.config(text=str(PING_INTERVAL))  # Reset countdown when it runs out
        label.after(1000, lambda: update_countdown(label))  # Start countdown again

def create_window(ip_address):
    window = tk.Tk()
    window.title('mareklight')  # Set window title
    window.geometry('200x200')
    window.timer_id = None  # Initialize timer_id
    message_widget = tk.Text(window, height=2, width=30)
    message_widget.pack(side='top')
    update_window_color(window, ip_address, message_widget)
    countdown_label = tk.Label(window, text=str(PING_INTERVAL), bg=window.cget('bg'))
    countdown_label.pack(side='bottom', anchor='w')
    update_countdown(countdown_label)
    window.mainloop()

if __name__ == "__main__":
    ip_address = '192.168.145.20'  # Replace with your IP address
    create_window(ip_address)