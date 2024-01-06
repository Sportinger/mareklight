import threading
from PIL import Image
import pystray
from pystray import MenuItem as item
import subprocess
import tkinter as tk
from tkinter import simpledialog
import time

# Create and hide the root window immediately
root = tk.Tk()
root.withdraw()

PING_INTERVAL = 60  # Time between pings in seconds
update_lock = threading.Lock() 

def ping_ip(ip_address):
    try:
        # Set creationflags to CREATE_NO_WINDOW to suppress the console window
        process = subprocess.run(["ping", "-n", "1", "-w", "1000", ip_address[0]],
                                 capture_output=True, text=True, encoding='cp850',
                                 timeout=2, creationflags=subprocess.CREATE_NO_WINDOW)
        output = process.stdout
        if "TTL=" in output:
            return True, output
        else:
            return False, output
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        return False, e.output if e.output else ""

def create_image(color):
    # Create an image with given background color
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), color)
    return image

def flash_icon_blue(icon):
    with update_lock:
        original_icon = icon.icon
        icon.icon = create_image('blue')
        time.sleep(0.5)
        icon.icon = original_icon

def update_tray_icon(icon, ip_address, running):
    while running[0]:
        flash_icon_blue(icon)
        success, _ = ping_ip(ip_address)
        color = 'green' if success else 'red'
        icon.icon = create_image(color)
        time.sleep(PING_INTERVAL)

def set_ip(icon, ip_address, running):
    # Use the hidden root window for the dialog
    new_ip = simpledialog.askstring("Enter IP", "Enter new IP address:", parent=root, initialvalue=ip_address[0])
    if new_ip:
        ip_address[0] = new_ip
        flash_icon_blue(icon)



def update_interval(new_interval):
    global PING_INTERVAL
    PING_INTERVAL = new_interval

def create_tray_icon(ip_address, running):
    # Define a function to update the menu dynamically
    def update_menu():
        return pystray.Menu(
            item('Update Interval', interval_menu),
            item(f'Enter IP (Current: {ip_address[0]})', lambda: set_ip(icon, ip_address, running)),  # Display the current IP in the menu
            item('Exit', exit_program)  # Add an exit option to the menu
        )

    def exit_program():
        running[0] = False
        icon.stop()

    interval_menu = pystray.Menu(
        item('1 sec', lambda: update_interval(1)),
        item('10 sec', lambda: update_interval(10)),
        item('1 min', lambda: update_interval(60)),
        item('10 min', lambda: update_interval(600))
    )
    icon = pystray.Icon("mareklight", create_image('red'), "mareklight", menu=update_menu())  # Use update_menu function
    update_thread = threading.Thread(target=update_tray_icon, args=(icon, ip_address, running))
    update_thread.start()
    icon.run()
    update_thread.join()

if __name__ == "__main__":
    ip_address = ['192.168.146.139']  # Use a list to allow modification
    running = [True]
    try:
        create_tray_icon(ip_address, running)
    finally:
        running[0] = False